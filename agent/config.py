"""Shared paths and the facts-sheet loader.

Paths resolve from environment variables first so tests can point the agent
at a temporary world without touching the checked-in data:

  - CARTWHEEL_DB: path to the SQLite database (default data/cartwheel.db).
  - CARTWHEEL_POLICIES_DIR: path to the policy corpus (default data/policies).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def db_path() -> Path:
    return Path(os.environ.get("CARTWHEEL_DB", REPO_ROOT / "data" / "cartwheel.db"))


def policies_dir() -> Path:
    return Path(
        os.environ.get("CARTWHEEL_POLICIES_DIR", REPO_ROOT / "data" / "policies")
    )


def facts_path() -> Path:
    return REPO_ROOT / "facts.yaml"


@lru_cache(maxsize=1)
def _load_facts_cached(path: str) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


def load_facts() -> dict[str, Any]:
    """Load facts.yaml (cached; the facts sheet does not change at runtime)."""
    return _load_facts_cached(str(facts_path()))
