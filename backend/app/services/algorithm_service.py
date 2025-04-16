from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from app.services.data_service import DataService
from app.services.alpaca_service import AlpacaService
from app.models.algorithm import Algorithm, AlgorithmType
from app.models.signal import Signal, SignalType
from app.models.position import Position, PositionStatus
from app.models.trade import Trade, TradeType, TradeStatus
from numba import njit
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

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

class AlgorithmService:
    def __init__(self, data_service: DataService, alpaca_service: AlpacaService):
        self.data_service = data_service
        self.alpaca_service = alpaca_service

    async def generate_signal(self, algorithm: Algorithm, symbol: str) -> Optional[Signal]:
        try:
            # Get historical data
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=algorithm.lookback_period)
            data = await self.data_service.get_historical_data(symbol, start_date, end_date)
            
            if data.empty:
                logger.warning(f"No data available for {symbol}")
                return None

            # Convert data to numpy array for calculations
            close_prices = data['close'].values
            if len(close_prices) < 2:
                logger.warning(f"Not enough data points for {symbol}")
                return None

            # Generate signal based on algorithm type
            if algorithm.type == AlgorithmType.MOVING_AVERAGE_CROSSOVER:
                signal = self._generate_moving_average_signal(close_prices, algorithm)
            elif algorithm.type == AlgorithmType.RSI:
                signal = self._generate_rsi_signal(close_prices, algorithm)
            elif algorithm.type == AlgorithmType.MACD:
                signal = self._generate_macd_signal(close_prices, algorithm)
            else:
                logger.error(f"Unsupported algorithm type: {algorithm.type}")
                return None

            if signal:
                logger.info(f"Generated {signal.type} signal for {symbol}")
            return signal

        except Exception as e:
            logger.error(f"Error in generate_signal: {str(e)}")
            return None

    def _generate_moving_average_signal(self, close_prices: np.ndarray, algorithm: Algorithm) -> Optional[Signal]:
        try:
            # Calculate moving averages
            short_window = algorithm.parameters.get('short_window', 20)
            long_window = algorithm.parameters.get('long_window', 50)
            
            short_ma, long_ma = calculate_moving_averages(close_prices, short_window, long_window)
            
            # Generate signal
            if short_ma[-1] > long_ma[-1] and short_ma[-2] <= long_ma[-2]:
                return Signal(
                    type=SignalType.BUY, 
                    symbol=algorithm.symbol,
                    timestamp=datetime.utcnow(),
                    confidence=1.0, 
                    metadata={"short_ma": short_ma[-1], "long_ma": long_ma[-1]}
                )
            elif short_ma[-1] < long_ma[-1] and short_ma[-2] >= long_ma[-2]:
                return Signal(
                    type=SignalType.SELL, 
                    symbol=algorithm.symbol,
                    timestamp=datetime.utcnow(),
                    confidence=1.0, 
                    metadata={"short_ma": short_ma[-1], "long_ma": long_ma[-1]}
                )
            return None
        except Exception as e:
            logger.error(f"Error in _generate_moving_average_signal: {str(e)}")
            return None

    def _generate_rsi_signal(self, close_prices: np.ndarray, algorithm: Algorithm) -> Optional[Signal]:
        try:
            # Calculate RSI
            period = algorithm.parameters.get('period', 14)
            overbought = algorithm.parameters.get('overbought', 70)
            oversold = algorithm.parameters.get('oversold', 30)
            
            delta = pd.Series(close_prices).diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1] # Get the last RSI value
            
            # Check if rsi calculation resulted in NaN or Inf
            if np.isnan(current_rsi) or np.isinf(current_rsi):
                logger.warning(f"RSI calculation resulted in invalid value ({current_rsi}) for {algorithm.symbol}. Skipping signal.")
                return None

            # Generate signal
            if current_rsi < oversold:
                return Signal(
                    type=SignalType.BUY, 
                    symbol=algorithm.symbol,
                    timestamp=datetime.utcnow(),
                    confidence=1.0, 
                    metadata={"rsi": current_rsi, "oversold_threshold": oversold}
                )
            elif current_rsi > overbought:
                return Signal(
                    type=SignalType.SELL, 
                    symbol=algorithm.symbol,
                    timestamp=datetime.utcnow(),
                    confidence=1.0, 
                    metadata={"rsi": current_rsi, "overbought_threshold": overbought}
                )
            return None
        except Exception as e:
            logger.error(f"Error in _generate_rsi_signal: {str(e)}")
            return None

    def _generate_macd_signal(self, close_prices: np.ndarray, algorithm: Algorithm) -> Optional[Signal]:
        try:
            # Calculate MACD
            short_window = algorithm.parameters.get('short_window', 12)
            long_window = algorithm.parameters.get('long_window', 26)
            signal_window = algorithm.parameters.get('signal_window', 9)
            
            exp1 = pd.Series(close_prices).ewm(span=short_window, adjust=False).mean()
            exp2 = pd.Series(close_prices).ewm(span=long_window, adjust=False).mean()
            macd = exp1 - exp2
            signal_line = macd.ewm(span=signal_window, adjust=False).mean()
            
            current_macd = macd.iloc[-1]
            prev_macd = macd.iloc[-2]
            current_signal_line = signal_line.iloc[-1]
            prev_signal_line = signal_line.iloc[-2]

             # Check if calculations resulted in NaN or Inf
            if any(np.isnan([current_macd, prev_macd, current_signal_line, prev_signal_line])) or \
               any(np.isinf([current_macd, prev_macd, current_signal_line, prev_signal_line])):
                logger.warning(f"MACD calculation resulted in invalid value for {algorithm.symbol}. Skipping signal.")
                return None

            # Generate signal based on crossover
            if current_macd > current_signal_line and prev_macd <= prev_signal_line:
                 return Signal(
                    type=SignalType.BUY, 
                    symbol=algorithm.symbol,
                    timestamp=datetime.utcnow(),
                    confidence=1.0, 
                    metadata={"macd": current_macd, "signal_line": current_signal_line}
                )
            elif current_macd < current_signal_line and prev_macd >= prev_signal_line:
                 return Signal(
                    type=SignalType.SELL, 
                    symbol=algorithm.symbol,
                    timestamp=datetime.utcnow(),
                    confidence=1.0, 
                    metadata={"macd": current_macd, "signal_line": current_signal_line}
                )
            return None 
        except Exception as e:
            logger.error(f"Error in _generate_macd_signal: {str(e)}")
            return None

    async def run_algorithm_instance(self, algorithm: Algorithm, db: Session) -> Optional[Signal]:
        """
        Runs a specific algorithm instance, fetches data, calculates signals using the appropriate
        internal method, saves the latest signal to the database if generated, and returns the 
        Pydantic Signal object.
        """
        print(f"--- Running Algorithm ID: {algorithm.id}, Symbol: {algorithm.symbol}, Type: {algorithm.type} ---")
        
        # Import the DB version of the enum for comparison
        from app.models.db_models import AlgorithmType as DBAlgorithmType 

        # Extract parameters and perform basic validation
        try:
            symbol = algorithm.symbol
            params = algorithm.parameters
            # Use the DB Enum instance directly from the loaded algorithm object
            algo_type_from_db = algorithm.type 

            # Common params (can be adjusted or made type-specific)
            timeframe = params.get('timeframe', '1D')
            lookback_days = params.get('lookback_days', 90) # Increased default for safety
            limit = 1000 # Max bars to fetch initially

            # Validate required parameters based on type using the DB Enum
            if algo_type_from_db == DBAlgorithmType.MOVING_AVERAGE_CROSSOVER:
                short_window = params.get('short_window')
                long_window = params.get('long_window')
                if not short_window or not long_window:
                    raise ValueError("Missing short_window or long_window")
                if short_window >= long_window:
                    raise ValueError("Short window must be less than long window")
                required_data_length = long_window # Need at least long_window points
            elif algo_type_from_db == DBAlgorithmType.RSI:
                period = params.get('period')
                overbought = params.get('overbought')
                oversold = params.get('oversold')
                if not period or not overbought or not oversold:
                    raise ValueError("Missing period, overbought, or oversold")
                required_data_length = period + 1 # Need period + 1 for diff calculation
            elif algo_type_from_db == DBAlgorithmType.MACD:
                short_window = params.get('short_window')
                long_window = params.get('long_window')
                signal_window = params.get('signal_window')
                if not short_window or not long_window or not signal_window:
                    raise ValueError("Missing short_window, long_window, or signal_window")
                required_data_length = long_window + signal_window # Rough estimate
            else:
                # This else should now correctly catch genuinely unsupported types
                raise ValueError(f"Unsupported algorithm type stored in DB: {algo_type_from_db}")

        except Exception as e:
            # Log the specific error encountered during parameter validation
            logger.error(f"Algorithm {algorithm.id}: Error validating parameters: {e!r}") 
            return None # Cannot proceed without valid parameters
            
        # Log the specific timeframe value before passing it
        logger.info(f"Algorithm {algorithm.id}: Using timeframe parameter value: '{timeframe}'")

        # Fetch historical data
        try:
            prices = await self.alpaca_service.get_historical_bars(
                symbol=symbol,
                timeframe=timeframe,
                lookback_days=lookback_days,
                limit=limit
            )
            
            if not prices or len(prices) < required_data_length:
                logger.warning(f"Algorithm {algorithm.id}: Insufficient historical price data ({len(prices) if prices else 0}) for {symbol}. Need at least {required_data_length}. Skipping signal.")
                return None
                
            close_prices = np.array(prices)
            print(f"--- Fetched {len(close_prices)} price points for {symbol} ---")
            
        except Exception as e:
            logger.error(f"Algorithm {algorithm.id}: Error fetching historical data for {symbol}: {e!r}")
            return None
            
        # Generate signal using the appropriate internal method
        generated_pydantic_signal: Optional[Signal] = None
        try:
            # Pass the original algorithm object (which might be needed by the generation funcs)
            if algo_type_from_db == DBAlgorithmType.MOVING_AVERAGE_CROSSOVER:
                generated_pydantic_signal = self._generate_moving_average_signal(close_prices, algorithm)
            elif algo_type_from_db == DBAlgorithmType.RSI:
                generated_pydantic_signal = self._generate_rsi_signal(close_prices, algorithm)
            elif algo_type_from_db == DBAlgorithmType.MACD:
                generated_pydantic_signal = self._generate_macd_signal(close_prices, algorithm)
                 
        except Exception as e:
            logger.error(f"Algorithm {algorithm.id}: Error during signal generation function for {symbol}: {e!r}")
            return None # Signal generation failed

        # Save the signal to the database if generated
        if generated_pydantic_signal:
            try:
                # Import the DB model here to avoid circular dependency issues at module level
                from app.models.db_models import Signal as DBSignal, SignalType as DBSignalType
                
                # Map Pydantic Signal to DB Signal Model
                db_signal = DBSignal(
                    algorithm_id=algorithm.id,
                    type=getattr(DBSignalType, generated_pydantic_signal.type.name),
                    symbol=generated_pydantic_signal.symbol,
                    confidence=generated_pydantic_signal.confidence,
                    timestamp=generated_pydantic_signal.timestamp,
                    additional_data=generated_pydantic_signal.metadata
                )
                db.add(db_signal)
                db.commit()
                db.refresh(db_signal)
                logger.info(f"--- Saved Signal ID: {db_signal.id} for Algorithm ID: {algorithm.id} ({str(generated_pydantic_signal.type.value)}) ---")
                
                # Return the Pydantic model for the API response
                return generated_pydantic_signal 
                
            except ImportError:
                 logger.error(f"Failed to import database Signal model (DBSignal). Cannot save signal for Algorithm ID {algorithm.id}.")
                 db.rollback() # Rollback potential add
                 return None # Indicate failure but signal was technically generated
            except Exception as e:
                db.rollback()
                logger.error(f"Algorithm {algorithm.id}: Error saving signal to database: {e!r}")
                return None # Failed to save
        else:
            logger.info(f"--- No BUY/SELL signal generated by algorithm {algorithm.id} ({symbol}) ---")
            return None

    # Placeholder for other algorithm-related methods if needed
    def list_algorithms_for_user(self, user_id: int, db: Session) -> List[Algorithm]:
         # Example: Method to list algorithms (implementation might exist elsewhere)
         pass 