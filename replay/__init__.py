"""Sandbox replay harness (Module 3).

`rollout.py` runs one evaluation case against the real agent on a fresh world
(instructor-provided). `harness.py` is the fan-out: replay one failing input
~100 times in a reset sandbox and characterize the failure distribution
(the two functions marked hw6 are yours to implement).
"""

from replay.harness import ReplayInfraError, replay_case, summarize_rollouts

__all__ = ["ReplayInfraError", "replay_case", "summarize_rollouts"]
