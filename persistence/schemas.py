from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class DecisionRecord:
    """Serialised form of a single player decision."""

    schema_version: int = 1
    timestamp: str = ""
    hand_label: str = ""          # e.g. "Soft 18"
    dealer_up: str = ""           # e.g. "6"
    player_action: str = ""       # Action.name
    optimal_action: str = ""
    was_correct: bool = False
    is_primary: bool = True
    coach_response: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "timestamp": self.timestamp,
            "hand_label": self.hand_label,
            "dealer_up": self.dealer_up,
            "player_action": self.player_action,
            "optimal_action": self.optimal_action,
            "was_correct": self.was_correct,
            "is_primary": self.is_primary,
            "coach_response": self.coach_response,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DecisionRecord":
        return cls(
            schema_version=data.get("schema_version", 1),
            timestamp=data.get("timestamp", ""),
            hand_label=data.get("hand_label", ""),
            dealer_up=data.get("dealer_up", ""),
            player_action=data.get("player_action", ""),
            optimal_action=data.get("optimal_action", ""),
            was_correct=data.get("was_correct", False),
            is_primary=data.get("is_primary", True),
            coach_response=data.get("coach_response"),
        )


@dataclass
class SessionSummary:
    """Per-session stats snapshot written at session end."""

    schema_version: int = 1
    session_id: str = ""
    started_at: str = ""
    ended_at: str = ""
    total_decisions: int = 0
    correct_decisions: int = 0
    accuracy: Optional[float] = None
    starting_bankroll: int = 0
    ending_bankroll: int = 0
    best_streak: int = 0
    by_category: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "session_id": self.session_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "total_decisions": self.total_decisions,
            "correct_decisions": self.correct_decisions,
            "accuracy": self.accuracy,
            "starting_bankroll": self.starting_bankroll,
            "ending_bankroll": self.ending_bankroll,
            "best_streak": self.best_streak,
            "by_category": self.by_category,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionSummary":
        return cls(
            schema_version=data.get("schema_version", 1),
            session_id=data.get("session_id", ""),
            started_at=data.get("started_at", ""),
            ended_at=data.get("ended_at", ""),
            total_decisions=data.get("total_decisions", 0),
            correct_decisions=data.get("correct_decisions", 0),
            accuracy=data.get("accuracy"),
            starting_bankroll=data.get("starting_bankroll", 0),
            ending_bankroll=data.get("ending_bankroll", 0),
            best_streak=data.get("best_streak", 0),
            by_category=data.get("by_category", {}),
        )


@dataclass
class SessionHistory:
    """Ordered list of session summaries."""

    schema_version: int = 1
    sessions: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "sessions": self.sessions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionHistory":
        return cls(
            schema_version=data.get("schema_version", 1),
            sessions=data.get("sessions", []),
        )


@dataclass
class AppSettings:
    """User-configurable application settings."""

    schema_version: int = 1
    coach: str = "rule"           # "rule" | "llm"
    num_decks: int = 6
    dealer_hits_soft_17: bool = False
    double_after_split: bool = True
    late_surrender: bool = True
    starting_bankroll: int = 1000
    min_bet: int = 10
    max_bet: int = 500
    sound_enabled: bool = True
    show_hints: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "coach": self.coach,
            "num_decks": self.num_decks,
            "dealer_hits_soft_17": self.dealer_hits_soft_17,
            "double_after_split": self.double_after_split,
            "late_surrender": self.late_surrender,
            "starting_bankroll": self.starting_bankroll,
            "min_bet": self.min_bet,
            "max_bet": self.max_bet,
            "sound_enabled": self.sound_enabled,
            "show_hints": self.show_hints,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppSettings":
        return cls(
            schema_version=data.get("schema_version", 1),
            coach=data.get("coach", "rule"),
            num_decks=data.get("num_decks", 6),
            dealer_hits_soft_17=data.get("dealer_hits_soft_17", False),
            double_after_split=data.get("double_after_split", True),
            late_surrender=data.get("late_surrender", True),
            starting_bankroll=data.get("starting_bankroll", 1000),
            min_bet=data.get("min_bet", 10),
            max_bet=data.get("max_bet", 500),
            sound_enabled=data.get("sound_enabled", True),
            show_hints=data.get("show_hints", False),
        )


@dataclass
class CrashRecovery:
    """Snapshot written on uncaught exception so the player can resume."""

    schema_version: int = 1
    session_id: str = ""
    crashed_at: str = ""
    bankroll: int = 0
    decisions_so_far: list[dict[str, Any]] = field(default_factory=list)
    exception_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "session_id": self.session_id,
            "crashed_at": self.crashed_at,
            "bankroll": self.bankroll,
            "decisions_so_far": self.decisions_so_far,
            "exception_summary": self.exception_summary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CrashRecovery":
        return cls(
            schema_version=data.get("schema_version", 1),
            session_id=data.get("session_id", ""),
            crashed_at=data.get("crashed_at", ""),
            bankroll=data.get("bankroll", 0),
            decisions_so_far=data.get("decisions_so_far", []),
            exception_summary=data.get("exception_summary", ""),
        )
