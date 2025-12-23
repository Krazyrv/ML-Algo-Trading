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

IB_HOST = os.getenv("IB_HOST")
IB_PORT = os.getenv("IB_PAPER_GATEWAY_PORT") # Use the paper trading port for testing
IB_CLIENT_ID = int(os.getenv("IB_CLIENT_ID")) # Convert to the required data type
IB_DUMMY_ID = int(os.getenv("IB_DUMMY_ID"))



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


class Strategies():
    def __init__(self, conn:IBKRConnection):
        self._conn = conn
        self.df = None
        print(f"Strategy base class initialized. {type(conn.get_ib())}")
        pass

    def get_data(self, contract, durationStr="300 D", barSizeSetting="5 mins", whatToShow="TRADES"):
        """
        Get historical data for a given contract.

        returns: historical data as a DataFrame
        """
        barSizeSetting_options = ['1 secs', '5 secs', '10 secs', '15 secs', '30 secs',
                '1 min', '2 mins', '3 mins', '5 mins', '10 mins', '15 mins',
                '20 mins', '30 mins',
                '1 hour', '2 hours', '3 hours', '4 hours', '8 hours',
                '1 day', '1 week', '1 month']
        whatToShow_options = ['TRADES', 'MIDPOINT', 'BID', 'ASK', 
                              'BID_ASK','ADJUSTED_LAST', 'HISTORICAL_VOLATILITY',
                              'OPTION_IMPLIED_VOLATILITY', 'REBATE_RATE', 'FEE_RATE',
                              'YIELD_BID', 'YIELD_ASK', 'YIELD_BID_ASK', 'YIELD_LAST']
        if whatToShow not in whatToShow_options:
            raise ValueError(f"Invalid whatToShow option. Choose from {whatToShow_options}")
        if barSizeSetting not in barSizeSetting_options:
            raise ValueError(f"Invalid barSizeSetting option. Choose from {barSizeSetting_options}")
        try:
            ib = self._conn.get_ib()
            ib.qualifyContracts(contract)
            bars = ib.reqHistoricalData(
                contract,
                endDateTime='',
                durationStr=durationStr,
                barSizeSetting=barSizeSetting,
                whatToShow=whatToShow,
                useRTH=True,
                formatDate=1
            )
            return util.df(bars)
        except Exception as e:
            print(f"Error fetching historical data: {e}")
            return None
        
    def place_order(self, contract: Stock, action: str, quantity: int, order_type: str = 'MKT') -> Trade:
        """Helper to place and monitor a simple market or limit order."""
        ib = self._conn.get_ib()
        if order_type == 'MKT':
            order = MarketOrder(action, quantity)
        else: # For simplicity, treat all other as LimitOrder (needs refinement for real use)
            print("Warning: Only Market Orders are fully implemented in this base function.")
            order = MarketOrder(action, quantity) 
        
        trade = ib.placeOrder(contract, order)
        print(f"Order submitted. Action: {action} {quantity}, ID: {trade.order.orderId}")
        
        # Wait for the trade to finish (Filled, Cancelled, etc.)
        while not trade.isDone():
            ib.sleep(0.5)
            
        final_status = trade.orderStatus.status
        if final_status == 'Filled':
            print(f"Order FILLED. Qty: {trade.filled()}, Avg Price: ${trade.avgFillPrice}")
        else:
            print(f"Order finished with status: {final_status}")
            
        return trade
    
    def calculate_pnl(self, action: str, quantity: int, fill_price: float, current_price: float) -> float:
        """
        Calculate profit/loss for a single position.
        action: 'BUY' or 'SELL'
        quantity: Absolute number of shares/contracts
        fill_price: The price at which the order was filled
        current_price: The current market price of the asset
        """
        if action == 'BUY':
            pnl = (current_price - fill_price) * quantity
        elif action == 'SELL':
            pnl = (fill_price - current_price) * quantity
        else:
            raise ValueError("Action must be 'BUY' or 'SELL'")
        return pnl

    def calculate_accumulated_pnl(self, trades: list) -> float:
        """
        Calculate the accumulated profit/loss from a list of trades.
        trades: A list of dictionaries, each containing 'action', 'quantity', 'fill_price', 'current_price'.
        """
        total_pnl = 0.0
        for trade in trades:
            total_pnl += self.calculate_pnl(trade['action'], trade['quantity'], trade['fill_price'], trade['current_price'])
        return total_pnl
    
    def evaluate_performance(self, trades: list):
        """
        Evaluate performance metrics from a list of trades.
        trades: A list of dictionaries, each containing 'action', 'quantity', 'fill_price', 'current_price'.
        Returns a dictionary with total PnL and number of trades.
        """
        total_pnl = self.calculate_accumulated_pnl(trades)
        num_trades = len(trades)
        performance = {
            'total_pnl': total_pnl,
            'num_trades': num_trades,
            'average_pnl_per_trade': total_pnl / num_trades if num_trades > 0 else 0
        }
        return performance

    def test_strategy(self):
        """Method to test the strategy logic."""
        raise NotImplementedError("Base class test_strategy must be overridden by a concrete strategy.")


    # Keeping strategies_method as a placeholder for a general strategy execution
    def strategies_method(self):
        raise NotImplementedError("Base class strategies_method must be overridden by a concrete strategy.")


class MovingAverageStrategy(Strategies):
    def __init__(self, conn: IBKRConnection, symbol: str, fast_period: int = 10, slow_period: int = 30):
        # Pass the connection object to the parent constructor
        super().__init__(conn=conn)
        self.symbol = symbol
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.contract = Stock(symbol, 'SMART', 'USD')
        print(f"Moving Average Strategy initialized for {symbol} ({fast_period}/{slow_period} periods).")

    def analyze_data(self, df: pd.DataFrame) -> Optional[str]:
        """Calculates MAs and generates a trade signal."""
        ib = self._conn.get_ib()
        if df is None or df.empty:
            return None

        # 1. Calculate Moving Averages on the closing price
        df[f'SMA_{self.fast_period}'] = df['close'].rolling(self.fast_period).mean()
        df[f'SMA_{self.slow_period}'] = df['close'].rolling(self.slow_period).mean()
        
        # Drop initial rows where MAs are NaN
        df.dropna(inplace=True) 

        if df.empty:
            return None

        df['Signal'] = 0

        # When 20-day SMA crosses above 50-day SMA
        df.loc[(df[f'SMA_{self.fast_period}'] > df[f'SMA_{self.slow_period}']) & (df[f'SMA_{self.fast_period}'].shift(1) < df[f'SMA_{self.slow_period}'].shift(1)), 'Signal'] = 1
        # When 20-day SMA crosses below 50-day SMA
        df.loc[(df[f'SMA_{self.fast_period}'] < df[f'SMA_{self.slow_period}']) & (df[f'SMA_{self.fast_period}'].shift(1) > df[f'SMA_{self.slow_period}'].shift(1)), 'Signal'] = -1

        # Create columns for plotting buy and sell signals at the close price
        df['Buy_Signal_Price'] = df.loc[df['Signal'] == 1, 'close']
        df['Sell_Signal_Price'] = df.loc[df['Signal'] == -1, 'close']

        # 2. Determine Signal (based on the last complete bar)
        last_fast = df[f'SMA_{self.fast_period}'].iloc[-1]
        last_slow = df[f'SMA_{self.slow_period}'].iloc[-1]
        
        # Check current position (simplified check)
        # Note: A real implementation would need to monitor the portfolio continuously.
        portfolio = ib.portfolio()
        current_position = next((item.position for item in portfolio if item.contract.symbol == self.symbol), 0)

        signal = None
        if last_fast > last_slow and current_position <= 0:
            # Fast MA crossed above Slow MA (Buy Signal)
            signal = 'BUY'
        elif last_fast < last_slow and current_position > 0:
            # Fast MA crossed below Slow MA (Sell/Close Signal)
            signal = 'SELL'
            
        print(f"Analysis: Fast MA: {last_fast:.2f}, Slow MA: {last_slow:.2f}, Signal: {signal}")
        self.df = df
        return signal

    def plot_signals(self, df: pd.DataFrame):
        df = self.df
        # 3. Visualize the Results
        plt.figure(figsize=(14, 7))

        # Plot closing price
        plt.plot(df['date'], df['close'], label='Close Price', color='blue', alpha=0.6)

        # Plot moving averages
        plt.plot(df['date'], df[f'SMA_{self.fast_period}'], label=f'{self.fast_period}-day SMA', color='green', linestyle='--')
        plt.plot(df['date'], df[f'SMA_{self.slow_period}'], label=f'{self.slow_period}-day SMA', color='red', linestyle='--')

        # Plot buy signals
        plt.scatter(df['date'], df['Buy_Signal_Price'], marker='^', color='green', s=100, label='Buy Signal', zorder=5)
        # Plot sell signals
        plt.scatter(df['date'], df['Sell_Signal_Price'], marker='v', color='red', s=100, label='Sell Signal', zorder=5)


        plt.title('AAPL Moving Average Crossover Strategy')
        plt.xlabel('Date')
        plt.ylabel('Price (USD)')
        plt.legend()
        plt.grid(True)
        plt.show()

    def run_strategy(self):
        """Main execution method for the strategy."""
        
        # 1. Get the necessary historical data
        data = self.get_data(
            self.contract, 
            durationStr="60 D", 
            barSizeSetting="1 hour"
        )
        
        if data is None:
            print("Could not retrieve data. Strategy halted.")
            return

        # 2. Analyze the data and get a signal
        signal = self.analyze_data(data)
        
        # 3. Execute the trade based on the signal
        if signal == 'BUY':
            # self.place_order(self.contract, 'BUY', quantity=10)
            print(f"Placing BUY order for {self.symbol}.")
        elif signal == 'SELL':
            # In this simple example, we assume we sell our entire position (10 shares)
            # self.place_order(self.contract, 'SELL', quantity=10) 
            print(f"Placing SELL order for {self.symbol}.")
        else:
            print(f"No trade signal generated for {self.symbol}.")
    
    def test_strategy(self):
        df = self.df.copy()
        df['Asset_Return'] = (1 + df['close'].pct_change()).cumprod() 
        df['Strategy_Return'] = (1+ \
                                 df['close'].pct_change() * (df['Signal'].shift(1)*-1)).cumprod()

        plt.figure(figsize=(14,7))
        plt.plot(df['date'], df['Asset_Return'], label='Asset Return', color='blue')
        plt.plot(df['date'], df['Strategy_Return'], label='Strategy Return', color='orange')
        plt.title('Strategy vs Asset Return')
        return df
        


# Example usage
ib_conn = IBKRConnection(live_trading=False)
# ib_conn.connect()
# ib = ib_conn.get_ib()
# print(f"Server time: {ib.reqCurrentTime()}")

# strat = MovingAverageStrategy(conn=ib_conn, symbol='AAPL', fast_period=10, slow_period=30)
# strat.run_strategy()

# ib_conn.disconnect()





