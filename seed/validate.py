"""Extraction check: policy-doc claims vs facts.yaml.

Instructor-provided. This is the dev-scale version of the validation stage in
the six-stage corpus pipeline (Module 1 outline, Lecture 3.1). Each doc's
front matter declares which facts it uses and what value it claims for each.
The check enforces two things:

  1. Every claimed fact value equals the value in facts.yaml.
  2. Every number that appears in the doc body is accounted for, either by a
     claimed fact or by the doc's `extra_numbers` list (used for values that
     come from seed data, like a store's override window).

At full scale the same check runs over the model-drafted corpus, which is the
point: the LLM writes prose, code computes facts, and this file is where the
two meet.

Usage:
    uv run python -m seed.validate [--policies PATH]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")


def parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    """Split a policy doc into (front matter dict, body)."""
    if not text.startswith("---"):
        raise ValueError("policy doc has no front matter")
    _, raw, body = text.split("---", 2)
    return yaml.safe_load(raw), body


def _numeric_values(value: Any) -> list[float]:
    """Flatten a claimed fact value into the numbers it contains."""
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, (list, tuple)):
        out: list[float] = []
        for item in value:
            out.extend(_numeric_values(item))
        return out
    return []


def validate_doc(path: Path, facts: dict[str, Any]) -> list[str]:
    """Return a list of problems for one doc (empty when the doc is clean)."""
    problems: list[str] = []
    front, body = parse_front_matter(path.read_text())
    facts_used: dict[str, Any] = front.get("facts_used") or {}
    extra_numbers = front.get("extra_numbers") or []

    allowed: set[float] = set(_numeric_values(extra_numbers))
    for key, claimed in facts_used.items():
        if key not in facts:
            problems.append(f"{path.name}: unknown facts key {key!r}")
            continue
        if facts[key] != claimed:
            problems.append(
                f"{path.name}: claims {key}={claimed!r} but facts.yaml says {facts[key]!r}"
            )
        allowed.update(_numeric_values(claimed))

    for match in NUMBER_RE.finditer(body):
        number = float(match.group())
        if number not in allowed:
            problems.append(
                f"{path.name}: body contains {match.group()} which no declared fact accounts for"
            )
    return problems


def validate_policies(policies_dir: Path, facts: dict[str, Any]) -> list[str]:
    """Validate every doc in the corpus. Returns all problems found."""
    problems: list[str] = []
    docs = sorted(policies_dir.glob("*.md"))
    if not docs:
        return [f"no policy docs found in {policies_dir}"]
    for path in docs:
        problems.extend(validate_doc(path, facts))
    return problems


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Validate policy docs against facts.yaml.")
    parser.add_argument("--policies", type=Path, default=repo_root / "data" / "policies")
    parser.add_argument("--facts", type=Path, default=repo_root / "facts.yaml")
    args = parser.parse_args()
    with open(args.facts) as f:
        facts = yaml.safe_load(f)
    problems = validate_policies(args.policies, facts)
    if problems:
        print("Validation failed:")
        for problem in problems:
            print(f"- {problem}")
        sys.exit(1)
    print(f"All policy docs in {args.policies} check out against {args.facts}.")


if __name__ == "__main__":
    main()
