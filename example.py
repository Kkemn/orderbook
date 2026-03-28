"""Quick demo of the order book."""
from decimal import Decimal
from orderbook import Order, OrderBook, Side, OrderType

book = OrderBook("BTC/USD")

# Seed some resting asks
for price, qty in [(101, 2), (102, 5), (103, 8), (104, 3)]:
    book.add_order(Order(side=Side.ASK, price=Decimal(str(price)), quantity=Decimal(str(qty))))

# Seed some resting bids
for price, qty in [(100, 4), (99, 6), (98, 10), (97, 2)]:
    book.add_order(Order(side=Side.BID, price=Decimal(str(price)), quantity=Decimal(str(qty))))

print(book)
print()

# Aggressive buy that sweeps two levels
print(">>> Sending aggressive BID @ 102 qty=6")
trades = book.add_order(Order(side=Side.BID, price=Decimal("102"), quantity=Decimal("6")))
for t in trades:
    print(" ", t)

print()
print(book)
print()

# Market sell
print(">>> Sending MARKET SELL qty=5")
mo = Order(side=Side.ASK, price=None, quantity=Decimal("5"), order_type=OrderType.MARKET)
trades = book.add_order(mo)
for t in trades:
    print(" ", t)

print()
print(book)
print()
print(f"Total trades executed: {len(book.trades)}")
