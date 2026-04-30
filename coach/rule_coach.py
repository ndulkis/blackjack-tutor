from __future__ import annotations

from analytics.session import Decision
from coach.base import Coach, CoachResult
from core.game import Action
from core.rules import RuleSet
from strategy.rationales import RATIONALES

# ---------------------------------------------------------------------------
# Player-action display names
# ---------------------------------------------------------------------------
_ACTION_NAME: dict[Action, str] = {
    Action.HIT: "hit",
    Action.STAND: "stand",
    Action.DOUBLE: "double",
    Action.SPLIT: "split",
    Action.SURRENDER: "surrender",
    Action.INSURE: "take insurance",
    Action.DECLINE_INSURANCE: "decline insurance",
}

# ---------------------------------------------------------------------------
# Rationale tag → human-readable explanation fragment
# ---------------------------------------------------------------------------
_RATIONALE_TEXT: dict[str, str] = {
    "hit_low_total_no_bust_risk": "you can't bust with one more card, so always draw to improve.",
    "hit_9_vs_strong_dealer": "the dealer's strong card makes doubling unprofitable; hit to improve.",
    "hit_9_vs_neutral_dealer": "the dealer's 7 is neutral; a double would risk too much for a 9.",
    "double_9_vs_dealer_bust_range": "the dealer is in the bust range (3–6), so doubling your 9 maximises profit on a likely dealer bust.",
    "double_10_vs_dealer_bust_range": "a 10 gives you one of the best doubling hands; the dealer's card makes a bust likely.",
    "double_10_vs_neutral_dealer": "doubling 10 vs a neutral dealer (7–9) still has positive expected value.",
    "hit_10_vs_strong_dealer_no_double_edge": "the dealer's 10 or Ace is too strong; doubling has no edge — just hit.",
    "double_11_best_starting_total": "11 is the best doubling total; any 10-value card gives you 21.",
    "double_11_vs_strong_dealer_still_positive_ev": "even vs a dealer 10, doubling 11 is profitable because you reach 21 on any 10-value draw.",
    "hit_11_vs_dealer_ace_no_double_advantage": "vs an Ace, the dealer has too high a chance of blackjack; doubling 11 loses its edge.",
    "hit_12_vs_neutral_dealer_dealer_bust_rate_low": "the dealer's 2 or 3 has a lower bust rate than 4–6; your 12 must draw.",
    "stand_12_vs_dealer_bust_range": "the dealer shows 4–6 — the highest bust range. Let the dealer bust; your 12 stands.",
    "hit_12_vs_strong_dealer": "the dealer is strong; you must improve your 12 even at bust risk.",
    "stand_vs_dealer_bust_range": "the dealer shows a bust card (2–6). Stand and let the dealer bust — don't risk busting yourself.",
    "hit_vs_strong_dealer_must_improve": "the dealer is too strong to stand; you must draw and hope to improve.",
    "hit_15_vs_neutral_dealer": "dealer 7–9 is too strong to let stand on 15; draw to improve.",
    "surrender_15_high_bust_risk_vs_strong_dealer": "surrendering returns half your bet. Against a dealer 10 or Ace, your 15 loses more than 50 % of the time — surrendering is the least costly option.",
    "hit_16_vs_neutral_dealer": "dealer 7 or 8 is strong enough that you must draw, accepting the bust risk.",
    "surrender_16_negative_ev_vs_strong_dealer": "hard 16 is the worst hand in blackjack. Against a dealer 9, 10, or Ace you lose more than half the time — surrendering saves you money.",
    "stand_pat_17_or_better": "17 or better is a strong enough total to stand on; drawing risks busting for little gain.",
    "hit_soft_improve_weak_total": "your soft total is weak; drawing can only improve it (Ace drops to 1 if needed).",
    "double_soft_vs_weak_dealer_two_ways_to_win": "doubling a soft hand vs 5 or 6 gives you two ways to win: a good draw OR a dealer bust.",
    "double_soft_vs_dealer_bust_range": "the dealer's 4–6 is the prime bust range; doubling your soft hand maximises profit.",
    "double_soft_17_vs_bust_range_standing_value_negative": "soft 17 is actually a losing standing hand; doubling vs 3–6 turns it into a winner.",
    "hit_soft_17_draw_to_improvement": "soft 17 has negative standing value vs this dealer card; draw to improve.",
    "double_soft_18_vs_bust_range_gain_on_strong_total": "soft 18 is strong but doubling vs 2–6 adds even more value when the dealer is likely to bust.",
    "stand_soft_18_beats_dealer_likely_17": "18 beats the dealer's most likely outcome of 17; stand.",
    "stand_soft_18_tied_with_dealer_likely_18": "18 ties the dealer's most likely outcome here; standing preserves your bet.",
    "hit_soft_18_vs_strong_dealer_18_loses_too_often": "vs a dealer 9, 10, or Ace, 18 loses too often — draw and try to improve.",
    "stand_soft_19_plus_strong_total": "19 or better is a powerful hand; no draw can help more than standing.",
    "always_split_aces_maximizes_blackjack_probability": "splitting Aces gives each new hand a chance at blackjack — always split them.",
    "split_small_pair_vs_dealer_bust_range_das_advantage": "the dealer is in the bust range; splitting and potentially doubling after (DAS) turns a weak hand into two profitable ones.",
    "split_small_pair_vs_dealer_neutral": "splitting vs a neutral dealer creates two hands that are each stronger than the combined weak total.",
    "hit_small_pair_vs_strong_dealer": "the dealer is too strong to split into two weak hands; combine them and hit.",
    "hit_4s_vs_neutral_dealer": "4+4=8 is a workable total to hit; splitting into two 4s vs this dealer card creates two weak hands.",
    "split_4s_only_vs_weak_dealer_das_creates_edge": "vs 5 or 6 you can split 4s and likely double after — the dealer's bust rate makes this profitable.",
    "never_split_5s_double_as_hard_10": "never split 5s — 10 is one of the best doubling totals. Two hands of 5 are far weaker.",
    "never_split_5s_hit_vs_strong_dealer": "never split 5s. Treat them as hard 10 and hit vs a strong dealer.",
    "split_6s_vs_dealer_bust_range": "the dealer shows a bust card; split your 6s to create two hands that benefit from the likely dealer bust.",
    "hit_6s_vs_neutral_dealer_12_too_weak_to_stand": "6+6=12 is too weak to stand, and splitting into two 6s vs a strong dealer creates two losing hands — hit instead.",
    "split_7s_improve_from_weak_14": "14 is a losing hand; split your 7s to start two fresh hands against this dealer bust card.",
    "split_7s_vs_dealer_7_create_two_17s": "splitting 7s vs a dealer 7 gives each hand a chance to reach 17 and push — better than standing on 14.",
    "hit_7s_vs_strong_dealer_14_must_improve": "the dealer is too strong; 14 must improve. Splitting into two 7s against a strong dealer just creates two losing hands.",
    "always_split_8s_16_is_worst_hand": "16 is the worst hand in blackjack. Always split 8s — each 8 can become a winning hand on its own.",
    "split_9s_18_beats_dealer_bust_range": "18 is a winning hand vs a bust-range dealer, but two hands starting at 9 each beat the dealer's likely bust.",
    "stand_9s_vs_7_already_winning_hand_likely_17": "18 beats a dealer's most likely 17; stand on your 18 rather than splitting into two uncertain hands.",
    "split_9s_18_doesnt_beat_dealers_likely_18_or_19": "vs dealer 8, your 18 ties at best; split to create two chances to beat the dealer.",
    "split_9s_18_doesnt_beat_dealers_likely_19": "vs dealer 9, standing on 18 mostly loses; split to improve your odds.",
    "stand_9s_vs_10_splitting_creates_more_losing_hands": "vs dealer 10, splitting 9s creates two hands that each lose more often than your 18 does.",
    "stand_9s_vs_ace_splitting_creates_more_losing_hands": "vs an Ace, standing on 18 is safer than splitting into two hands that each face a dealer Ace.",
    "never_split_10s_20_is_near_unbeatable": "20 wins almost every hand. Never split 10s — splitting throws away a near-certain winner.",
}

# Fallback for any tag not explicitly mapped
_FALLBACK_TEXT = "basic strategy says this is the optimal play based on expected value."


def _rationale_text(decision: Decision) -> str:
    """Look up a human-readable rationale for why optimal_action was correct."""
    hand = decision.hand_snapshot
    dealer_key = 11 if decision.dealer_up.rank == "A" else decision.dealer_up.value

    if hand.is_pair:
        rank = hand.cards[0].rank
        norm = "T" if rank in {"10", "J", "Q", "K"} else rank
        tag = RATIONALES["pair"].get(norm, {}).get(dealer_key)
    elif hand.is_soft:
        tag = RATIONALES["soft"].get(hand.total, {}).get(dealer_key)
    else:
        total = max(hand.total, 4)
        tag = RATIONALES["hard"].get(total, {}).get(dealer_key)

    return _RATIONALE_TEXT.get(tag or "", _FALLBACK_TEXT)


# ---------------------------------------------------------------------------
# Template builders
# ---------------------------------------------------------------------------

def _correct_message(decision: Decision) -> str:
    action = _ACTION_NAME[decision.player_action]
    rationale = _rationale_text(decision)
    return f"Correct! {action.capitalize()} is right here — {rationale}"


def _incorrect_message(decision: Decision) -> str:
    played = _ACTION_NAME[decision.player_action]
    optimal = _ACTION_NAME[decision.optimal_action]
    rationale = _rationale_text(decision)
    return (
        f"Not quite. You chose to {played}, but the correct play is to {optimal}. "
        f"Reason: {rationale}"
    )


def _insurance_message(decision: Decision) -> str:
    took = decision.player_action == Action.INSURE
    correct = decision.was_correct
    if correct and took:
        return "Correct! Insurance is a side bet that pays 2:1 if the dealer has blackjack. In this situation it was the right call."
    if correct and not took:
        return "Correct — declining insurance is almost always right. The expected value of insurance is negative in the long run."
    if not correct and took:
        return "Insurance is rarely correct. It's a side bet with negative expected value; declining is almost always optimal."
    return "You should have taken insurance here. When the dealer shows an Ace and you have a strong hand, insurance can be profitable."


class RuleCoach:
    """Instantly-ready rule-based coach backed by template strings."""

    def explain(self, decision: Decision, rules: RuleSet) -> CoachResult:
        if not decision.is_primary:
            text = _insurance_message(decision)
        elif decision.was_correct:
            text = _correct_message(decision)
        else:
            text = _incorrect_message(decision)
        return CoachResult(text)
