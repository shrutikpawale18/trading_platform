from enum import Enum
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class TradeType(str, Enum):
    BUY = "buy"
    SELL = "sell"

class TradeStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class Trade(BaseModel):
    symbol: str
    quantity: float
    price: float
    side: TradeType
    status: TradeStatus
    order_id: str
    created_at: datetime
    filled_at: Optional[datetime] = None
    metadata: Optional[dict] = None

    class Config:
        use_enum_values = True

    @property
    def notional_value(self) -> Optional[float]:
        if self.price is None:
            return None
        return self.quantity * self.price 