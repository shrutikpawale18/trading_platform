from enum import Enum
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class Signal(BaseModel):
    type: SignalType
    symbol: str
    timestamp: datetime
    confidence: float
    metadata: Optional[dict] = None

    class Config:
        use_enum_values = True 