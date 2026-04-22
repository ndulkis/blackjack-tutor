from __future__ import annotations

import json
from pathlib import Path


def data_dir() -> Path:
    """Returns ~/.blackjack_tutor/, creating it if needed."""
    p = Path.home() / ".blackjack_tutor"
    p.mkdir(exist_ok=True)
    return p


def write_json_atomic(path: Path, data: dict) -> None:
    """Write JSON to path via a .tmp sibling then rename (atomic on POSIX, near-atomic on Windows)."""
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)
