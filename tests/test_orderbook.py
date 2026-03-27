import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from decimal import Decimal
from orderbook import Order, OrderBook, Side, OrderType, OrderStatus


def make_book():
    return OrderBook("BTC/USD")


def bid(price, qty):
    return Order(side=Side.BID, price=Decimal(str(price)), quantity=Decimal(str(qty)))


def ask(price, qty):
    return Order(side=Side.ASK, price=Decimal(str(price)), quantity=Decimal(str(qty)))


# ------------------------------------------------------------------
# Basic insertion
# ------------------------------------------------------------------

def test_add_bid_no_match():
    book = make_book()
    o = bid(100, 1)
    trades = book.add_order(o)
    assert trades == []
    assert book.best_bid == Decimal("100")
    assert book.best_ask is None


def test_add_ask_no_match():
    book = make_book()
    o = ask(101, 1)
    trades = book.add_order(o)
    assert trades == []
    assert book.best_ask == Decimal("101")
    assert book.best_bid is None


def test_spread():
    book = make_book()
    book.add_order(bid(100, 1))
    book.add_order(ask(102, 1))
    assert book.spread == Decimal("2")
    assert book.mid_price == Decimal("101")


# ------------------------------------------------------------------
# Matching
# ------------------------------------------------------------------

def test_exact_match():
    book = make_book()
    book.add_order(ask(100, 5))
    trades = book.add_order(bid(100, 5))
    assert len(trades) == 1
    assert trades[0].price == Decimal("100")
    assert trades[0].quantity == Decimal("5")
    assert book.best_bid is None
    assert book.best_ask is None


def test_partial_fill_resting():
    book = make_book()
    book.add_order(ask(100, 10))
    trades = book.add_order(bid(100, 3))
    assert len(trades) == 1
    assert trades[0].quantity == Decimal("3")
    assert book.best_ask == Decimal("100")
    assert book.asks_depth()[0][1] == Decimal("7")


def test_partial_fill_aggressor():
    book = make_book()
    book.add_order(ask(100, 3))
    trades = book.add_order(bid(100, 10))
    assert len(trades) == 1
    assert trades[0].quantity == Decimal("3")
    assert book.best_bid == Decimal("100")
    assert book.bids_depth()[0][1] == Decimal("7")


def test_price_priority():
    book = make_book()
    book.add_order(ask(102, 5))
    book.add_order(ask(101, 5))
    book.add_order(ask(103, 5))
    assert book.best_ask == Decimal("101")


def test_time_priority():
    book = make_book()
    a1 = ask(100, 3)
    a2 = ask(100, 7)
    book.add_order(a1)
    book.add_order(a2)
    # aggressor fills 3 — should take from a1 first
    trades = book.add_order(bid(100, 3))
    assert trades[0].sell_order_id == a1.order_id
    assert a1.status == OrderStatus.FILLED
    assert a2.status == OrderStatus.OPEN


def test_multiple_levels_filled():
    book = make_book()
    book.add_order(ask(100, 2))
    book.add_order(ask(101, 3))
    book.add_order(ask(102, 5))
    trades = book.add_order(bid(101, 4))
    # Should fill 2 @ 100, then 2 @ 101
    assert len(trades) == 2
    assert trades[0].price == Decimal("100")
    assert trades[1].price == Decimal("101")


# ------------------------------------------------------------------
# Market orders
# ------------------------------------------------------------------

def test_market_buy():
    book = make_book()
    book.add_order(ask(100, 5))
    mo = Order(side=Side.BID, price=Decimal("0"), quantity=Decimal("5"), order_type=OrderType.MARKET)
    trades = book.add_order(mo)
    assert len(trades) == 1
    assert mo.status == OrderStatus.FILLED


def test_market_order_partial_cancel():
    book = make_book()
    book.add_order(ask(100, 3))
    mo = Order(side=Side.BID, price=Decimal("0"), quantity=Decimal("10"), order_type=OrderType.MARKET)
    trades = book.add_order(mo)
    assert mo.status == OrderStatus.CANCELLED
    assert mo.filled_quantity == Decimal("3")


# ------------------------------------------------------------------
# Cancel
# ------------------------------------------------------------------

def test_cancel_order():
    book = make_book()
    o = bid(100, 5)
    book.add_order(o)
    result = book.cancel_order(o.order_id)
    assert result is True
    assert o.status == OrderStatus.CANCELLED
    assert book.best_bid is None


def test_cancel_nonexistent():
    book = make_book()
    assert book.cancel_order("fake-id") is False


# ------------------------------------------------------------------
# Depth
# ------------------------------------------------------------------

def test_depth_aggregation():
    book = make_book()
    book.add_order(bid(100, 3))
    book.add_order(bid(100, 7))   # same level
    book.add_order(bid(99, 5))
    depth = book.bids_depth()
    assert depth[0] == (Decimal("100"), Decimal("10"))
    assert depth[1] == (Decimal("99"), Decimal("5"))
