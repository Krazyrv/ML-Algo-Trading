import queue

from ib_insync import Stock, MarketOrder, IB, util

from systems import IBKRConnection, HistoricPandasDataHandler, IBKRLiveDataHandler, TradingEngine
from events import MarketEvent, SignalEvent, OrderEvent, FillEvent
from strategy import MovingAverageStrategy, MachineLearningStrategy
from portfolio_manager import PortfolioManager
from execution import ExecutionHandler, SimulatedExecutionHandler

import nest_asyncio
nest_asyncio.apply()


if __name__ == "__main__":
    
    # --- CHOOSE YOUR MODE ---
    MODE = "BACKTEST" # Change to "LIVE" when ready
    symbol = 'AAPL'
    events_queue = queue.Queue()

    # 1. Connect to IBKR
    ib_conn = IBKRConnection(live_trading=False) # live_trading=False uses paper port 7497
    ib_conn.connect()
    contract = Stock(symbol, 'SMART', 'USD')
    if MODE == "BACKTEST":
        
        dummy_df = ib_conn.get_data(contract, durationStr="60 D", barSizeSetting="1 hour")
        data_handler = HistoricPandasDataHandler(events_queue, dummy_df, symbol)
        strategy = MovingAverageStrategy(events_queue, data_handler, symbol, fast_period=10, slow_period=30)
        portfolio = PortfolioManager(events_queue, data_handler, initial_capital=100000.0)
        execution = SimulatedExecutionHandler(events_queue, data_handler)

        # 3. Run Engine
        engine = TradingEngine(data_handler, strategy, portfolio, execution, events_queue)
        engine.run()
