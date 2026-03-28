from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime, timezone
import uuid


@dataclass
class Trade:
    buy_order_id: str
    sell_order_id: str
    price: Decimal
    quantity: Decimal
    trade_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return (
            f"Trade(id={self.trade_id[:8]}, price={self.price}, "
            f"qty={self.quantity}, at={self.timestamp.strftime('%H:%M:%S.%f')})"
        )
