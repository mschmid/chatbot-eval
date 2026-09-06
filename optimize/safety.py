"""Run the Homework 8 safety tests and save a machine readable result."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from optimize.workflow import RESULTS_DIR, current_commit, now_utc, write_json


def main() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--runxfail", "tests/test_adversarial.py", "-q"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )
    record = {
        "created_at": now_utc(),
        "git_commit": current_commit(),
        "passed": result.returncode == 0,
        "command": "python -m pytest --runxfail tests/test_adversarial.py -q",
        "output": (result.stdout + result.stderr)[-8000:],
    }
    path = RESULTS_DIR / "safety-latest.json"
    write_json(path, record)
    print(json.dumps({"passed": record["passed"], "result": str(path)}, indent=2))
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
