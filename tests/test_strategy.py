"""Tests for strategy/charts.py, strategy/rationales.py, and strategy/engine.py.

Covers:
- CSV cross-check: every CSV row matches charts.py primary action
- Hard-total coverage across all (total × dealer_up) cells
- Soft-total coverage across all cells
- Pairs coverage including 5,5 and T,T special cases
- Context-aware fallback: DAS=False strips DOUBLE on post-split hands
- Surrender=False strips SURRENDER from fallback chain
- Rationale structure matches chart structure
"""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from core.card import Card
from core.game import Action
from core.hand import Hand
from core.rules import RuleSet
from strategy.charts import HARD_TOTALS, PAIRS, SOFT_TOTALS
from strategy.engine import ActionContext, optimal_action
from strategy.rationales import RATIONALES

FIXTURES = Path(__file__).parent / "fixtures"
CSV_PATH = FIXTURES / "basic_strategy_s17_das.csv"

_DEALER_UPS = list(range(2, 12))  # 2..10, 11=Ace


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _card(rank: str, suit: str = "H") -> Card:
    return Card(rank, suit)


def _dealer(rank: str) -> Card:
    """Create a dealer up-card. Use 'A' for Ace."""
    return _card(rank)


def _hard_hand(total: int) -> Hand:
    """Return a 2-card hard hand with the given total (2 ≤ total ≤ 20)."""
    assert 4 <= total <= 20, f"Use a different construction for total={total}"
    # Build: a 2 + (total-2), avoiding aces to keep it hard
    low = min(total - 2, 9)
    high = total - low
    # Clamp high to ≤ 10 (T-value)
    if high > 10:
        high = 10
        low = total - high
    rank_low = str(low) if low < 10 else "10"
    rank_high = str(high) if high < 10 else "10"
    return Hand(cards=[_card(rank_low, "H"), _card(rank_high, "D")])


def _soft_hand(total: int) -> Hand:
    """Return a 2-card soft hand: Ace + (total-11)."""
    other_val = total - 11
    assert 2 <= other_val <= 10, f"Cannot build soft {total} with 2 cards"
    rank = str(other_val) if other_val < 10 else "T"
    return Hand(cards=[_card("A", "H"), _card(rank, "D")])


def _pair_hand(rank: str) -> Hand:
    """Return a 2-card pair hand."""
    return Hand(cards=[_card(rank, "H"), _card(rank, "D")])


def _dealer_up(up_key: int) -> Card:
    """Convert a chart dealer key (2-10, 11=Ace) to a Card."""
    if up_key == 11:
        return _card("A")
    if up_key == 10:
        return _card("10")
    return _card(str(up_key))


def _primary_action(entry: object) -> Action:
    """Return the first action from a chart entry (single or tuple)."""
    return entry[0] if isinstance(entry, tuple) else entry  # type: ignore[index]


# ---------------------------------------------------------------------------
# CSV cross-check: charts.py must match the manually transcribed fixture
# ---------------------------------------------------------------------------

class TestCsvCrossCheck:
    """Every row in the CSV fixture must match the corresponding chart entry."""

    def _action_name(self, entry: object) -> str:
        return _primary_action(entry).name

    @pytest.mark.parametrize("row", list(csv.DictReader(CSV_PATH.open())))
    def test_csv_matches_charts(self, row: dict[str, str]) -> None:
        category = row["category"]
        dealer_up = int(row["dealer_up"]) if row["dealer_up"].isdigit() else 11
        expected = row["action"]

        if category == "hard":
            total = int(row["player_value"])
            entry = HARD_TOTALS[total][dealer_up]
        elif category == "soft":
            total = int(row["player_value"])
            entry = SOFT_TOTALS[total][dealer_up]
        else:  # pair
            rank = row["player_value"]
            entry = PAIRS[rank][dealer_up]

        assert self._action_name(entry) == expected, (
            f"{category} {row['player_value']} vs dealer {dealer_up}: "
            f"chart says {self._action_name(entry)}, CSV says {expected}"
        )


# ---------------------------------------------------------------------------
# Hard totals
# ---------------------------------------------------------------------------

class TestHardTotals:
    def test_hard_4_to_8_always_hit(self) -> None:
        for total in range(4, 9):
            for up in _DEALER_UPS:
                assert HARD_TOTALS[total][up] == Action.HIT

    def test_hard_9_hit_vs_2(self) -> None:
        assert HARD_TOTALS[9][2] == Action.HIT

    def test_hard_9_double_vs_3_to_6(self) -> None:
        for up in (3, 4, 5, 6):
            assert HARD_TOTALS[9][up] == (Action.DOUBLE, Action.HIT)

    def test_hard_9_hit_vs_7_to_ace(self) -> None:
        for up in (7, 8, 9, 10, 11):
            assert HARD_TOTALS[9][up] == Action.HIT

    def test_hard_10_double_vs_2_to_9(self) -> None:
        for up in range(2, 10):
            assert HARD_TOTALS[10][up] == (Action.DOUBLE, Action.HIT)

    def test_hard_10_hit_vs_10_ace(self) -> None:
        assert HARD_TOTALS[10][10] == Action.HIT
        assert HARD_TOTALS[10][11] == Action.HIT

    def test_hard_11_double_vs_2_to_10(self) -> None:
        for up in range(2, 11):
            assert HARD_TOTALS[11][up] == (Action.DOUBLE, Action.HIT)

    def test_hard_11_hit_vs_ace(self) -> None:
        assert HARD_TOTALS[11][11] == Action.HIT

    def test_hard_12_hit_vs_2_3(self) -> None:
        assert HARD_TOTALS[12][2] == Action.HIT
        assert HARD_TOTALS[12][3] == Action.HIT

    def test_hard_12_stand_vs_4_to_6(self) -> None:
        for up in (4, 5, 6):
            assert HARD_TOTALS[12][up] == Action.STAND

    def test_hard_12_hit_vs_7_to_ace(self) -> None:
        for up in (7, 8, 9, 10, 11):
            assert HARD_TOTALS[12][up] == Action.HIT

    def test_hard_13_14_stand_vs_2_to_6(self) -> None:
        for total in (13, 14):
            for up in range(2, 7):
                assert HARD_TOTALS[total][up] == Action.STAND

    def test_hard_13_14_hit_vs_7_to_ace(self) -> None:
        for total in (13, 14):
            for up in range(7, 12):
                assert HARD_TOTALS[total][up] == Action.HIT

    def test_hard_15_stand_vs_2_to_6(self) -> None:
        for up in range(2, 7):
            assert HARD_TOTALS[15][up] == Action.STAND

    def test_hard_15_hit_vs_7_to_9(self) -> None:
        for up in (7, 8, 9):
            assert HARD_TOTALS[15][up] == Action.HIT

    def test_hard_15_surrender_vs_10_ace(self) -> None:
        assert HARD_TOTALS[15][10] == (Action.SURRENDER, Action.HIT)
        assert HARD_TOTALS[15][11] == (Action.SURRENDER, Action.HIT)

    def test_hard_16_stand_vs_2_to_6(self) -> None:
        for up in range(2, 7):
            assert HARD_TOTALS[16][up] == Action.STAND

    def test_hard_16_hit_vs_7_8(self) -> None:
        assert HARD_TOTALS[16][7] == Action.HIT
        assert HARD_TOTALS[16][8] == Action.HIT

    def test_hard_16_surrender_vs_9_10_ace(self) -> None:
        for up in (9, 10, 11):
            assert HARD_TOTALS[16][up] == (Action.SURRENDER, Action.HIT)

    def test_hard_17_to_21_always_stand(self) -> None:
        for total in range(17, 22):
            for up in _DEALER_UPS:
                assert HARD_TOTALS[total][up] == Action.STAND


# ---------------------------------------------------------------------------
# Soft totals
# ---------------------------------------------------------------------------

class TestSoftTotals:
    def test_soft_13_14_double_vs_5_6_only(self) -> None:
        for total in (13, 14):
            for up in _DEALER_UPS:
                entry = SOFT_TOTALS[total][up]
                if up in (5, 6):
                    assert entry == (Action.DOUBLE, Action.HIT)
                else:
                    assert entry == Action.HIT

    def test_soft_15_16_double_vs_4_to_6(self) -> None:
        for total in (15, 16):
            for up in _DEALER_UPS:
                entry = SOFT_TOTALS[total][up]
                if up in (4, 5, 6):
                    assert entry == (Action.DOUBLE, Action.HIT)
                else:
                    assert entry == Action.HIT

    def test_soft_17_double_vs_3_to_6(self) -> None:
        for up in _DEALER_UPS:
            entry = SOFT_TOTALS[17][up]
            if up in (3, 4, 5, 6):
                assert entry == (Action.DOUBLE, Action.HIT)
            else:
                assert entry == Action.HIT

    def test_soft_18_double_stand_vs_2_to_6(self) -> None:
        for up in range(2, 7):
            assert SOFT_TOTALS[18][up] == (Action.DOUBLE, Action.STAND)

    def test_soft_18_stand_vs_7_8(self) -> None:
        assert SOFT_TOTALS[18][7] == Action.STAND
        assert SOFT_TOTALS[18][8] == Action.STAND

    def test_soft_18_hit_vs_9_10_ace(self) -> None:
        for up in (9, 10, 11):
            assert SOFT_TOTALS[18][up] == Action.HIT

    def test_soft_19_to_21_always_stand(self) -> None:
        for total in (19, 20, 21):
            for up in _DEALER_UPS:
                assert SOFT_TOTALS[total][up] == Action.STAND


# ---------------------------------------------------------------------------
# Pairs
# ---------------------------------------------------------------------------

class TestPairs:
    def test_aces_always_split(self) -> None:
        for up in _DEALER_UPS:
            assert PAIRS["A"][up] == Action.SPLIT

    def test_twos_threes_split_vs_2_to_7(self) -> None:
        for rank in ("2", "3"):
            for up in range(2, 8):
                assert PAIRS[rank][up] == Action.SPLIT

    def test_twos_threes_hit_vs_8_to_ace(self) -> None:
        for rank in ("2", "3"):
            for up in (8, 9, 10, 11):
                assert PAIRS[rank][up] == Action.HIT

    def test_fours_split_vs_5_6_only(self) -> None:
        for up in _DEALER_UPS:
            if up in (5, 6):
                assert PAIRS["4"][up] == Action.SPLIT
            else:
                assert PAIRS["4"][up] == Action.HIT

    def test_fives_never_split_treated_as_hard_10(self) -> None:
        for up in range(2, 10):
            assert PAIRS["5"][up] == (Action.DOUBLE, Action.HIT)
        assert PAIRS["5"][10] == Action.HIT
        assert PAIRS["5"][11] == Action.HIT

    def test_sixes_split_vs_2_to_6(self) -> None:
        for up in range(2, 7):
            assert PAIRS["6"][up] == Action.SPLIT
        for up in (7, 8, 9, 10, 11):
            assert PAIRS["6"][up] == Action.HIT

    def test_sevens_split_vs_2_to_7(self) -> None:
        for up in range(2, 8):
            assert PAIRS["7"][up] == Action.SPLIT
        for up in (8, 9, 10, 11):
            assert PAIRS["7"][up] == Action.HIT

    def test_eights_always_split(self) -> None:
        for up in _DEALER_UPS:
            assert PAIRS["8"][up] == Action.SPLIT

    def test_nines_split_except_7_10_ace(self) -> None:
        stand_ups = {7, 10, 11}
        for up in _DEALER_UPS:
            if up in stand_ups:
                assert PAIRS["9"][up] == Action.STAND
            else:
                assert PAIRS["9"][up] == Action.SPLIT

    def test_tens_never_split_always_stand(self) -> None:
        for up in _DEALER_UPS:
            assert PAIRS["T"][up] == Action.STAND


# ---------------------------------------------------------------------------
# Engine: basic lookup
# ---------------------------------------------------------------------------

class TestEngine:
    _rules = RuleSet()

    def test_hard_16_vs_10_returns_surrender(self) -> None:
        hand = _hard_hand(16)
        ctx = ActionContext(can_surrender=True)
        result = optimal_action(hand, _dealer_up(10), self._rules, ctx)
        assert result == Action.SURRENDER

    def test_hard_16_vs_10_no_surrender_returns_hit(self) -> None:
        hand = _hard_hand(16)
        ctx = ActionContext(can_surrender=False)
        result = optimal_action(hand, _dealer_up(10), self._rules, ctx)
        assert result == Action.HIT

    def test_hard_11_vs_6_returns_double(self) -> None:
        hand = _hard_hand(11)
        ctx = ActionContext(can_double=True)
        result = optimal_action(hand, _dealer_up(6), self._rules, ctx)
        assert result == Action.DOUBLE

    def test_hard_11_vs_6_no_double_returns_hit(self) -> None:
        hand = _hard_hand(11)
        ctx = ActionContext(can_double=False)
        result = optimal_action(hand, _dealer_up(6), self._rules, ctx)
        assert result == Action.HIT

    def test_hard_13_vs_5_returns_stand(self) -> None:
        hand = _hard_hand(13)
        result = optimal_action(hand, _dealer_up(5), self._rules)
        assert result == Action.STAND

    def test_soft_18_vs_6_returns_double(self) -> None:
        hand = _soft_hand(18)
        ctx = ActionContext(can_double=True)
        result = optimal_action(hand, _dealer_up(6), self._rules, ctx)
        assert result == Action.DOUBLE

    def test_soft_18_vs_6_no_double_returns_stand(self) -> None:
        hand = _soft_hand(18)
        ctx = ActionContext(can_double=False)
        result = optimal_action(hand, _dealer_up(6), self._rules, ctx)
        assert result == Action.STAND

    def test_soft_18_vs_9_returns_hit(self) -> None:
        hand = _soft_hand(18)
        result = optimal_action(hand, _dealer_up(9), self._rules)
        assert result == Action.HIT

    def test_pair_aces_vs_6_returns_split(self) -> None:
        hand = _pair_hand("A")
        result = optimal_action(hand, _dealer_up(6), self._rules)
        assert result == Action.SPLIT

    def test_pair_8s_vs_ace_returns_split(self) -> None:
        hand = _pair_hand("8")
        result = optimal_action(hand, _dealer_up(11), self._rules)
        assert result == Action.SPLIT

    def test_pair_9s_vs_7_returns_stand(self) -> None:
        hand = _pair_hand("9")
        result = optimal_action(hand, _dealer_up(7), self._rules)
        assert result == Action.STAND

    def test_pair_9s_vs_8_returns_split(self) -> None:
        hand = _pair_hand("9")
        result = optimal_action(hand, _dealer_up(8), self._rules)
        assert result == Action.SPLIT

    def test_pair_10s_vs_6_returns_stand(self) -> None:
        hand = _pair_hand("10")
        result = optimal_action(hand, _dealer_up(6), self._rules)
        assert result == Action.STAND

    def test_pair_5s_vs_6_returns_double(self) -> None:
        hand = _pair_hand("5")
        ctx = ActionContext(can_double=True)
        result = optimal_action(hand, _dealer_up(6), self._rules, ctx)
        assert result == Action.DOUBLE

    def test_pair_5s_vs_10_returns_hit(self) -> None:
        hand = _pair_hand("5")
        result = optimal_action(hand, _dealer_up(10), self._rules)
        assert result == Action.HIT

    # J, Q, K normalise to "T" in pairs table
    def test_pair_jacks_vs_5_returns_stand(self) -> None:
        hand = Hand(cards=[_card("J", "H"), _card("J", "D")])
        result = optimal_action(hand, _dealer_up(5), self._rules)
        assert result == Action.STAND

    def test_pair_queens_vs_6_returns_stand(self) -> None:
        hand = Hand(cards=[_card("Q", "H"), _card("Q", "D")])
        result = optimal_action(hand, _dealer_up(6), self._rules)
        assert result == Action.STAND


# ---------------------------------------------------------------------------
# Engine: DAS=False context
# ---------------------------------------------------------------------------

class TestEngineDasOff:
    """With DAS disabled, DOUBLE should not be returned for post-split hands."""

    _rules = RuleSet(double_after_split=False)

    def test_hard_11_post_split_no_double_returns_hit(self) -> None:
        hand = _hard_hand(11)
        hand.is_split_from = "some-parent"
        ctx = ActionContext(is_post_split=True, can_double=False)
        result = optimal_action(hand, _dealer_up(6), self._rules, ctx)
        assert result == Action.HIT

    def test_soft_18_post_split_no_double_returns_stand(self) -> None:
        hand = _soft_hand(18)
        hand.is_split_from = "some-parent"
        ctx = ActionContext(is_post_split=True, can_double=False)
        result = optimal_action(hand, _dealer_up(5), self._rules, ctx)
        assert result == Action.STAND


# ---------------------------------------------------------------------------
# Engine: late surrender disabled
# ---------------------------------------------------------------------------

class TestEngineSurrenderOff:
    _rules = RuleSet(late_surrender=False)

    def test_hard_15_vs_10_no_surrender_returns_hit(self) -> None:
        hand = _hard_hand(15)
        ctx = ActionContext(can_surrender=False)
        result = optimal_action(hand, _dealer_up(10), self._rules, ctx)
        assert result == Action.HIT

    def test_hard_16_vs_9_no_surrender_returns_hit(self) -> None:
        hand = _hard_hand(16)
        ctx = ActionContext(can_surrender=False)
        result = optimal_action(hand, _dealer_up(9), self._rules, ctx)
        assert result == Action.HIT


# ---------------------------------------------------------------------------
# Rationale structure
# ---------------------------------------------------------------------------

class TestRationales:
    def test_hard_rationale_keys_match_chart(self) -> None:
        assert set(RATIONALES["hard"].keys()) == set(HARD_TOTALS.keys())

    def test_soft_rationale_keys_match_chart(self) -> None:
        assert set(RATIONALES["soft"].keys()) == set(SOFT_TOTALS.keys())

    def test_pair_rationale_keys_match_chart(self) -> None:
        assert set(RATIONALES["pair"].keys()) == set(PAIRS.keys())

    def test_all_rationale_values_are_strings(self) -> None:
        for category in ("hard", "soft", "pair"):
            for player_val, dealer_map in RATIONALES[category].items():
                for dealer_up, rationale in dealer_map.items():
                    assert isinstance(rationale, str), (
                        f"RATIONALES[{category!r}][{player_val!r}][{dealer_up}] "
                        f"is not a str: {rationale!r}"
                    )
                    assert rationale, "Rationale string must not be empty"

    def test_hard_16_vs_10_rationale_mentions_surrender(self) -> None:
        rationale = RATIONALES["hard"][16][10]
        assert "surrender" in rationale

    def test_pair_8_rationale_mentions_split(self) -> None:
        rationale = RATIONALES["pair"]["8"][2]
        assert "split" in rationale
