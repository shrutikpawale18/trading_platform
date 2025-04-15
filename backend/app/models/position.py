from enum import Enum
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class PositionStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"

class Position(BaseModel):
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    status: PositionStatus
    entry_time: datetime
    last_updated: datetime
    unrealized_pnl: float
    metadata: Optional[dict] = None

    class Config:
        use_enum_values = True

    @property
    def unrealized_pnl(self) -> float:
        return (self.current_price - self.entry_price) * self.quantity

    @property
    def unrealized_pnl_percent(self) -> float:
        return ((self.current_price - self.entry_price) / self.entry_price) * 100 