from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
import numpy as np
from numba import njit
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
import time

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

# Create limiter instance
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Trading Algorithm API",
             description="API for algorithmic trading using Alpaca",
             version="1.0.0")

# Add rate limiter error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Add your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Trading Algorithm API",
        version="1.0.0",
        description="API for algorithmic trading using Alpaca",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

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
    active_algorithm_count: int
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
    print(f"--- Received automated trading config request: {config} ---") # Log received config
    try:
        if config.is_active:
            print("--- Attempting to start automated trading --- ") # Log start attempt
            await trading_service.start_trading({
                "position_size": config.position_size,
                "max_loss_percent": config.max_loss_percent
            })
            print("--- Call to start_trading completed --- ") # Log start completion
        else:
            print("--- Attempting to stop automated trading --- ") # Log stop attempt
            await trading_service.stop_trading() # Make stop async
            print("--- Call to stop_trading completed --- ") # Log stop completion
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
        # Use the DB model for querying
        from .models.db_models import Algorithm as DBAlgorithm, Position as DBPosition, Trade as DBTrade, PositionStatus
        
        base_algo_query = db.query(DBAlgorithm).filter(DBAlgorithm.user_id == current_user.id)
        algo_count = base_algo_query.count()
        # Query for active algorithms
        active_algo_count = base_algo_query.filter(DBAlgorithm.is_active == True).count() 
        
        open_pos_count = db.query(DBPosition).filter(
            DBPosition.user_id == current_user.id,
            DBPosition.status == PositionStatus.OPEN # Use the enum member from db_models
        ).count()
        
        one_day_ago = datetime.utcnow() - timedelta(days=1)
        recent_trades_count = db.query(DBTrade).filter(
            DBTrade.user_id == current_user.id,
            DBTrade.created_at >= one_day_ago
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
            active_algorithm_count=active_algo_count,
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
    user_id: str # Changed from int to str to match UUID
    is_active: bool # Added field
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True # Ensure AlgorithmType enum is serialized correctly

# Pydantic model for returning Signal data
class SignalRead(BaseModel):
    id: int
    algorithm_id: int
    signal_type: SignalType
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
        use_enum_values = True

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

# New endpoint to manually trigger an algorithm run and generate/save a signal
@app.post("/api/algorithms/{algorithm_id}/run", 
          response_model=Optional[SignalRead], 
          responses={ # Define possible responses
              201: {"description": "Signal generated and saved", "model": SignalRead},
              200: {"description": "Algorithm ran, no BUY/SELL signal generated"}
          })
async def run_specific_algorithm(
    algorithm_id: int,
    response: JSONResponse, # Inject response object to set status code
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    algorithm_service: AlgorithmService = Depends(get_algorithm_service)
):
    """Manually run a specific algorithm instance. 
    Returns 201 Created with signal data if a BUY/SELL signal is generated.
    Returns 200 OK with empty body if no BUY/SELL signal is generated.
    """
    print(f"--- Received request to run algorithm ID: {algorithm_id} for user: {current_user.email} ---")
    
    # Fetch the algorithm from DB, ensuring it belongs to the user
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
        
    # Run the algorithm instance using the service
    generated_signal = await algorithm_service.run_algorithm_instance(db_algo, db)
    
    if generated_signal:
        # Signal generated: Return 201 Created with the signal data
        print(f"--- Successfully ran Algorithm ID: {algorithm_id}, generated Signal ID: {generated_signal.id} ({generated_signal.type.value}) ---")
        response.status_code = status.HTTP_201_CREATED # Explicitly set 201
        return generated_signal
    else:
        # No BUY/SELL signal generated (or service error occurred and was logged)
        # Return 200 OK with empty body
        print(f"--- No BUY/SELL signal generated or error occurred for Algorithm ID: {algorithm_id}. Returning 200 OK. ---")
        response.status_code = status.HTTP_200_OK
        return None # Return None which results in empty body for Optional[SignalRead]

# Endpoint to CREATE a new algorithm
@app.post("/api/algorithms", response_model=AlgorithmRead, status_code=status.HTTP_201_CREATED)
async def create_algorithm(
    algorithm_data: AlgorithmCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    alpaca_service: AlpacaService = Depends(get_alpaca_service)
):
    """Create a new algorithm for the current user."""
    print(f"--- Received request to create algorithm for user: {current_user.email} ---")
    print(f"--- Algorithm Data: {algorithm_data} ---")
    
    # --- Add Asset Validation --- 
    symbol_to_check = algorithm_data.symbol.upper() # Ensure consistent casing
    is_valid = await alpaca_service.is_asset_valid(symbol_to_check)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Symbol '{symbol_to_check}' is invalid or not tradable on Alpaca."
        )
    # --- End Asset Validation --- 
        
    # Create the new Algorithm database object
    db_algo = Algorithm(
        user_id=current_user.id,
        symbol=algorithm_data.symbol,
        type=algorithm_data.type,
        parameters=algorithm_data.parameters,
        is_active=False # Default to inactive when created
    )
    
    try:
        db.add(db_algo)
        db.commit()
        db.refresh(db_algo)
        print(f"--- Successfully created Algorithm ID: {db_algo.id} for user {current_user.id} ---")
        return db_algo
    except Exception as e:
        db.rollback()
        print(f"!!! Error creating algorithm: {e!r}")
        # TODO: Check for specific DB errors like unique constraints if needed
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create algorithm: {e!r}"
        )

# Endpoint to DELETE an algorithm
@app.delete("/api/algorithms/{algorithm_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_algorithm(
    algorithm_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a specific algorithm belonging to the current user."""
    print(f"--- Received request to DELETE algorithm ID: {algorithm_id} for user: {current_user.email} ---")
    
    # Fetch the algorithm from DB, ensuring it belongs to the user
    db_algo = db.query(Algorithm).filter(
        Algorithm.id == algorithm_id,
        Algorithm.user_id == current_user.id
    ).first()
    
    if not db_algo:
        print(f"--- Algorithm ID: {algorithm_id} not found or not owned by user: {current_user.email} --- ")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Algorithm not found or not authorized"
        )
        
    try:
        db.delete(db_algo)
        db.commit()
        print(f"--- Successfully deleted Algorithm ID: {algorithm_id} ---")
        # Return No Content implicitly by FastAPI for 204 status
        return
    except Exception as e:
        db.rollback()
        print(f"!!! Error deleting algorithm ID {algorithm_id}: {e!r}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete algorithm: {e!r}"
        )

# ... rest of endpoints ... 

class AlgorithmResult(BaseModel):
    priceData: List[Dict[str, Any]]
    signals: List[Dict[str, Any]]
    algorithm: AlgorithmRead

@app.get("/api/algorithms/{algorithm_id}/results", response_model=AlgorithmResult)
async def get_algorithm_results(
    algorithm_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    algorithm_service: AlgorithmService = Depends(get_algorithm_service)
):
    """Get detailed results for a specific algorithm including price data and signals."""
    try:
        # Get the algorithm
        algorithm = db.query(Algorithm).filter(
            Algorithm.id == algorithm_id,
            Algorithm.user_id == current_user.id
        ).first()
        
        if not algorithm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Algorithm not found"
            )

        # Get historical price data
        timeframe = algorithm.parameters.get('timeframe', '5Min')
        lookback_days = algorithm.parameters.get('lookback_days', 5)
        
        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=lookback_days)

        # Get bars from Alpaca
        df = await algorithm_service.data_service.get_historical_data(
            symbol=algorithm.symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date
        )

        # Convert DataFrame to price data format
        price_data = []
        for timestamp, row in df.iterrows():
            price_data.append({
                'timestamp': timestamp.isoformat(),
                'price': float(row['close']),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'volume': float(row['volume'])
            })

        # Get signals for this algorithm
        signals = db.query(Signal).filter(
            Signal.algorithm_id == algorithm_id
        ).order_by(Signal.timestamp.desc()).all()

        # Convert signals to response format
        signal_data = []
        for signal in signals:
            signal_data.append({
                'id': signal.id,
                'type': signal.signal_type.value,
                'timestamp': signal.timestamp.isoformat(),
                'price': float(signal.details.get('price', 0)) if signal.details else 0,
                'details': signal.details
            })

        return {
            'priceData': price_data,
            'signals': signal_data,
            'algorithm': algorithm
        }

    except Exception as e:
        print(f"Error getting algorithm results: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving algorithm results"
        )

# ... rest of endpoints ... 

# Request validation models
class HistoricalBarsRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    timeframe: str = Field(default="1D", pattern="^(1Min|5Min|15Min|1H|1D)$")
    lookback_days: Optional[int] = Field(default=None, ge=1, le=365)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: Optional[int] = Field(default=1000, ge=1, le=10000)

    @validator('end_date')
    def validate_dates(cls, end_date, values):
        if 'start_date' in values and end_date and values['start_date']:
            if end_date <= values['start_date']:
                raise ValueError('end_date must be after start_date')
        return end_date

class OrderRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    quantity: float = Field(..., gt=0)
    side: str = Field(..., pattern="^(buy|sell)$")
    time_in_force: str = Field(default="day", pattern="^(day|gtc)$")

class PositionRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)

# Response models
class BarResponse(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

class OrderResponse(BaseModel):
    order_id: str
    client_order_id: str
    status: str
    symbol: str
    qty: str
    filled_qty: str
    filled_avg_price: Optional[str] = None

class PositionResponse(BaseModel):
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    status: str
    timestamp: datetime

# Update endpoints to use the models
@app.get("/api/historical-bars/{symbol}", response_model=List[BarResponse])
@limiter.limit("5/minute")
async def get_historical_bars(
    request: Request,
    symbol: str,
    timeframe: str = "1D",
    lookback_days: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 1000
):
    try:
        # Validate request using Pydantic model
        request_data = HistoricalBarsRequest(
            symbol=symbol,
            timeframe=timeframe,
            lookback_days=lookback_days,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        # Get bars from Alpaca service
        bars = await alpaca_service.get_historical_bars(
            symbol=request_data.symbol,
            timeframe=request_data.timeframe,
            lookback_days=request_data.lookback_days,
            start_date=request_data.start_date,
            end_date=request_data.end_date,
            limit=request_data.limit
        )
        
        return [BarResponse(**bar) for bar in bars]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@app.post("/api/place-order", response_model=OrderResponse)
@limiter.limit("3/minute")
async def place_order(
    request: Request,
    order_data: OrderRequest,
    alpaca_service: AlpacaService = Depends(get_alpaca_service)
):
    try:
        order = await alpaca_service.place_order(
            symbol=order_data.symbol,
            quantity=order_data.quantity,
            side=order_data.side,
            time_in_force=order_data.time_in_force
        )
        return OrderResponse(**order)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@app.get("/api/position/{symbol}", response_model=PositionResponse)
@limiter.limit("10/minute")
async def get_position(
    request: Request,
    symbol: str,
    alpaca_service: AlpacaService = Depends(get_alpaca_service)
):
    try:
        position = await alpaca_service.get_position(symbol)
        if not position:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No position found for symbol {symbol}"
            )
        return PositionResponse(**position.dict())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# ... rest of endpoints ... 