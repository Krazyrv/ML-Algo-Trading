import queue

from events import OrderEvent

class PortfolioManager:
    """
    Manages position sizing, risk management, and tracks the current 
    cash and holdings of the account.
    """
    def __init__(self, events_queue, data_handler, initial_capital=1000000.0):
        self.events_queue = events_queue
        self.data_handler = data_handler
        self.initial_capital = initial_capital
        self.current_cash = initial_capital
        
        # Tracks how many shares of each symbol we currently own
        self.holdings = {} 
        
    def update_signal(self, event):
        """
        Acts on a SignalEvent to generate new orders 
        based on portfolio logic.
        """
        if event.type == 'SIGNAL':
            symbol = event.symbol
            direction = event.signal_type
            
            # 1. Position Sizing Logic (Risk Management)
            # For this example, we buy a fixed quantity of 10 shares.
            # In a pro system, you'd calculate: (Risk_per_trade / Stop_Loss_Distance)
            order_quantity = 10 
            
            # Check current holdings
            current_qty = self.holdings.get(symbol, 0)
            order_type = 'MKT' # Market order
            
            # 2. Translate Strategy Signals into specific Broker Orders
            if direction == 'LONG' and current_qty == 0:
                # We have no position, strategy says go LONG. We buy.
                order = OrderEvent(symbol, order_type, order_quantity, 'BUY')
                self.events_queue.put(order)
                print(f"[PORTFOLIO] Approved LONG signal. Generated BUY order for {order_quantity} {symbol}.")
                
            elif direction == 'SHORT' and current_qty > 0:
                # We are long, strategy says go SHORT/EXIT. We sell our current position to close.
                # Note: We sell 'current_qty' to flatten the position.
                order = OrderEvent(symbol, order_type, current_qty, 'SELL')
                self.events_queue.put(order)
                print(f"[PORTFOLIO] Approved SHORT/EXIT signal. Generated SELL order to close {current_qty} {symbol}.")
            
            # Note: If the strategy sends a LONG signal but we are already LONG, 
            # the portfolio intelligently ignores it to prevent over-leveraging.

    def update_fill(self, event):
        """
        Updates portfolio current cash and holdings from a FillEvent.
        (We will use this in Part 5!)
        """
        if event.type == 'FILL':
            fill_cost = event.quantity * event.fill_price
            
            if event.direction == 'BUY':
                self.holdings[event.symbol] = self.holdings.get(event.symbol, 0) + event.quantity
                self.current_cash -= (fill_cost + event.commission)
            elif event.direction == 'SELL':
                self.holdings[event.symbol] = self.holdings.get(event.symbol, 0) - event.quantity
                self.current_cash += (fill_cost - event.commission)
                
            print(f"[PORTFOLIO] Fill received. New Cash Balance: ${self.current_cash:.2f} | Holdings: {self.holdings}")

            