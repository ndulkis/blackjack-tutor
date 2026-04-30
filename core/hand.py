from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from core.card import Card


@dataclass
class Hand:
    """A player or dealer hand during a round.

    cards: ordered list of dealt cards.
    is_split_from: ID of the parent hand if this hand was created by splitting, else None.
    has_doubled: True after a double-down action.
    is_surrendered: True after a late surrender.
    is_split_ace: True if this hand was created by splitting aces (one card only, no further
        actions).
    """

    cards: list[Card] = field(default_factory=list)
    is_split_from: Optional[str] = None
    has_doubled: bool = False
    is_surrendered: bool = False
    is_split_ace: bool = False

    def _compute(self) -> tuple[int, bool]:
        """Return (best_total, is_soft). Reduces aces from 11→1 as needed to stay ≤21."""
        total = sum(c.value for c in self.cards)
        aces_as_11 = sum(1 for c in self.cards if c.rank == "A")
        while total > 21 and aces_as_11 > 0:
            total -= 10
            aces_as_11 -= 1
        return total, aces_as_11 > 0

    @property
    def total(self) -> int:
        """Best total ≤ 21, or lowest bust total if all reductions still exceed 21."""
        return self._compute()[0]

    @property
    def is_soft(self) -> bool:
        """True if at least one ace is currently counted as 11."""
        return self._compute()[1]

    @property
    def is_pair(self) -> bool:
        """True if exactly 2 cards with equal blackjack value (eligible to split).

        Any two 10-value cards (10/J/Q/K) are considered a pair per house rules.
        """
        return len(self.cards) == 2 and self.cards[0].value == self.cards[1].value

    @property
    def is_natural_blackjack(self) -> bool:
        """True only for a 2-card 21 on an unsplit hand (pays 3:2)."""
        return len(self.cards) == 2 and self.total == 21 and self.is_split_from is None

    @property
    def category_label(self) -> str:
        """Analytics zone label. Priority: pair > soft > hard."""
        if self.is_pair:
            return f"Pair {self.cards[0].rank}s"
        if self.is_soft:
            return f"Soft {self.total}"
        return f"Hard {self.total}"
