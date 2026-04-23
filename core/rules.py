from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuleSet:
    """Immutable game rule configuration.

    Defaults match the project variant:
      6-deck shoe, S17 (dealer stands on soft 17), DAS, late surrender,
      BJ pays 3:2, 75% penetration, $10–$500 bets in $5 increments,
      $1000 starting bankroll.
    """

    num_decks: int = 6
    dealer_hits_soft_17: bool = False  # False = S17 (stands), True = H17
    double_after_split: bool = True
    late_surrender: bool = True
    bj_payout: float = 1.5  # 3:2
    penetration: float = 0.75
    min_bet: int = 10
    max_bet: int = 500
    bet_increment: int = 5
    starting_bankroll: int = 1000

    def __post_init__(self) -> None:
        if self.num_decks < 1:
            raise ValueError(f"num_decks must be ≥ 1, got {self.num_decks}")
        if not (0.0 < self.penetration <= 1.0):
            raise ValueError(f"penetration must be in (0, 1], got {self.penetration}")
        if self.bj_payout <= 1.0:
            raise ValueError(f"bj_payout must be > 1.0, got {self.bj_payout}")
        if self.min_bet < 1:
            raise ValueError(f"min_bet must be ≥ 1, got {self.min_bet}")
        if self.max_bet < self.min_bet:
            raise ValueError(
                f"max_bet ({self.max_bet}) must be ≥ min_bet ({self.min_bet})"
            )
        if self.bet_increment < 1:
            raise ValueError(f"bet_increment must be ≥ 1, got {self.bet_increment}")
        if self.starting_bankroll < self.min_bet:
            raise ValueError(
                f"starting_bankroll ({self.starting_bankroll}) must be ≥ min_bet ({self.min_bet})"
            )

    def is_valid_bet(self, amount: int) -> bool:
        """True if amount is within bounds and a multiple of bet_increment."""
        return (
            self.min_bet <= amount <= self.max_bet
            and (amount - self.min_bet) % self.bet_increment == 0
        )
