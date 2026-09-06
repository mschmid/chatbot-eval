"""Shared state-directory plumbing for the error-analysis helpers.

Every helper in this package reads and writes plain files under
``analysis/state/`` (the Artifact J layout), so that every run is
inspectable and resumable. This private module centralizes:

  - locating the state root (overridable with ``CARTWHEEL_ANALYSIS_STATE``
    so tests point at a committed fixture directory or a temp dir),
  - reading and writing JSON and JSONL,
  - append-only writes for label files (a label edit appends a new line
    and marks the prior line ``superseded_by``; nothing is overwritten).

It is not one of the agent-facing helper functions; the SKILL doc never
references it. Keep it dependency-free (standard library only).
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable

# The state directory that ships with the skill fork. Helpers default here;
# tests set CARTWHEEL_ANALYSIS_STATE to a copy so they never mutate the
# committed demo data.
_DEFAULT_STATE = Path(__file__).resolve().parent.parent / "state"


def state_root() -> Path:
    """Return the active state directory, honoring the env override."""
    override = os.environ.get("CARTWHEEL_ANALYSIS_STATE")
    root = Path(override) if override else _DEFAULT_STATE
    return root


def state_path(*parts: str) -> Path:
    """Join ``parts`` onto the state root without creating anything."""
    return state_root().joinpath(*parts)


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default: Any = None) -> Any:
    """Load JSON from ``path``; return ``default`` if the file is absent."""
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    """Write JSON atomically (temp file + rename) so a crash never leaves
    a half-written state file."""
    _ensure_parent(path)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file into a list of dicts; empty list if absent."""
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """Append one JSON object as a line. This is the only write path for
    label files, so the flip history stays complete: a correction appends a
    new line rather than editing an old one."""
    _ensure_parent(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False))
        handle.write("\n")


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    """Rewrite a JSONL file from ``records``. Used only to seed a fresh
    human judgments used for validation; ordinary edits go through :func:`append_jsonl`."""
    _ensure_parent(path)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False))
                handle.write("\n")
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
