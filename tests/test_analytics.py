"""Tests for analytics/session.py and analytics/streaks.py."""
from __future__ import annotations

import pytest

from analytics.session import (
    CategoryStats,
    Decision,
    InsuranceStats,
    SessionTracker,
    _zone,
)
from analytics.streaks import StreakTracker
from core.card import Card
from core.game import Action
from core.hand import Hand


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _card(rank: str, suit: str = "H") -> Card:
    return Card(rank, suit)


def _hand(*ranks: str) -> Hand:
    return Hand(cards=[_card(r, s) for r, s in zip(ranks, "HDCS")])


def _decision(
    hand: Hand,
    dealer_rank: str,
    player: Action,
    optimal: Action,
    is_primary: bool = True,
) -> Decision:
    return Decision(
        hand_snapshot=hand,
        dealer_up=_card(dealer_rank),
        player_action=player,
        optimal_action=optimal,
        was_correct=(player == optimal),
        is_primary=is_primary,
        timestamp=Decision.make_timestamp(),
    )


# ---------------------------------------------------------------------------
# CategoryStats
# ---------------------------------------------------------------------------

class TestCategoryStats:
    def test_accuracy_none_when_no_decisions(self) -> None:
        assert CategoryStats().accuracy is None

    def test_accuracy_calculation(self) -> None:
        s = CategoryStats(correct=3, total=4)
        assert s.accuracy == pytest.approx(0.75)

    def test_perfect_accuracy(self) -> None:
        s = CategoryStats(correct=5, total=5)
        assert s.accuracy == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Zone bucketing
# ---------------------------------------------------------------------------

class TestZone:
    def test_hard_5_to_11(self) -> None:
        for total, r1, r2 in [(5, "2", "3"), (8, "3", "5"), (11, "5", "6")]:
            hand = _hand(r1, r2)
            assert not hand.is_soft
            d = _decision(hand, "6", Action.HIT, Action.HIT)
            assert _zone(d) == "Hard 5-11", f"total={total}"

    def test_hard_12_to_16(self) -> None:
        for r1, r2 in [("5", "7"), ("6", "8"), ("7", "9")]:
            hand = _hand(r1, r2)
            d = _decision(hand, "6", Action.STAND, Action.STAND)
            assert _zone(d) == "Hard 12-16"

    def test_hard_17_plus(self) -> None:
        hand = _hand("9", "8")  # hard 17
        d = _decision(hand, "6", Action.STAND, Action.STAND)
        assert _zone(d) == "Hard 17+"

    def test_soft_total(self) -> None:
        hand = _hand("A", "6")  # soft 17
        assert hand.is_soft
        d = _decision(hand, "6", Action.HIT, Action.HIT)
        assert _zone(d) == "Soft totals"

    def test_pair(self) -> None:
        hand = Hand(cards=[_card("8", "H"), _card("8", "D")])
        assert hand.is_pair
        d = _decision(hand, "6", Action.SPLIT, Action.SPLIT)
        assert _zone(d) == "Pairs"


# ---------------------------------------------------------------------------
# SessionTracker — accuracy
# ---------------------------------------------------------------------------

class TestSessionTrackerAccuracy:
    def test_accuracy_none_when_empty(self) -> None:
        tracker = SessionTracker()
        assert tracker.accuracy() is None

    def test_all_correct(self) -> None:
        tracker = SessionTracker()
        for _ in range(5):
            tracker.record(_decision(_hand("5", "6"), "7", Action.HIT, Action.HIT))
        assert tracker.accuracy() == pytest.approx(1.0)

    def test_all_wrong(self) -> None:
        tracker = SessionTracker()
        for _ in range(4):
            tracker.record(_decision(_hand("5", "6"), "7", Action.STAND, Action.HIT))
        assert tracker.accuracy() == pytest.approx(0.0)

    def test_mixed_accuracy(self) -> None:
        tracker = SessionTracker()
        for _ in range(3):
            tracker.record(_decision(_hand("5", "6"), "7", Action.HIT, Action.HIT))
        for _ in range(1):
            tracker.record(_decision(_hand("5", "6"), "7", Action.STAND, Action.HIT))
        assert tracker.accuracy() == pytest.approx(0.75)

    def test_secondary_decisions_excluded_from_accuracy(self) -> None:
        tracker = SessionTracker()
        tracker.record(_decision(_hand("5", "6"), "7", Action.HIT, Action.HIT))
        # Add a wrong insurance decision (secondary)
        tracker.record(
            _decision(_hand("5", "6"), "A", Action.INSURE, Action.DECLINE_INSURANCE, is_primary=False)
        )
        assert tracker.accuracy() == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# SessionTracker — six-category bucketing
# ---------------------------------------------------------------------------

class TestSessionTrackerCategories:
    def test_hard_5_11_bucket(self) -> None:
        tracker = SessionTracker()
        hand = _hand("4", "5")  # hard 9
        tracker.record(_decision(hand, "6", Action.DOUBLE, Action.DOUBLE))
        tracker.record(_decision(hand, "6", Action.HIT, Action.DOUBLE))  # wrong
        cats = tracker.by_category()
        assert cats["Hard 5-11"].total == 2
        assert cats["Hard 5-11"].correct == 1

    def test_hard_12_16_bucket(self) -> None:
        tracker = SessionTracker()
        hand = _hand("6", "7")  # hard 13
        tracker.record(_decision(hand, "5", Action.STAND, Action.STAND))
        cats = tracker.by_category()
        assert cats["Hard 12-16"].total == 1
        assert cats["Hard 12-16"].correct == 1

    def test_hard_17_plus_bucket(self) -> None:
        tracker = SessionTracker()
        hand = _hand("9", "9")  # hard 18 (pair too, but is_pair checked first by _zone — wait, _zone checks pair first)
        # Use non-pair hard 17+
        hand2 = Hand(cards=[_card("9", "H"), _card("8", "D")])  # hard 17
        tracker.record(_decision(hand2, "6", Action.STAND, Action.STAND))
        cats = tracker.by_category()
        assert cats["Hard 17+"].total == 1

    def test_soft_totals_bucket(self) -> None:
        tracker = SessionTracker()
        hand = _hand("A", "7")  # soft 18
        tracker.record(_decision(hand, "9", Action.HIT, Action.HIT))
        cats = tracker.by_category()
        assert cats["Soft totals"].total == 1

    def test_pairs_bucket(self) -> None:
        tracker = SessionTracker()
        hand = Hand(cards=[_card("8", "H"), _card("8", "D")])
        tracker.record(_decision(hand, "6", Action.SPLIT, Action.SPLIT))
        cats = tracker.by_category()
        assert cats["Pairs"].total == 1

    def test_surrender_bucket(self) -> None:
        tracker = SessionTracker()
        hand = _hand("8", "8")  # hard 16 — would be a pair but let's use 8+8 directly
        # Make it look like a non-pair hard 16
        hand2 = Hand(cards=[_card("9", "H"), _card("7", "D")])  # hard 16
        tracker.record(_decision(hand2, "10", Action.SURRENDER, Action.SURRENDER))
        cats = tracker.by_category()
        assert cats["Surrender"].total == 1

    def test_missed_surrender_goes_to_surrender_bucket(self) -> None:
        """When optimal was SURRENDER but player chose HIT, bucket as Surrender."""
        tracker = SessionTracker()
        hand = Hand(cards=[_card("9", "H"), _card("7", "D")])  # hard 16
        tracker.record(_decision(hand, "10", Action.HIT, Action.SURRENDER))
        cats = tracker.by_category()
        assert cats["Surrender"].total == 1
        assert cats["Surrender"].correct == 0

    def test_categories_sum_matches_total_primary_decisions(self) -> None:
        tracker = SessionTracker()
        hands = [
            _hand("3", "4"),  # hard 7
            _hand("A", "6"),  # soft 17
            _hand("6", "8"),  # hard 14
            Hand(cards=[_card("8", "H"), _card("8", "D")]),  # pair
        ]
        for hand in hands:
            tracker.record(_decision(hand, "6", Action.HIT, Action.HIT))
        cats = tracker.by_category()
        total_from_cats = sum(s.total for s in cats.values())
        assert total_from_cats == 4


# ---------------------------------------------------------------------------
# SessionTracker — insurance stats
# ---------------------------------------------------------------------------

class TestInsuranceStats:
    def _ins_decision(self, player: Action, optimal: Action) -> Decision:
        hand = _hand("9", "8")
        return Decision(
            hand_snapshot=hand,
            dealer_up=_card("A"),
            player_action=player,
            optimal_action=optimal,
            was_correct=(player == optimal),
            is_primary=False,
            timestamp=Decision.make_timestamp(),
        )

    def test_taken_correctly(self) -> None:
        tracker = SessionTracker()
        tracker.record(self._ins_decision(Action.INSURE, Action.INSURE))
        stats = tracker.insurance_stats()
        assert stats.taken_correctly == 1
        assert stats.total == 1

    def test_declined_correctly(self) -> None:
        tracker = SessionTracker()
        tracker.record(self._ins_decision(Action.DECLINE_INSURANCE, Action.DECLINE_INSURANCE))
        stats = tracker.insurance_stats()
        assert stats.declined_correctly == 1

    def test_taken_incorrectly(self) -> None:
        tracker = SessionTracker()
        tracker.record(self._ins_decision(Action.INSURE, Action.DECLINE_INSURANCE))
        stats = tracker.insurance_stats()
        assert stats.taken_incorrectly == 1

    def test_declined_incorrectly(self) -> None:
        tracker = SessionTracker()
        tracker.record(self._ins_decision(Action.DECLINE_INSURANCE, Action.INSURE))
        stats = tracker.insurance_stats()
        assert stats.declined_incorrectly == 1

    def test_insurance_does_not_affect_accuracy(self) -> None:
        tracker = SessionTracker()
        tracker.record(_decision(_hand("3", "4"), "6", Action.HIT, Action.HIT))
        tracker.record(self._ins_decision(Action.INSURE, Action.DECLINE_INSURANCE))
        assert tracker.accuracy() == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# StreakTracker
# ---------------------------------------------------------------------------

class TestStreakTracker:
    def test_initial_state(self) -> None:
        t = StreakTracker()
        assert t.current == 0
        assert t.best == 0

    def test_correct_increments_current(self) -> None:
        t = StreakTracker()
        t.record(True, True)
        t.record(True, True)
        assert t.current == 2

    def test_incorrect_resets_current(self) -> None:
        t = StreakTracker()
        t.record(True, True)
        t.record(True, True)
        t.record(False, True)
        assert t.current == 0

    def test_best_preserved_after_reset(self) -> None:
        t = StreakTracker()
        for _ in range(5):
            t.record(True, True)
        t.record(False, True)
        assert t.best == 5
        assert t.current == 0

    def test_new_streak_updates_best(self) -> None:
        t = StreakTracker()
        for _ in range(3):
            t.record(True, True)
        t.record(False, True)
        for _ in range(7):
            t.record(True, True)
        assert t.best == 7
        assert t.current == 7

    def test_secondary_decisions_do_not_affect_streak(self) -> None:
        t = StreakTracker()
        t.record(True, True)
        t.record(True, True)
        t.record(False, False)  # secondary wrong — must not break streak
        assert t.current == 2
        t.record(True, False)   # secondary correct — must not extend streak
        assert t.current == 2

    def test_streak_after_all_wrong(self) -> None:
        t = StreakTracker()
        for _ in range(4):
            t.record(False, True)
        assert t.current == 0
        assert t.best == 0

    def test_single_correct(self) -> None:
        t = StreakTracker()
        t.record(True, True)
        assert t.current == 1
        assert t.best == 1
