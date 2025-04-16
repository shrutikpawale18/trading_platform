import pytest
from datetime import datetime, timedelta, timezone
from app.services.alpaca_service import AlpacaService
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@pytest.mark.asyncio
async def test_get_historical_bars():
    # Initialize Alpaca service
    api_key = os.getenv("APCA_API_KEY_ID")
    secret_key = os.getenv("APCA_API_SECRET_KEY")
    service = AlpacaService(api_key_id=api_key, secret_key=secret_key)
    
    # Test with AAPL using a date range from last month
    symbol = "AAPL"
    timeframe = "1D"
    end_date = datetime(2024, 3, 15, tzinfo=timezone.utc)  # March 15th
    start_date = end_date - timedelta(days=5)  # 5 days before March 15th
    
    try:
        # Get historical bars with fixed dates
        bars = await service.get_historical_bars(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date
        )
        
        # Verify the response
        assert bars is not None, "No bars returned"
        assert len(bars) > 0, "Empty bars list"
        
        # Check the structure of the first bar
        first_bar = bars[0]
        assert 'timestamp' in first_bar, "Missing timestamp"
        assert 'open' in first_bar, "Missing open price"
        assert 'high' in first_bar, "Missing high price"
        assert 'low' in first_bar, "Missing low price"
        assert 'close' in first_bar, "Missing close price"
        assert 'volume' in first_bar, "Missing volume"
        
        print(f"Successfully retrieved {len(bars)} bars for {symbol}")
        print(f"First bar: {first_bar}")
        
    except Exception as e:
        pytest.fail(f"Error in get_historical_bars: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_get_historical_bars()) 