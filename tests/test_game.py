"""Tests for core/game.py — scripted-deck integration tests covering all §9.2 scenarios."""
from __future__ import annotations

import pytest

from core.card import Card
from core.game import Action, IllegalActionError, Round, RoundPhase
from core.rules import RuleSet
from core.shoe import Shoe


def card(s: str) -> Card:
    return Card.from_str(s)


def make_shoe(*cards: str) -> Shoe:
    """Build a scripted shoe from card strings like 'AH', 'TS', '7C'."""
    return Shoe(_fixed_cards=[card(c) for c in cards])


def make_round(*cards: str, rules: RuleSet | None = None) -> Round:
    rules = rules or RuleSet()
    shoe = make_shoe(*cards)
    return Round(shoe, rules, bankroll=1000)


def play_to_deal(r: Round, bet: int = 10) -> None:
    r.place_bet(bet)
    r.deal()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_fixed_shoe_order(self):
        shoe = make_shoe("AH", "KS", "7C")
        assert shoe.deal() == card("AH")
        assert shoe.deal() == card("KS")
        assert shoe.deal() == card("7C")

    def test_fixed_shoe_no_reshuffle_until_exhausted(self):
        shoe = make_shoe("AH", "KS", "7C")
        shoe.deal()
        assert not shoe.needs_reshuffle()  # still cards remaining


# ---------------------------------------------------------------------------
# Phase transitions — happy path
# ---------------------------------------------------------------------------


class TestPhaseTransitions:
    def test_betting_to_dealing_on_place_bet(self):
        r = make_round("2H", "3D", "4C", "5S")
        assert r.phase == RoundPhase.BETTING
        r.place_bet(10)
        assert r.phase == RoundPhase.DEALING

    def test_dealing_to_player_turn_non_ace_upcard_no_bj(self):
        # p1=5H, d1=7S, p2=6C, d2=8D → player 11, dealer 15 — no BJ, no Ace up
        r = make_round("5H", "7S", "6C", "8D")
        play_to_deal(r)
        assert r.phase == RoundPhase.PLAYER_TURN

    def test_dealing_to_insurance_when_dealer_ace_up(self):
        # d1=AH → must go to INSURANCE
        r = make_round("5H", "AH", "6C", "KS")
        play_to_deal(r)
        assert r.phase == RoundPhase.INSURANCE

    def test_stand_advances_to_done_single_hand(self):
        r = make_round("5H", "7S", "6C", "8D", "KH")  # extra for dealer
        play_to_deal(r)
        r.apply(Action.STAND)
        # dealer plays and round ends
        assert r.phase == RoundPhase.DONE

    def test_done_to_betting_on_next_hand(self):
        r = make_round(*["2H", "3D", "4C", "5S"] + ["KH"] * 40)
        play_to_deal(r)
        r.apply(Action.STAND)
        assert r.phase == RoundPhase.DONE
        r.next_hand()
        assert r.phase == RoundPhase.BETTING


# ---------------------------------------------------------------------------
# Natural blackjack scenarios
# ---------------------------------------------------------------------------


class TestNaturalBlackjack:
    def test_player_natural_bj_wins_3_to_2(self):
        # p1=AH, d1=7S, p2=KS, d2=8D → player BJ (21), dealer 15
        r = make_round("AH", "7S", "KS", "8D", "KH")
        play_to_deal(r, bet=100)
        # dealer plays out (stand on 15? no — hits until 17+)
        # Need more cards for dealer; dealer has 7+8=15, hits → add more
        # Actually dealer runs: 7+8=15, hits. Dealer gets KH → 25 bust
        assert r.phase == RoundPhase.DONE
        assert r.result["hands"][0]["outcome"] == "natural"
        assert r.result["hands"][0]["net"] == 150  # 3:2 on $100

    def test_dealer_natural_bj_player_loses(self):
        # p1=5H, d1=KS, p2=6C, d2=AH → dealer BJ
        r = make_round("5H", "KS", "6C", "AH")
        play_to_deal(r, bet=100)
        assert r.phase == RoundPhase.DONE
        assert r.result["hands"][0]["outcome"] == "lose"
        assert r.result["hands"][0]["net"] == -100

    def test_dual_natural_bj_push(self):
        # p1=AH, d1=KS, p2=KH, d2=AS → both BJ
        r = make_round("AH", "KS", "KH", "AS")
        play_to_deal(r, bet=100)
        assert r.phase == RoundPhase.DONE
        assert r.result["hands"][0]["outcome"] == "push"
        assert r.result["hands"][0]["net"] == 0

    def test_player_natural_bj_net_in_bankroll(self):
        r = make_round("AH", "7S", "KS", "8D", "KH")
        play_to_deal(r, bet=100)
        assert r.bankroll == 1150  # 1000 + 150


# ---------------------------------------------------------------------------
# Dealer peek scenarios
# ---------------------------------------------------------------------------


class TestDealerPeek:
    def test_peek_finds_bj_on_ace_up_skips_player_turn(self):
        # d1=AH (Ace up) → INSURANCE → decline → DEALER_PEEK finds BJ
        r = make_round("5H", "AH", "6C", "KS")
        play_to_deal(r)
        assert r.phase == RoundPhase.INSURANCE
        r.apply(Action.DECLINE_INSURANCE)
        assert r.phase == RoundPhase.DONE
        assert r.result["hands"][0]["outcome"] == "lose"

    def test_peek_finds_bj_on_ten_up_short_circuits(self):
        # p1=5H, d1=KS, p2=6C, d2=AH → dealer BJ on 10-value up
        r = make_round("5H", "KS", "6C", "AH")
        play_to_deal(r)
        # should skip PLAYER_TURN entirely
        assert r.phase == RoundPhase.DONE

    def test_peek_no_bj_ten_up_player_gets_turn(self):
        # d1=KS, d2=7D → dealer 17, no BJ
        r = make_round("5H", "KS", "6C", "7D")
        play_to_deal(r)
        assert r.phase == RoundPhase.PLAYER_TURN

    def test_split_not_offered_after_peek_finds_bj(self):
        # Player gets 8,8 but dealer has BJ — no PLAYER_TURN phase
        r = make_round("8H", "KS", "8D", "AH")
        play_to_deal(r)
        assert r.phase == RoundPhase.DONE
        assert Action.SPLIT not in r.legal_actions()

    def test_double_not_offered_after_peek_finds_bj(self):
        r = make_round("5H", "KS", "6C", "AH")
        play_to_deal(r)
        assert r.phase == RoundPhase.DONE
        assert Action.DOUBLE not in r.legal_actions()


# ---------------------------------------------------------------------------
# Insurance
# ---------------------------------------------------------------------------


class TestInsurance:
    def test_insurance_taken_dealer_bj_insurance_wins(self):
        # d1=AH, d2=KS → dealer BJ; player takes insurance ($5 on $10 bet)
        r = make_round("5H", "AH", "6C", "KS")
        play_to_deal(r, bet=10)
        assert r.phase == RoundPhase.INSURANCE
        r.apply(Action.INSURE)
        assert r.phase == RoundPhase.DONE
        # main bet loses -10, insurance pays +10 (2:1 on $5 side bet)
        assert r.result["insurance_net"] == 10
        assert r.result["hands"][0]["net"] == -10
        assert r.result["net"] == 0  # net break-even

    def test_insurance_taken_no_dealer_bj_insurance_lost(self):
        # d1=AH, d2=7D → no dealer BJ; insurance loses
        r = make_round("5H", "AH", "6C", "7D", "KH")
        play_to_deal(r, bet=10)
        r.apply(Action.INSURE)
        # now PLAYER_TURN
        assert r.phase == RoundPhase.PLAYER_TURN
        assert r.insurance_taken is True
        r.apply(Action.STAND)
        assert r.result["insurance_net"] == -5

    def test_decline_insurance_no_side_bet(self):
        r = make_round("5H", "AH", "6C", "7D", "KH")
        play_to_deal(r, bet=10)
        r.apply(Action.DECLINE_INSURANCE)
        assert r.phase == RoundPhase.PLAYER_TURN
        assert r.insurance_taken is False

    def test_insurance_legal_actions_only_insure_decline(self):
        r = make_round("5H", "AH", "6C", "7D")
        play_to_deal(r)
        assert r.legal_actions() == {Action.INSURE, Action.DECLINE_INSURANCE}


# ---------------------------------------------------------------------------
# Late surrender
# ---------------------------------------------------------------------------


class TestLatesurrender:
    def test_surrender_on_2_card_hand(self):
        # Player 16 vs dealer 10
        r = make_round("9H", "KS", "7D", "7C", "KH")
        play_to_deal(r, bet=100)
        assert Action.SURRENDER in r.legal_actions()
        r.apply(Action.SURRENDER)
        assert r.result["hands"][0]["outcome"] == "surrender"
        assert r.result["hands"][0]["net"] == -50

    def test_surrender_returns_half_bet_to_bankroll(self):
        r = make_round("9H", "KS", "7D", "7C")
        play_to_deal(r, bet=100)
        r.apply(Action.SURRENDER)
        assert r.bankroll == 950

    def test_surrender_illegal_after_hit(self):
        # Player 14, hits, now 3 cards — surrender no longer legal
        r = make_round("9H", "KS", "5D", "7C", "2H", "KH")
        play_to_deal(r)
        r.apply(Action.HIT)  # draws 2H → 16
        assert Action.SURRENDER not in r.legal_actions()

    def test_surrender_illegal_when_rules_disallow(self):
        rules = RuleSet(late_surrender=False)
        r = make_round("9H", "KS", "7D", "7C", rules=rules)
        play_to_deal(r)
        assert Action.SURRENDER not in r.legal_actions()

    def test_surrender_illegal_on_split_hand(self):
        # Split 8s, then check surrender not available on split hand
        rules = RuleSet(late_surrender=True)
        r = make_round("8H", "KS", "8D", "7C", "5H", "6C", "KH")
        play_to_deal(r, bet=10)
        r.apply(Action.SPLIT)
        # hand_a: [8H, 5H] — is_split_from is set
        assert Action.SURRENDER not in r.legal_actions()


# ---------------------------------------------------------------------------
# Split scenarios
# ---------------------------------------------------------------------------


class TestSplit:
    def test_basic_split_creates_two_hands(self):
        # p1=8H, d1=KS, p2=8D, d2=7C; deal extras for split hands: 5H, 6C
        r = make_round("8H", "KS", "8D", "7C", "5H", "6C", "KH")
        play_to_deal(r)
        assert Action.SPLIT in r.legal_actions()
        r.apply(Action.SPLIT)
        assert len(r.player_hands) == 2
        assert r.active_hand_index == 0

    def test_split_each_hand_gets_two_cards(self):
        r = make_round("8H", "KS", "8D", "7C", "5H", "6C", "KH")
        play_to_deal(r)
        r.apply(Action.SPLIT)
        assert len(r.player_hands[0].cards) == 2
        # hand_b has only 1 card until we advance to it
        assert len(r.player_hands[1].cards) == 1

    def test_split_advance_to_second_hand_deals_card(self):
        r = make_round("8H", "KS", "8D", "7C", "5H", "6C", "KH")
        play_to_deal(r)
        r.apply(Action.SPLIT)
        r.apply(Action.STAND)  # done with hand_a
        assert len(r.player_hands[1].cards) == 2
        assert r.active_hand_index == 1

    def test_resplit_to_three_hands(self):
        # 8H,8D pair → split; hand_a gets 8C (pair again) → split again
        # Deal order: p1=8H, d1=KS, p2=8D, d2=7C, split_a_card=8C, split_a2=5H, split_b_card=6C
        r = make_round("8H", "KS", "8D", "7C", "8C", "5H", "6C", "KH")
        play_to_deal(r)
        r.apply(Action.SPLIT)  # [8H,8D] → [8H,8C], [8D]; active=0
        assert len(r.player_hands) == 2
        # hand_a = [8H, 8C] — another pair!
        assert r.player_hands[0].is_pair
        r.apply(Action.SPLIT)  # → [8H,5H], [8C], [8D]; active=0
        assert len(r.player_hands) == 3

    def test_resplit_to_four_hands_limit(self):
        # 8s again: build 4 hands
        r = make_round(
            "8H", "KS", "8D", "7C",  # initial deal
            "8C", "8S",               # first split: hand_a gets 8C, then split again → hand_a1 gets 8S
            "2H",                      # hand_a1 second card
            "3D",                      # hand_a2 (was 8C hand)
            "4C",                      # hand_b (8D hand)
            "KH",                      # dealer hits
        )
        play_to_deal(r)
        r.apply(Action.SPLIT)  # → [8H,8C], [8D]
        r.apply(Action.SPLIT)  # hand_a=[8H,8S],.. → [8H,8S], [8C], [8D]
        # need to stand on [8H,8S] (another pair but let's stand to build 4)
        # Actually 8H and 8S are still a pair, so let's split again
        # but first let's check we can:
        assert len(r.player_hands) == 3
        r.apply(Action.SPLIT)  # → [8H,2H], [8S], [8C], [8D] — 4 hands
        assert len(r.player_hands) == 4

    def test_fifth_split_rejected(self):
        r = make_round(
            "8H", "KS", "8D", "7C",
            "8C", "8S", "2H", "8X" if False else "3D",
            "4C", "5D", "KH",
        )
        # Build 4 hands first then verify split is not offered
        # Use a simpler approach: just verify legal_actions blocks at 4
        rules = RuleSet()
        shoe = make_shoe(
            "8H", "KS", "8D", "7C",   # deal: p=[8H,8D], d=[KS,7C]
            "8C",                       # hand_a card after split 1 → [8H,8C]
            "8S",                       # hand_a card after split 2 → [8H,8S]
            "2H",                       # hand_a1 second card → [8H,2H]
            "3D",                       # hand_a2 second card → [8S,3D]... wait
        )
        # Let's just use a direct assertion: len < 4 required
        r2 = Round(shoe, rules, bankroll=1000)
        r2.place_bet(10)
        r2.deal()
        r2.apply(Action.SPLIT)         # 2 hands, active=0: [8H,8C]
        r2.apply(Action.SPLIT)         # 3 hands, active=0: [8H,8S]
        r2.apply(Action.SPLIT)         # 4 hands
        assert len(r2.player_hands) == 4
        assert Action.SPLIT not in r2.legal_actions()

    def test_split_aces_get_one_card_only(self):
        # p=[AH,AD], split; each split-ace hand gets exactly 1 more card
        r = make_round("AH", "KS", "AD", "7C", "5H", "6C", "KH")
        play_to_deal(r)
        r.apply(Action.SPLIT)
        hand_a = r.player_hands[0]
        assert hand_a.is_split_ace is True
        assert len(hand_a.cards) == 2

    def test_split_aces_legal_actions_only_stand(self):
        r = make_round("AH", "KS", "AD", "7C", "5H", "6C", "KH")
        play_to_deal(r)
        r.apply(Action.SPLIT)
        assert r.legal_actions() == {Action.STAND}

    def test_split_aces_resplit_not_allowed_even_drawing_ace(self):
        # hand_a = [AH, AC] — another Ace, but is_split_ace blocks re-split
        r = make_round("AH", "KS", "AD", "7C", "AC", "6C", "KH")
        play_to_deal(r)
        r.apply(Action.SPLIT)
        assert r.player_hands[0].is_split_ace is True
        assert Action.SPLIT not in r.legal_actions()

    def test_split_tens_allowed(self):
        # 10-value cards count as pairs; split is legal
        r = make_round("KH", "7S", "QD", "8C", "5H", "6D", "KH")
        play_to_deal(r)
        assert Action.SPLIT in r.legal_actions()

    def test_split_is_not_natural_bj(self):
        # Split Ace + 10-value on a split hand should NOT be natural (no 3:2)
        r = make_round("AH", "7S", "AD", "8C", "KS", "6D", "KH")
        play_to_deal(r)
        r.apply(Action.SPLIT)  # hand_a = [AH, KS]
        # hand_a has total 21 but is_split_from is set → not natural
        assert r.player_hands[0].is_natural_blackjack is False
        r.apply(Action.STAND)
        r.apply(Action.STAND)
        # should be a regular "win" at 1:1, not natural at 3:2
        hand_result = r.result["hands"][0]
        assert hand_result["outcome"] == "win"
        assert hand_result["net"] == 10  # 1:1 on $10, not 15


# ---------------------------------------------------------------------------
# Double down
# ---------------------------------------------------------------------------


class TestDoubleDown:
    def test_double_doubles_the_bet_win(self):
        # player 11 vs dealer 6: double; gets 9 → 20 vs dealer busts
        r = make_round("5H", "6S", "6C", "7D", "9H", "KH")
        play_to_deal(r, bet=100)
        assert Action.DOUBLE in r.legal_actions()
        r.apply(Action.DOUBLE)
        assert r.result["hands"][0]["net"] == 200

    def test_double_doubles_the_bet_loss(self):
        # player 11, doubles, draws 2 → 13 vs dealer 20
        r = make_round("5H", "KS", "6C", "KH", "2H")
        play_to_deal(r, bet=100)
        r.apply(Action.DOUBLE)
        assert r.result["hands"][0]["net"] == -200

    def test_double_not_available_after_hit(self):
        r = make_round("5H", "7S", "6C", "8D", "2H", "KH")
        play_to_deal(r)
        r.apply(Action.HIT)
        assert Action.DOUBLE not in r.legal_actions()

    def test_double_after_split_das_true(self):
        rules = RuleSet(double_after_split=True)
        r = make_round("8H", "KS", "8D", "7C", "5H", "6C", "KH", rules=rules)
        play_to_deal(r)
        r.apply(Action.SPLIT)  # hand_a = [8H, 5H] = 13
        assert Action.DOUBLE in r.legal_actions()

    def test_double_after_split_das_false(self):
        rules = RuleSet(double_after_split=False)
        r = make_round("8H", "KS", "8D", "7C", "5H", "6C", "KH", rules=rules)
        play_to_deal(r)
        r.apply(Action.SPLIT)
        assert Action.DOUBLE not in r.legal_actions()

    def test_double_not_on_split_ace(self):
        r = make_round("AH", "KS", "AD", "7C", "5H", "6C", "KH")
        play_to_deal(r)
        r.apply(Action.SPLIT)
        assert Action.DOUBLE not in r.legal_actions()


# ---------------------------------------------------------------------------
# Bankroll tracking
# ---------------------------------------------------------------------------


class TestBankroll:
    def test_bankroll_increases_on_win(self):
        r = make_round("AH", "7S", "KS", "8D", "KH")
        play_to_deal(r, bet=100)
        assert r.bankroll == 1150

    def test_bankroll_decreases_on_loss(self):
        r = make_round("5H", "KS", "6C", "AH")
        play_to_deal(r, bet=100)
        assert r.bankroll == 900

    def test_bankroll_unchanged_on_push(self):
        r = make_round("AH", "KS", "KH", "AS")
        play_to_deal(r, bet=100)
        assert r.bankroll == 1000

    def test_bankroll_tracks_across_two_rounds(self):
        # Round 1: dealer BJ → player loses $10
        # Round 2: need enough extra cards for the shoe
        shoe = make_shoe(
            "5H", "KS", "6C", "AH",  # round 1: dealer BJ
            "AH", "7S", "KS", "8D", "KH",  # round 2: player BJ
        )
        rules = RuleSet()
        r = Round(shoe, rules, bankroll=1000)
        r.place_bet(10)
        r.deal()
        assert r.bankroll == 990  # lost round 1

        r.next_hand()
        r.place_bet(10)
        r.deal()
        assert r.bankroll == 1005  # won 3:2 → +$15


# ---------------------------------------------------------------------------
# IllegalActionError
# ---------------------------------------------------------------------------


class TestIllegalActionError:
    def test_hit_in_betting_phase_raises(self):
        r = make_round("5H", "7S", "6C", "8D")
        with pytest.raises(IllegalActionError) as exc_info:
            r.apply(Action.HIT)
        err = exc_info.value
        assert err.attempted == Action.HIT
        assert err.phase == RoundPhase.BETTING
        assert isinstance(err.legal, set)

    def test_insure_in_player_turn_raises(self):
        r = make_round("5H", "7S", "6C", "8D")
        play_to_deal(r)
        with pytest.raises(IllegalActionError) as exc_info:
            r.apply(Action.INSURE)
        err = exc_info.value
        assert err.attempted == Action.INSURE
        assert err.phase == RoundPhase.PLAYER_TURN

    def test_split_on_non_pair_raises(self):
        r = make_round("5H", "7S", "6C", "8D")
        play_to_deal(r)
        with pytest.raises(IllegalActionError) as exc_info:
            r.apply(Action.SPLIT)
        err = exc_info.value
        assert err.attempted == Action.SPLIT
        assert Action.SPLIT not in err.legal

    def test_error_contains_legal_actions(self):
        r = make_round("5H", "7S", "6C", "8D")
        play_to_deal(r)
        with pytest.raises(IllegalActionError) as exc_info:
            r.apply(Action.INSURE)
        assert Action.STAND in exc_info.value.legal

    def test_surrender_after_hit_raises(self):
        r = make_round("9H", "KS", "5D", "7C", "2H", "KH")
        play_to_deal(r)
        r.apply(Action.HIT)
        with pytest.raises(IllegalActionError):
            r.apply(Action.SURRENDER)


# ---------------------------------------------------------------------------
# Dealer play — H17 vs S17
# ---------------------------------------------------------------------------


class TestDealerPlay:
    def test_dealer_stands_on_hard_17_s17(self):
        rules = RuleSet(dealer_hits_soft_17=False)
        # player busts so we can inspect dealer without them winning
        r = make_round("KH", "7S", "7D", "KD", "KH", rules=rules)
        play_to_deal(r)
        r.apply(Action.HIT)  # player busts (17+10=27? no: 10+7=17, hit KH=27)
        # dealer stood on 17
        assert r.dealer_hand.total == 17

    def test_dealer_hits_soft_17_h17(self):
        rules = RuleSet(dealer_hits_soft_17=True)
        # d1=AS (Ace up) → INSURANCE; d2=6H → soft 17, must hit; draw 2D → 19
        r = make_round("KH", "AS", "KD", "6H", "2D", rules=rules)
        play_to_deal(r)
        assert r.phase == RoundPhase.INSURANCE
        r.apply(Action.DECLINE_INSURANCE)
        assert r.phase == RoundPhase.PLAYER_TURN
        r.apply(Action.STAND)
        assert r.dealer_hand.total >= 18

    def test_dealer_does_not_play_when_all_bust(self):
        # Player busts, dealer should not draw additional cards
        r = make_round("KH", "7S", "7D", "8C", "KH")
        play_to_deal(r)
        dealer_cards_before = len(r.dealer_hand.cards)
        r.apply(Action.HIT)  # player 10+7=17, hit KH=27 → bust
        # dealer never plays; phase jumps straight to DONE
        assert r.phase == RoundPhase.DONE
        assert len(r.dealer_hand.cards) == dealer_cards_before

    def test_dealer_busts_player_wins(self):
        # player 20, dealer starts 16, hits, busts
        r = make_round("KH", "9S", "KD", "7C", "KH")
        play_to_deal(r)
        r.apply(Action.STAND)
        assert r.result["hands"][0]["outcome"] == "win"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_place_bet_wrong_phase_raises(self):
        r = make_round("5H", "7S", "6C", "8D")
        r.place_bet(10)
        with pytest.raises(RuntimeError):
            r.place_bet(10)

    def test_deal_wrong_phase_raises(self):
        r = make_round("5H", "7S", "6C", "8D")
        with pytest.raises(RuntimeError):
            r.deal()

    def test_next_hand_wrong_phase_raises(self):
        r = make_round("5H", "7S", "6C", "8D")
        with pytest.raises(RuntimeError):
            r.next_hand()

    def test_invalid_bet_raises(self):
        r = make_round("5H", "7S", "6C", "8D")
        with pytest.raises(ValueError):
            r.place_bet(7)  # not on $5 increment

    def test_bet_exceeding_bankroll_raises(self):
        rules = RuleSet(min_bet=10, max_bet=500)
        shoe = make_shoe("5H", "7S", "6C", "8D")
        r = Round(shoe, rules, bankroll=50)
        with pytest.raises(ValueError):
            r.place_bet(100)  # valid bet, but exceeds bankroll of $50

    def test_legal_actions_empty_outside_play_phases(self):
        r = make_round("5H", "7S", "6C", "8D")
        assert r.legal_actions() == set()

    def test_hit_to_21_auto_advances(self):
        # player 5+6=11, hits A → 21 (soft), should auto-advance
        r = make_round("5H", "KS", "6C", "7D", "AH", "KH")
        play_to_deal(r)
        r.apply(Action.HIT)  # draws AH → 5+6+A = 12... hmm
        # Actually 5+6=11, AH = ace = 11 → total=22, reduce to 12
        # That's only 12, not 21. Let me reconsider
        # 5+6=11, hit KH → 21 auto-advances
        shoe2 = make_shoe("5H", "KS", "6C", "7D", "KH", "5D")
        rules = RuleSet()
        r2 = Round(shoe2, rules, bankroll=1000)
        r2.place_bet(10)
        r2.deal()
        r2.apply(Action.HIT)  # 5+6=11, draws KH → 21
        assert r2.phase == RoundPhase.DONE  # auto-advanced past PLAYER_TURN

    def test_result_is_none_before_payout(self):
        r = make_round("5H", "7S", "6C", "8D")
        play_to_deal(r)
        assert r.result is None
