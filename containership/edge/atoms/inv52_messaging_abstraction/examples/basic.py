"""Minimal broker-independent INV-52 example."""
from inv52_messaging_abstraction import PubSub, envelope

bus = PubSub()
bus.allow("orders", "shop")
large_orders = []
bus.subscribe("orders", lambda msg: msg["data"]["total"] >= 100, large_orders)
bus.publish("shop", "orders", envelope("shop", "order.placed", {"total": 250}))
print(large_orders[0])
