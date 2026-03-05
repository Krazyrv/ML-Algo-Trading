import os
import time
import queue
import datetime
from abc import ABC, abstractmethod
from collections import deque

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt  # Fixed import for plotting
from ib_insync import Stock, MarketOrder, IB, util

# ==========================================
# 0. UTILITIES & CONNECTION
# ==========================================
class IBKRConnection():
    def __init__(self, host='127.0.0.1', port=7497, client_id=1, live_trading=False):
        self.ib = None
        self.host = host
        self.client_id = client_id
        self.port = port
        self.live_trading = live_trading

    def connect(self):
        try:
            self.ib = IB()
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            if self.ib.isConnected():
                print(f"Connected to IBKR at {self.host}:{self.port}")
                return self.ib
        except Exception as e:
            print(f"Connection failed: {e}")
            return None

    def disconnect(self):
        if self.ib and self.ib.isConnected():
            self.ib.disconnect()
            print("Disconnected from IBKR")

    def get_ib(self):
        return self.ib

# ==========================================
# 1. EVENTS
# ==========================================
class Event: pass

class MarketEvent(Event):
    def __init__(self): self.type = 'MARKET'

class SignalEvent(Event):
    def __init__(self, strategy_id, symbol, datetime, signal_type, strength=1.0):
        self.type = 'SIGNAL'
        self.strategy_id = strategy_id
        self.symbol = symbol
        self.datetime = datetime
        self.signal_type = signal_type

class OrderEvent(Event):
    def __init__(self, symbol, order_type, quantity, direction):
        self.type = 'ORDER'
        self.symbol = symbol
        self.order_type = order_type
        self.quantity = quantity
        self.direction = direction

class FillEvent(Event):
    def __init__(self, timeindex, symbol, exchange, quantity, direction, fill_price, commission=0.0):
        self.type = 'FILL'
        self.timeindex = timeindex
        self.symbol = symbol
        self.exchange = exchange
        self.quantity = quantity
        self.direction = direction
        self.fill_price = fill_price
        self.commission = commission

# ==========================================
# 2. DATA HANDLERS
# ==========================================
class DataHandler(ABC):
    @abstractmethod
    def get_latest_bar(self, symbol): pass
    @abstractmethod
    def update_bars(self): pass

class HistoricPandasDataHandler(DataHandler):
    def __init__(self, events_queue, data, symbol):
        self.events_queue = events_queue
        self.symbol = symbol
        self.data = data.copy()
        self.data_generator = self.data.iterrows()
        self.latest_data = []
        self.continue_backtest = True

    def get_latest_bar(self, symbol):
        return self.latest_data[-1] if self.latest_data else None

    def update_bars(self):
        try:
            index, row = next(self.data_generator)
            self.latest_data.append({
                'symbol': self.symbol, 'datetime': index,
                'open': row['open'], 'high': row['high'],
                'low': row['low'], 'close': row['close']
            })
            self.events_queue.put(MarketEvent())
        except StopIteration:
            self.continue_backtest = False

class IBKRLiveDataHandler(DataHandler):
    def __init__(self, events_queue, ib_conn, contract):
        self.events_queue = events_queue
        self.ib = ib_conn.get_ib()
        self.contract = contract
        self.latest_bar = None
        self.ib.qualifyContracts(self.contract)
        self.continue_backtest = True # Required for the Engine loop

    def start_live_feed(self):
        print(f"Subscribing to live data for {self.contract.symbol}...")
        self.bars = self.ib.reqHistoricalData(
            self.contract, endDateTime='', durationStr='1 D',
            barSizeSetting='1 min', whatToShow='TRADES',
            useRTH=True, formatDate=1, keepUpToDate=True
        )
        self.bars.updateEvent += self.on_bar_update

    def on_bar_update(self, bars, hasNewBar):
        if hasNewBar:
            new_bar = bars[-1]
            self.latest_bar = {'symbol': self.contract.symbol, 'datetime': new_bar.date, 'close': new_bar.close}
            self.events_queue.put(MarketEvent())

    def get_latest_bar(self, symbol): return self.latest_bar
    def update_bars(self): self.ib.sleep(0.1) # Yields to TWS network traffic

# ==========================================
# 3. STRATEGY
# ==========================================
class Strategy(ABC):
    @abstractmethod
    def calculate_signals(self, event): pass

class MovingAverageStrategy(Strategy):
    def __init__(self, events_queue, data_handler, symbol, fast_period=10, slow_period=30):
        self.events_queue = events_queue
        self.data_handler = data_handler
        self.symbol = symbol
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.prices = deque(maxlen=slow_period)
        self.current_position = 0 

    def calculate_signals(self, event):
        if event.type == 'MARKET':
            latest_bar = self.data_handler.get_latest_bar(self.symbol)
            if latest_bar:
                self.prices.append(latest_bar['close'])
                if len(self.prices) == self.slow_period:
                    price_list = list(self.prices)
                    fast_ma = np.mean(price_list[-self.fast_period:])
                    slow_ma = np.mean(price_list[-self.slow_period:])

                    if fast_ma > slow_ma and self.current_position <= 0:
                        print(f"[{latest_bar['datetime']}] SIGNAL: Going LONG.")
                        self.events_queue.put(SignalEvent("MA_Cross", self.symbol, latest_bar['datetime'], 'LONG'))
                        self.current_position = 1
                    elif fast_ma < slow_ma and self.current_position >= 0:
                        print(f"[{latest_bar['datetime']}] SIGNAL: Going SHORT.")
                        self.events_queue.put(SignalEvent("MA_Cross", self.symbol, latest_bar['datetime'], 'SHORT'))
                        self.current_position = -1

# ==========================================
# 4. PORTFOLIO MANAGER
# ==========================================
class PortfolioManager:
    def __init__(self, events_queue, data_handler, initial_capital=100000.0):
        self.events_queue = events_queue
        self.data_handler = data_handler
        self.initial_capital = initial_capital
        self.current_cash = initial_capital
        self.holdings = {}
        self.equity_curve = [] 

    def update_signal(self, event):
        if event.type == 'SIGNAL':
            order_quantity = 50 
            current_qty = self.holdings.get(event.symbol, 0)
            
            if event.signal_type == 'LONG' and current_qty == 0:
                self.events_queue.put(OrderEvent(event.symbol, 'MKT', order_quantity, 'BUY'))
            elif event.signal_type == 'SHORT' and current_qty > 0:
                self.events_queue.put(OrderEvent(event.symbol, 'MKT', current_qty, 'SELL'))

    def update_fill(self, event):
        if event.type == 'FILL':
            fill_cost = event.quantity * event.fill_price
            if event.direction == 'BUY':
                self.holdings[event.symbol] = self.holdings.get(event.symbol, 0) + event.quantity
                self.current_cash -= (fill_cost + event.commission)
            elif event.direction == 'SELL':
                self.holdings[event.symbol] = self.holdings.get(event.symbol, 0) - event.quantity
                self.current_cash += (fill_cost - event.commission)

    def record_equity(self):
        total_holdings_value = 0.0
        for symbol, qty in self.holdings.items():
            latest = self.data_handler.get_latest_bar(symbol)
            if latest: total_holdings_value += (qty * latest['close'])
        
        total_equity = self.current_cash + total_holdings_value
        latest_date = self.data_handler.get_latest_bar(list(self.holdings.keys())[0] if self.holdings else 'AAPL')['datetime']
        self.equity_curve.append({'datetime': latest_date, 'equity': total_equity})

# ==========================================
# 5. EXECUTION
# ==========================================
class ExecutionHandler(ABC):
    @abstractmethod
    def execute_order(self, event): pass

class SimulatedExecutionHandler(ExecutionHandler):
    def __init__(self, events_queue, data_handler):
        self.events_queue = events_queue
        self.data_handler = data_handler

    def execute_order(self, event):
        if event.type == 'ORDER':
            latest_bar = self.data_handler.get_latest_bar(event.symbol)
            fill_price = latest_bar['close']
            commission = max(1.0, event.quantity * 0.005)
            self.events_queue.put(FillEvent(latest_bar['datetime'], event.symbol, 'SIM', event.quantity, event.direction, fill_price, commission))
            print(f"[EXECUTION] Filled {event.direction} {event.quantity} {event.symbol} @ ${fill_price:.2f}")

class IBKRExecutionHandler(ExecutionHandler):
    def __init__(self, events_queue, ib_conn):
        self.events_queue = events_queue
        self.ib = ib_conn.get_ib()

    def execute_order(self, event):
        if event.type == 'ORDER':
            print(f"[IBKR EXECUTION] Routing {event.direction} order for {event.quantity} {event.symbol} to broker...")
            contract = Stock(event.symbol, 'SMART', 'USD')
            self.ib.qualifyContracts(contract)
            
            order = MarketOrder(event.direction, event.quantity)
            trade = self.ib.placeOrder(contract, order)
            
            while not trade.isDone():
                self.ib.sleep(0.1)
                
            if trade.orderStatus.status == 'Filled':
                fill_price = trade.avgFillPrice
                commission = sum(c.commission for c in trade.commissionReport) if trade.commissionReport else 0.0
                
                print(f"[IBKR EXECUTION] FILLED Qty: {trade.filled()}, Avg Price: ${fill_price}")
                self.events_queue.put(FillEvent(
                    datetime.datetime.now(), event.symbol, 'SMART', trade.filled(), event.direction, fill_price, commission
                ))

# ==========================================
# 6. EVALUATION
# ==========================================
class QuantitativeEvaluator:
    """Calculates institutional-grade metrics from a strategy's equity curve."""
    def __init__(self, risk_free_rate: float = 0.02):
        self.risk_free_rate = risk_free_rate
        self.trading_days_per_year = 252

    def calculate_metrics(self, df: pd.DataFrame) -> dict:
        if df.empty: return {}
        
        df['Daily_Return'] = df['Strategy_Return'].pct_change()
        total_return = df['Strategy_Return'].iloc[-1] - 1.0

        daily_volatility = df['Daily_Return'].std()
        annual_volatility = daily_volatility * np.sqrt(self.trading_days_per_year)

        expected_annual_return = df['Daily_Return'].mean() * self.trading_days_per_year
        excess_return = expected_annual_return - self.risk_free_rate
        sharpe_ratio = excess_return / annual_volatility if annual_volatility > 0 else 0.0

        negative_returns = df[df['Daily_Return'] < 0]['Daily_Return']
        downside_deviation = negative_returns.std() * np.sqrt(self.trading_days_per_year)
        sortino_ratio = excess_return / downside_deviation if downside_deviation > 0 else 0.0

        df['Peak'] = df['Strategy_Return'].cummax()
        df['Drawdown'] = (df['Strategy_Return'] - df['Peak']) / df['Peak']
        max_drawdown = df['Drawdown'].min()

        winning_days = len(df[df['Daily_Return'] > 0])
        total_trading_days = len(df[df['Daily_Return'] != 0])
        win_rate = winning_days / total_trading_days if total_trading_days > 0 else 0

        return {
            "Total Return": f"{total_return * 100:.2f}%",
            "Annualized Volatility": f"{annual_volatility * 100:.2f}%",
            "Sharpe Ratio": round(sharpe_ratio, 3),
            "Sortino Ratio": round(sortino_ratio, 3),
            "Max Drawdown": f"{max_drawdown * 100:.2f}%",
            "Win Rate (Days)": f"{win_rate * 100:.2f}%"
        }

    def plot_drawdown(self, df: pd.DataFrame):
        if 'Drawdown' not in df.columns:
            df['Peak'] = df['Strategy_Return'].cummax()
            df['Drawdown'] = (df['Strategy_Return'] - df['Peak']) / df['Peak']

        plt.figure(figsize=(14, 5))
        plt.fill_between(df.index, df['Drawdown'], 0, color='red', alpha=0.3)
        plt.plot(df.index, df['Drawdown'], color='red', linewidth=1)
        plt.title('Strategy Drawdown (Underwater Curve)')
        plt.xlabel('Date')
        plt.ylabel('Drawdown %')
        plt.grid(True, alpha=0.3)
        plt.show()

# ==========================================
# 7. THE TRADING ENGINE
# ==========================================
class TradingEngine:
    def __init__(self, data_handler, strategy, portfolio, execution, events_queue):
        self.data_handler = data_handler
        self.strategy = strategy
        self.portfolio = portfolio
        self.execution = execution
        self.events_queue = events_queue

    def run(self):
        print("Starting Trading Engine Loop...")
        try:
            while self.data_handler.continue_backtest:
                self.data_handler.update_bars()
                
                while not self.events_queue.empty():
                    event = self.events_queue.get()
                    
                    if event.type == 'MARKET':
                        self.strategy.calculate_signals(event)
                        self.portfolio.record_equity()
                    elif event.type == 'SIGNAL':
                        self.portfolio.update_signal(event)
                    elif event.type == 'ORDER':
                        self.execution.execute_order(event)
                    elif event.type == 'FILL':
                        self.portfolio.update_fill(event)
        except KeyboardInterrupt:
            print("\nTrading Engine interrupted by user.")
        print("Trading Engine Stopped.")

# ==========================================
# 8. EXECUTION BLOCK
# ==========================================
if __name__ == "__main__":
    
    # --- CHOOSE YOUR MODE ---
    MODE = "BACKTEST" # Change to "LIVE" when ready
    symbol = 'AAPL'
    events_queue = queue.Queue()
    
    # -----------------------------------------------------
    # OPTION A: SIMULATED BACKTEST
    # -----------------------------------------------------
    if MODE == "BACKTEST":
        print("--- RUNNING SIMULATED BACKTEST ---")
        
        # 1. Create simulated data
        dates = pd.date_range(start='2023-01-01', periods=200, freq='D')
        prices = 150 + 20 * np.sin(np.linspace(0, 4 * np.pi, 200))
        dummy_df = pd.DataFrame({'open': prices, 'high': prices+1, 'low': prices-1, 'close': prices}, index=dates)

        # 2. Setup Backtest Handlers
        data_handler = HistoricPandasDataHandler(events_queue, dummy_df, symbol)
        strategy = MovingAverageStrategy(events_queue, data_handler, symbol, fast_period=10, slow_period=30)
        portfolio = PortfolioManager(events_queue, data_handler, initial_capital=100000.0)
        execution = SimulatedExecutionHandler(events_queue, data_handler)

        # 3. Run Engine
        engine = TradingEngine(data_handler, strategy, portfolio, execution, events_queue)
        engine.run()
        
        # 4. Evaluate Performance 
        print("\n--- Strategy Performance Report ---")
        # Convert portfolio history to Evaluator's required DataFrame format
        eval_df = pd.DataFrame(portfolio.equity_curve).set_index('datetime')
        eval_df['Strategy_Return'] = eval_df['equity'] / eval_df['equity'].iloc[0] # Normalize starting equity to 1.0
        
        evaluator = QuantitativeEvaluator()
        metrics = evaluator.calculate_metrics(eval_df)
        
        for metric, value in metrics.items():
            print(f"{metric}: {value}")
            
        evaluator.plot_drawdown(eval_df)


    # -----------------------------------------------------
    # OPTION B: LIVE IBKR TRADING
    # -----------------------------------------------------
    elif MODE == "LIVE":
        print("--- STARTING LIVE IBKR TRADING ---")
        
        # 1. Connect to IBKR
        ib_conn = IBKRConnection(live_trading=False) # live_trading=False uses paper port 7497
        ib_conn.connect()
        
        if ib_conn.get_ib().isConnected():
            # 2. Setup Live Handlers
            contract = Stock(symbol, 'SMART', 'USD')
            data_handler = IBKRLiveDataHandler(events_queue, ib_conn, contract)
            strategy = MovingAverageStrategy(events_queue, data_handler, symbol, fast_period=10, slow_period=30)
            portfolio = PortfolioManager(events_queue, data_handler, initial_capital=100000.0)
            execution = IBKRExecutionHandler(events_queue, ib_conn)
            
            # Start Live Feed stream
            data_handler.start_live_feed()
            
            # 3. Run Engine (will block and listen forever until Ctrl+C)
            engine = TradingEngine(data_handler, strategy, portfolio, execution, events_queue)
            engine.run()
            
            # Cleanly disconnect when stopped
            ib_conn.disconnect()
        else:
            print("Failed to start LIVE trading. Check IBKR connection.")