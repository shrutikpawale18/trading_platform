from typing import Optional, List
from datetime import datetime, timedelta
import pandas as pd
import logging
from app.services.alpaca_service import AlpacaService
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class DataService:
    def __init__(self, alpaca_service: AlpacaService):
        self.alpaca_service = alpaca_service

    async def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = '1D'
    ) -> pd.DataFrame:
        """Get historical market data for a symbol."""
        try:
            # Calculate lookback period
            lookback_days = (end_date - start_date).days
            print(f"--- Calculated lookback period: {lookback_days} days ---")
            
            # Get historical bars from Alpaca
            bars = await self.alpaca_service.get_historical_bars(
                symbol=symbol,
                timeframe=timeframe,
                lookback_days=lookback_days
            )
            
            if not bars:
                print(f"Warning: No bars returned for {symbol}")
                return pd.DataFrame()
            
            print(f"--- Received {len(bars)} bars from Alpaca ---")
            
            # Create DataFrame from the processed bars
            df = pd.DataFrame(bars)
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            print(f"--- Created DataFrame with shape: {df.shape} ---")
            print(f"--- DataFrame columns: {df.columns.tolist()} ---")
            print(f"--- First few rows of DataFrame:\n{df.head()} ---")
            
            return df
            
        except Exception as e:
            print(f"!!! Error in get_historical_data: {e!r}")
            raise HTTPException(status_code=400, detail=str(e))

    async def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get the latest price for a symbol."""
        try:
            # Get latest quote from Alpaca
            quote = await self.alpaca_service.get_latest_quote(symbol)
            if quote:
                return float(quote.c)
            return None
        except Exception as e:
            logger.error(f"Error getting latest price for {symbol}: {str(e)}")
            return None

    async def get_market_status(self) -> bool:
        """Check if the market is currently open."""
        try:
            clock = await self.alpaca_service.get_clock()
            return clock.is_open
        except Exception as e:
            logger.error(f"Error getting market status: {str(e)}")
            return False 