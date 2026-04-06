# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an algorithmic trading system for Interactive Brokers (IBKR) that supports both live/paper trading and event-driven backtesting. The project has two parallel implementations:

1. **Simple strategy layer** (`src/`) — direct IBKR connection for quick testing
2. **Event-driven backtesting framework** (`test/test_system/`) — full modular system

## Setup

Prerequisites: IBKR account with TWS or IB Gateway running.

```bash
pip install -r requirements.txt
```

Configure `.env` with IBKR credentials:
```
IB_HOST = 127.0.0.1
IB_CLIENT_ID = <your_client_id>
IB_LIVE_PORT = 7496   # TWS live
IB_PAPER_PORT = 7497  # TWS paper
```

## Running the System

**Run backtesting (event-driven framework):**
```bash
python test/test_system/main.py
```
Set `MODE = "BACKTEST"` or `MODE = "LIVE"` inside `main.py` before running.

**Run simple strategy directly:**
```python
# In a notebook or script
from src.connection.ibkr_connector import IBKRConnection
from src.trading.strategies.moving_average import MovingAverageStrategy
```

**Jupyter entry point:**
```bash
jupyter notebook main.ipynb
```

## Architecture

### Event-Driven System (`test/test_system/`)

The backtesting framework follows an event-driven message queue pattern:

```
DataHandler → MarketEvent → Strategy → SignalEvent → PortfolioManager → OrderEvent → ExecutionHandler → FillEvent → PortfolioManager
```

All components share a single `queue.Queue`. The `TradingEngine` loop drains this queue, dispatching each event to the appropriate handler.

| File | Responsibility |
|------|---------------|
| `events.py` | Defines `MarketEvent`, `SignalEvent`, `OrderEvent`, `FillEvent` |
| `systems.py` | `DataHandler` ABC, `HistoricPandasDataHandler`, `IBKRLiveDataHandler`, `TradingEngine` |
| `strategy.py` | `Strategy` ABC, `MovingAverageStrategy`, `MachineLearningStrategy` (stub) |
| `portfolio_manager.py` | Position tracking, cash balance, equity curve, signal→order sizing |
| `execution.py` | `SimulatedExecutionHandler` (instant fills), `IBKRExecutionHandler` (live) |
| `main.py` | Wires all components together and starts `TradingEngine.run()` |

### Simple Strategy Layer (`src/`)

- `src/connection/ibkr_connector.py` — `IBKRConnection` wraps `ib_insync`, handles live vs paper mode
- `src/trading/strategies/strategy.py` — Base `Strategies` class with IBKR data fetching, order placement, P&L helpers
- `src/trading/strategies/moving_average.py` — `MovingAverageStrategy`: SMA crossover signals, backtesting, plotting

### Switching Backtest vs Live

In `test/test_system/main.py`, the `MODE` variable controls which data handler and execution handler are instantiated:
- `"BACKTEST"` → `HistoricPandasDataHandler` + `SimulatedExecutionHandler`
- `"LIVE"` → `IBKRLiveDataHandler` + `IBKRExecutionHandler`

## Key Dependencies

- `ib_insync` — IBKR API wrapper (requires TWS/IB Gateway running)
- `pandas`, `numpy` — data manipulation
- `matplotlib` — strategy signal visualization
- `torch` — reserved for future ML strategies
- `nest_asyncio` — allows asyncio in Jupyter notebooks
