from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal
from datetime import datetime
import uuid


class Side(Enum):
    BID = "bid"
    ASK = "ask"


class OrderType(Enum):
    LIMIT = "limit"
    MARKET = "market"


class OrderStatus(Enum):
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"


@dataclass
class Order:
    side: Side
    price: Decimal  # None for market orders
    quantity: Decimal
    order_type: OrderType = OrderType.LIMIT
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    status: OrderStatus = field(default=OrderStatus.OPEN)
    filled_quantity: Decimal = field(default=Decimal("0"))

    @property
    def remaining_quantity(self) -> Decimal:
        return self.quantity - self.filled_quantity

    @property
    def is_fully_filled(self) -> bool:
        return self.filled_quantity >= self.quantity

    def fill(self, quantity: Decimal) -> None:
        self.filled_quantity += quantity
        if self.is_fully_filled:
            self.status = OrderStatus.FILLED
        else:
            self.status = OrderStatus.PARTIALLY_FILLED

    def cancel(self) -> None:
        self.status = OrderStatus.CANCELLED

    def __repr__(self) -> str:
        return (
            f"Order(id={self.order_id[:8]}, side={self.side.value}, "
            f"price={self.price}, qty={self.quantity}, "
            f"filled={self.filled_quantity}, status={self.status.value})"
        )
