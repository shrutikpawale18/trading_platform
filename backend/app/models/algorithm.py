from enum import Enum
from typing import Dict, Any
from pydantic import BaseModel

class AlgorithmType(str, Enum):
    MOVING_AVERAGE_CROSSOVER = "moving_average_crossover"
    RSI = "rsi"
    MACD = "macd"
    BOLLINGER_BANDS = "bollinger_bands"

class Algorithm(BaseModel):
    symbol: str
    type: AlgorithmType
    parameters: Dict[str, Any]

    class Config:
        use_enum_values = True 