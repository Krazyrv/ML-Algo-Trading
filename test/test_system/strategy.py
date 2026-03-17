from abc import ABC, abstractmethod
from collections import deque
import numpy as np

from events import SignalEvent, MarketEvent, Event, OrderEvent, FillEvent
from systems import HistoricPandasDataHandler, IBKRLiveDataHandler

# import torch

class Strategy(ABC):
    """
    Abstract base class for all trading strategies. 
    Whether it's a simple moving average or a complex AI/ML neural network, 
    it must inherit from this class and implement 'calculate_signals'.
    """
    @abstractmethod
    def calculate_signals(self, event):
        """
        Listens for MarketEvents, updates internal indicators, 
        and pushes SignalEvents to the queue if conditions are met.
        """
        pass


class MovingAverageStrategy(Strategy):
    """
    Event-driven Moving Average Crossover Strategy.
    """
    def __init__(self, events_queue, data_handler, symbol, fast_period=10, slow_period=30):
        self.events_queue = events_queue
        self.data_handler = data_handler
        self.symbol = symbol
        self.fast_period = fast_period
        self.slow_period = slow_period
        
        # Internal memory (Stateful processing)
        # deque automatically pushes old prices out when it reaches maxlen
        self.prices = deque(maxlen=slow_period) 
        
        # Track what the strategy currently thinks our position is
        # (1 = Long, -1 = Short, 0 = Flat)
        self.current_position = 0 
        
    def  calculate_signals(self, event):
        """
        Triggered every time a new MarketEvent is pulled from the queue.
        """
        if event.type == 'MARKET':
            latest_bar = self.data_handler.get_latest_bar(self.symbol)
            
            if latest_bar is not None:
                # Add the newest price to our rolling window
                self.prices.append(latest_bar['close'])
                
                # Do not generate signals until we have enough data to calculate the slow MA
                if len(self.prices) == self.slow_period:
                    # Convert deque to list for calculation
                    price_list = list(self.prices)
                    
                    fast_ma = np.mean(price_list[-self.fast_period:])
                    slow_ma = np.mean(price_list[-self.slow_period:])
                    
                    # LOGIC: Fast crosses ABOVE Slow -> BUY
                    if fast_ma > slow_ma and self.current_position <= 0:
                        print(f"[{latest_bar['datetime']}] SIGNAL: Fast MA ({fast_ma:.2f}) > Slow MA ({slow_ma:.2f}). Going LONG.")
                        
                        signal = SignalEvent(
                            strategy_id="MA_Cross_1", 
                            symbol=self.symbol, 
                            datetime=latest_bar['datetime'], 
                            signal_type='LONG', 
                            strength=1.0
                        )
                        self.events_queue.put(signal)
                        self.current_position = 1 # Update state
                        
                    # LOGIC: Fast crosses BELOW Slow -> SELL/SHORT
                    elif fast_ma < slow_ma and self.current_position >= 0:
                        print(f"[{latest_bar['datetime']}] SIGNAL: Fast MA ({fast_ma:.2f}) < Slow MA ({slow_ma:.2f}). Going SHORT/FLAT.")
                        
                        signal = SignalEvent(
                            strategy_id="MA_Cross_1", 
                            symbol=self.symbol, 
                            datetime=latest_bar['datetime'], 
                            signal_type='SHORT', 
                            strength=1.0
                        )
                        self.events_queue.put(signal)
                        self.current_position = -1 # Update state   

class MachineLearningStrategy(Strategy):
    """ No space left on current device, will implement later """
    def __init__(self, events_queue, data_handler, model_path):
        # self.model = torch.load(model_path) # Load pre-trained AI
        pass
        # ...
        
    def calculate_signals(self, event):
        # 1. Get latest 100 bars from data_handler
        # 2. Format into a tensor
        # 3. prediction = self.model(tensor)
        # 4. If prediction > 0.8: emit SignalEvent!
        pass

# import pandas as pd
# import queue
# # (Assuming the Event, DataHandler, and Strategy classes are loaded)

# # 1. Create a dummy price dataset with a clear crossover
# # Prices start low, trend high (creating a Buy), then crash (creating a Sell)
# dates = pd.date_range(start='2023-01-01', periods=8, freq='D')
# dummy_df = pd.DataFrame({
#     'open': [10, 11, 12, 13, 14, 15, 9, 8],
#     'high': [10, 11, 12, 13, 14, 15, 9, 8],
#     'low': [10, 11, 12, 13, 14, 15, 9, 8],
#     'close': [10, 11, 12, 13, 14, 15, 9, 8], # Focus on the close
# }, index=dates)

# # 2. Setup the infrastructure
# events_queue = queue.Queue()

# # Initialize the DataHandler
# data_handler = HistoricPandasDataHandler(events_queue, dummy_df, symbol='AAPL')

# # Initialize the Strategy (Using short periods so we can see it trigger quickly)
# # Fast MA = 2 periods, Slow MA = 4 periods
# mac_strategy = MovingAverageStrategy(events_queue, data_handler, symbol='AAPL', fast_period=2, slow_period=4)

# print("Starting Strategy Engine Loop...\n")

# # 3. The Main Trading Loop
# while data_handler.continue_backtest:
#     # Tell the data handler to push the next bar (This puts a MarketEvent in the queue)
#     data_handler.update_bars()
    
#     # Process all events in the queue
#     while not events_queue.empty():
#         event = events_queue.get()
        
#         if event.type == 'MARKET':
#             latest = data_handler.get_latest_bar('AAPL')
#             print(f"Market Tick -> Date: {latest['datetime'].date()} | Price: ${latest['close']:.2f}")
            
#             # The Engine passes the MarketEvent to the strategy
#             mac_strategy.calculate_signals(event)
            
#         elif event.type == 'SIGNAL':
#             print(f">>> CAUGHT IN QUEUE: {event.signal_type} Signal for {event.symbol} from {event.strategy_id} <<<")
#             # In the next step, the Portfolio Manager will pick this up!

# print("\nSimulation Complete.")