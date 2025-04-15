from datetime import datetime, timedelta
import asyncio
import logging
from typing import Optional, Dict

# Inject Database session
from sqlalchemy.orm import Session, sessionmaker

from .alpaca_service import AlpacaService
from .algorithm_service import AlgorithmService
# Import Algorithm model directly for querying
from app.models.db_models import Algorithm, AlgorithmType # Assuming models are in db_models now
from app.models.signal import Signal, SignalType
from app.models.position import Position, PositionStatus
from app.models.trade import Trade, TradeType, TradeStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutomatedTradingService:
    # Accept SessionLocal factory instead of Session
    def __init__(self, algorithm_service: AlgorithmService, alpaca_service: AlpacaService, session_local: sessionmaker):
        self.algorithm_service = algorithm_service
        self.alpaca_service = alpaca_service
        self.SessionLocal = session_local # Store the factory
        self.is_active = False
        self.config = None
        self.current_position = None # This might need to be per-symbol
        self.last_trade_time = None

    async def start_trading(self, config: Dict):
        """Start automated trading with the given configuration."""
        try:
            self.config = config
            self.is_active = True
            logger.info("Automated trading started with config: %s", config)
            # Start the main processing loop in the background
            asyncio.create_task(self.run_active_strategies_loop())
            return True
        except Exception as e:
            logger.error(f"Error starting automated trading: {str(e)}")
            raise

    def stop_trading(self):
        """Stop automated trading."""
        self.is_active = False
        self.config = None
        logger.info("Automated trading stopped")

    def get_status(self) -> Dict:
        """Get current trading status."""
        return {
            "is_active": self.is_active,
            "current_position": self.current_position.__dict__ if self.current_position else None,
            "last_trade_time": self.last_trade_time,
            "config": self.config
        }

    async def run_active_strategies_loop(self, interval_seconds: int = 60):
        """Main loop to periodically fetch and process active strategies."""
        logger.info(f"Starting active strategies processing loop (interval: {interval_seconds}s)...")
        while self.is_active:
            db: Optional[Session] = None # Define db variable
            try:
                logger.info("Fetching active algorithms from DB...")
                # Create a new session for this loop iteration
                db = self.SessionLocal()
                active_algorithms = db.query(Algorithm).filter(Algorithm.is_active == True).all()
                logger.info(f"Found {len(active_algorithms)} active algorithms.")

                if not active_algorithms:
                    logger.info("No active algorithms found. Sleeping.")
                else:
                    # Process each active algorithm
                    for algo in active_algorithms:
                        logger.info(f"Processing algorithm ID {algo.id} ({algo.type.name} for {algo.symbol})...")
                        # Pass the specific algorithm object, not recreating it
                        await self.process_single_algorithm(algo) 
                        await asyncio.sleep(1) 
                
                logger.info(f"Finished processing cycle. Sleeping for {interval_seconds} seconds.")
                
            except Exception as e:
                logger.error(f"Error in active strategies loop: {e!r}. Sleeping and retrying.")
                # No await sleep here, happens in finally
            finally:
                if db: # Ensure session is closed
                    db.close()
                # Sleep regardless of success or error before next iteration
                await asyncio.sleep(interval_seconds)
        
        logger.info("Active strategies processing loop stopped.")

    # Renamed from process_trading_cycle to process_single_algorithm
    async def process_single_algorithm(self, algorithm: Algorithm):
        """Process a single trading cycle for the given algorithm instance."""
        if not self.is_active:
            logger.warning(f"Trading is not active, skipping processing for algo {algorithm.id}")
            return
        
        if not algorithm.is_active: # Double check just in case
            logger.warning(f"Algorithm ID {algorithm.id} is not active, skipping.")
            return

        try:
            symbol = algorithm.symbol
            logger.info(f"Generating signal for {symbol} using algo ID {algorithm.id}")
            # Generate trading signal using the fetched algorithm object
            signal = await self.algorithm_service.generate_signal(algorithm, symbol)
            if not signal:
                logger.info(f"No signal generated for {symbol} by algo {algorithm.id}")
                return

            logger.info(f"Signal generated: {signal.type.name}")
            # Get current position for this specific symbol
            position = await self.alpaca_service.get_position(symbol)
            # self.current_position = position # Maybe track positions differently?

            # Process signal based on current position
            if signal.type == SignalType.BUY and not position:
                logger.info(f"Processing BUY signal for {symbol}")
                await self._process_buy_signal(symbol)
            elif signal.type == SignalType.SELL and position:
                logger.info(f"Processing SELL signal for {symbol}")
                await self._process_sell_signal(symbol)
            else:
                logger.info(f"Signal {signal.type.name} does not warrant action for {symbol} (Position: {position is not None})")

            # self.last_trade_time = datetime.utcnow() # Maybe track per algo/symbol?

        except Exception as e:
            logger.error(f"Error in trading cycle for algo {algorithm.id} ({symbol}): {str(e)}")
            # Consider whether to raise or just log

    async def _process_buy_signal(self, symbol: str):
        """Process a buy signal."""
        try:
            # Calculate position size based on account balance
            balance = await self.alpaca_service.get_account_balance()
            position_size = balance * self.config.get('position_size', 0.1)  # Default 10% of balance
            
            # Place buy order
            trade = await self.alpaca_service.place_order(
                symbol=symbol,
                quantity=position_size,
                side=TradeType.BUY
            )
            
            if trade and trade.status == TradeStatus.FILLED:
                logger.info(f"Buy order filled for {symbol}: {trade}")
                # Position update might happen via trade stream or explicit fetch
            else:
                logger.warning(f"Buy order not filled or failed for {symbol}")

        except Exception as e:
            logger.error(f"Error processing buy signal for {symbol}: {str(e)}")
            # raise # Decide if individual signal errors should stop the loop

    async def _process_sell_signal(self, symbol: str):
        """Process a sell signal."""
        try:
            # Close existing position
            trade = await self.alpaca_service.close_position(symbol)
            
            if trade and trade.status == TradeStatus.FILLED:
                logger.info(f"Sell order filled for {symbol}: {trade}")
                # Position update might happen via trade stream or explicit fetch
            else:
                logger.warning(f"Sell order not filled or failed for {symbol}")

        except Exception as e:
            logger.error(f"Error processing sell signal for {symbol}: {str(e)}")
            # raise # Decide if individual signal errors should stop the loop

    # Remove the old process_trading_cycle method if it still exists
    # async def process_trading_cycle(...): ... 