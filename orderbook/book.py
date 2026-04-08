from decimal import Decimal
from sortedcontainers import SortedDict
from typing import List, Dict, Tuple
from .order import Order, Side, OrderType, OrderStatus
from .level import PriceLevel
from .trade import Trade


class OrderBook:
    """
    Price-time priority limit order book.

    Bids: sorted descending (highest price first — best bid on top).
    Asks: sorted ascending (lowest price first — best ask on top).
    """

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        # Negative key trick: store bids with negated price so SortedDict
        # gives us descending order via normal ascending iteration.
        self._bids: SortedDict = SortedDict()   # {-price: PriceLevel}
        self._asks: SortedDict = SortedDict()   # { price: PriceLevel}
        self._orders: Dict[str, Order] = {}
        self.trades: List[Trade] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_order(self, order: Order) -> List[Trade]:
        """Add a new order to the book. Returns any trades that resulted."""
        self._orders[order.order_id] = order
        if order.order_type == OrderType.MARKET:
            return self._match_market(order)
        return self._match_limit(order)

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order. Returns True if found and cancelled."""
        order = self._orders.get(order_id)
        if order is None or order.status in (OrderStatus.FILLED, OrderStatus.CANCELLED):
            return False
        order.cancel()
        self._remove_from_book(order)
        return True

    # ------------------------------------------------------------------
    # Best prices
    # ------------------------------------------------------------------

    @property
    def best_bid(self) -> Decimal | None:
        if not self._bids:
            return None
        neg_price = self._bids.keys()[0]
        return -neg_price

    @property
    def best_ask(self) -> Decimal | None:
        if not self._asks:
            return None
        return self._asks.keys()[0]

    @property
    def spread(self) -> Decimal | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return self.best_ask - self.best_bid

    @property
    def mid_price(self) -> Decimal | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return (self.best_bid + self.best_ask) / 2

    # ------------------------------------------------------------------
    # Depth snapshots
    # ------------------------------------------------------------------

    def bids_depth(self, levels: int = 10) -> List[Tuple[Decimal, Decimal]]:
        """Return [(price, total_qty), ...] for top N bid levels."""
        result = []
        for neg_price, level in self._bids.items():
            result.append((-neg_price, level.total_quantity))
            if len(result) >= levels:
                break
        return result

    def asks_depth(self, levels: int = 10) -> List[Tuple[Decimal, Decimal]]:
        """Return [(price, total_qty), ...] for top N ask levels."""
        result = []
        for price, level in self._asks.items():
            result.append((price, level.total_quantity))
            if len(result) >= levels:
                break
        return result

    # ------------------------------------------------------------------
    # Matching engine
    # ------------------------------------------------------------------

    def _match_limit(self, order: Order) -> List[Trade]:
        trades = []
        if order.side == Side.BID:
            trades = self._fill_against_asks(order)
            if not order.is_fully_filled and order.status != OrderStatus.CANCELLED:
                self._insert_bid(order)
        else:
            trades = self._fill_against_bids(order)
            if not order.is_fully_filled and order.status != OrderStatus.CANCELLED:
                self._insert_ask(order)
        self.trades.extend(trades)
        return trades

    def _match_market(self, order: Order) -> List[Trade]:
        if order.side == Side.BID:
            trades = self._fill_against_asks(order)
        else:
            trades = self._fill_against_bids(order)
        # Unfilled remainder of a market order is cancelled
        if not order.is_fully_filled:
            order.cancel()
        self.trades.extend(trades)
        return trades

    def _fill_against_asks(self, bid: Order) -> List[Trade]:
        trades = []
        while self._asks and not bid.is_fully_filled:
            best_ask_price = self._asks.keys()[0]
            if bid.order_type == OrderType.LIMIT and bid.price < best_ask_price:
                break
            level = self._asks[best_ask_price]
            trades.extend(self._fill_level(bid, level, best_ask_price))
            if not level:
                del self._asks[best_ask_price]
        return trades

    def _fill_against_bids(self, ask: Order) -> List[Trade]:
        trades = []
        while self._bids and not ask.is_fully_filled:
            neg_price = self._bids.keys()[0]
            best_bid_price = -neg_price
            if ask.order_type == OrderType.LIMIT and ask.price > best_bid_price:
                break
            level = self._bids[neg_price]
            trades.extend(self._fill_level(ask, level, best_bid_price))
            if not level:
                del self._bids[neg_price]
        return trades

    def _fill_level(self, aggressor: Order, level: PriceLevel, fill_price: Decimal) -> List[Trade]:
        trades = []
        to_remove = []
        for passive in level:
            if aggressor.is_fully_filled:
                break
            fill_qty = min(aggressor.remaining_quantity, passive.remaining_quantity)
            aggressor.fill(fill_qty)
            passive.fill(fill_qty)
            if aggressor.side == Side.BID:
                trade = Trade(aggressor.order_id, passive.order_id, fill_price, fill_qty)
            else:
                trade = Trade(passive.order_id, aggressor.order_id, fill_price, fill_qty)
            trades.append(trade)
            if passive.is_fully_filled:
                to_remove.append(passive.order_id)
        for oid in to_remove:
            level.remove(oid)
        return trades

    # ------------------------------------------------------------------
    # Book insertion helpers
    # ------------------------------------------------------------------

    def _insert_bid(self, order: Order) -> None:
        key = -order.price
        if key not in self._bids:
            self._bids[key] = PriceLevel(order.price)
        self._bids[key].add(order)

    def _insert_ask(self, order: Order) -> None:
        key = order.price
        if key not in self._asks:
            self._asks[key] = PriceLevel(order.price)
        self._asks[key].add(order)

    def _remove_from_book(self, order: Order) -> None:
        if order.side == Side.BID:
            key = -order.price
            level = self._bids.get(key)
            if level:
                level.remove(order.order_id)
                if not level:
                    del self._bids[key]
        else:
            key = order.price
            level = self._asks.get(key)
            if level:
                level.remove(order.order_id)
                if not level:
                    del self._asks[key]

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        lines = [f"=== OrderBook [{self.symbol}] ==="]
        lines.append(f"  Best bid: {self.best_bid}  Best ask: {self.best_ask}  Spread: {self.spread}")
        lines.append("  ASKS (lowest first):")
        for price, qty in reversed(self.asks_depth(5)):
            lines.append(f"    {price:>12}  {qty:>12}")
        lines.append("  " + "-" * 28)
        lines.append("  BIDS (highest first):")
        for price, qty in self.bids_depth(5):
            lines.append(f"    {price:>12}  {qty:>12}")
        return "\n".join(lines)
