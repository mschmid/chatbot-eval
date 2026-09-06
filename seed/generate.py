"""Deterministic world generator for Cartwheel.

Instructor-provided. Students never need to edit this file, and never need to
run it more than once. Two runs with the same arguments produce byte-identical
data (tests/test_seed_determinism.py checks this), so every seeded fact is a
stable ground truth for later modules.

Scales:
  - "dev" (default): the 20 curated core stores, ~40 products per store,
    ~10K orders over 18 months, users in three roles, and a ~15-doc placeholder
    policy corpus rendered from facts.yaml. Everything runs offline.
  - "full": the lecture-scale world (~500 stores, ~50K products sampled from
    the Amazon Reviews 2023 metadata on Hugging Face, ~100K orders, ~600-doc
    corpus). Not implemented in the starter repo; see the error message in
    `generate_world` for what it will do.

Usage:
    uv run python -m seed.generate [--scale dev|full] [--db PATH] [--policies PATH]
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml

from seed.eligibility import effective_return_window_days, is_refund_eligible
from seed.policies import render_platform_policies, render_store_policy
from seed.validate import validate_policies

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = REPO_ROOT / "data" / "cartwheel.db"
DEFAULT_POLICIES_DIR = REPO_ROOT / "data" / "policies"
DEFAULT_FACTS_PATH = REPO_ROOT / "facts.yaml"

# Every date in the world is relative to this fixed anchor, never to
# datetime.now(), so the seed is deterministic and the pinned demo orders
# ("delivered 12 days ago") never drift.
WORLD_ASOF = date(2026, 7, 1)
RNG_SEED = 20260701
ORDER_SPAN_DAYS = 548  # ~18 months

# The 20 curated core stores (name, category, return-window override in days
# or None, restocking-fee opt-in). Everything students must *know* lives here;
# the ~480-store long tail exists only at full scale.
CORE_STORES: list[tuple[str, str, int | None, bool]] = [
    ("Blue Heron Ceramics", "home_and_kitchen", None, False),
    ("Juniper Home Goods", "home_and_kitchen", 14, False),  # the Artifact A override
    ("Petal & Stem", "garden", None, False),
    ("Copperline Tools", "tools", None, False),
    ("Cascade Audio", "electronics", None, True),
    ("Bright Socket Electronics", "electronics", None, False),
    ("Northwind Books", "books", 45, False),
    ("Paper Lantern Press", "books", None, False),
    ("Trailhead Supply", "outdoors", None, False),
    ("Meridian Cycles", "outdoors", 21, False),
    ("Little Fox Toys", "toys", None, False),
    ("Wooden Whale Workshop", "toys", None, False),
    ("Saltbox Pantry", "grocery", 7, False),
    ("Golden Hour Coffee", "grocery", None, False),
    ("Second Stitch Apparel", "clothing", None, True),
    ("Harbor Knits", "clothing", None, False),
    ("Fern & Fog Skincare", "beauty", None, False),
    ("Clover Field Naturals", "beauty", None, False),
    ("Pocket Arcade", "electronics", None, False),
    ("Atlas Stationery", "office", None, False),
]

DEV_SCALE = {
    "products_per_store": 40,
    "shoppers": 500,
    "support_staff": 5,
    "orders": 10_000,
    "escalations": 150,
}

# Pinned demo orders (Module 1 outline, Artifact L). The seed must produce
# exactly these three rows so every lecture demo and screenshot reproduces.
# All three belong to the demo shopper (user 1) and store 1, which has no
# return-window override.
DEMO_SHOPPER_ID = 1
DEMO_STORE_ID = 1
PINNED_ORDERS = [
    # (order_id, total_cents, delivered days before WORLD_ASOF, note)
    (4127, 8400, 12, "inside the 30-day window and under the $100 threshold"),
    (3980, 5200, 45, "outside the 30-day window"),
    (4455, 24000, 5, "above the $100 threshold; refund queues for approval"),
]

FIRST_NAMES = [
    "Ava", "Ben", "Carmen", "Dev", "Elena", "Farid", "Grace", "Hugo",
    "Imani", "Jonas", "Kira", "Luis", "Maya", "Noor", "Otis", "Priya",
    "Quinn", "Rosa", "Sam", "Tessa", "Umar", "Vera", "Wes", "Xiomara",
    "Yuki", "Zeke",
]
LAST_NAMES = [
    "Alvarez", "Brooks", "Chen", "Diaz", "Ekwueme", "Fischer", "Garcia",
    "Hassan", "Ito", "Johnson", "Kaur", "Lindqvist", "Moreau", "Nguyen",
    "Okafor", "Park", "Quist", "Rivera", "Silva", "Tran", "Ueda", "Volkov",
    "Watts", "Xu", "Yilmaz", "Zhang",
]

PRODUCT_ADJECTIVES = [
    "Classic", "Compact", "Everyday", "Handmade", "Heavy-Duty", "Matte",
    "Midnight", "Modern", "Portable", "Rustic", "Signature", "Slim",
    "Speckled", "Sturdy", "Travel", "Vintage", "Walnut", "Woven",
]
PRODUCT_NOUNS: dict[str, list[str]] = {
    "home_and_kitchen": ["Mug", "Serving Bowl", "Cutting Board", "Vase", "Pitcher", "Dinner Plate Set", "Teapot", "Tray"],
    "garden": ["Planter", "Trowel Set", "Watering Can", "Seed Kit", "Garden Gloves", "Pruning Shears"],
    "tools": ["Hammer", "Screwdriver Set", "Tape Measure", "Level", "Utility Knife", "Socket Set"],
    "electronics": ["Headphones", "Bluetooth Speaker", "USB-C Hub", "Desk Lamp", "Webcam", "Mechanical Keyboard", "Power Bank"],
    "books": ["Field Guide", "Novel", "Poetry Collection", "Cookbook", "Atlas", "Journal"],
    "outdoors": ["Water Bottle", "Daypack", "Camp Stove", "Headlamp", "Trekking Poles", "Dry Bag"],
    "toys": ["Building Blocks", "Puzzle", "Plush Fox", "Wooden Train", "Card Game", "Marble Run"],
    "grocery": ["Coffee Beans", "Olive Oil", "Hot Sauce", "Tea Sampler", "Granola", "Jam Trio"],
    "clothing": ["Beanie", "Scarf", "Crewneck", "Rain Shell", "Wool Socks", "Tote Bag"],
    "beauty": ["Face Serum", "Hand Cream", "Bar Soap", "Lip Balm", "Bath Salts", "Shampoo Bar"],
    "office": ["Notebook", "Fountain Pen", "Desk Organizer", "Sticky Notes", "Planner", "Pencil Set"],
}


def load_facts(facts_path: Path) -> dict[str, Any]:
    with open(facts_path) as f:
        return yaml.safe_load(f)


SCHEMA = """
CREATE TABLE stores (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    return_window_days_override INTEGER,
    restocking_fee_opt_in INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('shopper', 'merchant', 'support')),
    store_id INTEGER REFERENCES stores(id)
);
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    store_id INTEGER NOT NULL REFERENCES stores(id),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    price_cents INTEGER NOT NULL
);
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    store_id INTEGER NOT NULL REFERENCES stores(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    total_cents INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('placed', 'shipped', 'delivered', 'cancelled', 'refunded')),
    ordered_at TEXT NOT NULL,
    shipped_at TEXT,
    delivered_at TEXT,
    refund_eligible INTEGER NOT NULL
);
CREATE TABLE refunds (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    amount_cents INTEGER NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('auto_approved', 'queued_for_approval')),
    created_at TEXT NOT NULL
);
CREATE TABLE escalations (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    store_id INTEGER REFERENCES stores(id),
    order_id INTEGER REFERENCES orders(id),
    summary TEXT NOT NULL,
    context TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE data_quality_cases (
    case_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    issue_type TEXT NOT NULL,
    description TEXT NOT NULL,
    expected_handling TEXT NOT NULL
);
CREATE INDEX idx_orders_user ON orders(user_id);
CREATE INDEX idx_orders_store ON orders(store_id);
CREATE INDEX idx_orders_ordered_at ON orders(ordered_at);
CREATE INDEX idx_products_store ON products(store_id);
"""


def _slugify(name: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]", "-", name.lower())).strip("-")


def _seed_stores(conn: sqlite3.Connection) -> None:
    for i, (name, category, override, restock) in enumerate(CORE_STORES, start=1):
        conn.execute(
            "INSERT INTO stores (id, name, slug, category, return_window_days_override, restocking_fee_opt_in) VALUES (?, ?, ?, ?, ?, ?)",
            (i, name, _slugify(name), category, override, int(restock)),
        )


def _seed_users(conn: sqlite3.Connection, rng: random.Random) -> None:
    # Shoppers: ids 1..N. User 1 is the demo shopper used in lecture.
    for i in range(1, DEV_SCALE["shoppers"] + 1):
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        conn.execute(
            "INSERT INTO users (id, name, role, store_id) VALUES (?, ?, 'shopper', NULL)",
            (i, name),
        )
    # Merchants: ids 9001..9020, one per core store. User 9001 is the demo merchant.
    for i in range(1, len(CORE_STORES) + 1):
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        conn.execute(
            "INSERT INTO users (id, name, role, store_id) VALUES (?, ?, 'merchant', ?)",
            (9000 + i, name, i),
        )
    # Support staff: ids 9501..9505. User 9501 is the demo support user.
    for i in range(1, DEV_SCALE["support_staff"] + 1):
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        conn.execute(
            "INSERT INTO users (id, name, role, store_id) VALUES (?, ?, 'support', NULL)",
            (9500 + i, name),
        )


def _seed_products(conn: sqlite3.Connection, rng: random.Random) -> None:
    product_id = 0
    for store_id, (store_name, category, _override, _restock) in enumerate(CORE_STORES, start=1):
        nouns = PRODUCT_NOUNS[category]
        for _ in range(DEV_SCALE["products_per_store"]):
            product_id += 1
            title = f"{rng.choice(PRODUCT_ADJECTIVES)} {rng.choice(nouns)}"
            description = (
                f"{title} from {store_name}. Placeholder dev-scale listing; "
                f"the full-scale catalog is sampled from the Amazon Reviews "
                f"2023 metadata."
            )
            price_cents = rng.randrange(500, 30000, 25)
            conn.execute(
                "INSERT INTO products (id, store_id, title, description, category, price_cents) VALUES (?, ?, ?, ?, ?, ?)",
                (product_id, store_id, title, description, category, price_cents),
            )


def _store_windows(conn: sqlite3.Connection, platform_window: int) -> dict[int, int]:
    rows = conn.execute("SELECT id, return_window_days_override FROM stores").fetchall()
    return {
        row[0]: effective_return_window_days(platform_window, row[1]) for row in rows
    }


def _seed_orders(conn: sqlite3.Connection, rng: random.Random, facts: dict[str, Any]) -> None:
    platform_window = facts["return_window_days"]
    windows = _store_windows(conn, platform_window)
    products = conn.execute(
        "SELECT id, store_id, price_cents FROM products ORDER BY id"
    ).fetchall()
    n_products = len(products)
    refund_rows: list[tuple[int, int, str, str, str]] = []

    for order_id in range(1, DEV_SCALE["orders"] + 1):
        product_id, store_id, price_cents = products[rng.randrange(n_products)]
        user_id = rng.randrange(1, DEV_SCALE["shoppers"] + 1)
        quantity = 1 if rng.random() < 0.8 else 2
        total_cents = price_cents * quantity
        ordered_at = WORLD_ASOF - timedelta(days=rng.randrange(0, ORDER_SPAN_DAYS))

        shipped_at: date | None = None
        delivered_at: date | None = None
        if rng.random() < 0.04:
            status = "cancelled"
        else:
            ship_date = ordered_at + timedelta(days=rng.randrange(1, 4))
            deliver_date = ship_date + timedelta(days=rng.randrange(2, 8))
            if ship_date > WORLD_ASOF:
                status = "placed"
            elif deliver_date > WORLD_ASOF:
                status = "shipped"
                shipped_at = ship_date
            else:
                status = "delivered"
                shipped_at = ship_date
                delivered_at = deliver_date
                # Some delivered orders were refunded later.
                if rng.random() < 0.06:
                    status = "refunded"
                    refund_delay = rng.randrange(1, windows[store_id] + 1)
                    refund_date = min(deliver_date + timedelta(days=refund_delay), WORLD_ASOF)
                    refund_status = (
                        "queued_for_approval"
                        if total_cents > facts["refund_auto_approve_threshold_usd"] * 100
                        else "auto_approved"
                    )
                    refund_rows.append(
                        (
                            order_id,
                            total_cents,
                            "seeded historical refund",
                            refund_status,
                            refund_date.isoformat(),
                        )
                    )

        eligible = is_refund_eligible(
            status=status,
            delivered_at=delivered_at,
            as_of=WORLD_ASOF,
            return_window_days=windows[store_id],
        )
        conn.execute(
            "INSERT INTO orders (id, user_id, store_id, product_id, quantity, total_cents, status, ordered_at, shipped_at, delivered_at, refund_eligible) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                order_id,
                user_id,
                store_id,
                product_id,
                quantity,
                total_cents,
                status,
                ordered_at.isoformat(),
                shipped_at.isoformat() if shipped_at else None,
                delivered_at.isoformat() if delivered_at else None,
                int(eligible),
            ),
        )

    for order_id, amount_cents, reason, refund_status, created_at in refund_rows:
        conn.execute(
            "INSERT INTO refunds (order_id, amount_cents, reason, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (order_id, amount_cents, reason, refund_status, created_at),
        )


def _pin_demo_orders(conn: sqlite3.Connection, facts: dict[str, Any]) -> None:
    """Overwrite the three Artifact L demo orders with exact values."""
    platform_window = facts["return_window_days"]
    store_override = conn.execute(
        "SELECT return_window_days_override FROM stores WHERE id = ?", (DEMO_STORE_ID,)
    ).fetchone()[0]
    assert store_override is None, "the demo store must use the platform window"
    window = effective_return_window_days(platform_window, store_override)
    product_id = conn.execute(
        "SELECT id FROM products WHERE store_id = ? ORDER BY id LIMIT 1", (DEMO_STORE_ID,)
    ).fetchone()[0]

    for order_id, total_cents, delivered_days_ago, _note in PINNED_ORDERS:
        delivered_at = WORLD_ASOF - timedelta(days=delivered_days_ago)
        shipped_at = delivered_at - timedelta(days=3)
        ordered_at = shipped_at - timedelta(days=2)
        eligible = is_refund_eligible(
            status="delivered",
            delivered_at=delivered_at,
            as_of=WORLD_ASOF,
            return_window_days=window,
        )
        conn.execute("DELETE FROM refunds WHERE order_id = ?", (order_id,))
        conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
        conn.execute(
            "INSERT INTO orders (id, user_id, store_id, product_id, quantity, total_cents, status, ordered_at, shipped_at, delivered_at, refund_eligible) "
            "VALUES (?, ?, ?, ?, 1, ?, 'delivered', ?, ?, ?, ?)",
            (
                order_id,
                DEMO_SHOPPER_ID,
                DEMO_STORE_ID,
                product_id,
                total_cents,
                ordered_at.isoformat(),
                shipped_at.isoformat(),
                delivered_at.isoformat(),
                int(eligible),
            ),
        )


def _seed_data_quality_cases(conn: sqlite3.Connection) -> None:
    """Insert deterministic, documented data defects for evaluation scenarios.

    The affected records are outside the three lecture orders. Each mutation
    has a manifest row so scenario generation can target the defect without
    treating corrupted state as unquestioned ground truth.
    """
    first_title = conn.execute("SELECT title FROM products WHERE id = 1").fetchone()[0]
    conn.execute("UPDATE products SET title = ? WHERE id = 2", (first_title,))
    conn.execute("UPDATE products SET title = '' WHERE id = 3")
    conn.execute("UPDATE products SET price_cents = -500 WHERE id = 4")

    conn.execute(
        "UPDATE orders SET status = 'delivered', shipped_at = '2026-06-25', "
        "delivered_at = '2026-06-23', refund_eligible = 0 WHERE id = 8001"
    )
    conn.execute(
        "UPDATE orders SET status = 'delivered', shipped_at = '2026-06-20', "
        "delivered_at = NULL, refund_eligible = 0 WHERE id = 8002"
    )
    product_store = conn.execute(
        "SELECT p.store_id FROM orders o JOIN products p ON p.id = o.product_id "
        "WHERE o.id = 8003"
    ).fetchone()[0]
    conflicting_store = 1 if product_store != 1 else 2
    conn.execute("UPDATE orders SET store_id = ? WHERE id = 8003", (conflicting_store,))

    cases = [
        (
            "dq-product-duplicate-title",
            "product",
            2,
            "duplicate_title",
            "Products 1 and 2 have the same title within one store.",
            "Use stable identifiers or ask for clarification before claiming a unique match.",
        ),
        (
            "dq-product-missing-title",
            "product",
            3,
            "missing_title",
            "The product title is an empty string.",
            "Do not invent a product name.",
        ),
        (
            "dq-product-invalid-price",
            "product",
            4,
            "invalid_price",
            "The product price is negative.",
            "Do not present the negative price as a valid offer.",
        ),
        (
            "dq-order-reversed-dates",
            "order",
            8001,
            "reversed_chronology",
            "The recorded shipment date occurs after the delivery date.",
            "Identify the inconsistent chronology and escalate instead of asserting a timeline.",
        ),
        (
            "dq-order-missing-delivery-date",
            "order",
            8002,
            "missing_required_date",
            "The order status is delivered but the delivery date is missing.",
            "Do not compute a return deadline from a missing delivery date.",
        ),
        (
            "dq-order-store-mismatch",
            "order",
            8003,
            "store_mismatch",
            "The order store differs from the store owning the referenced product.",
            "Preserve authorization and escalate the inconsistent record.",
        ),
    ]
    conn.executemany(
        "INSERT INTO data_quality_cases "
        "(case_id, entity_type, entity_id, issue_type, description, expected_handling) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        cases,
    )


def _seed_escalations(conn: sqlite3.Connection, rng: random.Random) -> None:
    summaries = [
        "refund above approval threshold",
        "item arrived damaged",
        "wrong item shipped",
        "chargeback question",
        "account access question",
    ]
    delivered_orders = conn.execute(
        "SELECT id, user_id, store_id FROM orders WHERE status IN ('delivered', 'refunded') ORDER BY id"
    ).fetchall()
    for _ in range(DEV_SCALE["escalations"]):
        order_id, user_id, store_id = delivered_orders[rng.randrange(len(delivered_orders))]
        created_at = WORLD_ASOF - timedelta(days=rng.randrange(0, ORDER_SPAN_DAYS))
        conn.execute(
            "INSERT INTO escalations (user_id, store_id, order_id, summary, context, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                user_id,
                store_id,
                order_id,
                rng.choice(summaries),
                json.dumps({"order_id": order_id, "seeded": True}),
                created_at.isoformat(),
            ),
        )


def _write_policies(policies_dir: Path, facts: dict[str, Any]) -> int:
    policies_dir.mkdir(parents=True, exist_ok=True)
    for old in policies_dir.glob("*.md"):
        old.unlink()
    docs = render_platform_policies(facts)
    for store_id, (name, _category, override, restock) in enumerate(CORE_STORES, start=1):
        doc = render_store_policy(facts, name, _slugify(name), override, restock)
        if doc is not None:
            docs.append(doc)
        del store_id
    for doc in docs:
        (policies_dir / f"{doc.policy_id}.md").write_text(doc.to_markdown())
    return len(docs)


def generate_world(
    *,
    scale: str = "dev",
    db_path: Path | None = None,
    policies_dir: Path | None = None,
    facts_path: Path | None = None,
    quiet: bool = True,
) -> None:
    """Generate the Cartwheel world: SQLite database plus policy corpus."""
    if scale == "full":
        raise NotImplementedError(
            "The 'full' scale (~500 stores, ~50K products sampled from the "
            "Amazon Reviews 2023 metadata on Hugging Face, ~100K orders, "
            "~600-doc corpus) is not implemented in the starter repo. It "
            "needs network access for the Hugging Face pull and ships with "
            "the lecture environment. Use --scale dev, which is the default "
            "and is all the homework needs."
        )
    if scale != "dev":
        raise ValueError(f"unknown scale: {scale!r} (expected 'dev' or 'full')")

    db_path = db_path or DEFAULT_DB_PATH
    policies_dir = policies_dir or DEFAULT_POLICIES_DIR
    facts_path = facts_path or DEFAULT_FACTS_PATH
    facts = load_facts(facts_path)
    rng = random.Random(RNG_SEED)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        _seed_stores(conn)
        _seed_users(conn, rng)
        _seed_products(conn, rng)
        _seed_orders(conn, rng, facts)
        _pin_demo_orders(conn, facts)
        _seed_data_quality_cases(conn)
        _seed_escalations(conn, rng)
        for key, value in [
            ("platform_name", facts["platform_name"]),
            ("world_asof", WORLD_ASOF.isoformat()),
            ("scale", scale),
            ("rng_seed", str(RNG_SEED)),
        ]:
            conn.execute("INSERT INTO meta (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
    finally:
        conn.close()

    n_docs = _write_policies(policies_dir, facts)
    problems = validate_policies(policies_dir, facts)
    if problems:
        raise RuntimeError(
            "policy validation failed:\n" + "\n".join(f"- {p}" for p in problems)
        )
    if not quiet:
        print(f"Seeded {db_path} at scale '{scale}' (as of {WORLD_ASOF}).")
        print(f"Wrote and validated {n_docs} policy docs in {policies_dir}.")
        print("Pinned demo orders: #4127, #3980, #4455 (owner: user 1, store 1).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the Cartwheel world.")
    parser.add_argument("--scale", choices=["dev", "full"], default="dev")
    parser.add_argument("--db", type=Path, default=None, help="output SQLite path")
    parser.add_argument("--policies", type=Path, default=None, help="output policies dir")
    args = parser.parse_args()
    generate_world(
        scale=args.scale, db_path=args.db, policies_dir=args.policies, quiet=False
    )


if __name__ == "__main__":
    main()
