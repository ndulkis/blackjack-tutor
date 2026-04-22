from __future__ import annotations

from dataclasses import dataclass

RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
SUITS = ("H", "D", "C", "S")

_RANK_TO_CHAR: dict[str, str] = {r: r if len(r) == 1 else "T" for r in RANKS}
_CHAR_TO_RANK: dict[str, str] = {v: k for k, v in _RANK_TO_CHAR.items()}


@dataclass(frozen=True)
class Card:
    """A single playing card.

    rank: '2'..'10', 'J', 'Q', 'K', 'A'
    suit: 'H', 'D', 'C', 'S'
    String encoding: 'TS' = ten of spades, 'AH' = ace of hearts.
    """

    rank: str
    suit: str

    def __post_init__(self) -> None:
        if self.rank not in RANKS:
            raise ValueError(f"Invalid rank: {self.rank!r}")
        if self.suit not in SUITS:
            raise ValueError(f"Invalid suit: {self.suit!r}")

    @classmethod
    def from_str(cls, s: str) -> Card:
        """Parse a two-character card string, e.g. 'TS' → Card('10', 'S')."""
        if len(s) != 2:
            raise ValueError(f"Card string must be 2 characters: {s!r}")
        rank_char, suit = s[0], s[1]
        rank = _CHAR_TO_RANK.get(rank_char)
        if rank is None or suit not in SUITS:
            raise ValueError(f"Invalid card string: {s!r}")
        return cls(rank, suit)

    def __str__(self) -> str:
        return _RANK_TO_CHAR[self.rank] + self.suit

    @property
    def value(self) -> int:
        """Blackjack point value. Aces return 11; Hand adjusts them to 1 as needed."""
        if self.rank == "A":
            return 11
        if self.rank in ("10", "J", "Q", "K"):
            return 10
        return int(self.rank)
