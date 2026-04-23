"""Tests for core/rules.py."""
from __future__ import annotations

import pytest

from core.rules import RuleSet


class TestRuleSetDefaults:
    def test_default_values(self):
        r = RuleSet()
        assert r.num_decks == 6
        assert r.dealer_hits_soft_17 is False
        assert r.double_after_split is True
        assert r.late_surrender is True
        assert r.bj_payout == 1.5
        assert r.penetration == 0.75
        assert r.min_bet == 10
        assert r.max_bet == 500
        assert r.bet_increment == 5
        assert r.starting_bankroll == 1000

    def test_immutable(self):
        r = RuleSet()
        with pytest.raises((AttributeError, TypeError)):
            r.num_decks = 8  # type: ignore[misc]


class TestRuleSetValidation:
    def test_num_decks_zero_raises(self):
        with pytest.raises(ValueError, match="num_decks"):
            RuleSet(num_decks=0)

    def test_penetration_zero_raises(self):
        with pytest.raises(ValueError, match="penetration"):
            RuleSet(penetration=0.0)

    def test_penetration_above_one_raises(self):
        with pytest.raises(ValueError, match="penetration"):
            RuleSet(penetration=1.1)

    def test_penetration_exactly_one_valid(self):
        r = RuleSet(penetration=1.0)
        assert r.penetration == 1.0

    def test_bj_payout_one_raises(self):
        with pytest.raises(ValueError, match="bj_payout"):
            RuleSet(bj_payout=1.0)

    def test_bj_payout_six_to_five(self):
        r = RuleSet(bj_payout=1.2)
        assert r.bj_payout == 1.2

    def test_min_bet_zero_raises(self):
        with pytest.raises(ValueError, match="min_bet"):
            RuleSet(min_bet=0)

    def test_max_bet_below_min_raises(self):
        with pytest.raises(ValueError, match="max_bet"):
            RuleSet(min_bet=50, max_bet=25)

    def test_max_bet_equal_min_valid(self):
        r = RuleSet(min_bet=25, max_bet=25)
        assert r.min_bet == r.max_bet

    def test_bet_increment_zero_raises(self):
        with pytest.raises(ValueError, match="bet_increment"):
            RuleSet(bet_increment=0)

    def test_starting_bankroll_below_min_bet_raises(self):
        with pytest.raises(ValueError, match="starting_bankroll"):
            RuleSet(min_bet=50, max_bet=500, starting_bankroll=25)


class TestRuleSetToggles:
    def test_h17_variant(self):
        r = RuleSet(dealer_hits_soft_17=True)
        assert r.dealer_hits_soft_17 is True

    def test_no_das(self):
        r = RuleSet(double_after_split=False)
        assert r.double_after_split is False

    def test_no_surrender(self):
        r = RuleSet(late_surrender=False)
        assert r.late_surrender is False


class TestIsValidBet:
    def test_min_bet_valid(self):
        assert RuleSet().is_valid_bet(10) is True

    def test_max_bet_valid(self):
        assert RuleSet().is_valid_bet(500) is True

    def test_mid_range_valid(self):
        assert RuleSet().is_valid_bet(100) is True

    def test_below_min_invalid(self):
        assert RuleSet().is_valid_bet(5) is False

    def test_above_max_invalid(self):
        assert RuleSet().is_valid_bet(505) is False

    def test_not_on_increment_invalid(self):
        assert RuleSet().is_valid_bet(13) is False

    def test_one_increment_above_min(self):
        assert RuleSet().is_valid_bet(15) is True

    def test_custom_increment(self):
        r = RuleSet(min_bet=25, max_bet=500, bet_increment=25)
        assert r.is_valid_bet(25) is True
        assert r.is_valid_bet(50) is True
        assert r.is_valid_bet(30) is False
