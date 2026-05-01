from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from core.card import Card
from core.game import Action
from core.hand import Hand


@dataclass
class Decision:
    hand_snapshot: Hand
    dealer_up: Card
    player_action: Action
    optimal_action: Action
    was_correct: bool
    is_primary: bool      # False for insurance / declined-surrender-when-not-optimal
    timestamp: str
    coach_response: Optional[str] = None

    @staticmethod
    def make_timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()


@dataclass
class CategoryStats:
    correct: int = 0
    total: int = 0

    @property
    def accuracy(self) -> Optional[float]:
        return self.correct / self.total if self.total else None


@dataclass
class InsuranceStats:
    taken_correctly: int = 0   # took insurance when optimal
    declined_correctly: int = 0
    taken_incorrectly: int = 0
    declined_incorrectly: int = 0

    @property
    def total(self) -> int:
        return (
            self.taken_correctly
            + self.declined_correctly
            + self.taken_incorrectly
            + self.declined_incorrectly
        )


# Six hand-zone categories from spec §7.2
_CATEGORIES = ("Hard 17+", "Hard 12-16", "Hard 5-11", "Soft totals", "Pairs", "Surrender")


def _zone(decision: Decision) -> str:
    """Map a primary decision to one of the six hand-zone category labels."""
    hand = decision.hand_snapshot
    if hand.is_pair:
        return "Pairs"
    total = hand.total
    if hand.is_soft:
        return "Soft totals"
    # Hard totals
    if total >= 17:
        return "Hard 17+"
    if total >= 12:
        return "Hard 12-16"
    return "Hard 5-11"


class SessionTracker:
    def __init__(self) -> None:
        self._decisions: list[Decision] = []
        self._by_category: dict[str, CategoryStats] = {
            cat: CategoryStats() for cat in _CATEGORIES
        }
        self._insurance: InsuranceStats = InsuranceStats()

    def record(self, decision: Decision) -> None:
        self._decisions.append(decision)

        if not decision.is_primary:
            self._update_insurance(decision)
            return

        # Surrender decisions count in the "Surrender" zone when the optimal
        # action was SURRENDER (player either took it or missed it).
        if decision.optimal_action == Action.SURRENDER:
            zone = "Surrender"
        else:
            zone = _zone(decision)

        stats = self._by_category[zone]
        stats.total += 1
        if decision.was_correct:
            stats.correct += 1

    def _update_insurance(self, decision: Decision) -> None:
        took = decision.player_action == Action.INSURE
        optimal = decision.optimal_action == Action.INSURE
        if took and optimal:
            self._insurance.taken_correctly += 1
        elif took and not optimal:
            self._insurance.taken_incorrectly += 1
        elif not took and optimal:
            self._insurance.declined_incorrectly += 1
        else:
            self._insurance.declined_correctly += 1

    def accuracy(self) -> Optional[float]:
        """Overall accuracy across primary decisions only."""
        total = sum(s.total for s in self._by_category.values())
        correct = sum(s.correct for s in self._by_category.values())
        return correct / total if total else None

    def by_category(self) -> dict[str, CategoryStats]:
        return dict(self._by_category)

    def insurance_stats(self) -> InsuranceStats:
        return self._insurance

    def decisions(self) -> list[Decision]:
        return list(self._decisions)
