"""Test fixtures. Everything runs offline with no API keys.

The session-scoped `world` fixture seeds a fresh dev-scale world into a
temp directory and points the agent at it through the CARTWHEEL_DB and
CARTWHEEL_POLICIES_DIR env vars, so tests never touch data/. Tests that
mutate the database (refunds, cancellations) use `world_copy`, which hands
each test its own copy.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from seed.generate import generate_world


@pytest.fixture(scope="session")
def world(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    root = tmp_path_factory.mktemp("world")
    db = root / "cartwheel.db"
    policies = root / "policies"
    generate_world(scale="dev", db_path=db, policies_dir=policies)
    os.environ["CARTWHEEL_DB"] = str(db)
    os.environ["CARTWHEEL_POLICIES_DIR"] = str(policies)
    return {"db": db, "policies": policies}


@pytest.fixture
def world_copy(
    world: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    db = tmp_path / "cartwheel.db"
    shutil.copy(world["db"], db)
    monkeypatch.setenv("CARTWHEEL_DB", str(db))
    return db


@pytest.fixture
def analysis_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Hand each Module 2 test its own copy of the committed demo state.

    The error-analysis helpers read and write files under
    ``analysis/state/`` (the Artifact J layout). Copying the committed demo
    state into a temp dir and pointing ``CARTWHEEL_ANALYSIS_STATE`` there
    lets the invariant tests exercise writes (freeze, label appends) without
    mutating the checked-in fixture, exactly as ``world_copy`` does for the
    database. Everything here is offline: no keys, no LLM calls.
    """
    src = Path(__file__).resolve().parent.parent / "analysis" / "state"
    dst = tmp_path / "state"
    shutil.copytree(src, dst)
    monkeypatch.setenv("CARTWHEEL_ANALYSIS_STATE", str(dst))
    return dst
