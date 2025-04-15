from datetime import datetime, timedelta
import asyncio
import logging
from typing import Dict, Optional
from alpaca.trading.stream import TradingStream
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest

from .alpaca_service import AlpacaService

class AutomatedTradingService:
    def __init__(self, alpaca_service: AlpacaService):
        self.alpaca_service = alpaca_service
        self.trading_stream = None
        self.current_positions: Dict[str, float] = {}
        self.is_running = False
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        """Initialize the trading stream and get current positions"""
        try:
            # Get current positions
            positions = await self.alpaca_service.get_positions()
            self.current_positions = {
                position.symbol: float(position.qty) 
                for position in positions
            }
            
            # Initialize trading stream
            self.trading_stream = TradingStream(
                api_key=self.alpaca_service.api_key,
                secret_key=self.alpaca_service.secret_key,
                paper=self.alpaca_service.paper
            )
            
            # Subscribe to trade updates
            self.trading_stream.subscribe_trade_updates(self.handle_trade_update)
            
            self.logger.info("Automated trading service initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize automated trading: {str(e)}")
            return False

    async def handle_trade_update(self, trade_update):
        """Handle trade updates and update position tracking"""
        try:
            symbol = trade_update.order.symbol
            if trade_update.event == 'fill':
                if trade_update.order.side == OrderSide.BUY:
                    self.current_positions[symbol] = self.current_positions.get(symbol, 0) + float(trade_update.order.filled_qty)
                else:
                    self.current_positions[symbol] = self.current_positions.get(symbol, 0) - float(trade_update.order.filled_qty)
                
                # Remove position if quantity is zero
                if self.current_positions[symbol] == 0:
                    del self.current_positions[symbol]
                
                self.logger.info(f"Position updated for {symbol}: {self.current_positions.get(symbol, 0)}")
        except Exception as e:
            self.logger.error(f"Error handling trade update: {str(e)}")

    async def run_trading_loop(self, symbol: str, timeframe: str, lookback_days: int, 
                             short_window: int, long_window: int, max_position_size: float = 0.1):
        """Run continuous trading loop with the specified parameters"""
        if not self.is_running:
            self.is_running = True
            self.logger.info("Starting trading loop...")
            
            try:
                while self.is_running:
                    try:
                        # Get historical bars
                        prices = await self.alpaca_service.get_historical_bars(
                            symbol=symbol,
                            timeframe=timeframe,
                            lookback_days=lookback_days
                        )
                        
                        if not prices:
                            self.logger.warning("No price data received")
                            await asyncio.sleep(60)
                            continue
                        
                        # Calculate moving averages
                        short_ma, long_ma = self.calculate_moving_averages(prices, short_window, long_window)
                        
                        # Generate signal
                        signal = self.generate_signal(short_ma, long_ma)
                        
                        # Get current position
                        current_position = self.current_positions.get(symbol, 0)
                        
                        # Execute trade based on signal and position
                        if signal == 1 and current_position <= 0:
                            # Buy signal and no position or short position
                            await self.execute_trade(symbol, OrderSide.BUY, max_position_size)
                        elif signal == -1 and current_position >= 0:
                            # Sell signal and no position or long position
                            await self.execute_trade(symbol, OrderSide.SELL, max_position_size)
                        
                        # Wait for next iteration
                        await asyncio.sleep(60)  # Adjust based on timeframe
                        
                    except Exception as e:
                        self.logger.error(f"Error in trading loop: {str(e)}")
                        await asyncio.sleep(60)
                        
            except Exception as e:
                self.logger.error(f"Trading loop stopped due to error: {str(e)}")
            finally:
                self.is_running = False

    async def execute_trade(self, symbol: str, side: OrderSide, max_position_size: float):
        """Execute a trade with position sizing and risk management"""
        try:
            # Get account equity
            account = await self.alpaca_service.get_account()
            equity = float(account.equity)
            
            # Calculate position size
            position_size = equity * max_position_size
            
            # Get current price
            latest_trade = await self.alpaca_service.get_latest_trade(symbol)
            current_price = float(latest_trade.price)
            
            # Calculate quantity
            quantity = position_size / current_price
            
            # Place order
            order_request = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=side,
                time_in_force=TimeInForce.DAY
            )
            
            await self.alpaca_service.place_order(order_request)
            self.logger.info(f"Executed {side} order for {symbol}: {quantity} shares")
            
        except Exception as e:
            self.logger.error(f"Error executing trade: {str(e)}")

    def stop_trading(self):
        """Stop the trading loop"""
        self.is_running = False
        if self.trading_stream:
            self.trading_stream.stop()
        self.logger.info("Trading loop stopped")

    @staticmethod
    def calculate_moving_averages(prices: list, short_window: int, long_window: int):
        """Calculate moving averages"""
        short_ma = []
        long_ma = []
        
        for i in range(len(prices)):
            if i >= short_window - 1:
                short_ma.append(sum(prices[i-short_window+1:i+1]) / short_window)
            else:
                short_ma.append(None)
                
            if i >= long_window - 1:
                long_ma.append(sum(prices[i-long_window+1:i+1]) / long_window)
            else:
                long_ma.append(None)
                
        return short_ma, long_ma

    @staticmethod
    def generate_signal(short_ma: list, long_ma: list) -> int:
        """Generate trading signal based on moving averages"""
        if not short_ma or not long_ma:
            return 0
            
        # Get the last valid values
        short_last = next((x for x in reversed(short_ma) if x is not None), None)
        long_last = next((x for x in reversed(long_ma) if x is not None), None)
        
        if short_last is None or long_last is None:
            return 0
            
        if short_last > long_last:
            return 1  # Buy signal
        elif short_last < long_last:
            return -1  # Sell signal
        else:
            return 0  # Hold signal 