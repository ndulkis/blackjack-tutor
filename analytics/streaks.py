from __future__ import annotations


class StreakTracker:
    """Tracks the current and best correct-decision streaks.

    Only primary decisions count; insurance and other secondary decisions
    are ignored.
    """

    def __init__(self) -> None:
        self._current: int = 0
        self._best: int = 0

    def record(self, was_correct: bool, is_primary: bool) -> None:
        if not is_primary:
            return
        if was_correct:
            self._current += 1
            if self._current > self._best:
                self._best = self._current
        else:
            self._current = 0

    @property
    def current(self) -> int:
        return self._current

    @property
    def best(self) -> int:
        return self._best
