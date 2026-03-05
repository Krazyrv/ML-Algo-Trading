import queue
from datetime import datetime

class Event:
    """
    Base class providing an interface for all subsequent 
    (inherited) events, that will trigger further events in the 
    trading infrastructure.
    """
    pass

class MarketEvent(Event):
    """
    Handles the event of receiving a new market update with 
    corresponding bars or ticks.
    """
    def __init__(self):
        self.type = 'MARKET'

class SignalEvent(Event):
    """
    Handles the event of sending a Signal from a Strategy object.
    This is received by a Portfolio object and acted upon.
    """
    def __init__(self, strategy_id: str, symbol: str, datetime: datetime, signal_type: str, strength: float = 1.0):
        self.type = 'SIGNAL'
        self.strategy_id = strategy_id
        self.symbol = symbol
        self.datetime = datetime
        self.signal_type = signal_type  # 'LONG', 'SHORT', or 'EXIT'
        self.strength = strength        # Useful for AI/ML probabilities later (e.g., 0.85 confidence)

class OrderEvent(Event):
    """
    Handles the event of sending an Order to an execution system.
    The portfolio determines the order size and sends this.
    """
    def __init__(self, symbol: str, order_type: str, quantity: int, direction: str):
        self.type = 'ORDER'
        self.symbol = symbol
        self.order_type = order_type    # 'MKT' or 'LMT'
        self.quantity = quantity
        self.direction = direction      # 'BUY' or 'SELL'

    def print_order(self):
        print(f"Order: {self.direction} {self.quantity} {self.symbol} ({self.order_type})")

class FillEvent(Event):
    """
    Encapsulates the notion of a Filled Order, as returned 
    from a brokerage (like IBKR). Stores the quantity actually filled 
    and at what price.
    """
    def __init__(self, timeindex: datetime, symbol: str, exchange: str, quantity: int, 
                 direction: str, fill_price: float, commission: float = 0.0):
        self.type = 'FILL'
        self.timeindex = timeindex
        self.symbol = symbol
        self.exchange = exchange
        self.quantity = quantity
        self.direction = direction
        self.fill_price = fill_price
        self.commission = commission