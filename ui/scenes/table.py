from __future__ import annotations

from typing import Optional

import pygame

from analytics.session import Decision, SessionTracker
from analytics.streaks import StreakTracker
from coach.rule_coach import RuleCoach
from core.game import Action, Round, RoundPhase
from core.hand import Hand
from core.rules import RuleSet
from core.shoe import Shoe
from strategy.engine import ActionContext, optimal_action
from ui import theme

# Keyboard → Action for the player turn
_KEY_ACTION: dict[int, Action] = {
    pygame.K_h: Action.HIT,
    pygame.K_s: Action.STAND,
    pygame.K_d: Action.DOUBLE,
    pygame.K_p: Action.SPLIT,
    pygame.K_r: Action.SURRENDER,
}

_ACTION_LABEL: dict[Action, str] = {
    Action.HIT:       "[H]it",
    Action.STAND:     "[S]tand",
    Action.DOUBLE:    "[D]ouble",
    Action.SPLIT:     "s[P]lit",
    Action.SURRENDER: "su[R]render",
}

_CARD_W = 70
_CARD_H = 95
_CARD_RAD = 6

# Vertical layout anchors
_DEALER_Y   = 80
_PLAYER_Y   = 240
_ACTION_Y   = 400
_FEEDBACK_Y = 470


class TableScene:
    def __init__(self, rules: RuleSet) -> None:
        self._rules = rules
        self._shoe = Shoe(rules.num_decks)
        self._round = Round(self._shoe, rules, rules.starting_bankroll)
        self._tracker = SessionTracker()
        self._streaks = StreakTracker()
        self._coach = RuleCoach()
        self._bet: int = rules.min_bet
        self._feedback: str = ""
        self._feedback_correct: Optional[bool] = None
        self._fonts: dict[str, pygame.font.Font] = {}

    # ─── events ──────────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        if event.type != pygame.KEYDOWN:
            return None
        key = event.key
        phase = self._round.phase

        if key == pygame.K_ESCAPE:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
            return None

        if phase == RoundPhase.BETTING:
            if key in (pygame.K_SPACE, pygame.K_RETURN):
                self._start_round()
            elif key == pygame.K_UP:
                self._bet = min(
                    self._bet + self._rules.bet_increment, self._rules.max_bet
                )
            elif key == pygame.K_DOWN:
                self._bet = max(
                    self._bet - self._rules.bet_increment, self._rules.min_bet
                )

        elif phase == RoundPhase.INSURANCE:
            if key == pygame.K_y:
                self._act(Action.INSURE)
            elif key == pygame.K_n:
                self._act(Action.DECLINE_INSURANCE)

        elif phase == RoundPhase.PLAYER_TURN:
            action = _KEY_ACTION.get(key)
            if action and action in self._round.legal_actions():
                self._act(action)

        elif phase == RoundPhase.DONE:
            if key == pygame.K_SPACE:
                self._next_round()

        return None

    # ─── game logic ──────────────────────────────────────────────────────────

    def _start_round(self) -> None:
        self._feedback = ""
        self._feedback_correct = None
        self._round.place_bet(self._bet)
        self._round.deal()

    def _act(self, action: Action) -> None:
        hand = self._round.player_hands[self._round.active_hand_index]
        dealer_up = self._round.dealer_hand.cards[0]
        phase = self._round.phase

        # Snapshot hand state before apply() mutates it
        snap = Hand(
            cards=list(hand.cards),
            is_split_from=hand.is_split_from,
            has_doubled=hand.has_doubled,
            is_surrendered=hand.is_surrendered,
            is_split_ace=hand.is_split_ace,
        )

        if phase == RoundPhase.INSURANCE:
            optimal = Action.DECLINE_INSURANCE   # basic strategy always declines
            was_correct = action == optimal
            is_primary = False
        else:
            legal = self._round.legal_actions()
            ctx = ActionContext(
                is_post_split=hand.is_split_from is not None,
                can_double=Action.DOUBLE in legal,
                can_surrender=Action.SURRENDER in legal,
            )
            optimal = optimal_action(hand, dealer_up, self._rules, ctx)
            was_correct = action == optimal
            is_primary = True

        decision = Decision(
            hand_snapshot=snap,
            dealer_up=dealer_up,
            player_action=action,
            optimal_action=optimal,
            was_correct=was_correct,
            is_primary=is_primary,
            timestamp=Decision.make_timestamp(),
        )
        coach_result = self._coach.explain(decision, self._rules)
        decision.coach_response = coach_result.get()

        self._tracker.record(decision)
        self._streaks.record(was_correct, is_primary)
        self._feedback = coach_result.get()
        self._feedback_correct = was_correct if is_primary else None

        self._round.apply(action)

    def _next_round(self) -> None:
        self._round.next_hand()
        self._feedback = ""
        self._feedback_correct = None

    # ─── font helper ─────────────────────────────────────────────────────────

    def _font(self, key: str, size: int) -> pygame.font.Font:
        if key not in self._fonts:
            self._fonts[key] = pygame.font.SysFont("monospace", size)
        return self._fonts[key]

    # ─── draw ────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface) -> None:
        self._draw_hud(surface)
        phase = self._round.phase
        if phase == RoundPhase.BETTING:
            self._draw_betting(surface)
            return
        self._draw_dealer(surface)
        self._draw_player_hands(surface)
        if phase == RoundPhase.INSURANCE:
            self._draw_insurance_prompt(surface)
        elif phase == RoundPhase.PLAYER_TURN:
            self._draw_action_buttons(surface)
        elif phase == RoundPhase.DONE:
            self._draw_result(surface)
        self._draw_feedback(surface)

    def _draw_hud(self, surface: pygame.Surface) -> None:
        font = self._font("hud", theme.BODY_PT)
        acc = self._tracker.accuracy()
        acc_str = f"{acc:.0%}" if acc is not None else "--%"
        text = (
            f"Bankroll: ${self._round.bankroll}"
            f"   Bet: ${self._bet}"
            f"   Streak: {self._streaks.current}"
            f"   Accuracy: {acc_str}"
        )
        surf = font.render(text, True, theme.TEXT)
        surface.blit(surf, (20, 15))

    def _draw_betting(self, surface: pygame.Surface) -> None:
        cx = theme.WIDTH // 2
        big = self._font("headline", theme.SUMMARY_HEADLINE_PT)
        small = self._font("body", theme.BODY_PT)
        bet_surf = big.render(f"Place your bet: ${self._bet}", True, theme.ACCENT)
        surface.blit(bet_surf, bet_surf.get_rect(center=(cx, 330)))
        hint = small.render("↑/↓ to adjust   Space to deal", True, theme.TEXT_DIM)
        surface.blit(hint, hint.get_rect(center=(cx, 395)))

    def _draw_dealer(self, surface: pygame.Surface) -> None:
        cards = self._round.dealer_hand.cards
        if not cards:
            return
        reveal = self._round.phase == RoundPhase.DONE
        cx = theme.WIDTH // 2
        n = len(cards)
        total_w = n * _CARD_W + (n - 1) * 12
        x = cx - total_w // 2
        for i, card in enumerate(cards):
            self._draw_card(surface, card, x, _DEALER_Y, face_down=(i == 1 and not reveal))
            x += _CARD_W + 12
        font = self._font("body", theme.BODY_PT)
        if reveal:
            label = f"Dealer: {self._round.dealer_hand.total}"
        else:
            label = f"Dealer shows: {cards[0].rank}"
        surf = font.render(label, True, theme.TEXT_DIM)
        surface.blit(surf, surf.get_rect(center=(cx, _DEALER_Y + _CARD_H + 22)))

    def _draw_player_hands(self, surface: pygame.Surface) -> None:
        hands = self._round.player_hands
        if not hands:
            return
        n = len(hands)
        phase = self._round.phase
        active = self._round.active_hand_index
        font = self._font("body", theme.BODY_PT)
        slot_w = theme.WIDTH // n
        for hi, hand in enumerate(hands):
            is_active = (hi == active) and phase == RoundPhase.PLAYER_TURN
            cx = slot_w * hi + slot_w // 2
            nc = len(hand.cards)
            total_w = nc * _CARD_W + (nc - 1) * 8
            x = cx - total_w // 2
            if is_active:
                pygame.draw.rect(
                    surface, theme.ACCENT,
                    (x - 10, _PLAYER_Y - 10, total_w + 20, _CARD_H + 20),
                    2, border_radius=8,
                )
            for card in hand.cards:
                self._draw_card(surface, card, x, _PLAYER_Y)
                x += _CARD_W + 8
            color = theme.TEXT if is_active else theme.TEXT_DIM
            lbl = font.render(hand.category_label, True, color)
            surface.blit(lbl, lbl.get_rect(center=(cx, _PLAYER_Y + _CARD_H + 22)))

    def _draw_action_buttons(self, surface: pygame.Surface) -> None:
        legal = self._round.legal_actions()
        font = self._font("button", theme.BUTTON_PT)
        btn_w, btn_h = 140, 44
        buttons = [a for a in _ACTION_LABEL if a in legal]
        total_w = len(buttons) * btn_w + (len(buttons) - 1) * 12
        x = theme.WIDTH // 2 - total_w // 2
        for action in buttons:
            rect = pygame.Rect(x, _ACTION_Y, btn_w, btn_h)
            pygame.draw.rect(surface, theme.BUTTON_BG, rect, border_radius=6)
            pygame.draw.rect(surface, theme.ACCENT, rect, 1, border_radius=6)
            lbl = font.render(_ACTION_LABEL[action], True, theme.TEXT)
            surface.blit(lbl, lbl.get_rect(center=rect.center))
            x += btn_w + 12

    def _draw_insurance_prompt(self, surface: pygame.Surface) -> None:
        font = self._font("body", theme.BODY_PT)
        msg = font.render("Take insurance?   [Y]es   [N]o", True, theme.ACCENT)
        surface.blit(msg, msg.get_rect(center=(theme.WIDTH // 2, _ACTION_Y + 22)))

    def _draw_result(self, surface: pygame.Surface) -> None:
        result = self._round.result
        if not result:
            return
        net = result["net"]
        big = self._font("headline", theme.SUMMARY_HEADLINE_PT)
        small = self._font("body", theme.BODY_PT)
        if net > 0:
            text, color = f"+${net}", theme.CORRECT
        elif net < 0:
            text, color = f"-${abs(net)}", theme.MISTAKE
        else:
            text, color = "Push", theme.TEXT_DIM
        surf = big.render(text, True, color)
        surface.blit(surf, surf.get_rect(center=(theme.WIDTH // 2, _ACTION_Y + 20)))
        hint = small.render("Space → next hand", True, theme.TEXT_DIM)
        surface.blit(hint, hint.get_rect(center=(theme.WIDTH // 2, _ACTION_Y + 58)))

    def _draw_feedback(self, surface: pygame.Surface) -> None:
        if not self._feedback:
            return
        font = self._font("feedback", theme.BODY_PT)
        if self._feedback_correct is True:
            color = theme.CORRECT
        elif self._feedback_correct is False:
            color = theme.MISTAKE
        else:
            color = theme.TEXT_DIM
        words = self._feedback.split()
        lines: list[str] = []
        line: list[str] = []
        for word in words:
            test = " ".join(line + [word])
            if font.size(test)[0] > 900 and line:
                lines.append(" ".join(line))
                line = [word]
            else:
                line.append(word)
        if line:
            lines.append(" ".join(line))
        y = _FEEDBACK_Y
        for text_line in lines:
            surf = font.render(text_line, True, color)
            surface.blit(surf, surf.get_rect(center=(theme.WIDTH // 2, y)))
            y += theme.BODY_PT + 6

    def _draw_card(
        self, surface: pygame.Surface, card, x: int, y: int, face_down: bool = False
    ) -> None:
        rect = pygame.Rect(x, y, _CARD_W, _CARD_H)
        if face_down:
            pygame.draw.rect(surface, theme.FELT, rect, border_radius=_CARD_RAD)
            pygame.draw.rect(surface, theme.TEXT_DIM, rect, 1, border_radius=_CARD_RAD)
            return
        pygame.draw.rect(surface, theme.CARD_BG, rect, border_radius=_CARD_RAD)
        pygame.draw.rect(surface, (180, 180, 180), rect, 1, border_radius=_CARD_RAD)
        is_red = card.suit in ("H", "D")
        fg = (200, 30, 30) if is_red else (20, 20, 20)
        font = self._font("card", theme.CARD_PT)
        rank_str = card.rank if card.rank != "10" else "T"
        lbl = font.render(f"{rank_str}{card.suit}", True, fg)
        surface.blit(lbl, lbl.get_rect(center=rect.center))
