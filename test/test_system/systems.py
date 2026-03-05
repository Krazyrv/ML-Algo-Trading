import os
from dotenv import load_dotenv
import time
import pandas as pd
from typing import Optional
import matplotlib.pyplot as plt
# 1. Load the variables from the .env file
# This reads the key-value pairs and adds them to the environment (os.environ)
load_dotenv()

from ib_insync import Stock, MarketOrder, IB, util, Trade

from abc import ABC, abstractmethod 
import pandas as pd
import queue

# from test.test_system.events import MarketEvent
from events import MarketEvent

# Utility Functions
def print_loading_message(message, loop_count = 3, delay=0.3):
    # Function to print a loading message with dots for visual effect
    print(f"{message} ", end="", flush=True) 
    for _ in range(loop_count):
        print(f".", end="", flush=True) 
        time.sleep(delay)
    print()




class IBKRConnection():
    def __init__(self, 
                 host = os.getenv("IB_HOST"), 
                 port = None, 
                 client_id = int(os.getenv("IB_CLIENT_ID")), 
                 live_trading=False
                 ):
        self.ib = None            # Pending for get Stock ib instance as dict ['aapl': Stock(...), 'tsla': Stock(...)]
        self.host = host
        # self.client_id = client_id
        if live_trading:
            self.client_id = client_id
            self.port = os.getenv("IB_LIVE_PORT")
            print("Live trading mode enabled.")
        else:
            self.client_id = os.getenv("IB_TEST_ID")
            self.port = os.getenv("IB_PAPER_PORT")
            print("Paper trading mode enabled.")
        print(f"Connecting to IBKR at {self.host}:{self.port} with client ID {self.client_id}")
        import nest_asyncio
        nest_asyncio.apply()


    def connect(self):
        try:
            self.ib = IB()
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            if self.ib.isConnected():
                print(f"Connected to IBKR at {self.host}:{self.port} with client ID {self.client_id}")
                return self.ib
        except Exception as e:
            print(f"Connection failed: {e}")
            return None


    def disconnect(self):
        print_loading_message("Disconnecting from IBKR")
        if self.ib and self.ib.isConnected():
            self.ib.disconnect()
            # print("Disconnected from IBKR")

    def get_ib(self):
        return self.ib
    
    def get_current_time(self):
        if self.ib and self.ib.isConnected():
            return self.ib.reqCurrentTime()
        else:
            print("Not connected to IBKR.")
            return None
        

class DataHandler(ABC):
    """
    Abstract base class providing an interface for all data handlers 
    (both live and historical).
    """
    @abstractmethod
    def get_latest_bar(self, symbol):
        """Returns the last updated bar for a symbol."""
        pass

    @abstractmethod
    def update_bars(self):
        """Pushes the next bar(s) down the queue."""
        pass

class HistoricPandasDataHandler(DataHandler):
    """
    Data handler designed for backtesting. It takes a Pandas DataFrame, 
    iterates through it row by row, and mimics a live market feed.
    """
    def __init__(self, events_queue: queue.Queue, data: pd.DataFrame, symbol: str):
        self.events_queue = events_queue
        self.symbol = symbol
        self.data = data.copy()
        
        # We need an iterator to go row by row
        self.data_generator = self.data.iterrows()
        
        # This will hold the "current" view of the market 
        # (growing bar by bar, just like in real life)
        self.latest_data = []
        self.continue_backtest = True

    def get_latest_bar(self, symbol):
        """Returns the most recent bar from our simulated feed."""
        if self.latest_data:
            return self.latest_data[-1]
        return None

    def update_bars(self):
        """
        Gets the next row from the DataFrame. 
        If successful, pushes a MarketEvent to the queue.
        """
        try:
            index, row = next(self.data_generator)
            # Format the incoming row into a dictionary
            bar = {
                'symbol': self.symbol,
                'datetime': index,
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'volume': row.get('volume', 0)
            }
            self.latest_data.append(bar)
            
            # Announce to the system that new data has arrived!
            self.events_queue.put(MarketEvent())
            
        except StopIteration:
            # We reached the end of the historical DataFrame
            self.continue_backtest = False

class IBKRLiveDataHandler(DataHandler):
    """
    Data handler for LIVE trading. Reuses your ib_insync connection!
    """
    def __init__(self, events_queue: queue.Queue, ib_conn, contract):
        self.events_queue = events_queue
        self.ib = ib_conn.get_ib()
        self.contract = contract
        self.latest_bar = None
        
        # Qualify the contract (using your exact logic!)
        self.ib.qualifyContracts(self.contract)

    def start_live_feed(self):
        """Subscribes to live bar updates from IBKR."""
        print(f"Subscribing to live data for {self.contract.symbol}...")
        
        # reqHistoricalData with keepUpToDate=True creates a live stream in ib_insync
        self.bars = self.ib.reqHistoricalData(
            self.contract,
            endDateTime='',
            durationStr='1 D',
            barSizeSetting='1 min',
            whatToShow='TRADES',
            useRTH=True,
            formatDate=1,
            keepUpToDate=True # <--- This is the magic flag for live streaming
        )
        
        # Attach a callback: every time IBKR sends a new bar, run self.on_bar_update
        self.bars.updateEvent += self.on_bar_update

    def on_bar_update(self, bars, hasNewBar):
        """Callback triggered automatically by ib_insync."""
        if hasNewBar:
            new_bar = bars[-1]
            self.latest_bar = {
                'symbol': self.contract.symbol,
                'datetime': new_bar.date,
                'close': new_bar.close
            }
            # Announce to the rest of the system!
            self.events_queue.put(MarketEvent())

    def get_latest_bar(self, symbol):
        return self.latest_bar
    
    def update_bars(self):
        # In live trading with ib_insync, the callback (on_bar_update) 
        # handles the updates asynchronously. We just let it run.
        self.ib.sleep(0.1)

        
# Example usage
# ib_conn = IBKRConnection(live_trading=False)
# ib_conn.connect()
# ib = ib_conn.get_ib()
# print(f"Server time: {ib.reqCurrentTime()}")
# ib_conn.disconnect()