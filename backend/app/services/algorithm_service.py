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

logger = logging.getLogger(__name__)

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
            
            short_ma = pd.Series(close_prices).rolling(window=short_window).mean()
            long_ma = pd.Series(close_prices).rolling(window=long_window).mean()
            
            # Generate signal
            if short_ma.iloc[-1] > long_ma.iloc[-1] and short_ma.iloc[-2] <= long_ma.iloc[-2]:
                return Signal(
                    symbol=algorithm.symbol,
                    type=SignalType.BUY,
                    strength=1.0,
                    timestamp=datetime.utcnow()
                )
            elif short_ma.iloc[-1] < long_ma.iloc[-1] and short_ma.iloc[-2] >= long_ma.iloc[-2]:
                return Signal(
                    symbol=algorithm.symbol,
                    type=SignalType.SELL,
                    strength=1.0,
                    timestamp=datetime.utcnow()
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
            
            # Generate signal
            if rsi.iloc[-1] < oversold:
                return Signal(
                    symbol=algorithm.symbol,
                    type=SignalType.BUY,
                    strength=1.0,
                    timestamp=datetime.utcnow()
                )
            elif rsi.iloc[-1] > overbought:
                return Signal(
                    symbol=algorithm.symbol,
                    type=SignalType.SELL,
                    strength=1.0,
                    timestamp=datetime.utcnow()
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
            signal = macd.ewm(span=signal_window, adjust=False).mean()
            
            # Generate signal
            if macd.iloc[-1] > signal.iloc[-1] and macd.iloc[-2] <= signal.iloc[-2]:
                return Signal(
                    symbol=algorithm.symbol,
                    type=SignalType.BUY,
                    strength=1.0,
                    timestamp=datetime.utcnow()
                )
            elif macd.iloc[-1] < signal.iloc[-1] and macd.iloc[-2] >= signal.iloc[-2]:
                return Signal(
                    symbol=algorithm.symbol,
                    type=SignalType.SELL,
                    strength=1.0,
                    timestamp=datetime.utcnow()
                )
            return None
        except Exception as e:
            logger.error(f"Error in _generate_macd_signal: {str(e)}")
            return None 