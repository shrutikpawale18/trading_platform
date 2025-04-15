from sqlalchemy import Column, Integer, String, Float, DateTime, Enum as SQLEnum, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

# --- Enums --- (Keep these defined first)
class AlgorithmType(enum.Enum):
    MOVING_AVERAGE_CROSSOVER = "moving_average_crossover"
    RSI = "rsi"
    MACD = "macd"
    BOLLINGER_BANDS = "bollinger_bands"

class SignalType(enum.Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

class PositionStatus(enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"

class TradeType(enum.Enum):
    BUY = "buy"
    SELL = "sell"

class TradeStatus(enum.Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

# --- Models --- (Define independent models first, then dependent ones)

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True) # Keep String ID from original User model
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships defined after related models
    algorithms = relationship("Algorithm", back_populates="user")
    positions = relationship("Position", back_populates="user") # Add relationship from User to Position
    trades = relationship("Trade", back_populates="user")       # Add relationship from User to Trade

class Algorithm(Base):
    __tablename__ = "algorithms"

    id = Column(Integer, primary_key=True, index=True) # Keep Integer ID for Algorithm
    user_id = Column(String, ForeignKey("users.id")) # Foreign key to User.id (String)
    symbol = Column(String, index=True)
    type = Column(SQLEnum(AlgorithmType))
    parameters = Column(JSON)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="algorithms")
    signals = relationship("Signal", back_populates="algorithm")

class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True) # Keep Integer ID for Signal
    algorithm_id = Column(Integer, ForeignKey("algorithms.id")) # Foreign key to Algorithm.id (Integer)
    type = Column(SQLEnum(SignalType))
    symbol = Column(String, index=True)
    confidence = Column(Float) # Use confidence from db_models.py (strength was in database.py)
    additional_data = Column(JSON, nullable=True) # Keep renamed metadata
    created_at = Column(DateTime, default=datetime.utcnow) # Use created_at (timestamp was in database.py)

    algorithm = relationship("Algorithm", back_populates="signals")
    trades = relationship("Trade", back_populates="signal")

class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True) # Keep Integer ID for Position
    user_id = Column(String, ForeignKey("users.id")) # Add user_id ForeignKey from database.py definition
    symbol = Column(String, index=True)
    quantity = Column(Float)
    entry_price = Column(Float)
    current_price = Column(Float)
    status = Column(SQLEnum(PositionStatus))
    entry_time = Column(DateTime) # Keep entry_time (timestamp was in database.py)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    additional_data = Column(JSON, nullable=True) # Keep renamed metadata

    user = relationship("User", back_populates="positions") # Add relationship back to User
    trades = relationship("Trade", back_populates="position")

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True) # Keep Integer ID for Trade
    user_id = Column(String, ForeignKey("users.id")) # Add user_id ForeignKey from database.py definition
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=True) # Foreign key to Signal.id (Integer)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=True) # Foreign key to Position.id (Integer)
    symbol = Column(String, index=True)
    quantity = Column(Float)
    price = Column(Float)
    side = Column(SQLEnum(TradeType)) # Keep side (type was in database.py)
    status = Column(SQLEnum(TradeStatus))
    order_id = Column(String, unique=True) # Keep order_id
    created_at = Column(DateTime, default=datetime.utcnow) # Keep created_at (timestamp was in database.py)
    filled_at = Column(DateTime, nullable=True)
    additional_data = Column(JSON, nullable=True) # Keep renamed metadata

    user = relationship("User", back_populates="trades") # Add relationship back to User
    signal = relationship("Signal", back_populates="trades")
    position = relationship("Position", back_populates="trades") 