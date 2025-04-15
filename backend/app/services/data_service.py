from typing import Optional, List
from datetime import datetime, timedelta
import pandas as pd
import logging
from app.services.alpaca_service import AlpacaService

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
            # Get historical bars from Alpaca
            bars = await self.alpaca_service.get_historical_bars(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date
            )
            
            if not bars:
                logger.warning(f"No data returned for {symbol}")
                return pd.DataFrame()

            # Convert bars to DataFrame
            df = pd.DataFrame([{
                'timestamp': bar.t,
                'open': bar.o,
                'high': bar.h,
                'low': bar.l,
                'close': bar.c,
                'volume': bar.v
            } for bar in bars])
            
            # Set timestamp as index
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            return df

        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {str(e)}")
            return pd.DataFrame()

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