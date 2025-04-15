from alpaca.data.historical import StockHistoricalDataClient
from alpaca.trading.client import TradingClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame
from fastapi import HTTPException
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from alpaca.trading.requests import MarketOrderRequest, GetPortfolioHistoryRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from typing import Dict, List, Optional
import logging
from app.models.position import Position, PositionStatus
from app.models.trade import Trade, TradeType, TradeStatus
from alpaca.trading.models import PortfolioHistory
import httpx

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
            return {
                "order_id": order.id,
                "client_order_id": order.client_order_id,
                "status": order.status,
                "symbol": order.symbol,
                "qty": str(order.qty),
                "filled_qty": str(order.filled_qty),
                "filled_avg_price": str(order.filled_avg_price) if order.filled_avg_price else None
            }
        except Exception as e:
            print(f"!!! Exception during place_order: {e!r}")
            raise HTTPException(status_code=400, detail=str(e))
    
    async def get_order_status(self, order_id: str):
        print(f"--- Calling get_order() for {order_id} ---")
        try:
            # Note: This would need to be implemented with the trading API client
            # For now, returning a mock response
            return {
                "order_id": order_id,
                "client_order_id": "mock_client_order_id",
                "status": "filled",
                "filled_avg_price": "100.00",
                "qty": "1",
                "filled_qty": "1",
                "symbol": "AAPL"
            }
        except Exception as e:
            print(f"!!! Exception during get_order_status: {e!r}")
            raise HTTPException(status_code=400, detail=str(e))

    async def get_open_orders(self):
        print("--- Calling list_orders() with status=open ---")
        try:
            # Note: This would need to be implemented with the trading API client
            # For now, returning a mock response
            return []
        except Exception as e:
            print(f"!!! Exception during get_open_orders: {e!r}")
            raise HTTPException(status_code=400, detail=str(e))

    async def cancel_order(self, order_id: str):
        print(f"--- Calling cancel_order() for {order_id} ---")
        try:
            # Note: This would need to be implemented with the trading API client
            # For now, returning a mock response
            return {"status": "cancelled"}
        except Exception as e:
            print(f"!!! Exception during cancel_order: {e!r}")
            raise HTTPException(status_code=400, detail=str(e))

    async def get_assets(self):
        print("--- Calling list_assets() ---")
        try:
            # Note: This would need to be implemented with the trading API client
            # For now, returning a mock response
            return []
        except Exception as e:
            print(f"!!! Exception during get_assets: {e!r}")
            raise HTTPException(status_code=400, detail=str(e))

    async def get_historical_bars(self, symbol: str, timeframe: str = '1D', lookback_days: int = None, limit: int = 1000):
        print(f"--- Getting historical bars for {symbol} with timeframe={timeframe}, lookback_days={lookback_days}, limit={limit} ---")
        try:
            # Convert timeframe string to TimeFrame object
            timeframe_map = {
                '1D': TimeFrame.Day,
                '1H': TimeFrame.Hour,
                '15Min': TimeFrame(15, TimeFrame.Minute),
                '5Min': TimeFrame(5, TimeFrame.Minute),
                '1Min': TimeFrame(1, TimeFrame.Minute)
            }
            
            # Get the timeframe or raise an error if not supported
            if timeframe not in timeframe_map:
                raise ValueError(f"Unsupported timeframe: {timeframe}. Supported timeframes are: {list(timeframe_map.keys())}")
            
            tf = timeframe_map[timeframe]
            print(f"--- Using TimeFrame object: {tf} ---")
            
            # Calculate start date based on lookback_days
            end_date = datetime.now()
            if lookback_days is not None:
                # Add a buffer to ensure enough trading days are covered
                start_date = end_date - timedelta(days=int(lookback_days * 1.5) + 1) 
            else:
                start_date = end_date - timedelta(days=45) # Default buffer for 30 days
            
            # Format dates as YYYY-MM-DD strings
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")
            
            print(f"--- Fetching data from {start_date_str} to {end_date_str} ---")
            
            # Create request parameters for historical bars
            request_params = StockBarsRequest(
                symbol_or_symbols=[symbol],  # Pass as list
                timeframe=tf,
                start=start_date_str,
                end=end_date_str,
                limit=limit # Use the limit parameter
            )
            
            print(f"--- Request parameters: {request_params} ---")
            
            # Get the historical bars
            bars_response = self.market_data_client.get_stock_bars(request_params)
            print(f"--- Raw response type: {type(bars_response)} ---")
            
            if not bars_response:
                raise HTTPException(status_code=400, detail=f"No bars data returned for symbol {symbol}")

            # Get bars for the specific symbol
            symbol_bars = bars_response.data.get(symbol, [])
            print(f"--- Number of bars received for {symbol}: {len(symbol_bars)} ---")

            if not symbol_bars:
                raise HTTPException(status_code=400, detail=f"No bars available in response for symbol {symbol}")

            # Convert bars to list of closing prices
            prices = []
            for bar in symbol_bars:
                try:
                    # Each bar object has attributes like 'close', 'high', 'low', etc.
                    if hasattr(bar, 'close'):
                        prices.append(bar.close)
                    else:
                        print(f"--- Unexpected bar object format (missing 'close'): {bar} ---")
                        continue
                except Exception as e:
                    print(f"--- Error processing bar: {e!r}, bar: {bar} ---")
                    continue
            
            if not prices:
                print(f"--- No prices could be extracted from bars ---")
                print(f"--- First bar sample: {symbol_bars[0] if symbol_bars else 'No bars'} ---")
                raise HTTPException(status_code=400, detail=f"Could not extract closing prices from bars for symbol {symbol}")
            
            print(f"--- Extracted {len(prices)} price points for {symbol} ---")
            print(f"--- First price: {prices[0] if prices else 'None'}, Last price: {prices[-1] if prices else 'None'} ---")
            
            # Check if we have enough data points for the algorithm
            if len(prices) < 20:  # Minimum required for long window
                print(f"--- Warning: Not enough data ({len(prices)}) for long window (20). Adjust lookback or timeframe? ---")
                raise HTTPException(
                    status_code=400,
                    detail=f"Not enough price data ({len(prices)}) for the long window (20). Try increasing lookback_days or using a different timeframe."
                )
            
            # Ensure we don't exceed the requested limit (if provided)
            if limit and len(prices) > limit:
                prices = prices[-limit:]
                print(f"--- Truncated prices to requested limit: {limit} ---")

            return prices
            
        except Exception as e:
            print(f"!!! Exception during get_historical_bars: {e!r}")
            print(f"!!! Exception Type: {type(e).__name__}, Message: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error fetching historical bars: {str(e)}")

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

    async def place_order(self, symbol: str, quantity: float, side: OrderSide) -> Optional[Trade]:
        """Place a market order."""
        try:
            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=side,
                time_in_force=TimeInForce.DAY
            )
            
            order = self.trading_client.submit_order(order_data)
            
            return Trade(
                symbol=symbol,
                type=TradeType.BUY if side == OrderSide.BUY else TradeType.SELL,
                quantity=quantity,
                price=float(order.filled_avg_price) if order.filled_avg_price else None,
                status=TradeStatus.FILLED if order.status == 'filled' else TradeStatus.PENDING,
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            logger.error(f"Error placing order for {symbol}: {str(e)}")
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