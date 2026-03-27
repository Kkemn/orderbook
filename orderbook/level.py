from collections import deque
from decimal import Decimal
from typing import Deque, Iterator
from .order import Order


class PriceLevel:
    """All orders at a single price point, maintained in FIFO order."""

    def __init__(self, price: Decimal) -> None:
        self.price = price
        self._orders: Deque[Order] = deque()

    def add(self, order: Order) -> None:
        self._orders.append(order)

    def remove(self, order_id: str) -> bool:
        for i, order in enumerate(self._orders):
            if order.order_id == order_id:
                del self._orders[i]
                return True
        return False

    @property
    def total_quantity(self) -> Decimal:
        return sum(o.remaining_quantity for o in self._orders)

    @property
    def order_count(self) -> int:
        return len(self._orders)

    def __iter__(self) -> Iterator[Order]:
        return iter(self._orders)

    def __bool__(self) -> bool:
        return bool(self._orders)

    def __repr__(self) -> str:
        return f"PriceLevel(price={self.price}, qty={self.total_quantity}, orders={self.order_count})"
