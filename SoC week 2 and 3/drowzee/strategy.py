from src.backtester import Order, OrderBook
from typing import List

class Trader:
    def __init__(self):
        self.in_position = False
        self.entry_price = None
        self.trade_size = 50

    def run(self, state, current_position):
        result = {}
        orders: List[Order] = []
        order_depth: OrderBook = state.order_depth

        if not order_depth.buy_orders or not order_depth.sell_orders:
            return {"PRODUCT": []}

        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())

        # === EXIT ===
        if self.in_position and best_bid >= self.entry_price + 1:
            orders.append(Order("PRODUCT", best_bid, -self.trade_size))
            self.in_position = False
            self.entry_price = None

        # === ENTRY ===
        if not self.in_position:
            favorable_pairs = [
                (2034, 2037),
                (2035, 2038),
                (2033, 2036),
                (2036, 2039),
                (2032, 2035)
            ]
            for bid_target, ask_target in favorable_pairs:
                if best_bid == bid_target and best_ask == ask_target:
                    orders.append(Order("PRODUCT", best_ask, self.trade_size))
                    self.in_position = True
                    self.entry_price = best_ask
                    break

        result["PRODUCT"] = orders
        return result
