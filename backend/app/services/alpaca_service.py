from alpaca.data.historical import StockHistoricalDataClient
from alpaca.trading.client import TradingClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from fastapi import HTTPException
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from alpaca.trading.requests import MarketOrderRequest, GetPortfolioHistoryRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from typing import Dict, List, Optional, Tuple
import logging
from app.models.position import Position, PositionStatus
from app.models.trade import Trade, TradeType, TradeStatus
from alpaca.trading.models import PortfolioHistory
import httpx
from alpaca.common.exceptions import APIError
from functools import lru_cache
import time

# Load environment variables
load_dotenv()

# Get API keys from environment
APCA_API_KEY_ID = os.getenv("APCA_API_KEY_ID")
APCA_API_SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")

logger = logging.getLogger(__name__)

class AlpacaService:
    def __init__(self, api_key_id: str = None, secret_key: str = None, paper: bool = True):
        print(f"--- Initializing Alpaca API for paper={paper} ---")
        try:
            # Use provided keys or fall back to environment variables
            api_key = api_key_id or APCA_API_KEY_ID
            secret = secret_key or APCA_API_SECRET_KEY
            
            if not api_key or not secret:
                raise ValueError("API keys not found. Please provide them or set them in environment variables.")
            
            print(f"--- Using API Key ID: {api_key[:5]}... ---")
            
            # Initialize trading client first (as it's more critical)
            print("--- Initializing Trading Client ---")
            self.trading_client = TradingClient(
                api_key=api_key,
                secret_key=secret,
                paper=paper
            )
            
            # Test trading client connection
            try:
                account = self.trading_client.get_account()
                print(f"--- Trading account status: {account.status} ---")
                print(f"--- Account equity: {account.equity} ---")
            except Exception as e:
                print(f"!!! Failed to get trading account: {e!r}")
                raise
            
            # Initialize market data client
            print("--- Initializing Market Data Client ---")
            self.market_data_client = StockHistoricalDataClient(
                api_key=api_key,
                secret_key=secret
            )
            
            # Test market data client
            try:
                # Try to get a single bar to test the connection
                test_request = StockBarsRequest(
                    symbol_or_symbols="AAPL",
                    timeframe=TimeFrame.Day,
                    start="2024-01-01",
                    end="2024-01-02"
                )
                test_bars = self.market_data_client.get_stock_bars(test_request)
                if test_bars and "AAPL" in test_bars:
                    print(f"--- Market data test successful: {len(test_bars['AAPL'])} bars received ---")
                else:
                    print("--- Market data test successful but no bars returned ---")
            except Exception as e:
                print(f"!!! Failed to get market data: {e!r}")
                raise
            
            print(f"--- Successfully initialized both Alpaca clients ---")
            self.api_key = api_key
            self.secret_key = secret
            self.paper = paper
            self.base_url = "https://paper-api.alpaca.markets" if paper else "https://api.alpaca.markets"
            self._cache: Dict[str, Tuple[float, datetime]] = {}
            self._cache_ttl = 60  # Cache TTL in seconds
        except Exception as e:
            print(f"!!! FAILED to initialize Alpaca API: {e!r}")
            raise HTTPException(status_code=500, detail=f"Failed to initialize Alpaca API: {str(e)}")
    
    async def get_account_info(self):
        print("--- Calling get_account() ---")
        try:
            account = self.trading_client.get_account()
            return {
                "account_number": account.account_number,
                "status": account.status,
                "equity": str(account.equity),
                "buying_power": str(account.buying_power),
                "cash": str(account.cash),
                "currency": account.currency,
                "paper_trading": self.paper
            }
        except Exception as e:
            logger.error(f"!!! Exception during Alpaca get_account: {e!r}")
            raise HTTPException(status_code=400, detail=str(e))

    async def place_order(self, symbol: str, qty: float, side: str, time_in_force: str = 'day'):
        """Place a market order with string parameters."""
        print(f"--- Placing order for {symbol}: {side} {qty} shares ---")
        try:
            # Verify trading client is initialized
            if not hasattr(self, 'trading_client'):
                raise ValueError("Trading client not initialized")
            
            # Convert side string to OrderSide enum
            order_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
            
            # Convert time_in_force string to TimeInForce enum
            order_time_in_force = TimeInForce.DAY if time_in_force.lower() == 'day' else TimeInForce.GTC
            
            # Create a MarketOrderRequest object
            order_request = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=order_side,
                time_in_force=order_time_in_force
            )
            
            # Submit the order using the request object
            order = self.trading_client.submit_order(order_data=order_request)
            
            print(f"--- Order submitted successfully: {order} ---")
            
            # Create and return a Trade object
            return Trade(
                symbol=symbol,
                type=TradeType.BUY if order_side == OrderSide.BUY else TradeType.SELL,
                quantity=float(qty),
                price=float(order.filled_avg_price) if order.filled_avg_price else None,
                status=TradeStatus.FILLED if order.status == 'filled' else TradeStatus.PENDING,
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            logger.error(f"!!! Exception during place_order: {e!r}")
            raise HTTPException(status_code=400, detail=str(e))

    async def get_order_status(self, order_id: str):
        """Get the status of a specific order."""
        print(f"--- Getting order status for {order_id} ---")
        try:
            order = self.trading_client.get_order_by_id(order_id)
            return {
                "order_id": order.id,
                "client_order_id": order.client_order_id,
                "status": order.status,
                "filled_avg_price": str(order.filled_avg_price) if order.filled_avg_price else None,
                "qty": str(order.qty),
                "filled_qty": str(order.filled_qty),
                "symbol": order.symbol
            }
        except Exception as e:
            logger.error(f"!!! Exception during get_order_status: {e!r}")
            raise HTTPException(status_code=400, detail=str(e))

    async def get_open_orders(self):
        """Get all open orders."""
        print("--- Getting open orders ---")
        try:
            orders = self.trading_client.get_orders(status='open')
            return [{
                "order_id": order.id,
                "client_order_id": order.client_order_id,
                "status": order.status,
                "symbol": order.symbol,
                "qty": str(order.qty),
                "filled_qty": str(order.filled_qty),
                "filled_avg_price": str(order.filled_avg_price) if order.filled_avg_price else None
            } for order in orders]
        except Exception as e:
            logger.error(f"!!! Exception during get_open_orders: {e!r}")
            raise HTTPException(status_code=400, detail=str(e))

    async def cancel_order(self, order_id: str):
        """Cancel a specific order."""
        print(f"--- Cancelling order {order_id} ---")
        try:
            self.trading_client.cancel_order_by_id(order_id)
            return {"status": "cancelled", "order_id": order_id}
        except Exception as e:
            logger.error(f"!!! Exception during cancel_order: {e!r}")
            raise HTTPException(status_code=400, detail=str(e))

    async def get_assets(self):
        """Get all tradable assets."""
        print("--- Getting tradable assets ---")
        try:
            assets = self.trading_client.get_all_assets()
            return [{
                "id": asset.id,
                "symbol": asset.symbol,
                "name": asset.name,
                "status": asset.status,
                "tradable": asset.tradable,
                "marginable": asset.marginable,
                "shortable": asset.shortable,
                "easy_to_borrow": asset.easy_to_borrow,
                "fractionable": asset.fractionable
            } for asset in assets if asset.tradable]
        except Exception as e:
            logger.error(f"!!! Exception during get_assets: {e!r}")
            raise HTTPException(status_code=400, detail=str(e))

    def _get_cached_data(self, key: str) -> Optional[float]:
        if key in self._cache:
            value, timestamp = self._cache[key]
            if (datetime.now(timezone.utc) - timestamp).total_seconds() < self._cache_ttl:
                return value
            del self._cache[key]
        return None

    def _set_cached_data(self, key: str, value: float):
        self._cache[key] = (value, datetime.now(timezone.utc))

    @lru_cache(maxsize=100)
    async def get_historical_bars(
        self, 
        symbol: str, 
        timeframe: str = '1D', 
        lookback_days: int = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 1000
    ):
        print(f"--- Getting historical bars for {symbol} with timeframe={timeframe} ---")
        try:
            # Convert timeframe string to TimeFrame object
            if timeframe == '1D':
                tf = TimeFrame.Day
            elif timeframe == '1H':
                tf = TimeFrame.Hour
            elif timeframe == '15Min':
                tf = TimeFrame(15, TimeFrameUnit.Minute)
            elif timeframe == '5Min':
                tf = TimeFrame(5, TimeFrameUnit.Minute)
            elif timeframe == '1Min':
                tf = TimeFrame(1, TimeFrameUnit.Minute)
            else:
                raise ValueError(f"Unsupported timeframe: {timeframe}")
            
            print(f"--- Mapped timeframe string '{timeframe}' to TimeFrame object: {tf} ---")

            # Calculate date range
            if start_date is None or end_date is None:
                end_date = datetime.now(timezone.utc) - timedelta(minutes=15)  # Add 15-minute delay
                if lookback_days is not None:
                    start_date = end_date - timedelta(days=lookback_days)
                else:
                    start_date = end_date - timedelta(days=30)  # Default to 30 days
            
            print(f"--- Fetching data from {start_date} to {end_date} ---")
            
            # Create request parameters for historical bars
            request_params = StockBarsRequest(
                symbol_or_symbols=[symbol],  # Pass as list
                timeframe=tf,
                start=start_date,
                end=end_date,
                limit=limit,
                feed='iex'  # Use IEX feed for better compatibility
            )
            
            print(f"--- Request parameters constructed: {request_params} ---")
            
            # Get the historical bars
            bars_response = self.market_data_client.get_stock_bars(request_params)
            print(f"--- Raw response type: {type(bars_response)} ---")
            
            if not bars_response or symbol not in bars_response:
                raise HTTPException(status_code=400, detail=f"No bars data returned for symbol {symbol}")
            
            # Extract bars for the symbol
            bars = bars_response[symbol]
            print(f"--- Number of bars received for {symbol}: {len(bars)} ---")
            
            # Convert bars to a list of dictionaries with the correct attributes
            processed_bars = []
            for bar in bars:
                processed_bars.append({
                    'timestamp': bar.timestamp,
                    'open': float(bar.open),
                    'high': float(bar.high),
                    'low': float(bar.low),
                    'close': float(bar.close),
                    'volume': float(bar.volume)
                })
            
            return processed_bars

        except Exception as e:
            print(f"!!! Error getting historical bars: {e!r}")
            raise HTTPException(status_code=400, detail=str(e))

    async def get_latest_price(self, symbol: str) -> Optional[float]:
        """Fetches the latest ask price for a given stock symbol with caching."""
        print(f"--- Fetching latest quote for {symbol} ---")
        try:
            # Check cache first
            cached_price = self._get_cached_data(f"price_{symbol}")
            if cached_price is not None:
                print(f"--- Using cached price for {symbol}: {cached_price} ---")
                return cached_price

            if not hasattr(self, 'market_data_client'):
                raise ValueError("Market data client not initialized")
            
            request_params = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            latest_quote_response = self.market_data_client.get_stock_latest_quote(request_params)
            
            quote = latest_quote_response.get(symbol)
            
            if not quote:
                logger.warning(f"Could not get latest quote for {symbol}")
                return None
            
            latest_price = quote.ask_price
            print(f"--- Latest ask price for {symbol}: {latest_price} ---")
            
            # Cache the price
            self._set_cached_data(f"price_{symbol}", float(latest_price))
            
            return float(latest_price)

        except Exception as e:
            logger.error(f"!!! Exception fetching latest quote for {symbol}: {e!r}")
            return None

    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get the current position for a symbol."""
        try:
            position = self.trading_client.get_position(symbol)
            if position:
                return Position(
                    symbol=symbol,
                    quantity=float(position.qty),
                    entry_price=float(position.avg_entry_price),
                    current_price=float(position.current_price),
                    status=PositionStatus.OPEN,
                    timestamp=datetime.utcnow()
                )
            return None
        except Exception as e:
            logger.error(f"Error getting position for {symbol}: {str(e)}")
            return None

    async def close_position(self, symbol: str) -> Optional[Trade]:
        """Close an existing position."""
        try:
            position = await self.get_position(symbol)
            if not position:
                logger.warning(f"No position found for {symbol}")
                return None
            
            # Place an order to close the position
            side = OrderSide.SELL if position.quantity > 0 else OrderSide.BUY
            return await self.place_order(symbol, abs(position.quantity), side)
            
        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {str(e)}")
            return None

    async def get_account_balance(self) -> float:
        """Get the current account balance."""
        try:
            account = self.trading_client.get_account()
            return float(account.cash)
        except Exception as e:
            logger.error(f"Error getting account balance: {str(e)}")
            return 0.0 

    async def get_portfolio_history(
        self,
        period: str = "1M",
        timeframe: Optional[str] = None,
        date_end: Optional[datetime] = None,
        extended_hours: bool = False
    ) -> Optional[PortfolioHistory]:
        """Fetches portfolio history from Alpaca API using a direct HTTP request."""
        print(f"--- Fetching portfolio history via HTTP (period={period}, timeframe={timeframe}) ---")
        
        # Construct the API endpoint URL
        endpoint = f"{self.base_url}/v2/account/portfolio/history"
        
        # Prepare query parameters, filtering out None values
        params = {
            "period": period,
            "timeframe": timeframe,
            "date_end": date_end.isoformat() if date_end else None, # Format datetime if provided
            "extended_hours": str(extended_hours).lower() # Convert bool to lower string
        }
        query_params = {k: v for k, v in params.items() if v is not None}
        
        # Prepare headers
        headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
            "accept": "application/json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(endpoint, params=query_params, headers=headers)
                
            # Log status code
            print(f"--- Portfolio History API Response Status: {response.status_code} ---")
            
            # Check for successful response
            response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx responses
            
            # Parse the JSON response
            data = response.json()
            print(f"--- Portfolio History API Raw JSON Response: {data} ---")
            
            # Construct the PortfolioHistory object from the response data
            # Handle potential None values if API response fields are optional
            history = PortfolioHistory(
                timestamp=data.get('timestamp', []),
                equity=data.get('equity', []),
                profit_loss=data.get('profit_loss', []),
                profit_loss_pct=data.get('profit_loss_pct', []),
                base_value=data.get('base_value', 0.0), # Provide default if missing
                timeframe=data.get('timeframe', '') # Provide default if missing
                # Add other fields if they exist in the API response and model
            )
            
            print(f"--- Successfully parsed portfolio history. Timestamps: {len(history.timestamp)}, Equity points: {len(history.equity)} ---")
            return history
            
        except httpx.HTTPStatusError as e:
            # Log HTTP errors (e.g., 401 Unauthorized, 404 Not Found, 400 Bad Request)
            logger.error(f"!!! HTTP Error fetching portfolio history: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.RequestError as e:
            # Log other request errors (e.g., network issues)
            logger.error(f"!!! Request Error fetching portfolio history: {e!r}")
            return None
        except Exception as e:
            # Catch-all for other unexpected errors (e.g., JSON parsing)
            logger.error(f"!!! Unexpected error processing portfolio history: {e!r}")
            return None

    async def is_asset_valid(self, symbol: str) -> bool:
        """Checks if an asset symbol exists and is tradable on Alpaca."""
        print(f"--- Validating asset symbol: {symbol} ---")
        try:
            if not hasattr(self, 'trading_client'):
                logger.error("Trading client not initialized during asset validation.")
                return False # Or raise an internal error
            
            asset = self.trading_client.get_asset(symbol)
            if asset and asset.tradable:
                print(f"--- Asset {symbol} is valid and tradable. Status: {asset.status} ---")
                return True
            else:
                status = asset.status if asset else 'Not Found'
                tradable_status = asset.tradable if asset else 'N/A'
                logger.warning(f"Asset {symbol} is not valid/tradable. Status: {status}, Tradable: {tradable_status}")
                return False
        except APIError as e:
             # Specifically catch APIError for cases like 404 Not Found
             if e.status_code == 404:
                 logger.warning(f"Asset {symbol} not found on Alpaca.")
             else:
                 logger.error(f"!!! API Error validating asset {symbol}: {e!r}")
             return False
        except Exception as e:
            logger.error(f"!!! Unexpected error validating asset {symbol}: {e!r}")
            return False # Treat unexpected errors as invalid for safety