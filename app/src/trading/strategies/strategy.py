import os
from dotenv import load_dotenv
import time
import pandas as pd
from typing import Optional
import matplotlib.pyplot as plt
# 1. Load the variables from the .env file
# This reads the key-value pairs and adds them to the environment (os.environ)
load_dotenv()

# from connections.ibkr_connection import IBKRConnection

from ib_insync import Stock, MarketOrder, IB, util, Trade

class Strategies():
    def __init__(self, conn):
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
    

print("strategy.py loaded.")