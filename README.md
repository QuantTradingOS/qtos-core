# qtos-core

Deterministic, event-driven trading core engine for the QuantTradingOS organization. No AI, no Streamlit, no broker integrations—just a clear, minimal core that defines interfaces and an event loop.

## What the core engine is

- **Event-driven**: An `EventLoop` dispatches events to registered handlers in a fixed order. You feed it a sequence of events (e.g. in a backtest); handlers react and produce signals or update state.
- **Strong interfaces**: Strategy and RiskManager are abstract base classes. You implement `Strategy.on_event` (event → signals) and `RiskManager.check` (signal/order + portfolio → order or reject). The core does not implement trading logic; it defines the contracts.
- **Separation of concerns**:
  - **Events**: Immutable carriers (e.g. timestamp, payload).
  - **Signal**: Trading intent (symbol, side, quantity)—produced by strategies.
  - **Order**: Executable intent (e.g. after risk approval)—the core models orders but does not send them anywhere.
  - **Portfolio**: Cash and positions; mutable state updated by the engine (e.g. on simulated fills).
  - **EventLoop**: Subscriptions and deterministic dispatch.
  - **Strategy / RiskManager**: Implementations plug in behind the same interfaces.

The package is designed so that backtests and later live wiring can share the same types and flow: events in → strategies → signals → risk → orders → portfolio updates.

## What it intentionally does *not* do yet

- **No AI**: No models, no LLMs, no adaptive logic in the core. Strategies are pure functions of events and state.
- **No Streamlit / UI**: No dashboards or web apps. The core is a library.
- **No broker integrations**: No order routing, no market data feeds, no FIX/REST. The core deals in events, signals, and orders as data; brokers are future adapters.
- **No persistence**: No database or serialization. State lives in memory (e.g. `Portfolio`, `EventLoop`).
- **No execution layer**: No fill simulation, no slippage model, no matching engine. Those belong in a separate layer that turns orders into events the core can consume.

So: the core is the *contract* and the *event loop*; execution, data, and UI are out of scope for this package.

## How agents will integrate later

The design is ready for agents to sit *outside* the core:

1. **Agents as event producers**: An agent (or pipeline) can turn raw market data, news, or other inputs into the event stream that `EventLoop` runs on. The core stays deterministic; agents are one source of events.
2. **Agents as strategy or risk implementers**: An agent can implement `Strategy` or `RiskManager` by calling an LLM or a model and mapping the output to `Signal` or `Order`. The core still only sees events, signals, and orders—it does not care whether a human or an agent wrote the strategy.
3. **Agents as orchestrators**: A higher-level agent can choose which strategies to register, which risk manager to use, and when to start/stop the loop or feed new events. The core remains a dumb engine: it dispatches events and respects the interfaces.

So agents *use* qtos-core; they are not *inside* it. The core stays minimal, testable, and deterministic.

## Backtesting Framework

A modular backtesting framework sits on top of the core engine. It loads OHLCV data (CSV or DataFrame), builds market events, runs your strategy and risk manager through the EventLoop, updates the portfolio on simulated fills, and computes performance metrics. No AI, Streamlit, or broker connectivity—purely deterministic backtesting and metrics collection.

**Flow:** Load data → instantiate Portfolio, Strategy, RiskManager → feed market events to EventLoop → strategy emits signals → risk validates orders → portfolio and cash update on fills → collect trades and equity curve → compute metrics (final value, PnL, CAGR, Sharpe, max drawdown).

**Agent integration:** The engine accepts optional **advisors** (modify signals before risk), **validators** (modify or reject orders after risk), and **observers** (post-trade callbacks). Agents such as MarketRegime, Sentiment, or CapitalGuardian can plug in as one of these without changing the core.

**Usage:** Install with `pip install -e .` (pandas and numpy are required for backtesting). From the repo root, run the example with `PYTHONPATH=. python examples/buy_and_hold_backtest.py`.

**Example snippet:**

```python
from backtesting import BacktestEngine, load_csv, print_report
from backtesting.engine import PassThroughRiskManager
from qtos_core import Portfolio
from qtos_core.examples.buy_and_hold import BuyAndHoldStrategy

data = load_csv("path/to/ohlcv.csv", symbol="SPY")
portfolio = Portfolio(cash=100_000.0)
strategy = BuyAndHoldStrategy(symbol="SPY", quantity=50)
risk_manager = PassThroughRiskManager()
engine = BacktestEngine(strategy, risk_manager, portfolio)
result = engine.run(data, symbol="SPY")
print_report(result, initial_value=100_000.0)
```

## Requirements

- Python 3.11+
- pandas, numpy (for backtesting)

## Install

From the repo root:

```bash
pip install -e .
```

## Layout

```
qtos_core/           # Core engine
  events.py          # Event base type
  event_loop.py     # EventLoop (subscribe, dispatch, run)
  signal.py         # Signal, Side
  order.py          # Order, OrderType
  portfolio.py      # Portfolio (cash, positions)
  strategy.py       # Strategy ABC
  risk.py           # RiskManager ABC
  examples/
    buy_and_hold.py # Minimal example strategy

backtesting/         # Backtesting framework
  engine.py         # Orchestrates events through EventLoop; agent hooks
  metrics.py        # PnL, Sharpe, drawdown, CAGR
  data_loader.py    # Load CSV or DataFrame OHLCV
  portfolio_report.py  # Print performance summary

examples/            # Top-level examples
  buy_and_hold_backtest.py  # Demo backtest
  data/
    sample_ohlcv.csv       # Sample price data
```

## Example

```python
from datetime import datetime
from qtos_core import Event, EventLoop, Portfolio
from qtos_core.examples.buy_and_hold import BuyAndHoldStrategy

loop = EventLoop()
portfolio = Portfolio(cash=100_000.0)
strategy = BuyAndHoldStrategy(symbol="SPY", quantity=10)

def on_event(event: Event) -> None:
    for signal in strategy.on_event(event, portfolio):
        print(signal)  # e.g. persist or pass to risk/order layer

loop.subscribe(on_event)
loop.run([Event(timestamp=datetime.now(), payload=None)])
```

This illustrates the flow: one event → strategy emits a signal. In a full setup you would also register a risk manager and a handler that converts approved orders into portfolio updates or downstream actions.

## License

MIT.
