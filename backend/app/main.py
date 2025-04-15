from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import numpy as np
from numba import njit
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from .database import get_db, Base, SessionLocal
from .models import User, Trade, Algorithm, Position, PositionStatus, TradeStatus, Signal, AlgorithmType, SignalType, TradeType
from .services.alpaca_service import AlpacaService
from .services.algorithm_service import AlgorithmService
from .services.automated_trading_service import AutomatedTradingService
from .services.auth_service import AuthService
from .services.data_service import DataService
from .services.backup_service import BackupService

load_dotenv()

# --- Initialize Services (Singletons) ---
# This block MUST come before the dependency injectors below
try:
    GLOBAL_ALPACA_SERVICE = AlpacaService() 
    GLOBAL_DATA_SERVICE = DataService(GLOBAL_ALPACA_SERVICE)
    GLOBAL_ALGORITHM_SERVICE = AlgorithmService(GLOBAL_DATA_SERVICE, GLOBAL_ALPACA_SERVICE)
    GLOBAL_AUTOMATED_TRADING_SERVICE = AutomatedTradingService(
        GLOBAL_ALGORITHM_SERVICE, GLOBAL_ALPACA_SERVICE, SessionLocal 
    )
    print("--- Global services initialized successfully ---")
except Exception as e:
    print(f"!!! FATAL: Failed to initialize global services: {e!r}")
    GLOBAL_ALPACA_SERVICE = None
    GLOBAL_DATA_SERVICE = None
    GLOBAL_ALGORITHM_SERVICE = None
    GLOBAL_AUTOMATED_TRADING_SERVICE = None

GLOBAL_BACKUP_SERVICE = BackupService("trading.db")

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI(title="Trading Algorithm API")
print("--- FastAPI app object created ---")

# Add CORS middleware with proper configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Pydantic models
class UserCreate(BaseModel):
    email: str
    password: str

class UserRead(BaseModel):
    id: int
    email: str

    class Config:
        orm_mode = True

class TradeRequest(BaseModel):
    symbol: str
    quantity: float = Field(..., gt=0)
    side: str = Field(..., pattern="^(buy|sell)$")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class TradeRead(BaseModel):
    id: int
    symbol: str
    quantity: float
    price: Optional[float] = None
    side: str
    status: str
    order_id: str
    created_at: datetime

    class Config:
        orm_mode = True

class UserResponse(BaseModel):
    email: str
    is_active: bool

    class Config:
        from_attributes = True

# Add Pydantic model for Dashboard Stats
class DashboardStats(BaseModel):
    user_email: str
    algorithm_count: int
    open_position_count: int
    recent_trade_count: int
    account_equity: Optional[float] = None
    account_buying_power: Optional[float] = None

# Define AlgorithmStatusUpdate *before* it is used
class AlgorithmStatusUpdate(BaseModel):
    is_active: bool

# Authentication functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    return user

# Define new Input model for automated algo run
class AutoAlgoInput(BaseModel):
    symbol: str
    # Use strings for timeframe representation from user input
    timeframe_unit: str = Field("Day", pattern="^(Minute|Hour|Day)$")
    timeframe_value: int = Field(1, gt=0)
    lookback_days: int = Field(60, gt=0) # How many days of data to fetch
    short_window: int = Field(10, gt=0)
    long_window: int = Field(20, gt=0)

@njit
def calculate_moving_averages(prices: np.ndarray, short_window: int, long_window: int):
    short_ma = np.zeros_like(prices)
    long_ma = np.zeros_like(prices)
    
    for i in range(len(prices)):
        if i >= short_window - 1:
            short_ma[i] = np.mean(prices[i - short_window + 1:i + 1])
        if i >= long_window - 1:
            long_ma[i] = np.mean(prices[i - long_window + 1:i + 1])
    
    return short_ma, long_ma

@njit
def generate_signals(short_ma: np.ndarray, long_ma: np.ndarray):
    signals = np.zeros_like(short_ma)
    
    for i in range(1, len(signals)):
        # Generate signals based on current MA positions
        if short_ma[i] > long_ma[i]:
            signals[i] = 1  # Buy signal when short MA is above long MA
        elif short_ma[i] < long_ma[i]:
            signals[i] = -1  # Sell signal when short MA is below long MA
        # HOLD (0) when MAs are equal (rare case)
    
    return signals

# Load standard Alpaca config from environment
# Recommended names: APCA_API_KEY_ID, APCA_API_SECRET_KEY
APCA_API_KEY_ID = os.getenv("APCA_API_KEY_ID") 
APCA_API_SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")
PAPER_TRADING = os.getenv("PAPER_TRADING", "true").lower() == "true"

# Remove or comment out the Broker API specific key loading
# CENTRAL_ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
# CENTRAL_ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
# CENTRAL_ALPACA_PAPER_TRADING = os.getenv("ALPACA_PAPER_TRADING", "true").lower() == "true"

if not APCA_API_KEY_ID or not APCA_API_SECRET_KEY:
    print("WARNING: Standard Alpaca API Key ID/Secret not configured in environment!")

# --- Service Dependency Injectors --- 
# Defined AFTER global variables are initialized
def get_alpaca_service():
    if GLOBAL_ALPACA_SERVICE is None:
        raise HTTPException(status_code=503, detail="Alpaca Service not available")
    return GLOBAL_ALPACA_SERVICE

def get_data_service(): 
    if GLOBAL_DATA_SERVICE is None:
         raise HTTPException(status_code=503, detail="Data Service not available")
    return GLOBAL_DATA_SERVICE

def get_algorithm_service(): 
    if GLOBAL_ALGORITHM_SERVICE is None:
         raise HTTPException(status_code=503, detail="Algorithm Service not available")
    return GLOBAL_ALGORITHM_SERVICE

def get_automated_trading_service(): 
    if GLOBAL_AUTOMATED_TRADING_SERVICE is None:
         raise HTTPException(status_code=503, detail="Automated Trading Service not available")
    return GLOBAL_AUTOMATED_TRADING_SERVICE

def get_backup_service():
    return GLOBAL_BACKUP_SERVICE

def get_auth_service(db: Session = Depends(get_db)):
    return AuthService(db)

# Add new models for automated trading
class AutomatedTradingConfig(BaseModel):
    # Make config fields optional as they are mainly needed for starting
    position_size: Optional[float] = None # Percentage of buying power to use per trade (0.0 to 1.0)
    max_loss_percent: Optional[float] = None # Maximum loss percentage before stopping (0.0 to 1.0)
    is_active: bool  # This remains required

class TradingStatus(BaseModel):
    is_active: bool
    current_position: Optional[Dict] = None
    last_trade_time: Optional[datetime] = None
    pnl: Optional[float] = None
    config: Optional[Dict] = None

# Add backup-related models
class BackupInfo(BaseModel):
    path: str
    size: int
    created_at: datetime
    algorithm_count: int
    signal_count: int
    position_count: int
    trade_count: int

class BackupList(BaseModel):
    backups: List[BackupInfo]

@app.post("/register", response_model=UserResponse)
def register(user: UserCreate, auth_service: AuthService = Depends(get_auth_service)):
    try:
        db_user = auth_service.create_user(user.email, user.password)
        return UserResponse(email=db_user.email, is_active=db_user.is_active)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), auth_service: AuthService = Depends(get_auth_service)):
    user = auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = auth_service.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/place-order")
async def place_order(
    trade_request: TradeRequest,
    alpaca_service: AlpacaService = Depends(get_alpaca_service),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    user_id = None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        db_user = db.query(User).filter(User.email == email).first()
        if db_user:
            user_id = db_user.id
            print(f"--- Placing order on behalf of user ID: {user_id} ({email}) ---")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if not APCA_API_KEY_ID or not APCA_API_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Alpaca paper trading credentials not configured on server.")
    
    try:
        order_result = await alpaca_service.place_order(
            trade_request.symbol,
            trade_request.quantity,
            trade_request.side
        )
        
        if user_id:
            order_id_from_alpaca = order_result.get("order_id")
            status_from_alpaca = order_result.get("status")
            trade = Trade(
                user_id=user_id, 
                symbol=trade_request.symbol,
                quantity=trade_request.quantity,
                price=order_result.get("filled_avg_price"),
                side=trade_request.side,
                status=status_from_alpaca.value if hasattr(status_from_alpaca, 'value') else str(status_from_alpaca),
                order_id=str(order_id_from_alpaca) if order_id_from_alpaca else None
            )
            print(f"--- Preparing to save trade with order_id (str): {trade.order_id} ---")
            db.add(trade)
            db.commit()
            print("--- Trade saved successfully ---")
        else:
             print("Warning: Could not associate trade with a user.")
        
        return order_result
    except Exception as e:
        # Log the original exception from AlpacaService
        print(f"!!! Exception during alpaca_service.place_order: {e!r}") 
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/trade-status/{order_id}")
async def get_trade_status(
    order_id: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    user_id = None 
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        db_user = db.query(User).filter(User.email == email).first()
        if db_user:
            user_id = db_user.id
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    trade = db.query(Trade).filter(Trade.order_id == order_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found in database")
    
    if not APCA_API_KEY_ID or not APCA_API_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Alpaca paper trading credentials not configured on server.")
    
    alpaca_service = AlpacaService(
        APCA_API_KEY_ID,
        APCA_API_SECRET_KEY,
        paper=PAPER_TRADING
    )
    
    try:
        order_status = await alpaca_service.get_order_status(order_id)
        trade.status = order_status.get("status", trade.status)
        trade.price = order_status.get("filled_avg_price", trade.price)
        db.commit()
        
        return order_status
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/account-info")
async def get_account_info(
    token: str = Depends(oauth2_scheme)
):
    if not APCA_API_KEY_ID or not APCA_API_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Alpaca paper trading credentials not configured on server.")
    
    alpaca_service = AlpacaService(
        APCA_API_KEY_ID,
        APCA_API_SECRET_KEY,
        paper=PAPER_TRADING
    )
    
    try:
        print("--- Attempting to fetch central Alpaca account info ---")
        account_info = await alpaca_service.get_account_info()
        print("--- Successfully fetched central Alpaca account info ---")
        return account_info
    except Exception as e:
        print(f"!!! Exception during AlpacaService.get_account_info: {e!r}") # Log the raw exception
        # Optionally, check the type of e for more specific Alpaca errors
        # For now, re-raise with the original error string
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/run-algo")
async def run_automated_algorithm(
    input_data: AutoAlgoInput,
    token: str = Depends(oauth2_scheme)
):
    print(f"--- Running automated algo for symbol: {input_data.symbol} ---")
    # Instantiate Alpaca Service
    if not APCA_API_KEY_ID or not APCA_API_SECRET_KEY:
         raise HTTPException(status_code=500, detail="Alpaca credentials not configured on server.")
    alpaca_service = AlpacaService()  # Use environment variables

    try:
        # Convert timeframe to string format expected by alpaca_trade_api
        timeframe_map = {
            "Minute": "1Min",
            "Hour": "1H",
            "Day": "1D"
        }
        if input_data.timeframe_unit not in timeframe_map:
             raise ValueError("Invalid timeframe unit")
        
        # Create timeframe string (e.g., "1D", "1H", "1Min")
        timeframe = timeframe_map[input_data.timeframe_unit]

        # Fetch historical prices
        prices = await alpaca_service.get_historical_bars(
            symbol=input_data.symbol,
            timeframe=timeframe,
            lookback_days=input_data.lookback_days
        )
        
        # Validate windows against fetched data length
        if input_data.short_window >= input_data.long_window:
            raise ValueError("Short window must be less than long window")
        if len(prices) < input_data.long_window:
            raise ValueError(f"Not enough price data ({len(prices)}) for the long window ({input_data.long_window}). Try increasing lookback_days.")

        # Convert prices to numpy array
        prices_np = np.array(prices)
        
        # Calculate moving averages
        short_ma, long_ma = calculate_moving_averages(
            prices_np, 
            input_data.short_window, 
            input_data.long_window
        )
        
        # Generate signals
        signals = generate_signals(short_ma, long_ma)
        
        # Get latest signal
        latest_signal = signals[-1] if len(signals) > 0 else 0
        print(f"--- Latest signal for {input_data.symbol}: {latest_signal} ---")

        # Return results
        return {
            "symbol": input_data.symbol,
            "latest_signal": latest_signal,
            "num_prices": len(prices),
            "short_ma_last": short_ma[-1] if len(short_ma) > 0 else None,
            "long_ma_last": long_ma[-1] if len(long_ma) > 0 else None
        }
        
    except ValueError as e:
        print(f"!!! Value Error in run_automated_algorithm: {e!r}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"!!! Exception in run_automated_algorithm: {e!r}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"An error occurred running algorithm: {e!r}")

@app.get("/test-db")
async def test_db_endpoint(db: Session = Depends(get_db)):
    print("--- Entering /test-db endpoint ---")
    # We don't need to do anything with db, just check if get_db runs
    return {"message": "DB dependency resolution seems okay"}

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(AuthService(get_db()).get_current_user)):
    return UserResponse(email=current_user.email, is_active=current_user.is_active)

@app.get("/trades", response_model=List[TradeRead])
async def read_user_trades(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    print(f"--- Fetching trades for user: {current_user.email} ---")
    trades = db.query(Trade).filter(Trade.user_id == current_user.id).order_by(Trade.created_at.desc()).all()
    return trades 

@app.delete("/trades/{trade_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trade(
    trade_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    print(f"--- Attempting to delete trade ID: {trade_id} for user: {current_user.email} ---")
    trade = db.query(Trade).filter(Trade.id == trade_id).first()

    # Check if trade exists
    if not trade:
        print(f"--- Trade ID: {trade_id} not found ---")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found")

    # Check if the trade belongs to the current user
    if trade.user_id != current_user.id:
        print(f"--- User {current_user.email} not authorized to delete trade ID: {trade_id} ---")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this trade")

    db.delete(trade)
    db.commit()
    print(f"--- Trade ID: {trade_id} deleted successfully ---")
    # No content needs to be returned for a successful DELETE
    return 

@app.get("/orders/open")
async def read_open_orders(
    token: str = Depends(oauth2_scheme)
):
    if not APCA_API_KEY_ID or not APCA_API_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Alpaca credentials not configured on server.")
    
    alpaca_service = AlpacaService(
        APCA_API_KEY_ID,
        APCA_API_SECRET_KEY,
        paper=PAPER_TRADING
    )
    try:
        print("--- Fetching open orders via service ---")
        open_orders = await alpaca_service.get_open_orders()
        return open_orders
    except Exception as e:
        # Handle exceptions raised by the service
        # The service already logs details, re-raise or return specific error
        if isinstance(e, HTTPException):
             raise e # Re-raise FastAPI exceptions directly
        else:
             raise HTTPException(status_code=500, detail=f"Failed to get open orders: {e!r}")

@app.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_order_endpoint(
    order_id: str,
    token: str = Depends(oauth2_scheme)
):
    if not APCA_API_KEY_ID or not APCA_API_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Alpaca credentials not configured on server.")
    
    alpaca_service = AlpacaService(
        APCA_API_KEY_ID,
        APCA_API_SECRET_KEY,
        paper=PAPER_TRADING
    )
    try:
        print(f"--- Cancelling order {order_id} via service ---")
        await alpaca_service.cancel_order(order_id)
        # No content returned on successful delete
        return 
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e # Re-raise exceptions from service (e.g., 404 if order not found)
        else:
            raise HTTPException(status_code=500, detail=f"Failed to cancel order: {e!r}") 

@app.post("/api/automated-trading/config")
async def configure_automated_trading(
    config: AutomatedTradingConfig, 
    trading_service: AutomatedTradingService = Depends(get_automated_trading_service)
):
    """Configure and start/stop automated trading."""
    try:
        if config.is_active:
            await trading_service.start_trading({
                "position_size": config.position_size,
                "max_loss_percent": config.max_loss_percent
            })
        else:
            trading_service.stop_trading()
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/automated-trading/status")
async def get_trading_status(
    trading_service: AutomatedTradingService = Depends(get_automated_trading_service)
):
    """Get current automated trading status."""
    try:
        status = trading_service.get_status()
        return TradingStatus(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add backup endpoints
@app.post("/api/backup/create", response_model=BackupInfo)
async def create_backup(current_user: User = Depends(get_current_user)):
    """Create a new database backup."""
    try:
        backup_path = GLOBAL_BACKUP_SERVICE.create_backup()
        info = GLOBAL_BACKUP_SERVICE.get_backup_info(backup_path)
        return BackupInfo(**info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/backup/restore/{backup_path:path}")
async def restore_backup(
    backup_path: str,
    current_user: User = Depends(get_current_user)
):
    """Restore database from a backup."""
    try:
        GLOBAL_BACKUP_SERVICE.restore_backup(backup_path)
        return {"message": f"Database restored from backup: {backup_path}"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Backup file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/backup/list", response_model=BackupList)
async def list_backups(current_user: User = Depends(get_current_user)):
    """List all available backups."""
    try:
        backups = GLOBAL_BACKUP_SERVICE.list_backups()
        backup_info = [BackupInfo(**GLOBAL_BACKUP_SERVICE.get_backup_info(backup)) for backup in backups]
        return BackupList(backups=backup_info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/backup/cleanup")
async def cleanup_backups(
    keep_last_n: int = 5,
    current_user: User = Depends(get_current_user)
):
    """Cleanup old backups, keeping only the specified number of most recent ones."""
    try:
        GLOBAL_BACKUP_SERVICE.cleanup_old_backups(keep_last_n)
        return {"message": f"Cleanup completed. Kept the {keep_last_n} most recent backups."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/backup/info/{backup_path:path}", response_model=BackupInfo)
async def get_backup_info(
    backup_path: str,
    current_user: User = Depends(get_current_user)
):
    """Get information about a specific backup."""
    try:
        info = GLOBAL_BACKUP_SERVICE.get_backup_info(backup_path)
        return BackupInfo(**info)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Backup file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    alpaca_service: AlpacaService = Depends(get_alpaca_service)
):
    """Endpoint to fetch aggregated dashboard statistics for the current user."""
    try:
        print(f"--- Fetching dashboard stats for user: {current_user.email} ({current_user.id}) ---")

        # Fetch data from database
        algo_count = db.query(Algorithm).filter(Algorithm.user_id == current_user.id).count()
        open_pos_count = db.query(Position).filter(
            Position.user_id == current_user.id,
            Position.status == PositionStatus.OPEN # Use the enum member
        ).count()
        
        one_day_ago = datetime.utcnow() - timedelta(days=1)
        recent_trades_count = db.query(Trade).filter(
            Trade.user_id == current_user.id,
            Trade.created_at >= one_day_ago
        ).count()

        # Fetch data from Alpaca
        account_equity = None
        account_buying_power = None
        try:
            account_info = await alpaca_service.get_account_info()
            account_equity = float(account_info.get("equity", 0.0))
            account_buying_power = float(account_info.get("buying_power", 0.0))
            print(f"--- Fetched Alpaca account info for dashboard: Equity={account_equity}, Buying Power={account_buying_power} ---")
        except Exception as alpaca_error:
            print(f"!!! Warning: Could not fetch Alpaca account info for dashboard: {alpaca_error!r}")
            # Decide if this should be a hard error or just return None for these fields
            # For now, we'll allow the request to succeed with missing Alpaca data

        stats = DashboardStats(
            user_email=current_user.email,
            algorithm_count=algo_count,
            open_position_count=open_pos_count,
            recent_trade_count=recent_trades_count,
            account_equity=account_equity,
            account_buying_power=account_buying_power
        )
        print(f"--- Returning dashboard stats: {stats} ---")
        return stats

    except Exception as e:
        print(f"!!! Error fetching dashboard stats for user {current_user.email}: {e!r}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch dashboard statistics"
        ) 

class PositionRead(BaseModel):
    id: int
    symbol: str
    quantity: float
    entry_price: float
    current_price: float # Maybe fetch this live?
    status: PositionStatus
    entry_time: datetime
    last_updated: datetime
    additional_data: Optional[Dict] = None
    # Maybe add calculated PnL here later

    class Config:
        from_attributes = True
        use_enum_values = True # Ensure enums are serialized as strings

class PortfolioBalance(BaseModel):
    balance: Optional[float] = None
    equity: Optional[float] = None
    buying_power: Optional[float] = None

# Add model for portfolio history data points
class PortfolioHistoryPoint(BaseModel):
    date: str # Or datetime, depending on source
    equity: float

@app.get("/api/positions", response_model=List[PositionRead])
async def get_user_positions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch all positions for the current user."""
    print(f"--- Fetching positions for user: {current_user.email} ({current_user.id}) ---")
    positions = db.query(Position).filter(Position.user_id == current_user.id).all()
    # TODO: Potentially update current_price here from a live data feed
    return positions

@app.get("/api/portfolio/balance", response_model=PortfolioBalance)
async def get_portfolio_balance(
    current_user: User = Depends(get_current_user),
    alpaca_service: AlpacaService = Depends(get_alpaca_service)
):
    """Fetch portfolio balance/equity from Alpaca."""
    print(f"--- Fetching portfolio balance for user: {current_user.email} ({current_user.id}) ---")
    balance = None
    equity = None
    buying_power = None
    try:
        account_info = await alpaca_service.get_account_info()
        # Adjust keys based on actual Alpaca response if necessary
        equity = float(account_info.get("equity", 0.0))
        buying_power = float(account_info.get("buying_power", 0.0))
        balance = float(account_info.get("cash", 0.0)) # Assuming 'cash' represents balance
        print(f"--- Fetched Alpaca account info for portfolio: Equity={equity}, Buying Power={buying_power}, Balance={balance} ---")
    except Exception as alpaca_error:
        print(f"!!! Warning: Could not fetch Alpaca account info for portfolio: {alpaca_error!r}")
        # Return nulls if fetch fails
    
    return PortfolioBalance(balance=balance, equity=equity, buying_power=buying_power) 

# Add endpoint for portfolio history
@app.get("/api/portfolio/history", response_model=List[PortfolioHistoryPoint])
async def get_portfolio_history(
    # Add query parameters for period/timeframe if desired
    period: str = "1M", # Default period
    # timeframe: Optional[str] = None, # Optional timeframe
    current_user: User = Depends(get_current_user),
    alpaca_service: AlpacaService = Depends(get_alpaca_service)
):
    """Fetch historical portfolio equity data."""
    print(f"--- Fetching portfolio history for user: {current_user.email}, period: {period} ---")
    
    try:
        # Call the service method
        history_data = await alpaca_service.get_portfolio_history(period=period) # Add timeframe if needed

        # Log the data received from the service
        print(f"--- History data received from service: {history_data!r} ---")

        if history_data is None:
             # Handle case where service returned None (e.g., API error)
             print("--- Alpaca service returned no history data ---")
             return [] # Return empty list or raise appropriate HTTP error
        
        # Process the response from Alpaca SDK model into our Pydantic model
        processed_history: List[PortfolioHistoryPoint] = []
        if history_data.timestamp and history_data.equity:
            for ts, eq in zip(history_data.timestamp, history_data.equity):
                # Convert timestamp (assuming seconds epoch) to ISO string or desired format
                dt_object = datetime.fromtimestamp(ts)
                date_str = dt_object.strftime("%Y-%m-%d") # Or %Y-%m-%dT%H:%M:%S for more precision
                processed_history.append(PortfolioHistoryPoint(date=date_str, equity=eq))
            
            print(f"--- Processed {len(processed_history)} history points ---")
            return processed_history
        else:
            print("--- Alpaca history data missing timestamps or equity points ---")
            return []
            
    except Exception as e:
       print(f"!!! Error processing portfolio history request: {e!r}")
       # You might want more specific error handling here
       raise HTTPException(status_code=500, detail="Failed to fetch or process portfolio history")

# Pydantic models for Algorithm Management
class AlgorithmBase(BaseModel):
    symbol: str = Field(..., example="AAPL")
    type: AlgorithmType
    parameters: Dict[str, Any] = Field(..., example={"short_window": 20, "long_window": 50})

class AlgorithmCreate(AlgorithmBase):
    pass

class AlgorithmRead(AlgorithmBase):
    id: int
    user_id: str # Assuming user_id is string based on User model
    is_active: bool # Added field
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True # Ensure AlgorithmType enum is serialized correctly

@app.get("/api/algorithms", response_model=List[AlgorithmRead])
async def get_user_algorithms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch all algorithms belonging to the current user."""
    print(f"--- Fetching algorithms for user: {current_user.email} ({current_user.id}) ---")
    algos = db.query(Algorithm).filter(Algorithm.user_id == current_user.id).all()
    return algos

# Add PATCH endpoint to update status
@app.patch("/api/algorithms/{algorithm_id}/status", response_model=AlgorithmRead)
async def update_algorithm_status(
    algorithm_id: int,
    status_update: AlgorithmStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Activate or deactivate a specific algorithm belonging to the current user."""
    print(f"--- Attempting to update status for algorithm ID: {algorithm_id} to {status_update.is_active} for user: {current_user.email} ---")
    db_algo = db.query(Algorithm).filter(
        Algorithm.id == algorithm_id,
        Algorithm.user_id == current_user.id
    ).first()

    if not db_algo:
        print(f"--- Algorithm ID: {algorithm_id} not found or not owned by user: {current_user.email} ---")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Algorithm not found or not authorized"
        )
    
    db_algo.is_active = status_update.is_active
    db_algo.updated_at = datetime.utcnow() # Manually update timestamp
    
    try:
        db.commit()
        db.refresh(db_algo)
    except Exception as e:
        db.rollback()
        print(f"!!! Error during algorithm status update commit: {e!r}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to update algorithm status."
        )

    print(f"--- Algorithm ID: {algorithm_id} status updated successfully to {db_algo.is_active} ---")
    return db_algo

# ... rest of endpoints ... 