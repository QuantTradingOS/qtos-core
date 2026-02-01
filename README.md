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

## Requirements

- Python 3.11+

## Install

From the repo root:

```bash
pip install -e .
```

## Layout

```
qtos_core/
  events.py      # Event base type
  event_loop.py  # EventLoop (subscribe, dispatch, run)
  signal.py      # Signal, Side
  order.py       # Order, OrderType
  portfolio.py   # Portfolio (cash, positions)
  strategy.py    # Strategy ABC
  risk.py        # RiskManager ABC
  examples/
    buy_and_hold.py  # Minimal example strategy
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
