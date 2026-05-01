"""Tests for coach/base.py and coach/rule_coach.py."""
from __future__ import annotations

from analytics.session import Decision
from coach.base import Coach, CoachResult
from coach.rule_coach import RuleCoach
from core.card import Card
from core.game import Action
from core.hand import Hand
from core.rules import RuleSet

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _card(rank: str, suit: str = "H") -> Card:
    return Card(rank, suit)


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


def _hard(r1: str, r2: str) -> Hand:
    return Hand(cards=[_card(r1, "H"), _card(r2, "D")])


def _soft(other: str) -> Hand:
    return Hand(cards=[_card("A", "H"), _card(other, "D")])


def _pair(rank: str) -> Hand:
    return Hand(cards=[_card(rank, "H"), _card(rank, "D")])


_RULES = RuleSet()


# ---------------------------------------------------------------------------
# CoachResult
# ---------------------------------------------------------------------------

class TestCoachResult:
    def test_is_ready_immediately(self) -> None:
        result = CoachResult("nice play")
        assert result.is_ready()

    def test_get_returns_text(self) -> None:
        result = CoachResult("keep it up")
        assert result.get() == "keep it up"

    def test_pending_not_ready(self) -> None:
        result = CoachResult.pending()
        assert not result.is_ready()

    def test_pending_get_returns_empty(self) -> None:
        result = CoachResult.pending()
        assert result.get() == ""


# ---------------------------------------------------------------------------
# Coach Protocol
# ---------------------------------------------------------------------------

class TestCoachProtocol:
    def test_rule_coach_satisfies_protocol(self) -> None:
        coach = RuleCoach()
        assert isinstance(coach, Coach)


# ---------------------------------------------------------------------------
# RuleCoach — correct decisions
# ---------------------------------------------------------------------------

class TestRuleCoachCorrect:
    coach = RuleCoach()

    def test_correct_message_starts_with_correct(self) -> None:
        d = _decision(_hard("9", "8"), "6", Action.STAND, Action.STAND)
        result = self.coach.explain(d, _RULES)
        assert result.is_ready()
        assert result.get().lower().startswith("correct")

    def test_correct_message_mentions_action(self) -> None:
        d = _decision(_hard("4", "5"), "6", Action.DOUBLE, Action.DOUBLE)
        text = self.coach.explain(d, _RULES).get()
        assert "double" in text.lower()

    def test_correct_hit(self) -> None:
        d = _decision(_hard("3", "4"), "9", Action.HIT, Action.HIT)
        text = self.coach.explain(d, _RULES).get()
        assert "correct" in text.lower()

    def test_correct_split(self) -> None:
        d = _decision(_pair("8"), "6", Action.SPLIT, Action.SPLIT)
        text = self.coach.explain(d, _RULES).get()
        assert "correct" in text.lower()

    def test_correct_surrender(self) -> None:
        d = _decision(_hard("9", "7"), "10", Action.SURRENDER, Action.SURRENDER)
        text = self.coach.explain(d, _RULES).get()
        assert "correct" in text.lower()


# ---------------------------------------------------------------------------
# RuleCoach — incorrect decisions
# ---------------------------------------------------------------------------

class TestRuleCoachIncorrect:
    coach = RuleCoach()

    def test_incorrect_message_mentions_player_action(self) -> None:
        d = _decision(_hard("9", "7"), "6", Action.HIT, Action.STAND)
        text = self.coach.explain(d, _RULES).get()
        assert "hit" in text.lower()

    def test_incorrect_message_mentions_optimal_action(self) -> None:
        d = _decision(_hard("9", "7"), "6", Action.HIT, Action.STAND)
        text = self.coach.explain(d, _RULES).get()
        assert "stand" in text.lower()

    def test_missed_double_explains_stand_is_wrong(self) -> None:
        d = _decision(_hard("5", "6"), "5", Action.HIT, Action.DOUBLE)
        text = self.coach.explain(d, _RULES).get()
        assert "double" in text.lower()

    def test_missed_surrender_explanation_mentions_surrender(self) -> None:
        d = _decision(_hard("9", "7"), "10", Action.HIT, Action.SURRENDER)
        text = self.coach.explain(d, _RULES).get()
        assert "surrender" in text.lower()

    def test_missed_split_explanation_mentions_split(self) -> None:
        d = _decision(_pair("8"), "6", Action.HIT, Action.SPLIT)
        text = self.coach.explain(d, _RULES).get()
        assert "split" in text.lower()


# ---------------------------------------------------------------------------
# RuleCoach — insurance (secondary decisions)
# ---------------------------------------------------------------------------

class TestRuleCoachInsurance:
    coach = RuleCoach()

    def test_declined_correctly_message(self) -> None:
        d = _decision(
            _hard("9", "8"), "A",
            Action.DECLINE_INSURANCE, Action.DECLINE_INSURANCE,
            is_primary=False,
        )
        text = self.coach.explain(d, _RULES).get()
        assert "insurance" in text.lower()

    def test_taken_incorrectly_discourages_insurance(self) -> None:
        d = _decision(
            _hard("9", "8"), "A",
            Action.INSURE, Action.DECLINE_INSURANCE,
            is_primary=False,
        )
        text = self.coach.explain(d, _RULES).get()
        assert "insurance" in text.lower()
        # Should discourage the player
        assert any(word in text.lower() for word in ("negative", "rarely", "optimal"))

    def test_taken_correctly_encourages(self) -> None:
        d = _decision(
            _hard("9", "8"), "A",
            Action.INSURE, Action.INSURE,
            is_primary=False,
        )
        text = self.coach.explain(d, _RULES).get()
        assert "insurance" in text.lower()

    def test_declined_incorrectly_suggests_insurance(self) -> None:
        d = _decision(
            _hard("9", "8"), "A",
            Action.DECLINE_INSURANCE, Action.INSURE,
            is_primary=False,
        )
        text = self.coach.explain(d, _RULES).get()
        assert "insurance" in text.lower()


# ---------------------------------------------------------------------------
# RuleCoach — rationale coverage (soft and pair hands)
# ---------------------------------------------------------------------------

class TestRuleCoachRationale:
    coach = RuleCoach()

    def test_soft_18_vs_9_hit_explanation(self) -> None:
        d = _decision(_soft("7"), "9", Action.HIT, Action.HIT)
        text = self.coach.explain(d, _RULES).get()
        assert len(text) > 20

    def test_pair_aces_split_explanation(self) -> None:
        d = _decision(_pair("A"), "6", Action.SPLIT, Action.SPLIT)
        text = self.coach.explain(d, _RULES).get()
        assert "correct" in text.lower()

    def test_pair_10s_stand_explanation(self) -> None:
        d = _decision(_pair("10"), "6", Action.STAND, Action.STAND)
        text = self.coach.explain(d, _RULES).get()
        assert "correct" in text.lower()

    def test_explanation_always_returns_nonempty_string(self) -> None:
        """Every decision type must produce a non-empty message."""
        cases = [
            _decision(_hard("3", "4"), "7", Action.HIT, Action.HIT),
            _decision(_hard("9", "8"), "5", Action.STAND, Action.STAND),
            _decision(_soft("6"), "4", Action.DOUBLE, Action.DOUBLE),
            _decision(_pair("8"), "10", Action.SPLIT, Action.SPLIT),
            _decision(_hard("9", "7"), "10", Action.SURRENDER, Action.SURRENDER),
        ]
        for d in cases:
            text = self.coach.explain(d, _RULES).get()
            assert isinstance(text, str) and len(text) > 0
