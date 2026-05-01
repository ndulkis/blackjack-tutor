from __future__ import annotations

from typing import Protocol, runtime_checkable

from analytics.session import Decision
from core.rules import RuleSet


class CoachResult:
    """Wraps a coaching explanation that may be produced asynchronously.

    For rule-based coaching the result is always immediately ready.
    For LLM coaching the result is produced in a background thread and
    callers must poll is_ready() or block on get().
    """

    def __init__(self, text: str) -> None:
        self._text = text
        self._ready = True

    def is_ready(self) -> bool:
        return self._ready

    def get(self) -> str:
        """Return the explanation text; blocks until ready."""
        return self._text

    @classmethod
    def pending(cls) -> "CoachResult":
        """Create a not-yet-ready result (subclasses override _ready and _text)."""
        obj = cls.__new__(cls)
        obj._text = ""
        obj._ready = False
        return obj


@runtime_checkable
class Coach(Protocol):
    def explain(self, decision: Decision, rules: RuleSet) -> CoachResult: ...
