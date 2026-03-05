from abc import ABC, abstractmethod
from ib_insync import Stock, MarketOrder
import datetime

from events import FillEvent

class ExecutionHandler(ABC):
    """
    The abstract base class for handling order execution.
    """
    @abstractmethod
    def execute_order(self, event):
        """Takes an OrderEvent and executes it."""
        pass

class SimulatedExecutionHandler(ExecutionHandler):
    """
    Instantly fills orders at the current market price for backtesting.
    In a more advanced version, you would add slippage and latency here.
    """
    def __init__(self, events_queue, data_handler):
        self.events_queue = events_queue
        self.data_handler = data_handler

    def execute_order(self, event):
        if event.type == 'ORDER':
            # 1. Get the current price from our data handler
            latest_bar = self.data_handler.get_latest_bar(event.symbol)
            fill_price = latest_bar['close']
            
            # 2. Simulate commission (e.g., $1 minimum or $0.005 per share)
            commission = max(1.0, event.quantity * 0.005)
            
            # 3. Create a FillEvent and push it back to the queue
            fill_event = FillEvent(
                timeindex=latest_bar['datetime'],
                symbol=event.symbol,
                exchange='SIMULATED',
                quantity=event.quantity,
                direction=event.direction,
                fill_price=fill_price,
                commission=commission
            )
            self.events_queue.put(fill_event)
            print(f"[EXECUTION - SIM] FILLED {event.direction} {event.quantity} {event.symbol} @ ${fill_price:.2f}")


class IBKRExecutionHandler(ExecutionHandler):
    """
    Live trading execution handler using your original ib_insync logic!
    """
    def __init__(self, events_queue, ib_conn):
        self.events_queue = events_queue
        self.ib = ib_conn.get_ib()

    def execute_order(self, event):
        if event.type == 'ORDER':
            print(f"[EXECUTION - IBKR] Sending {event.direction} order for {event.quantity} {event.symbol} to broker...")
            
            # 1. Prepare the contract (Reusing your original logic)
            contract = Stock(event.symbol, 'SMART', 'USD')
            self.ib.qualifyContracts(contract)
            
            # 2. Prepare the order
            if event.order_type == 'MKT':
                order = MarketOrder(event.direction, event.quantity)
            else:
                print("Warning: Only Market Orders currently supported. Defaulting to MKT.")
                order = MarketOrder(event.direction, event.quantity)
                
            # 3. Send the order to IBKR
            trade = self.ib.placeOrder(contract, order)
            
            # 4. Wait for the fill (Using your original blocking loop for simplicity)
            # In a highly advanced system, you would attach an asynchronous callback here instead!
            while not trade.isDone():
                self.ib.sleep(0.1)
                
            if trade.orderStatus.status == 'Filled':
                fill_price = trade.avgFillPrice
                commission = sum(c.commission for c in trade.commissionReport) if trade.commissionReport else 0.0
                
                print(f"[EXECUTION - IBKR] Order FILLED. Qty: {trade.filled()}, Avg Price: ${fill_price}")
                
                # 5. Push the FillEvent back to the queue so the Portfolio Manager knows!
                fill_event = FillEvent(
                    timeindex=datetime.datetime.now(),
                    symbol=event.symbol,
                    exchange='SMART',
                    quantity=trade.filled(),
                    direction=event.direction,
                    fill_price=fill_price,
                    commission=commission
                )
                self.events_queue.put(fill_event)
            else:
                print(f"[EXECUTION - IBKR] Order failed or cancelled. Status: {trade.orderStatus.status}")      