from __future__ import annotations

# ---------------------------------------------------------------------------
# RATIONALES
# Same nested key structure as charts.py but values are snake_case tag strings.
# Top-level keys: "hard", "soft", "pair"
# Second-level keys: player total (int) or pair rank (str)
# Third-level keys: dealer up-card (int, 11 = Ace)
# Usage: RATIONALES["hard"][16][10] -> coaching tag for rule_coach.py
# ---------------------------------------------------------------------------

_DEALER_UPS = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]


def _row(*tags: str) -> dict[int, str]:
    return dict(zip(_DEALER_UPS, tags))


# Short aliases — each maps to the full snake_case tag used in rule_coach.py
_LBR = "hit_low_total_no_bust_risk"
_H9s = "hit_9_vs_strong_dealer"
_H9n = "hit_9_vs_neutral_dealer"
_D9  = "double_9_vs_dealer_bust_range"
_D10b = "double_10_vs_dealer_bust_range"
_D10n = "double_10_vs_neutral_dealer"
_H10 = "hit_10_vs_strong_dealer_no_double_edge"
_D11 = "double_11_best_starting_total"
_D11s = "double_11_vs_strong_dealer_still_positive_ev"
_H11a = "hit_11_vs_dealer_ace_no_double_advantage"
_H12n = "hit_12_vs_neutral_dealer_dealer_bust_rate_low"
_S12  = "stand_12_vs_dealer_bust_range"
_H12s = "hit_12_vs_strong_dealer"
_SB   = "stand_vs_dealer_bust_range"
_HM   = "hit_vs_strong_dealer_must_improve"
_H15n = "hit_15_vs_neutral_dealer"
_SR15 = "surrender_15_high_bust_risk_vs_strong_dealer"
_H16n = "hit_16_vs_neutral_dealer"
_SR16 = "surrender_16_negative_ev_vs_strong_dealer"
_S17  = "stand_pat_17_or_better"
_HSW  = "hit_soft_improve_weak_total"
_DS5  = "double_soft_vs_weak_dealer_two_ways_to_win"
_DSB  = "double_soft_vs_dealer_bust_range"
_DS17 = "double_soft_17_vs_bust_range_standing_value_negative"
_HS17 = "hit_soft_17_draw_to_improvement"
_DS18 = "double_soft_18_vs_bust_range_gain_on_strong_total"
_SS18a = "stand_soft_18_beats_dealer_likely_17"
_SS18b = "stand_soft_18_tied_with_dealer_likely_18"
_HS18  = "hit_soft_18_vs_strong_dealer_18_loses_too_often"
_SS19  = "stand_soft_19_plus_strong_total"
_SPA   = "always_split_aces_maximizes_blackjack_probability"
_SPsb  = "split_small_pair_vs_dealer_bust_range_das_advantage"
_SPsn  = "split_small_pair_vs_dealer_neutral"
_HPss  = "hit_small_pair_vs_strong_dealer"
_H4n   = "hit_4s_vs_neutral_dealer"
_SP4   = "split_4s_only_vs_weak_dealer_das_creates_edge"
_NS5d  = "never_split_5s_double_as_hard_10"
_NS5h  = "never_split_5s_hit_vs_strong_dealer"
_SP6   = "split_6s_vs_dealer_bust_range"
_H6n   = "hit_6s_vs_neutral_dealer_12_too_weak_to_stand"
_SP7b  = "split_7s_improve_from_weak_14"
_SP77  = "split_7s_vs_dealer_7_create_two_17s"
_H7s   = "hit_7s_vs_strong_dealer_14_must_improve"
_SP8   = "always_split_8s_16_is_worst_hand"
_SP9b  = "split_9s_18_beats_dealer_bust_range"
_S9_7  = "stand_9s_vs_7_already_winning_hand_likely_17"
_SP9_8 = "split_9s_18_doesnt_beat_dealers_likely_18_or_19"
_SP9_9 = "split_9s_18_doesnt_beat_dealers_likely_19"
_S9_10 = "stand_9s_vs_10_splitting_creates_more_losing_hands"
_S9_A  = "stand_9s_vs_ace_splitting_creates_more_losing_hands"
_ST    = "never_split_10s_20_is_near_unbeatable"

RATIONALES: dict = {
    "hard": {
        4:  _row(_LBR, _LBR, _LBR, _LBR, _LBR, _LBR, _LBR, _LBR, _LBR, _LBR),
        5:  _row(_LBR, _LBR, _LBR, _LBR, _LBR, _LBR, _LBR, _LBR, _LBR, _LBR),
        6:  _row(_LBR, _LBR, _LBR, _LBR, _LBR, _LBR, _LBR, _LBR, _LBR, _LBR),
        7:  _row(_LBR, _LBR, _LBR, _LBR, _LBR, _LBR, _LBR, _LBR, _LBR, _LBR),
        8:  _row(_LBR, _LBR, _LBR, _LBR, _LBR, _LBR, _LBR, _LBR, _LBR, _LBR),
        9:  _row(_H9s, _D9,  _D9,  _D9,  _D9,  _H9n, _H9s, _H9s, _H9s, _H9s),
        10: _row(_D10b, _D10b, _D10b, _D10b, _D10b, _D10n, _D10n, _D10n, _H10, _H10),
        11: _row(_D11, _D11, _D11, _D11, _D11, _D11, _D11, _D11, _D11s, _H11a),
        12: _row(_H12n, _H12n, _S12, _S12, _S12, _H12s, _H12s, _H12s, _H12s, _H12s),
        13: _row(_SB,  _SB,  _SB,  _SB,  _SB,  _HM,  _HM,  _HM,  _HM,  _HM),
        14: _row(_SB,  _SB,  _SB,  _SB,  _SB,  _HM,  _HM,  _HM,  _HM,  _HM),
        15: _row(_SB,  _SB,  _SB,  _SB,  _SB,  _H15n, _H15n, _H15n, _SR15, _SR15),
        16: _row(_SB,  _SB,  _SB,  _SB,  _SB,  _H16n, _H16n, _SR16, _SR16, _SR16),
        17: _row(_S17, _S17, _S17, _S17, _S17, _S17, _S17, _S17, _S17, _S17),
        18: _row(_S17, _S17, _S17, _S17, _S17, _S17, _S17, _S17, _S17, _S17),
        19: _row(_S17, _S17, _S17, _S17, _S17, _S17, _S17, _S17, _S17, _S17),
        20: _row(_S17, _S17, _S17, _S17, _S17, _S17, _S17, _S17, _S17, _S17),
        21: _row(_S17, _S17, _S17, _S17, _S17, _S17, _S17, _S17, _S17, _S17),
    },
    "soft": {
        13: _row(_HSW, _HSW, _HSW, _DS5, _DS5, _HSW, _HSW, _HSW, _HSW, _HSW),
        14: _row(_HSW, _HSW, _HSW, _DS5, _DS5, _HSW, _HSW, _HSW, _HSW, _HSW),
        15: _row(_HSW, _HSW, _DSB, _DSB, _DSB, _HSW, _HSW, _HSW, _HSW, _HSW),
        16: _row(_HSW, _HSW, _DSB, _DSB, _DSB, _HSW, _HSW, _HSW, _HSW, _HSW),
        17: _row(_HS17, _DS17, _DS17, _DS17, _DS17, _HS17, _HS17, _HS17, _HS17, _HS17),
        18: _row(_DS18, _DS18, _DS18, _DS18, _DS18, _SS18a, _SS18b, _HS18, _HS18, _HS18),
        19: _row(_SS19, _SS19, _SS19, _SS19, _SS19, _SS19, _SS19, _SS19, _SS19, _SS19),
        20: _row(_SS19, _SS19, _SS19, _SS19, _SS19, _SS19, _SS19, _SS19, _SS19, _SS19),
        21: _row(_SS19, _SS19, _SS19, _SS19, _SS19, _SS19, _SS19, _SS19, _SS19, _SS19),
    },
    "pair": {
        "A": _row(_SPA, _SPA, _SPA, _SPA, _SPA, _SPA, _SPA, _SPA, _SPA, _SPA),
        "2": _row(_SPsb, _SPsb, _SPsb, _SPsb, _SPsb, _SPsn, _HPss, _HPss, _HPss, _HPss),
        "3": _row(_SPsb, _SPsb, _SPsb, _SPsb, _SPsb, _SPsn, _HPss, _HPss, _HPss, _HPss),
        "4": _row(_H4n,  _H4n,  _H4n,  _SP4,  _SP4,  _H4n,  _H4n,  _H4n,  _H4n,  _H4n),
        "5": _row(_NS5d, _NS5d, _NS5d, _NS5d, _NS5d, _NS5d, _NS5d, _NS5d, _NS5h, _NS5h),
        "6": _row(_SP6,  _SP6,  _SP6,  _SP6,  _SP6,  _H6n,  _H6n,  _H6n,  _H6n,  _H6n),
        "7": _row(_SP7b, _SP7b, _SP7b, _SP7b, _SP7b, _SP77, _H7s,  _H7s,  _H7s,  _H7s),
        "8": _row(_SP8,  _SP8,  _SP8,  _SP8,  _SP8,  _SP8,  _SP8,  _SP8,  _SP8,  _SP8),
        "9": _row(_SP9b, _SP9b, _SP9b, _SP9b, _SP9b, _S9_7, _SP9_8, _SP9_9, _S9_10, _S9_A),
        "T": _row(_ST,   _ST,   _ST,   _ST,   _ST,   _ST,   _ST,   _ST,   _ST,   _ST),
    },
}
