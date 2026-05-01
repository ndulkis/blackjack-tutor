from __future__ import annotations

from dataclasses import dataclass

from core.card import Card
from core.game import Action
from core.hand import Hand
from core.rules import RuleSet
from strategy.charts import HARD_TOTALS, PAIRS, SOFT_TOTALS

# 10-value ranks that all map to "T" in the PAIRS table
_TEN_RANKS = frozenset({"10", "J", "Q", "K"})


@dataclass(frozen=True)
class ActionContext:
    is_post_split: bool = False
    can_double: bool = True
    can_surrender: bool = True


def _dealer_up_key(dealer_up: Card) -> int:
    """Convert a dealer up-card to the integer key used in the chart tables."""
    return 11 if dealer_up.rank == "A" else dealer_up.value


def _pair_rank_key(hand: Hand) -> str:
    """Normalise the pair rank to a PAIRS table key; J/Q/K → 'T'."""
    rank = hand.cards[0].rank
    return "T" if rank in _TEN_RANKS else rank


def _is_legal(action: Action, context: ActionContext) -> bool:
    if action == Action.DOUBLE and not context.can_double:
        return False
    if action == Action.SURRENDER and not context.can_surrender:
        return False
    if action == Action.SPLIT and context.is_post_split:
        # SPLIT legality for re-split is handled upstream; engine just
        # respects the context flag as a blanket post-split split guard.
        # Callers that allow re-split should set is_post_split=False.
        return False
    return True


def optimal_action(
    hand: Hand,
    dealer_up: Card,
    rules: RuleSet,
    context: ActionContext | None = None,
) -> Action:
    """Return the basic-strategy optimal action for *hand* against *dealer_up*.

    Lookup priority:
      1. PAIRS table  — when hand.is_pair (split may or may not be recommended)
      2. SOFT_TOTALS  — when hand.is_soft and not a pair
      3. HARD_TOTALS  — everything else

    Tuple chart values are ordered fallbacks; the first action legal in
    *context* is returned.  A plain Action value is returned directly.
    """
    if context is None:
        context = ActionContext(
            is_post_split=False,
            can_double=True,
            can_surrender=rules.late_surrender,
        )

    dealer_key = _dealer_up_key(dealer_up)

    if hand.is_pair:
        entry = PAIRS[_pair_rank_key(hand)][dealer_key]
    elif hand.is_soft:
        entry = SOFT_TOTALS[hand.total][dealer_key]
    else:
        total = max(hand.total, 4)  # chart starts at 4; lower totals always hit
        entry = HARD_TOTALS[total][dealer_key]

    if isinstance(entry, tuple):
        for action in entry:
            if _is_legal(action, context):
                return action
        # All fallbacks exhausted — should not happen with well-formed charts
        raise RuntimeError(
            f"No legal action found for {hand.category_label} vs {dealer_up} "
            f"with context {context}"
        )

    return entry
