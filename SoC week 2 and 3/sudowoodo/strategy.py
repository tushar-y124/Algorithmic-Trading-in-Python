from src.backtester import Order
from typing import List

class Trader:
    def run(self, state, current_position):
        result = {}
        orders: List[Order] = []
        order_depth: OrderBook = state.order_depth

        orders.append(Order("PRODUCT", 9998, 10))
        orders.append(Order("PRODUCT", 10002, -10))

        result["PRODUCT"] = orders
        return result