from datetime import datetime, timedelta
import asyncio
import logging
from typing import Optional, Dict, Any, List

# Inject Database session
from sqlalchemy.orm import Session, sessionmaker

from .alpaca_service import AlpacaService
from .algorithm_service import AlgorithmService
# Import models directly for querying and type hints
from ..models import Algorithm, AlgorithmType, Signal, SignalType, Position, PositionStatus, Trade, TradeType, TradeStatus
from ..models.db_models import Trade as DBTrade, Signal as DBSignal # Import DB models for saving
from alpaca.trading.enums import OrderSide

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
        self._trading_task: Optional[asyncio.Task] = None # To hold the background task
        # Track positions per symbol
        self._positions: Dict[str, Any] = {} 
        # Track last signal per algorithm to avoid duplicate actions
        self._last_signal: Dict[int, SignalType] = {}

    async def start_trading(self, config: Dict):
        """Start automated trading with the given configuration."""
        if self.is_active and self._trading_task and not self._trading_task.done():
            logger.warning("Trading task already running.")
            return True
            
        try:
            self.config = config
            self.is_active = True
            logger.info("Automated trading starting with config: %s", config)
            # Start the main processing loop in the background
            # TODO: Add interval customization from config?
            self._trading_task = asyncio.create_task(self._run_active_strategies_loop())
            return True
        except Exception as e:
            logger.error(f"Error starting automated trading: {e!r}")
            self.is_active = False
            self.config = None
            self._trading_task = None
            raise

    async def stop_trading(self):
        """Stop automated trading."""
        self.is_active = False
        if self._trading_task and not self._trading_task.done():
            self._trading_task.cancel() # Request cancellation
            try:
                await self._trading_task # Wait for the task to finish cancelling
            except asyncio.CancelledError:
                logger.info("Trading task successfully cancelled.")
            except Exception as e:
                logger.error(f"Error during trading task cancellation: {e!r}")
        self.config = None
        self._trading_task = None
        self._positions = {} # Clear positions on stop
        self._last_signal = {} # Clear last signals
        logger.info("Automated trading stopped.")

    def get_status(self) -> Dict:
        """Get current trading status."""
        task_status = "stopped"
        if self.is_active:
            if self._trading_task:
                if self._trading_task.done():
                     task_status = "finished" # Or potentially crashed
                     # Check for exception? self._trading_task.exception()
                else:
                     task_status = "running"
            else:
                task_status = "starting_error" # Should not happen if active

        return {
            "is_active": self.is_active,
            "task_status": task_status,
            "current_positions": self._positions,
            "last_signals": {str(k): v.name for k, v in self._last_signal.items()}, # Convert keys/values for JSON
            "config": self.config
        }

    async def _run_active_strategies_loop(self, interval_seconds: int = 60):
        """Main loop to periodically fetch and process active strategies."""
        logger.info(f"Starting active strategies processing loop (interval: {interval_seconds}s)...")
        while self.is_active:
            db: Optional[Session] = None # Define db variable
            try:
                logger.info("Starting new trading cycle...")
                # Create a new session for this loop iteration
                db = self.SessionLocal()
                
                # --- Update current positions for all relevant symbols first --- #
                # Get symbols from active algorithms
                active_algorithms = db.query(Algorithm).filter(Algorithm.is_active == True).all()
                active_symbols = {algo.symbol for algo in active_algorithms} 
                logger.info(f"Active symbols: {active_symbols}")
                
                # Fetch current positions for these symbols from Alpaca
                # Note: Alpaca API might not have a bulk position fetch, loop might be needed
                # Or fetch all positions and filter locally
                # For now, placeholder - assume _update_positions fetches needed data
                await self._update_positions(list(active_symbols))

                logger.info(f"Processing {len(active_algorithms)} active algorithms...")
                if not active_algorithms:
                    logger.info("No active algorithms found. Sleeping.")
                else:
                    # Process each active algorithm
                    for algo in active_algorithms:
                        logger.info(f"--- Processing algorithm ID {algo.id} ({algo.type.name} for {algo.symbol}) ---")
                        # Pass the specific algorithm object and DB session
                        await self._process_single_algorithm(algo, db) 
                        await asyncio.sleep(0.5) # Small delay between algos within a cycle
                
                logger.info(f"Finished processing cycle. Sleeping for {interval_seconds} seconds.")
                
            except asyncio.CancelledError:
                logger.info("Trading loop cancellation requested.")
                self.is_active = False # Ensure loop terminates
                break # Exit loop immediately
            except Exception as e:
                logger.exception(f"Error in active strategies loop: {e!r}. Sleeping and retrying.")
                # Log the full traceback
            finally:
                if db: # Ensure session is closed
                    db.close()
                # Sleep only if the loop wasn't cancelled
                if self.is_active:
                     try:
                          await asyncio.sleep(interval_seconds)
                     except asyncio.CancelledError:
                          logger.info("Sleep interrupted by cancellation.")
                          self.is_active = False # Ensure loop terminates
        
        logger.info("Active strategies processing loop finished.")

    async def _update_positions(self, symbols: List[str]):
        """Fetches and updates the current positions for the given symbols."""
        logger.info(f"Updating positions for symbols: {symbols}")
        # Placeholder: Fetch all positions and update self._positions
        try:
             all_positions_raw = await self.alpaca_service.trading_client.get_all_positions() # Using client directly for now
             self._positions = {pos.symbol: pos.__dict__ for pos in all_positions_raw}
             logger.info(f"Updated positions: {self._positions}")
        except Exception as e:
            logger.error(f"Error fetching positions from Alpaca: {e!r}")
            # Decide how to handle - clear existing? Keep stale? For now, log error.

    async def _process_single_algorithm(self, algorithm: Algorithm, db: Session):
        """Process a single trading cycle for the given algorithm instance."""
        if not self.is_active: # Re-check within the loop
            return

        try:
            symbol = algorithm.symbol
            algo_id = algorithm.id
            logger.info(f"Running algorithm instance ID {algo_id} for {symbol}")
            
            # Generate and save signal using AlgorithmService
            signal = await self.algorithm_service.run_algorithm_instance(algorithm, db)
            
            if not signal:
                logger.warning(f"No signal generated or saved for {symbol} by algo {algo_id}")
                return

            logger.info(f"Algo {algo_id}: Generated signal = {signal.signal_type.name}")
            
            # Get current position state for this symbol from our tracked dict
            current_position = self._positions.get(symbol)
            has_position = current_position is not None
            last_signal_for_algo = self._last_signal.get(algo_id)
            
            # Avoid acting on the same signal repeatedly
            if signal.signal_type == last_signal_for_algo:
                logger.info(f"Algo {algo_id}: Signal {signal.signal_type.name} is same as last signal. No action.")
                return
                
            # Update last signal
            self._last_signal[algo_id] = signal.signal_type

            # --- Trade Execution Logic --- #
            # Uncomment the execution calls
            if signal.signal_type == SignalType.BUY and not has_position:
                logger.info(f"ACTION (Algo {algo_id}): Executing BUY for {symbol}.")
                await self._execute_buy(symbol, algorithm, db)
            elif signal.signal_type == SignalType.SELL and has_position:
                logger.info(f"ACTION (Algo {algo_id}): Executing SELL (close position) for {symbol}.")
                await self._execute_sell(symbol, algorithm, db)
            else:
                logger.info(f"Algo {algo_id}: Signal {signal.signal_type.name} does not warrant action for {symbol} (Position: {has_position})")

        except Exception as e:
            logger.exception(f"Error processing algorithm ID {algorithm.id} ({algorithm.symbol}): {e!r}")
            # Log full traceback

    async def _execute_buy(self, symbol: str, algorithm: Algorithm, db: Session):
        """Executes a buy order based on config and algo, and saves the trade."""
        logger.info(f"Attempting BUY execution for {symbol} (Algo {algorithm.id})")
        trade_saved = False
        try:
            # 1. Get Buying Power
            account_info = await self.alpaca_service.get_account_info()
            buying_power = float(account_info.get('buying_power', 0.0))
            logger.info(f"BUY {symbol}: Available buying power: ${buying_power:.2f}")

            if buying_power <= 1: # Add a small buffer
                logger.warning(f"BUY {symbol}: Insufficient buying power (${buying_power:.2f}). Skipping order.")
                return

            # 2. Calculate Target Notional Value
            position_size_percent = self.config.get('position_size', 0.1) # Default 10%
            notional_value_to_buy = buying_power * position_size_percent 
            logger.info(f"BUY {symbol}: Target notional value: ${notional_value_to_buy:.2f} ({position_size_percent*100}% of buying power)")
            
            if notional_value_to_buy <= 0:
                 logger.warning(f"BUY {symbol}: Calculated notional value is zero or negative (${notional_value_to_buy:.2f}). Skipping order.")
                 return
            
            # 3. Get Latest Price
            latest_price = await self.alpaca_service.get_latest_price(symbol)
            if not latest_price or latest_price <= 0:
                logger.warning(f"BUY {symbol}: Could not fetch valid latest price ({latest_price}). Skipping order.")
                return
                
            # 4. Calculate Quantity from Notional and Price
            quantity_to_buy = notional_value_to_buy / latest_price
            logger.info(f"BUY {symbol}: Calculated quantity: {quantity_to_buy:.8f} (Notional ${notional_value_to_buy:.2f} / Price ${latest_price:.2f})")

            if quantity_to_buy <= 0:
                 logger.warning(f"BUY {symbol}: Calculated quantity is zero or negative ({quantity_to_buy:.8f}). Skipping order.")
                 return

            # 5. Place Order
            # Note: alpaca_service.place_order returns a Pydantic Trade model or None
            order_result_trade: Optional[Trade] = await self.alpaca_service.place_order(
                symbol=symbol,
                quantity=quantity_to_buy, 
                side=OrderSide.BUY 
            )
            
            if not order_result_trade:
                 logger.error(f"BUY {symbol}: Order placement failed or returned no result.")
                 return # Stop if order placement failed

            logger.info(f"BUY {symbol}: Order placement result: {order_result_trade}")
            
            # 6. Save Trade to DB
            try:
                db_trade = DBTrade(
                    user_id=algorithm.user_id, # Associate with the algorithm's user
                    signal_id=None, # TODO: Link signal if available?
                    position_id=None, # TODO: Link position if available?
                    symbol=order_result_trade.symbol,
                    quantity=order_result_trade.quantity,
                    price=order_result_trade.price, # Might be None initially
                    side=TradeType.BUY, # Use DB enum
                    status=TradeStatus.PENDING if order_result_trade.status == TradeStatus.PENDING else TradeStatus.FILLED, # Map status
                    order_id=order_result_trade.order_id, # Should exist if Trade object returned
                    created_at=order_result_trade.timestamp, # Use timestamp from trade
                    # filled_at=... # Update later if needed
                    # additional_data=... 
                )
                db.add(db_trade)
                db.commit()
                db.refresh(db_trade)
                trade_saved = True
                logger.info(f"BUY {symbol}: Saved Trade ID {db_trade.id} to database.")
            except Exception as db_error:
                 logger.exception(f"BUY {symbol}: Error saving trade to database: {db_error!r}")
                 db.rollback() # Rollback DB changes
                 # Decide if we should re-raise or just log

            # TODO: Update self._positions state after confirmed fill?

        except Exception as e:
            logger.exception(f"Error executing BUY for {symbol} (Algo {algorithm.id}): {e!r}")
            if not trade_saved: # Rollback if trade wasn't saved before another exception occurred
                db.rollback()

    async def _execute_sell(self, symbol: str, algorithm: Algorithm, db: Session):
        """Executes a sell order (closes position) and saves the trade."""
        logger.info(f"Attempting SELL execution for {symbol} (Algo {algorithm.id})")
        trade_saved = False
        try:
            # 1. Get current position quantity (as before)
            position_data = self._positions.get(symbol)
            if not position_data:
                logger.warning(f"SELL {symbol}: Position data not found in tracked state. Cannot close.")
                return
            current_qty_str = position_data.get('qty')
            if not current_qty_str:
                 logger.warning(f"SELL {symbol}: Quantity not found in position data: {position_data}. Cannot close.")
                 return
            try:
                current_qty = float(current_qty_str)
            except ValueError:
                 logger.warning(f"SELL {symbol}: Invalid quantity format '{current_qty_str}'. Cannot close.")
                 return
            if current_qty <= 0:
                logger.warning(f"SELL {symbol}: No position or non-positive quantity ({current_qty}). Skipping close order.")
                return
            logger.info(f"SELL {symbol}: Attempting to close position of {current_qty} shares.")

            # 2. Call self.alpaca_service.close_position 
            # close_position also returns a Pydantic Trade model or None
            close_result_trade: Optional[Trade] = await self.alpaca_service.close_position(symbol)
            
            if not close_result_trade:
                 logger.error(f"SELL {symbol}: Close position failed or returned no result.")
                 return # Stop if closing order failed

            logger.info(f"SELL {symbol}: Close position result: {close_result_trade}")
            
            # 3. Save Trade to DB
            try:
                db_trade = DBTrade(
                    user_id=algorithm.user_id,
                    signal_id=None, # TODO: Link signal?
                    position_id=None, # TODO: Link position?
                    symbol=close_result_trade.symbol,
                    quantity=close_result_trade.quantity, # Should be the closed quantity
                    price=close_result_trade.price, # Filled price
                    side=TradeType.SELL, # Use DB enum
                    status=TradeStatus.PENDING if close_result_trade.status == TradeStatus.PENDING else TradeStatus.FILLED,
                    order_id=close_result_trade.order_id,
                    created_at=close_result_trade.timestamp,
                )
                db.add(db_trade)
                db.commit()
                db.refresh(db_trade)
                trade_saved = True
                logger.info(f"SELL {symbol}: Saved Trade ID {db_trade.id} to database.")
            except Exception as db_error:
                 logger.exception(f"SELL {symbol}: Error saving trade to database: {db_error!r}")
                 db.rollback()

            # TODO: Update self._positions state after confirmed fill (likely remove symbol)

        except Exception as e:
            logger.exception(f"Error executing SELL for {symbol} (Algo {algorithm.id}): {e!r}")
            if not trade_saved:
                db.rollback() 