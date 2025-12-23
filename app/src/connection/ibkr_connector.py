import os
from ib_insync import IB
import time



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
        
print("IBKR Connector module loaded.")