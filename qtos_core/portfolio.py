"""
Portfolio: positions and cash. Read model for strategies and risk.

The core holds state here; it does not reconcile with a broker.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Portfolio:
    """
    Cash and positions. Mutable; updated by the engine on fills/settlements.
    """

    cash: float = 0.0
    positions: dict[str, float] = field(default_factory=dict)

    def position(self, symbol: str) -> float:
        """Quantity held in symbol. 0 if not present."""
        return self.positions.get(symbol, 0.0)

    def update_position(self, symbol: str, delta: float) -> None:
        """Adjust position by delta (positive = buy)."""
        self.positions[symbol] = self.position(symbol) + delta
        if self.positions[symbol] == 0:
            del self.positions[symbol]
