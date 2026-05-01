from __future__ import annotations

import random

from core.card import RANKS, SUITS, Card


class Shoe:
    """A multi-deck shoe with a penetration cut card.

    Deals cards in order until the cut card position is reached, then signals
    that a reshuffle is needed before the next round (never mid-round).
    """

    def __init__(
        self,
        num_decks: int = 6,
        penetration: float = 0.75,
        _fixed_cards: list[Card] | None = None,
    ) -> None:
        self.num_decks = num_decks
        self.penetration = penetration
        self._fixed_cards_override = _fixed_cards
        self._cards: list[Card] = []
        self._index: int = 0
        self._cut_card: int = 0
        self._build()

    def _build(self) -> None:
        if self._fixed_cards_override is not None:
            self._cards = list(self._fixed_cards_override)
            self._index = 0
            self._cut_card = len(self._cards)
            return
        self._cards = [
            Card(rank, suit)
            for _ in range(self.num_decks)
            for suit in SUITS
            for rank in RANKS
        ]
        random.shuffle(self._cards)
        self._index = 0
        self._cut_card = int(len(self._cards) * self.penetration)

    def deal(self) -> Card:
        """Deal the next card. Auto-reshuffles if the shoe is exhausted (safety net)."""
        if self._index >= len(self._cards):
            self._build()
        card = self._cards[self._index]
        self._index += 1
        return card

    def needs_reshuffle(self) -> bool:
        """True when the cut card position has been reached; check between rounds."""
        return self._index >= self._cut_card

    def reshuffle(self) -> None:
        """Reshuffle the shoe (call between rounds when needs_reshuffle() is True)."""
        self._build()

    @property
    def cards_remaining(self) -> int:
        return len(self._cards) - self._index
