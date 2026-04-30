from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Optional

import pygame

from core.rules import RuleSet
from ui import theme

_CRASH_PATH = Path.home() / ".blackjack_tutor" / "crash_recovery.json"


class _StubScene:
    """Placeholder drawn until a real scene is wired in."""

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        return None

    def draw(self, surface: pygame.Surface) -> None:
        font = pygame.font.SysFont(None, theme.SUMMARY_HEADLINE_PT)
        msg = font.render("Blackjack Tutor — coming soon", True, theme.TEXT)
        surface.blit(msg, msg.get_rect(center=(theme.WIDTH // 2, theme.HEIGHT // 2)))


class App:
    def __init__(self) -> None:
        pygame.init()
        self._screen = pygame.display.set_mode((theme.WIDTH, theme.HEIGHT))
        pygame.display.set_caption(theme.TITLE)
        self._clock = pygame.time.Clock()
        self._rules = RuleSet()
        self._scene_name = "table"
        self._scenes: dict[str, object] = self._build_scenes()
        self._running = True

    def _build_scenes(self) -> dict[str, object]:
        try:
            from ui.scenes.table import TableScene
            return {"table": TableScene(self._rules)}
        except ImportError:
            return {"table": _StubScene()}

    def _current(self) -> object:
        return self._scenes[self._scene_name]

    def run(self) -> None:
        try:
            while self._running:
                self._clock.tick(theme.FPS)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self._running = False
                        break
                    transition = self._current().handle_event(event)  # type: ignore[union-attr]
                    if transition and transition in self._scenes:
                        self._scene_name = transition
                self._screen.fill(theme.BG)
                self._current().draw(self._screen)  # type: ignore[union-attr]
                pygame.display.flip()
        except Exception:
            self._write_crash()
            raise
        finally:
            pygame.quit()

    def _write_crash(self) -> None:
        try:
            _CRASH_PATH.parent.mkdir(parents=True, exist_ok=True)
            _CRASH_PATH.write_text(
                json.dumps(
                    {"scene": self._scene_name, "traceback": traceback.format_exc()},
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass


def run() -> None:
    App().run()


if __name__ == "__main__":
    run()
