"""
Buy-and-hold backtest demo using the backtesting framework.

Demonstrates: load CSV → run strategy → risk check → portfolio updates → metrics.
Ready for agent integration (advisors, validators, observers).
"""

from pathlib import Path

from backtesting import BacktestEngine, load_csv, print_report
from backtesting.engine import PassThroughRiskManager
from qtos_core import Portfolio
from qtos_core.examples.buy_and_hold import BuyAndHoldStrategy


def main() -> None:
    # Path to sample data (relative to repo root or script)
    data_dir = Path(__file__).resolve().parent / "data"
    csv_path = data_dir / "sample_ohlcv.csv"

    # Load historical price data
    data = load_csv(csv_path, symbol="SPY")
    symbol = data.attrs.get("symbol", "SPY")

    # Initial capital and core components
    initial_cash = 100_000.0
    portfolio = Portfolio(cash=initial_cash)
    strategy = BuyAndHoldStrategy(symbol=symbol, quantity=50)
    risk_manager = PassThroughRiskManager()

    # Optional: plug in agents later as advisors, validators, observers
    # engine = BacktestEngine(strategy, risk_manager, portfolio, advisors=[...], validators=[...], observers=[...])
    engine = BacktestEngine(
        strategy=strategy,
        risk_manager=risk_manager,
        portfolio=portfolio,
        advisors=(),   # e.g. MarketRegime, Sentiment
        validators=(),  # e.g. CapitalGuardian
        observers=(),   # post-trade analysis
    )

    # Run backtest
    result = engine.run(data, symbol=symbol)

    # Performance summary
    print_report(result, initial_value=initial_cash)


if __name__ == "__main__":
    main()
