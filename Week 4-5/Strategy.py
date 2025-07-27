
from src.backtester import Order, OrderBook
from typing import List
import statistics
import math

def mid_price(ob: OrderBook) -> float:
    """Return midpoint of best bid/ask or fallback 0."""
    if not ob.buy_orders or not ob.sell_orders:
        return 0
    return (max(ob.buy_orders) + min(ob.sell_orders)) / 2

def z_score(price_series: List[float], lookback: int) -> float:
    """Calculate z-score for mean reversion."""
    if len(price_series) < lookback:
        return 0
    latest = price_series[-1]
    window = price_series[-lookback:]
    mu = statistics.mean(window)
    sigma = statistics.stdev(window) or 1
    return (latest - mu) / sigma

def simple_rsi(prices: List[float], period: int = 14) -> float:
    """Calculate RSI for momentum assessment."""
    if len(prices) < period + 1:
        return 50
    
    gains = []
    losses = []
    
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    if len(gains) < period:
        return 50
        
    avg_gain = statistics.mean(gains[-period:])
    avg_loss = statistics.mean(losses[-period:])
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

class BaseClass:
    def __init__(self, product_name: str, max_position: int):
        self.product_name = product_name
        self.max_position = max_position
        self.price_history = []
        self.position_history = []
        self.pnl_history = []
        self.entry_price = None

    def clip(self, qty: int, current_pos: int) -> int:
        """Respect position limits with enhanced risk management."""
        # Emergency stop if losses too large
        if hasattr(self, 'pnl_history') and len(self.pnl_history) > 0:
            current_pnl = self.pnl_history[-1] if self.pnl_history else 0
            if current_pnl < -self.max_position * 100:
                return 0
        
        if qty > 0:
            allowed = self.max_position - current_pos
            return min(qty, allowed)
        else:
            allowed = -self.max_position - current_pos
            return max(qty, allowed)

    def update_risk_metrics(self, current_price: float, position: int):
        """Update risk tracking metrics."""
        self.price_history.append(current_price)
        self.position_history.append(position)
        
        # Keep only recent history
        if len(self.price_history) > 1000:
            self.price_history = self.price_history[-500:]
            self.position_history = self.position_history[-500:]

    def should_stop_loss(self, current_price: float, position: int) -> bool:
        """Check if we should trigger stop loss."""
        if position == 0 or self.entry_price is None:
            return False
            
        # 2% stop loss
        stop_loss_threshold = 0.02
        
        if position > 0:  # Long position
            return current_price < self.entry_price * (1 - stop_loss_threshold)
        else:  # Short position
            return current_price > self.entry_price * (1 + stop_loss_threshold)

    def get_orders(self, state, orderbook: OrderBook, position: int) -> List[Order]:
        return []

# 1. SUDOWOODO - Conservative Market Making
class SudowoodoStrategy(BaseClass):
    def __init__(self):
        super().__init__("SUDOWOODO", 25)  # Reduced from 50
        self.fair_value = 10000

    def get_orders(self, state, ob, pos):
        if not ob.buy_orders or not ob.sell_orders:
            return []
        
        return [
            Order(self.product_name, self.fair_value + 3, self.clip(-5, pos)),
            Order(self.product_name, self.fair_value - 3, self.clip(5, pos)),
        ]

# 2. DROWZEE - Enhanced Mean Reversion
class DrowzeeStrategy(BaseClass):
    def __init__(self):
        super().__init__("DROWZEE", 25)  # Reduced from 50
        self.lookback = 50  # Increased lookback
        self.z_entry = 3.0  # More conservative entry
        self.z_exit = 0.3   # Earlier exit

    def get_orders(self, state, ob, pos):
        if not ob.buy_orders or not ob.sell_orders:
            return []

        best_bid = max(ob.buy_orders)
        best_ask = min(ob.sell_orders)
        mid = (best_bid + best_ask) / 2
        
        self.update_risk_metrics(mid, pos)
        
        # Stop loss check
        if self.should_stop_loss(mid, pos):
            return [Order(self.product_name, best_ask if pos > 0 else best_bid, -pos)]
        
        z = z_score(self.price_history, self.lookback)
        orders = []
        
        if z > self.z_entry and pos > -self.max_position:
            qty = self.clip(-10, pos)
            orders.append(Order(self.product_name, best_bid, qty))
            self.entry_price = mid
        elif z < -self.z_entry and pos < self.max_position:
            qty = self.clip(10, pos)
            orders.append(Order(self.product_name, best_ask, qty))
            self.entry_price = mid
        elif abs(z) < self.z_exit and pos != 0:
            orders.append(Order(self.product_name, best_ask if pos < 0 else best_bid, -pos))
            self.entry_price = None
        
        return orders

# 3. ABRA - Conservative Skewed Market Making
class AbraStrategy(BaseClass):
    def __init__(self):
        super().__init__("ABRA", 25)  # Reduced from 50
        self.look = 100
        self.skew = 0.08  # Reduced skew

    def get_orders(self, state, ob, pos):
        if not ob.buy_orders or not ob.sell_orders:
            return []
            
        mid = (max(ob.buy_orders) + min(ob.sell_orders)) / 2
        self.update_risk_metrics(mid, pos)
        
        z = z_score(self.price_history, self.look)
        orders = []
        
        if abs(z) < 0.5:  # More conservative threshold
            skew_mid = mid + self.skew * pos
            orders.append(Order(self.product_name, int(skew_mid - 2), self.clip(4, pos)))
            orders.append(Order(self.product_name, int(skew_mid + 2), self.clip(-4, pos)))
        elif z > 2.5 and pos > -self.max_position:
            orders.append(Order(self.product_name, max(ob.buy_orders), self.clip(-5, pos)))
        elif z < -2.5 and pos < self.max_position:
            orders.append(Order(self.product_name, min(ob.sell_orders), self.clip(5, pos)))
        
        return orders

# 4. JOLTEON - RSI-Based Contrarian (CHANGED from breakout)
class JolteonStrategy(BaseClass):
    def __init__(self):
        super().__init__("JOLTEON", 15)  # Much smaller position
        self.rsi_period = 20

    def get_orders(self, state, ob, pos):
        if not ob.buy_orders or not ob.sell_orders:
            return []
            
        mid = (max(ob.buy_orders) + min(ob.sell_orders)) / 2
        self.update_risk_metrics(mid, pos)
        
        if len(self.price_history) < self.rsi_period:
            return []
            
        rsi = simple_rsi(self.price_history, self.rsi_period)
        orders = []
        
        if rsi < 25 and pos < self.max_position:  # Oversold
            orders.append(Order(self.product_name, min(ob.sell_orders), self.clip(5, pos)))
            self.entry_price = mid
        elif rsi > 75 and pos > -self.max_position:  # Overbought
            orders.append(Order(self.product_name, max(ob.buy_orders), self.clip(-5, pos)))
            self.entry_price = mid
        elif 45 < rsi < 55 and pos != 0:  # Neutral - exit
            orders.append(Order(self.product_name, max(ob.buy_orders) if pos > 0 else min(ob.sell_orders), -pos))
            self.entry_price = None
        
        return orders

# 5. LUXRAY - Conservative Mean Reversion (CHANGED from trend following)
class LuxrayStrategy(BaseClass):
    def __init__(self):
        super().__init__("LUXRAY", 20)  # Much smaller position
        self.lookback = 80
        self.z_entry = 2.5

    def get_orders(self, state, ob, pos):
        if not ob.buy_orders or not ob.sell_orders:
            return []
            
        mid = (max(ob.buy_orders) + min(ob.sell_orders)) / 2
        self.update_risk_metrics(mid, pos)
        
        # Stop loss check
        if self.should_stop_loss(mid, pos):
            return [Order(self.product_name, max(ob.buy_orders) if pos > 0 else min(ob.sell_orders), -pos)]
        
        z = z_score(self.price_history, self.lookback)
        orders = []
        
        if z > self.z_entry and pos > -self.max_position:
            orders.append(Order(self.product_name, max(ob.buy_orders), self.clip(-8, pos)))
            self.entry_price = mid
        elif z < -self.z_entry and pos < self.max_position:
            orders.append(Order(self.product_name, min(ob.sell_orders), self.clip(8, pos)))
            self.entry_price = mid
        elif abs(z) < 0.5 and pos != 0:
            orders.append(Order(self.product_name, max(ob.buy_orders) if pos > 0 else min(ob.sell_orders), -pos))
            self.entry_price = None
        
        return orders

# 6. SHINX - Micro Market Making
class ShinxStrategy(BaseClass):
    def __init__(self):
        super().__init__("SHINX", 10)  # Very small position

    def get_orders(self, state, ob, pos):
        if not ob.buy_orders or not ob.sell_orders:
            return []
            
        mid = (max(ob.buy_orders) + min(ob.sell_orders)) / 2
        self.update_risk_metrics(mid, pos)
        
        orders = []
        if abs(pos) < 5:  # Only trade when position is small
            orders.append(Order(self.product_name, int(mid - 1), self.clip(3, pos)))
            orders.append(Order(self.product_name, int(mid + 1), self.clip(-3, pos)))
        
        return orders

# 7. ASH - Passive Market Making (CHANGED from momentum)
class AshStrategy(BaseClass):
    def __init__(self):
        super().__init__("ASH", 5)  # Very small position

    def get_orders(self, state, ob, pos):
        if not ob.buy_orders or not ob.sell_orders:
            return []
            
        mid = (max(ob.buy_orders) + min(ob.sell_orders)) / 2
        
        orders = []
        if abs(pos) < 3:
            orders.append(Order(self.product_name, int(mid - 5), self.clip(2, pos)))
            orders.append(Order(self.product_name, int(mid + 5), self.clip(-2, pos)))
        
        return orders

# 8. MISTY - Passive
class MistyStrategy(BaseClass):
    def __init__(self):
        super().__init__("MISTY", 5)  # Very small position
        self.bought = False

    def get_orders(self, state, ob, pos):
        if self.bought or not ob.buy_orders or not ob.sell_orders:
            return []
            
        self.bought = True
        mid = (max(ob.buy_orders) + min(ob.sell_orders)) / 2
        return [Order(self.product_name, int(mid), self.clip(3, pos))]

# Trader class
class Trader:
    MAX_LIMIT = 0

    def __init__(self):
        self.strategies = {
            "SUDOWOODO": SudowoodoStrategy(),
            "DROWZEE": DrowzeeStrategy(),
            "ABRA": AbraStrategy(),
            "JOLTEON": JolteonStrategy(),
            "LUXRAY": LuxrayStrategy(),
            "SHINX": ShinxStrategy(),
            "ASH": AshStrategy(),
            "MISTY": MistyStrategy(),
        }

    def run(self, state):
        result = {}
        positions = getattr(state, "positions", {})
        
        for product, ob in state.order_depth.items():
            strat = self.strategies.get(product)
            if not strat:
                continue
            current_pos = positions.get(product, 0)
            result[product] = strat.get_orders(state, ob, current_pos)
        
        return result, self.MAX_LIMIT
