from __future__ import annotations

import uuid
from enum import Enum, auto
from typing import Optional

from core.hand import Hand
from core.rules import RuleSet
from core.shoe import Shoe


class Action(Enum):
    HIT = auto()
    STAND = auto()
    DOUBLE = auto()
    SPLIT = auto()
    SURRENDER = auto()
    INSURE = auto()
    DECLINE_INSURANCE = auto()


class RoundPhase(Enum):
    BETTING = auto()
    DEALING = auto()
    INSURANCE = auto()
    DEALER_PEEK = auto()
    PLAYER_TURN = auto()
    DEALER_TURN = auto()
    PAYOUT = auto()
    DONE = auto()


class IllegalActionError(Exception):
    def __init__(
        self, attempted: Action, phase: RoundPhase, legal: set[Action]
    ) -> None:
        self.attempted = attempted
        self.phase = phase
        self.legal = legal
        super().__init__(
            f"Action {attempted.name} is illegal in phase {phase.name}. "
            f"Legal: {{{', '.join(a.name for a in legal)}}}"
        )


class Round:
    def __init__(self, shoe: Shoe, rules: RuleSet, bankroll: int) -> None:
        self._shoe = shoe
        self._rules = rules
        self.bankroll = bankroll
        self.phase = RoundPhase.BETTING
        self.bet: int = 0
        self.player_hands: list[Hand] = []
        self.active_hand_index: int = 0
        self.dealer_hand: Hand = Hand()
        self.insurance_taken: bool = False
        self._insurance_bet: int = 0
        self.result: Optional[dict] = None

    @property
    def _active_hand(self) -> Hand:
        return self.player_hands[self.active_hand_index]

    def place_bet(self, amount: int) -> None:
        if self.phase != RoundPhase.BETTING:
            raise RuntimeError(f"Cannot place bet in phase {self.phase.name}")
        if not self._rules.is_valid_bet(amount):
            raise ValueError(f"Invalid bet amount: {amount}")
        if amount > self.bankroll:
            raise ValueError(
                f"Bet {amount} exceeds bankroll {self.bankroll}"
            )
        self.bet = amount
        self.phase = RoundPhase.DEALING

    def deal(self) -> None:
        if self.phase != RoundPhase.DEALING:
            raise RuntimeError(f"Cannot deal in phase {self.phase.name}")
        player_hand = Hand()
        self.dealer_hand = Hand()
        # Standard deal order: p1, d1, p2, d2
        player_hand.cards.append(self._shoe.deal())
        self.dealer_hand.cards.append(self._shoe.deal())
        player_hand.cards.append(self._shoe.deal())
        self.dealer_hand.cards.append(self._shoe.deal())

        self.player_hands = [player_hand]
        self.active_hand_index = 0
        self.insurance_taken = False
        self._insurance_bet = 0
        self.result = None

        dealer_up = self.dealer_hand.cards[0]
        if dealer_up.rank == "A":
            self.phase = RoundPhase.INSURANCE
        else:
            self._do_dealer_peek()

    def _do_dealer_peek(self) -> None:
        self.phase = RoundPhase.DEALER_PEEK
        if self.dealer_hand.is_natural_blackjack:
            self._compute_payout()
        elif self.player_hands[0].is_natural_blackjack:
            # Player BJ confirmed (peek shows no dealer BJ); pay immediately
            self._compute_payout()
        else:
            self.phase = RoundPhase.PLAYER_TURN

    def apply(self, action: Action) -> None:
        legal = self.legal_actions()
        if action not in legal:
            raise IllegalActionError(action, self.phase, legal)
        if self.phase == RoundPhase.INSURANCE:
            self._apply_insurance(action)
        elif self.phase == RoundPhase.PLAYER_TURN:
            self._apply_player_action(action)

    def _apply_insurance(self, action: Action) -> None:
        if action == Action.INSURE:
            self.insurance_taken = True
            self._insurance_bet = self.bet // 2
        self._do_dealer_peek()

    def _apply_player_action(self, action: Action) -> None:
        hand = self._active_hand
        if action == Action.STAND:
            self._advance_hand()
        elif action == Action.HIT:
            hand.cards.append(self._shoe.deal())
            if hand.total >= 21:
                self._advance_hand()
        elif action == Action.DOUBLE:
            hand.has_doubled = True
            hand.cards.append(self._shoe.deal())
            self._advance_hand()
        elif action == Action.SPLIT:
            self._do_split()
        elif action == Action.SURRENDER:
            hand.is_surrendered = True
            self._advance_hand()

    def _do_split(self) -> None:
        hand = self._active_hand
        c1, c2 = hand.cards[0], hand.cards[1]
        parent_id = str(uuid.uuid4())
        is_ace = c1.rank == "A"
        hand_a = Hand(cards=[c1], is_split_from=parent_id, is_split_ace=is_ace)
        hand_b = Hand(cards=[c2], is_split_from=parent_id, is_split_ace=is_ace)

        idx = self.active_hand_index
        self.player_hands = (
            self.player_hands[:idx] + [hand_a, hand_b] + self.player_hands[idx + 1 :]
        )
        # Deal second card to the now-active hand_a
        hand_a.cards.append(self._shoe.deal())

    def _advance_hand(self) -> None:
        self.active_hand_index += 1
        if self.active_hand_index < len(self.player_hands):
            next_hand = self.player_hands[self.active_hand_index]
            if len(next_hand.cards) == 1:
                next_hand.cards.append(self._shoe.deal())
        else:
            self._end_player_turn()

    def _end_player_turn(self) -> None:
        all_terminal = all(
            h.total > 21 or h.is_surrendered for h in self.player_hands
        )
        if all_terminal:
            self._compute_payout()
        else:
            self.phase = RoundPhase.DEALER_TURN
            self.run_dealer()

    def run_dealer(self) -> None:
        while True:
            total = self.dealer_hand.total
            is_soft = self.dealer_hand.is_soft
            if total > 17:
                break
            if total == 17:
                if self._rules.dealer_hits_soft_17 and is_soft:
                    pass  # fall through to deal
                else:
                    break
            self.dealer_hand.cards.append(self._shoe.deal())
        self._compute_payout()

    def _compute_payout(self) -> None:
        dealer_total = self.dealer_hand.total
        dealer_bj = self.dealer_hand.is_natural_blackjack
        hand_results = []
        total_net = 0

        for hand in self.player_hands:
            hand_bet = self.bet * 2 if hand.has_doubled else self.bet
            if hand.is_surrendered:
                net = -(hand_bet // 2)
                outcome = "surrender"
            elif hand.total > 21:
                net = -hand_bet
                outcome = "bust"
            elif dealer_bj and not hand.is_natural_blackjack:
                net = -hand_bet
                outcome = "lose"
            elif hand.is_natural_blackjack and not dealer_bj:
                net = round(self.bet * self._rules.bj_payout)
                outcome = "natural"
            elif hand.total > dealer_total or dealer_total > 21:
                net = hand_bet
                outcome = "win"
            elif hand.total == dealer_total:
                net = 0
                outcome = "push"
            else:
                net = -hand_bet
                outcome = "lose"
            hand_results.append({"outcome": outcome, "net": net})
            total_net += net

        insurance_net = 0
        if self.insurance_taken:
            insurance_net = (
                self._insurance_bet * 2 if dealer_bj else -self._insurance_bet
            )
            total_net += insurance_net

        self.bankroll += total_net
        self.result = {
            "net": total_net,
            "hands": hand_results,
            "insurance_net": insurance_net,
        }
        self.phase = RoundPhase.DONE

    def legal_actions(self) -> set[Action]:
        if self.phase == RoundPhase.INSURANCE:
            return {Action.INSURE, Action.DECLINE_INSURANCE}
        if self.phase != RoundPhase.PLAYER_TURN:
            return set()

        hand = self._active_hand
        actions: set[Action] = {Action.STAND}

        if not hand.is_split_ace:
            actions.add(Action.HIT)

        if (
            self._rules.late_surrender
            and len(hand.cards) == 2
            and hand.is_split_from is None
        ):
            actions.add(Action.SURRENDER)

        if hand.is_pair and len(self.player_hands) < 4 and not hand.is_split_ace:
            actions.add(Action.SPLIT)

        if not hand.is_split_ace and len(hand.cards) == 2:
            if hand.is_split_from is None or self._rules.double_after_split:
                actions.add(Action.DOUBLE)

        return actions

    def next_hand(self) -> None:
        if self.phase != RoundPhase.DONE:
            raise RuntimeError(f"Cannot start next hand in phase {self.phase.name}")
        if self._shoe.needs_reshuffle():
            self._shoe.reshuffle()
        self.phase = RoundPhase.BETTING
        self.bet = 0
        self.player_hands = []
        self.active_hand_index = 0
        self.dealer_hand = Hand()
        self.insurance_taken = False
        self._insurance_bet = 0
        self.result = None
