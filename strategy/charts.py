from __future__ import annotations

from core.game import Action

# Shorthand aliases — keep tables readable and column-aligned
H = Action.HIT
S = Action.STAND
D = (Action.DOUBLE, Action.HIT)     # double if legal, else hit
DS = (Action.DOUBLE, Action.STAND)  # double if legal, else stand
RH = (Action.SURRENDER, Action.HIT) # surrender if legal, else hit
SP = Action.SPLIT

_DEALER_UPS = (2, 3, 4, 5, 6, 7, 8, 9, 10, 11)  # 11 = Ace


def _row(*actions: object) -> dict[int, object]:
    return dict(zip(_DEALER_UPS, actions))


# ---------------------------------------------------------------------------
# HARD_TOTALS
# Source: Wizard of Odds — 6-deck, S17, DAS, late surrender
# Outer key: player hard total (4–21)
# Inner key: dealer up-card value (2–10, 11=Ace)
# ---------------------------------------------------------------------------
HARD_TOTALS: dict[int, dict[int, Action | tuple[Action, ...]]] = {
    4:  _row(H,  H,  H,  H,  H,  H,  H,  H,  H,  H),
    5:  _row(H,  H,  H,  H,  H,  H,  H,  H,  H,  H),
    6:  _row(H,  H,  H,  H,  H,  H,  H,  H,  H,  H),
    7:  _row(H,  H,  H,  H,  H,  H,  H,  H,  H,  H),
    8:  _row(H,  H,  H,  H,  H,  H,  H,  H,  H,  H),
    9:  _row(H,  D,  D,  D,  D,  H,  H,  H,  H,  H),
    10: _row(D,  D,  D,  D,  D,  D,  D,  D,  H,  H),
    11: _row(D,  D,  D,  D,  D,  D,  D,  D,  D,  H),
    12: _row(H,  H,  S,  S,  S,  H,  H,  H,  H,  H),
    13: _row(S,  S,  S,  S,  S,  H,  H,  H,  H,  H),
    14: _row(S,  S,  S,  S,  S,  H,  H,  H,  H,  H),
    15: _row(S,  S,  S,  S,  S,  H,  H,  H,  RH, RH),
    16: _row(S,  S,  S,  S,  S,  H,  H,  RH, RH, RH),
    17: _row(S,  S,  S,  S,  S,  S,  S,  S,  S,  S),
    18: _row(S,  S,  S,  S,  S,  S,  S,  S,  S,  S),
    19: _row(S,  S,  S,  S,  S,  S,  S,  S,  S,  S),
    20: _row(S,  S,  S,  S,  S,  S,  S,  S,  S,  S),
    21: _row(S,  S,  S,  S,  S,  S,  S,  S,  S,  S),
}

# ---------------------------------------------------------------------------
# SOFT_TOTALS
# Outer key: player soft total (13–21); e.g. Ace+6 = soft 17 → key 17
# ---------------------------------------------------------------------------
SOFT_TOTALS: dict[int, dict[int, Action | tuple[Action, ...]]] = {
    13: _row(H,  H,  H,  D,  D,  H,  H,  H,  H,  H),
    14: _row(H,  H,  H,  D,  D,  H,  H,  H,  H,  H),
    15: _row(H,  H,  D,  D,  D,  H,  H,  H,  H,  H),
    16: _row(H,  H,  D,  D,  D,  H,  H,  H,  H,  H),
    17: _row(H,  D,  D,  D,  D,  H,  H,  H,  H,  H),
    18: _row(DS, DS, DS, DS, DS, S,  S,  H,  H,  H),
    19: _row(S,  S,  S,  S,  S,  S,  S,  S,  S,  S),
    20: _row(S,  S,  S,  S,  S,  S,  S,  S,  S,  S),
    21: _row(S,  S,  S,  S,  S,  S,  S,  S,  S,  S),
}

# ---------------------------------------------------------------------------
# PAIRS
# Outer key: rank character of the pair card ("2"–"9", "T", "A")
#   "T" covers T/J/Q/K — callers must normalise J/Q/K → "T" before lookup
# "5" and "T" entries intentionally use non-split actions (hard-10 / stand)
# ---------------------------------------------------------------------------
PAIRS: dict[str, dict[int, Action | tuple[Action, ...]]] = {
    "A": _row(SP, SP, SP, SP, SP, SP, SP, SP, SP, SP),
    "2": _row(SP, SP, SP, SP, SP, SP, H,  H,  H,  H),
    "3": _row(SP, SP, SP, SP, SP, SP, H,  H,  H,  H),
    "4": _row(H,  H,  H,  SP, SP, H,  H,  H,  H,  H),
    "5": _row(D,  D,  D,  D,  D,  D,  D,  D,  H,  H),  # never split 5s
    "6": _row(SP, SP, SP, SP, SP, H,  H,  H,  H,  H),
    "7": _row(SP, SP, SP, SP, SP, SP, H,  H,  H,  H),
    "8": _row(SP, SP, SP, SP, SP, SP, SP, SP, SP, SP),
    "9": _row(SP, SP, SP, SP, SP, S,  SP, SP, S,  S),
    "T": _row(S,  S,  S,  S,  S,  S,  S,  S,  S,  S),  # never split 10s
}
