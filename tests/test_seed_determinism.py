"""Two seed runs must produce identical worlds (Module 3 replays depend on
this)."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from seed.generate import generate_world


def _world_hash(db: Path, policies: Path) -> str:
    hasher = hashlib.sha256()
    conn = sqlite3.connect(db)
    try:
        for line in conn.iterdump():
            hasher.update(line.encode())
    finally:
        conn.close()
    for doc in sorted(policies.glob("*.md")):
        hasher.update(doc.name.encode())
        hasher.update(doc.read_bytes())
    return hasher.hexdigest()


def test_seed_is_deterministic(tmp_path: Path) -> None:
    hashes = []
    for run in ("a", "b"):
        db = tmp_path / run / "cartwheel.db"
        policies = tmp_path / run / "policies"
        generate_world(scale="dev", db_path=db, policies_dir=policies)
        hashes.append(_world_hash(db, policies))
    assert hashes[0] == hashes[1]


def test_seed_includes_documented_data_quality_cases(tmp_path: Path) -> None:
    db = tmp_path / "cartwheel.db"
    policies = tmp_path / "policies"
    generate_world(scale="dev", db_path=db, policies_dir=policies)

    conn = sqlite3.connect(db)
    try:
        cases = conn.execute(
            "SELECT case_id, entity_type, entity_id FROM data_quality_cases "
            "ORDER BY case_id"
        ).fetchall()
        reversed_dates = conn.execute(
            "SELECT shipped_at, delivered_at FROM orders WHERE id = 8001"
        ).fetchone()
        missing_date = conn.execute(
            "SELECT status, delivered_at FROM orders WHERE id = 8002"
        ).fetchone()
        product_defects = conn.execute(
            "SELECT title, price_cents FROM products WHERE id IN (3, 4) ORDER BY id"
        ).fetchall()
    finally:
        conn.close()

    assert len(cases) == 6
    assert reversed_dates[0] > reversed_dates[1]
    assert missing_date == ("delivered", None)
    assert product_defects[0][0] == ""
    assert product_defects[1][1] == -500
