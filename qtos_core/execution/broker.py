"""
Broker abstraction layer.

BrokerAdapter ABC: submit_order, get_portfolio, get_market_data.
Future live adapters (Alpaca, IBKR) implement this interface; paper adapter implements it for simulation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from qtos_core.order import Order

from qtos_core.execution.types import OrderStatus, PortfolioState

if TYPE_CHECKING:
    import pandas as pd


class BrokerAdapter(ABC):
    """
    Abstract broker adapter. Same interface for paper and live execution.
    Implementations: PaperBrokerAdapter (in this package); future: AlpacaAdapter, IBKRAdapter.
    """

    @abstractmethod
    def submit_order(self, order: Order) -> OrderStatus:
        """
        Submit an order. Returns status (filled, rejected, etc.).
        In paper mode: simulates fill at latest market price.
        In live mode: sends to broker and returns when acked/filled (implementation-dependent).
        """
        ...

    @abstractmethod
    def get_portfolio(self) -> PortfolioState:
        """Return current portfolio snapshot (cash + positions)."""
        ...

    @abstractmethod
    def get_market_data(self, symbols: list[str]) -> "pd.DataFrame":
        """
        Return latest market data for the given symbols.
        DataFrame should have columns appropriate for pricing (e.g. open, high, low, close, volume)
        and an index or column identifying symbol. Paper adapter returns simulated data;
        live adapters query broker/market data API.
        """
        ...


# ---------------------------------------------------------------------------
# Placeholder for future live broker adapters (do not modify backtesting).
# Uncomment and implement when integrating Alpaca, IBKR, etc.
# ---------------------------------------------------------------------------
#
# class AlpacaBrokerAdapter(BrokerAdapter):
#     """Live adapter for Alpaca. Requires ALPACA_API_KEY, ALPACA_SECRET_KEY."""
#
#     def submit_order(self, order: Order) -> OrderStatus:
#         # Call Alpaca API; map response to OrderStatus
#         raise NotImplementedError("Alpaca adapter not implemented")
#
#     def get_portfolio(self) -> PortfolioState:
#         raise NotImplementedError("Alpaca adapter not implemented")
#
#     def get_market_data(self, symbols: list[str]) -> pd.DataFrame:
#         raise NotImplementedError("Alpaca adapter not implemented")
#
# class IBKRBrokerAdapter(BrokerAdapter):
#     """Live adapter for Interactive Brokers. Requires TWS/Gateway and ib_insync or similar."""
#
#     def submit_order(self, order: Order) -> OrderStatus:
#         raise NotImplementedError("IBKR adapter not implemented")
#
#     def get_portfolio(self) -> PortfolioState:
#         raise NotImplementedError("IBKR adapter not implemented")
#
#     def get_market_data(self, symbols: list[str]) -> pd.DataFrame:
#         raise NotImplementedError("IBKR adapter not implemented")
