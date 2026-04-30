"""Tests for core/cards.py — targets ≥95% coverage."""
from __future__ import annotations

import pytest

from core.card import RANKS, SUITS, Card
from core.hand import Hand
from core.shoe import Shoe

# ---------------------------------------------------------------------------
# Card construction and validation
# ---------------------------------------------------------------------------

class TestCardConstruction:
    def test_valid_numeric_rank(self):
        c = Card("7", "H")
        assert c.rank == "7"
        assert c.suit == "H"

    def test_valid_ten(self):
        c = Card("10", "S")
        assert c.rank == "10"

    def test_valid_face_cards(self):
        for rank in ("J", "Q", "K", "A"):
            c = Card(rank, "D")
            assert c.rank == rank

    def test_all_suits(self):
        for suit in SUITS:
            c = Card("5", suit)
            assert c.suit == suit

    def test_invalid_rank_raises(self):
        with pytest.raises(ValueError, match="rank"):
            Card("1", "H")

    def test_invalid_suit_raises(self):
        with pytest.raises(ValueError, match="suit"):
            Card("A", "X")

    def test_frozen(self):
        c = Card("A", "H")
        with pytest.raises(Exception):
            c.rank = "K"  # type: ignore[misc]


class TestCardFromStr:
    def test_numeric_cards(self):
        assert Card.from_str("2H") == Card("2", "H")
        assert Card.from_str("9D") == Card("9", "D")

    def test_ten_encoding(self):
        assert Card.from_str("TS") == Card("10", "S")

    def test_face_and_ace(self):
        assert Card.from_str("JC") == Card("J", "C")
        assert Card.from_str("QH") == Card("Q", "H")
        assert Card.from_str("KD") == Card("K", "D")
        assert Card.from_str("AH") == Card("A", "H")

    def test_wrong_length_raises(self):
        with pytest.raises(ValueError):
            Card.from_str("10H")  # 3 chars

    def test_invalid_rank_char_raises(self):
        with pytest.raises(ValueError):
            Card.from_str("XH")

    def test_invalid_suit_char_raises(self):
        with pytest.raises(ValueError):
            Card.from_str("AX")


class TestCardStr:
    def test_str_ten(self):
        assert str(Card("10", "S")) == "TS"

    def test_str_ace(self):
        assert str(Card("A", "H")) == "AH"

    def test_str_numeric(self):
        assert str(Card("7", "D")) == "7D"

    def test_roundtrip(self):
        for rank in RANKS:
            for suit in SUITS:
                c = Card(rank, suit)
                assert Card.from_str(str(c)) == c


class TestCardValue:
    def test_numeric_values(self):
        for rank in ("2", "3", "4", "5", "6", "7", "8", "9"):
            assert Card(rank, "H").value == int(rank)

    def test_ten_value_cards(self):
        for rank in ("10", "J", "Q", "K"):
            assert Card(rank, "H").value == 10

    def test_ace_value(self):
        assert Card("A", "H").value == 11


# ---------------------------------------------------------------------------
# Hand total and soft/hard logic
# ---------------------------------------------------------------------------

def make_hand(*card_strs: str, **kwargs) -> Hand:
    return Hand(cards=[Card.from_str(s) for s in card_strs], **kwargs)


class TestHandTotal:
    def test_hard_no_aces(self):
        h = make_hand("7H", "9D")
        assert h.total == 16

    def test_hard_face_cards(self):
        h = make_hand("KH", "QD")
        assert h.total == 20

    def test_soft_ace_plus_six(self):
        h = make_hand("AH", "6D")
        assert h.total == 17
        assert h.is_soft is True

    def test_soft_ace_plus_king(self):
        h = make_hand("AH", "KD")
        assert h.total == 21
        assert h.is_soft is True

    def test_ace_reduces_on_bust(self):
        # A + 9 + 5 = 25 with ace as 11 → reduce to 15
        h = make_hand("AH", "9D", "5C")
        assert h.total == 15
        assert h.is_soft is False

    def test_two_aces(self):
        # A + A = 22 → reduce one → 12
        h = make_hand("AH", "AD")
        assert h.total == 12
        assert h.is_soft is True

    def test_two_aces_plus_nine(self):
        # A + A + 9 = 31 → reduce one → 21
        h = make_hand("AH", "AD", "9C")
        assert h.total == 21
        assert h.is_soft is True

    def test_two_aces_plus_nine_plus_two(self):
        # A + A + 9 + 2 = 23 → needs two reductions → 13
        h = make_hand("AH", "AD", "9C", "2S")
        assert h.total == 13
        assert h.is_soft is False

    def test_four_aces(self):
        # 44 → 34 → 24 → 14; one ace still soft
        h = make_hand("AH", "AD", "AC", "AS")
        assert h.total == 14
        assert h.is_soft is True

    def test_bust_all_high(self):
        h = make_hand("KH", "QD", "JC")
        assert h.total == 30
        assert h.is_soft is False

    def test_empty_hand(self):
        h = Hand()
        assert h.total == 0
        assert h.is_soft is False

    def test_single_card_ace(self):
        h = make_hand("AH")
        assert h.total == 11
        assert h.is_soft is True

    def test_single_card_non_ace(self):
        h = make_hand("7H")
        assert h.total == 7
        assert h.is_soft is False


# ---------------------------------------------------------------------------
# Hand.is_pair
# ---------------------------------------------------------------------------

class TestHandIsPair:
    def test_pair_of_sevens(self):
        assert make_hand("7H", "7D").is_pair is True

    def test_pair_of_aces(self):
        assert make_hand("AH", "AD").is_pair is True

    def test_mixed_ten_value_pair(self):
        # K and Q both have value 10 — per house rules, any two 10-value cards can split
        assert make_hand("KH", "QD").is_pair is True

    def test_ten_and_jack_pair(self):
        assert make_hand("TH", "JD").is_pair is True

    def test_not_pair_different_values(self):
        assert make_hand("7H", "8D").is_pair is False

    def test_not_pair_three_cards(self):
        assert make_hand("7H", "7D", "7C").is_pair is False

    def test_not_pair_one_card(self):
        assert make_hand("7H").is_pair is False

    def test_not_pair_empty(self):
        assert Hand().is_pair is False


# ---------------------------------------------------------------------------
# Hand.is_natural_blackjack
# ---------------------------------------------------------------------------

class TestHandIsNaturalBlackjack:
    def test_natural_ace_king(self):
        assert make_hand("AH", "KD").is_natural_blackjack is True

    def test_natural_ace_ten(self):
        assert make_hand("AH", "TD").is_natural_blackjack is True

    def test_natural_ace_jack(self):
        assert make_hand("AH", "JD").is_natural_blackjack is True

    def test_natural_ace_queen(self):
        assert make_hand("AH", "QD").is_natural_blackjack is True

    def test_not_natural_on_split_hand(self):
        h = make_hand("AH", "KD", is_split_from="parent-id")
        assert h.is_natural_blackjack is False

    def test_not_natural_three_card_21(self):
        h = make_hand("7H", "7D", "7C")
        assert h.is_natural_blackjack is False

    def test_not_natural_two_card_non_21(self):
        assert make_hand("7H", "8D").is_natural_blackjack is False

    def test_not_natural_empty(self):
        assert Hand().is_natural_blackjack is False


# ---------------------------------------------------------------------------
# Hand.category_label
# ---------------------------------------------------------------------------

class TestHandCategoryLabel:
    def test_hard_label(self):
        assert make_hand("7H", "9D").category_label == "Hard 16"

    def test_hard_label_high(self):
        assert make_hand("KH", "8D").category_label == "Hard 18"

    def test_soft_label(self):
        assert make_hand("AH", "6D").category_label == "Soft 17"

    def test_soft_label_ace_king(self):
        assert make_hand("AH", "KD").category_label == "Soft 21"

    def test_pair_label_sevens(self):
        assert make_hand("7H", "7D").category_label == "Pair 7s"

    def test_pair_label_aces(self):
        assert make_hand("AH", "AD").category_label == "Pair As"

    def test_pair_takes_priority_over_soft(self):
        # A-A is a pair AND soft; pair should win
        assert make_hand("AH", "AD").category_label == "Pair As"

    def test_reduced_ace_is_hard(self):
        # A + 9 + 5 = 15 (hard after reduction)
        assert make_hand("AH", "9D", "5C").category_label == "Hard 15"

    def test_pair_ten_value_mixed_ranks(self):
        assert make_hand("KH", "QD").category_label == "Pair Ks"

    def test_hard_five(self):
        assert make_hand("2H", "3D").category_label == "Hard 5"


# ---------------------------------------------------------------------------
# Shoe
# ---------------------------------------------------------------------------

class TestShoe:
    def test_default_deck_count(self):
        shoe = Shoe()
        assert shoe.num_decks == 6
        assert shoe.cards_remaining == 312  # 6 * 52

    def test_custom_deck_count(self):
        shoe = Shoe(num_decks=2)
        assert shoe.cards_remaining == 104

    def test_deal_returns_card(self):
        shoe = Shoe(num_decks=1)
        c = shoe.deal()
        assert isinstance(c, Card)

    def test_deal_decrements_remaining(self):
        shoe = Shoe(num_decks=1)
        initial = shoe.cards_remaining
        shoe.deal()
        assert shoe.cards_remaining == initial - 1

    def test_deal_all_unique_in_single_deck(self):
        shoe = Shoe(num_decks=1)
        dealt = [shoe.deal() for _ in range(52)]
        # All 52 unique cards should be dealt exactly once
        assert len(set((c.rank, c.suit) for c in dealt)) == 52

    def test_all_cards_represented_in_six_deck_shoe(self):
        shoe = Shoe(num_decks=6)
        dealt = [shoe.deal() for _ in range(312)]
        from collections import Counter
        counts = Counter((c.rank, c.suit) for c in dealt)
        assert all(v == 6 for v in counts.values())
        assert len(counts) == 52

    def test_needs_reshuffle_false_initially(self):
        shoe = Shoe()
        assert shoe.needs_reshuffle() is False

    def test_needs_reshuffle_true_after_penetration(self):
        shoe = Shoe(num_decks=1, penetration=0.5)
        for _ in range(26):  # 50% of 52
            shoe.deal()
        assert shoe.needs_reshuffle() is True

    def test_needs_reshuffle_false_before_cutcard(self):
        shoe = Shoe(num_decks=1, penetration=0.5)
        for _ in range(25):
            shoe.deal()
        assert shoe.needs_reshuffle() is False

    def test_reshuffle_resets_index(self):
        shoe = Shoe(num_decks=1, penetration=0.5)
        for _ in range(26):
            shoe.deal()
        shoe.reshuffle()
        assert shoe.needs_reshuffle() is False
        assert shoe.cards_remaining == 52

    def test_auto_reshuffle_on_exhaustion(self):
        # Deal past the end — shoe should auto-reshuffle rather than crash
        shoe = Shoe(num_decks=1, penetration=1.0)
        for _ in range(52):
            shoe.deal()
        # One more deal should trigger auto-reshuffle
        c = shoe.deal()
        assert isinstance(c, Card)

    def test_penetration_cut_card_position(self):
        shoe = Shoe(num_decks=1, penetration=0.75)
        assert shoe._cut_card == 39  # int(52 * 0.75)


# ---------------------------------------------------------------------------
# Hand flags (has_doubled, is_surrendered, is_split_ace)
# ---------------------------------------------------------------------------

class TestHandFlags:
    def test_default_flags(self):
        h = Hand()
        assert h.has_doubled is False
        assert h.is_surrendered is False
        assert h.is_split_ace is False
        assert h.is_split_from is None

    def test_set_flags(self):
        h = Hand(has_doubled=True, is_surrendered=False, is_split_ace=True, is_split_from="abc")
        assert h.has_doubled is True
        assert h.is_split_ace is True
        assert h.is_split_from == "abc"
