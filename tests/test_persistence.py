"""Tests for persistence/schemas.py and persistence/migrations.py."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from persistence.migrations import migrate
from persistence.schemas import (
    AppSettings,
    CrashRecovery,
    DecisionRecord,
    SessionHistory,
    SessionSummary,
)


# ---------------------------------------------------------------------------
# Round-trip helpers
# ---------------------------------------------------------------------------

def _roundtrip(obj, cls):
    """Serialise to dict, deserialise back, assert equality."""
    d = obj.to_dict()
    restored = cls.from_dict(d)
    assert restored.to_dict() == d
    return restored


# ---------------------------------------------------------------------------
# DecisionRecord
# ---------------------------------------------------------------------------

class TestDecisionRecord:
    def test_default_schema_version(self) -> None:
        assert DecisionRecord().schema_version == 1

    def test_roundtrip_defaults(self) -> None:
        _roundtrip(DecisionRecord(), DecisionRecord)

    def test_roundtrip_populated(self) -> None:
        rec = DecisionRecord(
            timestamp="2026-04-30T00:00:00+00:00",
            hand_label="Soft 18",
            dealer_up="6",
            player_action="DOUBLE",
            optimal_action="DOUBLE",
            was_correct=True,
            is_primary=True,
            coach_response="Great double!",
        )
        _roundtrip(rec, DecisionRecord)

    def test_roundtrip_null_coach_response(self) -> None:
        rec = DecisionRecord(coach_response=None)
        restored = _roundtrip(rec, DecisionRecord)
        assert restored.coach_response is None

    def test_from_dict_missing_fields_use_defaults(self) -> None:
        rec = DecisionRecord.from_dict({})
        assert rec.schema_version == 1
        assert rec.was_correct is False
        assert rec.is_primary is True

    def test_json_serialisable(self) -> None:
        rec = DecisionRecord(hand_label="Hard 16", dealer_up="10", was_correct=False)
        json.dumps(rec.to_dict())  # must not raise


# ---------------------------------------------------------------------------
# SessionSummary
# ---------------------------------------------------------------------------

class TestSessionSummary:
    def test_default_schema_version(self) -> None:
        assert SessionSummary().schema_version == 1

    def test_roundtrip_defaults(self) -> None:
        _roundtrip(SessionSummary(), SessionSummary)

    def test_roundtrip_populated(self) -> None:
        summary = SessionSummary(
            session_id="abc-123",
            started_at="2026-04-30T10:00:00+00:00",
            ended_at="2026-04-30T10:30:00+00:00",
            total_decisions=50,
            correct_decisions=45,
            accuracy=0.9,
            starting_bankroll=1000,
            ending_bankroll=1150,
            best_streak=12,
            by_category={"Hard 12-16": {"correct": 10, "total": 12}},
        )
        _roundtrip(summary, SessionSummary)

    def test_accuracy_can_be_none(self) -> None:
        summary = SessionSummary(accuracy=None)
        restored = _roundtrip(summary, SessionSummary)
        assert restored.accuracy is None

    def test_json_serialisable(self) -> None:
        json.dumps(SessionSummary(accuracy=0.85).to_dict())


# ---------------------------------------------------------------------------
# SessionHistory
# ---------------------------------------------------------------------------

class TestSessionHistory:
    def test_default_schema_version(self) -> None:
        assert SessionHistory().schema_version == 1

    def test_roundtrip_empty(self) -> None:
        _roundtrip(SessionHistory(), SessionHistory)

    def test_roundtrip_with_sessions(self) -> None:
        hist = SessionHistory(sessions=[{"session_id": "s1"}, {"session_id": "s2"}])
        _roundtrip(hist, SessionHistory)

    def test_sessions_defaults_to_empty_list(self) -> None:
        assert SessionHistory.from_dict({}).sessions == []

    def test_json_serialisable(self) -> None:
        json.dumps(SessionHistory(sessions=[{"accuracy": 0.9}]).to_dict())


# ---------------------------------------------------------------------------
# AppSettings
# ---------------------------------------------------------------------------

class TestAppSettings:
    def test_default_schema_version(self) -> None:
        assert AppSettings().schema_version == 1

    def test_defaults(self) -> None:
        s = AppSettings()
        assert s.coach == "rule"
        assert s.num_decks == 6
        assert s.dealer_hits_soft_17 is False
        assert s.double_after_split is True
        assert s.late_surrender is True
        assert s.starting_bankroll == 1000

    def test_roundtrip_defaults(self) -> None:
        _roundtrip(AppSettings(), AppSettings)

    def test_roundtrip_custom(self) -> None:
        settings = AppSettings(
            coach="llm",
            num_decks=2,
            dealer_hits_soft_17=True,
            double_after_split=False,
            late_surrender=False,
            starting_bankroll=500,
            min_bet=5,
            max_bet=200,
            sound_enabled=False,
            show_hints=True,
        )
        _roundtrip(settings, AppSettings)

    def test_from_dict_missing_fields_use_defaults(self) -> None:
        s = AppSettings.from_dict({})
        assert s.coach == "rule"
        assert s.num_decks == 6

    def test_json_serialisable(self) -> None:
        json.dumps(AppSettings().to_dict())


# ---------------------------------------------------------------------------
# CrashRecovery
# ---------------------------------------------------------------------------

class TestCrashRecovery:
    def test_default_schema_version(self) -> None:
        assert CrashRecovery().schema_version == 1

    def test_roundtrip_defaults(self) -> None:
        _roundtrip(CrashRecovery(), CrashRecovery)

    def test_roundtrip_populated(self) -> None:
        cr = CrashRecovery(
            session_id="xyz",
            crashed_at="2026-04-30T11:00:00+00:00",
            bankroll=750,
            decisions_so_far=[{"hand_label": "Hard 16", "was_correct": False}],
            exception_summary="ZeroDivisionError: division by zero",
        )
        _roundtrip(cr, CrashRecovery)

    def test_decisions_defaults_to_empty_list(self) -> None:
        assert CrashRecovery.from_dict({}).decisions_so_far == []

    def test_json_serialisable(self) -> None:
        json.dumps(CrashRecovery(bankroll=500).to_dict())


# ---------------------------------------------------------------------------
# Atomic write simulation — write-then-rename pattern
# ---------------------------------------------------------------------------

class TestAtomicWrite:
    """Verifies the pattern: write to .tmp, rename to final (atomic on most OSes)."""

    def test_atomic_write_produces_correct_file(self, tmp_path: Path) -> None:
        target = tmp_path / "settings.json"
        tmp_file = tmp_path / "settings.json.tmp"

        data = AppSettings(coach="llm", starting_bankroll=200).to_dict()
        tmp_file.write_text(json.dumps(data), encoding="utf-8")
        os.replace(tmp_file, target)

        assert target.exists()
        assert not tmp_file.exists()
        loaded = AppSettings.from_dict(json.loads(target.read_text()))
        assert loaded.coach == "llm"
        assert loaded.starting_bankroll == 200

    def test_corrupt_file_recovery(self, tmp_path: Path) -> None:
        corrupt = tmp_path / "settings.json"
        corrupt.write_text("{this is not json", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            json.loads(corrupt.read_text())

        # Recovery: fall back to defaults
        try:
            data = json.loads(corrupt.read_text())
        except json.JSONDecodeError:
            data = {}
        settings = AppSettings.from_dict(data)
        assert settings.coach == "rule"


# ---------------------------------------------------------------------------
# Migrations
# ---------------------------------------------------------------------------

class TestMigrations:
    def test_migrate_same_version_returns_unchanged(self) -> None:
        data = {"schema_version": 1, "coach": "llm"}
        result = migrate(data, from_version=1)
        assert result == data

    def test_migrate_returns_dict(self) -> None:
        result = migrate({}, from_version=1)
        assert isinstance(result, dict)
