from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.models.db_models import (
    Algorithm, Signal, Position, Trade,
    AlgorithmType, SignalType, PositionStatus, TradeType, TradeStatus
)

class DatabaseService:
    def __init__(self, db: Session):
        self.db = db

    # Algorithm operations
    def create_algorithm(self, symbol: str, type: AlgorithmType, parameters: dict) -> Algorithm:
        algorithm = Algorithm(
            symbol=symbol,
            type=type,
            parameters=parameters
        )
        self.db.add(algorithm)
        self.db.commit()
        self.db.refresh(algorithm)
        return algorithm

    def get_algorithm(self, algorithm_id: int) -> Optional[Algorithm]:
        return self.db.query(Algorithm).filter(Algorithm.id == algorithm_id).first()

    def get_algorithms_by_symbol(self, symbol: str) -> List[Algorithm]:
        return self.db.query(Algorithm).filter(Algorithm.symbol == symbol).all()

    # Signal operations
    def create_signal(
        self,
        algorithm_id: int,
        symbol: str,
        type: SignalType,
        confidence: float,
        metadata: Optional[dict] = None
    ) -> Signal:
        signal = Signal(
            algorithm_id=algorithm_id,
            symbol=symbol,
            type=type,
            confidence=confidence,
            metadata=metadata
        )
        self.db.add(signal)
        self.db.commit()
        self.db.refresh(signal)
        return signal

    def get_signals_by_algorithm(self, algorithm_id: int) -> List[Signal]:
        return self.db.query(Signal).filter(Signal.algorithm_id == algorithm_id).all()

    # Position operations
    def create_position(
        self,
        symbol: str,
        quantity: float,
        entry_price: float,
        current_price: float,
        metadata: Optional[dict] = None
    ) -> Position:
        position = Position(
            symbol=symbol,
            quantity=quantity,
            entry_price=entry_price,
            current_price=current_price,
            status=PositionStatus.OPEN,
            entry_time=datetime.utcnow(),
            metadata=metadata
        )
        self.db.add(position)
        self.db.commit()
        self.db.refresh(position)
        return position

    def update_position(
        self,
        position_id: int,
        current_price: float,
        status: Optional[PositionStatus] = None
    ) -> Optional[Position]:
        position = self.db.query(Position).filter(Position.id == position_id).first()
        if position:
            position.current_price = current_price
            if status:
                position.status = status
            self.db.commit()
            self.db.refresh(position)
        return position

    def get_open_positions(self) -> List[Position]:
        return self.db.query(Position).filter(Position.status == PositionStatus.OPEN).all()

    # Trade operations
    def create_trade(
        self,
        symbol: str,
        quantity: float,
        price: float,
        side: TradeType,
        order_id: str,
        signal_id: Optional[int] = None,
        position_id: Optional[int] = None,
        metadata: Optional[dict] = None
    ) -> Trade:
        trade = Trade(
            symbol=symbol,
            quantity=quantity,
            price=price,
            side=side,
            status=TradeStatus.PENDING,
            order_id=order_id,
            signal_id=signal_id,
            position_id=position_id,
            metadata=metadata
        )
        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)
        return trade

    def update_trade_status(
        self,
        order_id: str,
        status: TradeStatus,
        filled_at: Optional[datetime] = None
    ) -> Optional[Trade]:
        trade = self.db.query(Trade).filter(Trade.order_id == order_id).first()
        if trade:
            trade.status = status
            if filled_at:
                trade.filled_at = filled_at
            self.db.commit()
            self.db.refresh(trade)
        return trade

    def get_trades_by_position(self, position_id: int) -> List[Trade]:
        return self.db.query(Trade).filter(Trade.position_id == position_id).all()

    def get_trades_by_signal(self, signal_id: int) -> List[Trade]:
        return self.db.query(Trade).filter(Trade.signal_id == signal_id).all() 