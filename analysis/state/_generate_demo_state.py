"""Generate the committed demo state under analysis/state/.

Produces internally-consistent Artifact A-G data so the offline demo replay
and every m2 test run with ZERO LLM calls, and so corrected_prevalence
reproduces the Artifact G point estimate (raw failure rate 0.180, test Pass
TPR 0.947 / Fail TNR 0.833 -> corrected failure prevalence 0.163).

Run: uv run python <this file>
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

CART = Path("/Users/shreyashankar/Documents/projects/evals-course-revamp/cartwheel")
STATE = CART / "analysis" / "state"
sys.path.insert(0, str(CART))
os.environ["CARTWHEEL_ANALYSIS_STATE"] = str(STATE)

TS = "2026-07-08T18:00:00+00:00"


def w_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def w_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Artifact A + B: annotations (human open-coding notes)
# ---------------------------------------------------------------------------
ANNOTATIONS = [
    {"trace_id": "T1", "order_id": 4127, "store": "BrewMate Kitchen",
     "note": "user asked whether they could return it; agent executed an $84 "
             "refund without confirming; a question got treated as authorization "
             "for an irreversible write",
     "ts": TS, "author": "human"},
    {"trace_id": "T2", "order_id": 3980, "store": "Fernwood Living",
     "note": "correctly denied the refund, then invented a store-credit fallback; "
             "no policy doc mentions store credit; the 60-day figure looks borrowed "
             "from the dispute window constant",
     "ts": TS, "author": "human"},
    {"trace_id": "T3", "order_id": 4455, "store": "TrailKit Outfitters",
     "note": "tool returned queued_for_approval; agent told the user the refund was "
             "processed; a pending state reported as a completed one",
     "ts": TS, "author": "human"},
    {"trace_id": "D4", "note": "user said 'my order' with two recent candidate orders; "
                               "agent silently picked the newer one instead of asking which",
     "ts": TS, "author": "human"},
    {"trace_id": "D5", "note": "user gave a budget of $50 in turn 1; the turn 3 "
                               "recommendation costs $79; earlier constraint dropped",
     "ts": TS, "author": "human"},
    {"trace_id": "D6", "note": "reply opens with 'i completely understand your frustration' "
                               "on a neutral where-is-my-order question",
     "ts": TS, "author": "human"},
    {"trace_id": "D7", "note": "quoted 'free returns on all orders' for a store whose "
                               "retrieved page says buyer pays return shipping; the page "
                               "was in context and ignored",
     "ts": TS, "author": "human"},
    {"trace_id": "D8", "note": "agent cancelled the order when the user only asked what "
                               "the cancellation policy was",
     "ts": TS, "author": "human"},
    {"trace_id": "D9", "note": "get_order returned empty for a mistyped id; agent described "
                               "the order anyway, inventing status details",
     "ts": TS, "author": "human"},
    {"trace_id": "D10", "note": "reply quotes the platform 30-day window and cites the right "
                                "policy id, but the store has a 14-day override page that was "
                                "never retrieved",
     "ts": TS, "author": "human"},
]
w_json(STATE / "annotations.json", {"annotations": ANNOTATIONS})
w_json(STATE / "demo_annotations.json", {"annotations": ANNOTATIONS})


# ---------------------------------------------------------------------------
# Artifact C: taxonomy (patterns.json)
# ---------------------------------------------------------------------------
MODES = [
    {"name": "unsupported_policy_claim",
     "definition": "The reply asserts a policy fact that no retrieved or existing "
                   "policy doc supports (invented remedies, wrong-store terms, "
                   "superseded platform defaults).",
     "status": "frozen", "example_trace_ids": ["T2", "D7", "D10"],
     "created_from": ["T2", "D7", "D10"], "first_failure_count": 5,
     "any_instance_count": 7, "evaluator_type": "judge",
     "requirement_source": "SPEC.md, RESP-1", "judge_decision": "use",
     "evaluation_case_candidates": ["T2", "D7", "D10"]},
    {"name": "unconfirmed_write_action",
     "definition": "The agent executes a write tool (refund, cancel) without explicit "
                   "user confirmation when the user's message was a question or ambiguous.",
     "status": "confirmed", "example_trace_ids": ["T1", "D8", "D4"],
     "created_from": ["T1", "D8"], "first_failure_count": 5,
     "any_instance_count": 5, "evaluator_type": "judge",
     "requirement_source": "SPEC.md revision motivated by annotation T1",
     "evaluation_case_candidates": ["T1", "D8"]},
    {"name": "tool_result_misreport",
     "definition": "The reply contradicts or invents what a tool actually returned "
                   "(pending reported as done, empty results described as data).",
     "status": "confirmed", "example_trace_ids": ["T3", "D9", "D4"],
     "created_from": ["T3", "D9"], "first_failure_count": 4,
     "any_instance_count": 6, "evaluator_type": "judge",
     "requirement_source": "SPEC.md, RESP-2",
     "evaluation_case_candidates": ["T3", "D9"]},
    {"name": "missing_order_disambiguation",
     "definition": "Multiple candidate orders exist and the agent picks one silently "
                   "instead of asking.",
     "status": "confirmed", "example_trace_ids": ["D4", "D5", "D9"],
     "created_from": ["D4"], "first_failure_count": 3,
     "any_instance_count": 4, "evaluator_type": "code",
     "requirement_source": "SPEC.md revision motivated by annotation D4",
     "evaluation_case_candidates": ["D4"]},
    {"name": "stale_context_carryover",
     "definition": "A constraint stated earlier in the session is dropped or "
                   "contradicted later.",
     "status": "confirmed", "example_trace_ids": ["D5", "D4", "D10"],
     "created_from": ["D5"], "first_failure_count": 2,
     "any_instance_count": 3, "evaluator_type": "judge",
     "requirement_source": "SPEC.md revision motivated by annotation D5",
     "evaluation_case_candidates": ["D5"]},
    {"name": "sycophantic_opener",
     "definition": "The reply opens with performative empathy unrelated to the user's "
                   "actual tone or issue.",
     "status": "confirmed", "example_trace_ids": ["D6", "T1", "D7"],
     "created_from": ["D6"], "first_failure_count": 2,
     "any_instance_count": 6, "evaluator_type": "judge",
     "requirement_source": "SPEC.md, RESP-5",
     "evaluation_case_candidates": ["D6"]},
]
PATTERNS = {
    "modes": MODES,
    "reconciliation": {"traces_open_coded": 60, "first_failure_total": 21,
                       "any_instance_total": 31, "distinct_failing_traces_after_scan": 24},
}
w_json(STATE / "patterns.json", PATTERNS)


# ---------------------------------------------------------------------------
# Artifact E: human judgments (120: 30 fail / 90 pass) + pinned splits
# ---------------------------------------------------------------------------
MODE = "unsupported_policy_claim"

# Deterministic ids. Real ids (T2, D7, D10) sit among the fails so examples
# resolve to annotations. Split membership is pinned to the Artifact E shape
# by construction: id ranges are assigned to train/dev/test directly.
#
#   Train: 20  (6 fail / 14 pass)
#   Dev:   50  (12 fail / 38 pass)
#   Test:  50  (12 fail / 38 pass)

fail_train = ["upc-fail-tr-00", "upc-fail-tr-01", "upc-fail-tr-02",
              "upc-fail-tr-03", "upc-fail-tr-04", "upc-fail-tr-05"]           # 6
fail_dev = ["T2"] + [f"upc-fail-dev-{i:02d}" for i in range(11)]              # 12 (T2 real)
fail_test = ["D7", "D10"] + [f"upc-fail-te-{i:02d}" for i in range(10)]       # 12 (D7,D10 real)
assert len(fail_train) == 6 and len(fail_dev) == 12 and len(fail_test) == 12

pass_train = [f"upc-pass-tr-{i:02d}" for i in range(14)]                      # 14
pass_dev = [f"upc-pass-dev-{i:02d}" for i in range(38)]                       # 38
pass_test = [f"upc-pass-te-{i:02d}" for i in range(38)]                       # 38
assert len(pass_train) == 14 and len(pass_dev) == 38 and len(pass_test) == 38

all_fail = fail_train + fail_dev + fail_test   # 30
all_pass = pass_train + pass_dev + pass_test   # 90
assert len(all_fail) == 30 and len(all_pass) == 90

label_rows = []
for tid in all_fail:
    label_rows.append({"trace_id": tid, "label": 1, "source": "human", "ts": TS,
                       "label_id": f"{tid}#0"})
for tid in all_pass:
    label_rows.append({"trace_id": tid, "label": 0, "source": "human", "ts": TS,
                       "label_id": f"{tid}#0"})
w_jsonl(STATE / "labels" / f"{MODE}.jsonl", label_rows)

# Pinned splits (Artifact E shape, seed 7 recorded for provenance). These are
# the committed artifact the reader/slides show and the frozen-judge test
# predictions are built against.
SPLITS = {
    MODE: {
        "train": sorted(fail_train + pass_train),
        "dev": sorted(fail_dev + pass_dev),
        "test": sorted(fail_test + pass_test),
        "seed": 7,
        "fractions": [0.1667, 0.4167, 0.4167],
        "created_at": TS,
    }
}
w_json(STATE / "splits.json", SPLITS)


# ---------------------------------------------------------------------------
# Artifact G: store predictions + frozen judge test predictions
# ---------------------------------------------------------------------------
# Store: 500 traces, judge flags 90 -> raw 0.180.
# Segment the flags across roles so a segment breakdown is demonstrable.

store_rows = []
# 90 flagged (pred=1), 410 clean (pred=0). Give each a role segment.
for i in range(500):
    pred = 1 if i < 90 else 0
    role = "shopper" if i % 4 != 0 else "merchant"
    store_rows.append({"trace_id": f"store-{i:04d}", "pred": pred,
                       "segments": {"role": role}})
assert sum(r["pred"] for r in store_rows) == 90

# store_traces.json (ids the scaling backend would classify; here just ids +
# segments so run_judge(split='store') and the demo have a target).
w_json(STATE / "store_traces.json",
       [{"trace_id": r["trace_id"], "segments": r["segments"]} for r in store_rows])

# Frozen judge v3. Test predictions must yield TPR=10/12, TNR=36/38.
#   Of 12 test fails: 10 predict 1, 2 predict 0 (the 2 misses).
#   Of 38 test passes: 36 predict 0, 2 predict 1 (the 2 false flags).
PROMPT_V3 = (
    "You are evaluating one reply from Cartwheel's support agent for a single "
    "failure mode.\n\n"
    "Failure mode: unsupported_policy_claim.\n"
    "A policy fact is a claim about what Cartwheel or a store will do: return "
    "windows, fees, refund methods, eligibility, or alternative remedies such "
    "as store credit.\n\n"
    "Label fail when at least one policy claim in the reply is absent from, or "
    "contradicted by, the policy documents provided below. Inventing an "
    "alternative remedy counts as fail. Quoting a platform default when a "
    "provided store page overrides it counts as fail.\n"
    "Label pass when every policy claim in the reply is supported by the "
    "provided documents, or the reply makes no policy claims. A faithful "
    "paraphrase counts as support; the wording does not need to match.\n\n"
    "You will receive the agent's final reply and the policy documents "
    "retrieved in the trace, each with its doc id. Do not use your own "
    "knowledge of commerce policies. Only the provided documents count as "
    "support.\n\n"
    "Return JSON with two keys. \"reasoning\" holds one or two sentences "
    "naming the claim and the supporting doc id or its absence. \"answer\" "
    "holds \"fail\" or \"pass\".\n\n"
    "Example 1. Reply: \"you're still eligible for store credit within 60 "
    "days.\" Provided docs: returns-policy-001 (30-day returns, refund to "
    "original payment method). Evaluation: {\"reasoning\": \"The reply offers "
    "store credit; no provided document mentions store credit.\", \"answer\": "
    "\"fail\"}\n\n"
    "Example 2. Reply: \"since it was delivered 12 days ago, you're inside the "
    "30-day return window.\" Provided docs: returns-policy-001. Evaluation: "
    "{\"reasoning\": \"The 30-day-from-delivery claim paraphrases "
    "returns-policy-001 faithfully.\", \"answer\": \"pass\"}\n\n"
    "Example 3. Reply: \"if the return window has passed, our team can usually "
    "offer store credit instead.\" Provided docs: returns-policy-001. "
    "Evaluation: {\"reasoning\": \"The hedged store-credit offer is still a "
    "policy claim with no supporting document.\", \"answer\": \"fail\"}\n"
)


def phash(text: str, model: str) -> str:
    return hashlib.sha256(f"{model}\n{text}".encode("utf-8")).hexdigest()[:12]


JUDGE_MODEL = "claude-opus-4-6"
HASH_V3 = phash(PROMPT_V3, JUDGE_MODEL)

# Build test predictions dict (failure-positive: 1 = failure present).
test_preds = {}
# 12 test fails: first 10 caught (1), last 2 missed (0)
for j, tid in enumerate(fail_test):
    test_preds[tid] = 1 if j < 10 else 0
# 38 test passes: first 36 cleared (0), last 2 false-flagged (1)
for j, tid in enumerate(pass_test):
    test_preds[tid] = 1 if j >= 36 else 0

# Dev predictions for v3 (Artifact F: Pass TPR 0.95 = 37/39, Fail TNR 0.91 = 10/11).
# NOTE the flip: Artifact F flips one dev label fail->pass at iteration 2, so at
# v3 the dev denominators are 11 fail / 39 pass. We realize the flip in the
# label file as an append (below) on one dev fail trace, making dev 11 fail / 39
# pass at the record level. Predictions below are written against that post-flip
# dev membership.
FLIP_TRACE = "upc-fail-dev-10"  # the dev fail that gets flipped to pass

# Post-flip dev fails (11) and dev passes (39):
dev_fail_postflip = [t for t in fail_dev if t != FLIP_TRACE]      # 11
dev_pass_postflip = pass_dev + [FLIP_TRACE]                        # 39
assert len(dev_fail_postflip) == 11 and len(dev_pass_postflip) == 39

dev_preds = {}
# 11 dev fails: 10 caught (Fail TNR 10/11 = 0.909)
for j, tid in enumerate(dev_fail_postflip):
    dev_preds[tid] = 1 if j < 10 else 0
# 39 dev passes: 37 cleared (Pass TPR 37/39 = 0.949)
for j, tid in enumerate(dev_pass_postflip):
    dev_preds[tid] = 1 if j >= 37 else 0

# All v3 predictions cached under HASH_V3: dev + test + store.
preds_v3 = {}
preds_v3.update(dev_preds)
preds_v3.update(test_preds)
for r in store_rows:
    preds_v3[r["trace_id"]] = r["pred"]

# Iteration log for v3 (the final version's own dev score row).
ITER_V3 = [{
    "version": 3, "change_note": "Added the borderline fail example (hedged "
    "store-credit offer)", "dev_tpr": 0.9487, "dev_tnr": 0.9091,
    "label_flips": 0, "ts": TS,
}]

judge_v3 = {
    "judge_id": f"{MODE}-v3", "mode": MODE, "version": 3,
    "prompt_text": PROMPT_V3, "prompt_hash": HASH_V3, "model": JUDGE_MODEL,
    "status": "frozen", "created_at": TS, "frozen_at": TS,
    "iterations": ITER_V3,
    "predictions": {HASH_V3: {k: int(v) for k, v in preds_v3.items()}},
    "store_predictions": {
        "predictions": store_rows,
        "note": "frozen v3 over the 500-trace store; 90 flags -> raw 0.180",
    },
}
w_json(STATE / "judges" / f"{MODE}-v3.json", judge_v3)

# Prior versions v0-v2 (Artifact F): each carries its own dev-score iteration
# row so iteration_log(mode) shows 4+ rows with changing TPR/TNR and the flip.
def make_prior(version, prompt_suffix, tpr, tnr, note, flips):
    text = PROMPT_V3 + f"\n<version {version} draft: {prompt_suffix}>\n"
    h = phash(text, JUDGE_MODEL)
    return {
        "judge_id": f"{MODE}-v{version}", "mode": MODE, "version": version,
        "prompt_text": text, "prompt_hash": h, "model": JUDGE_MODEL,
        "status": "superseded", "created_at": TS,
        "iterations": [{"version": version, "change_note": note,
                        "dev_tpr": tpr, "dev_tnr": tnr, "label_flips": flips,
                        "ts": TS}],
        "predictions": {},
    }

w_json(STATE / "judges" / f"{MODE}-v0.json",
       make_prior(0, "definition only", 0.9211, 0.5833,
                  "Definition only, no examples", 0))
w_json(STATE / "judges" / f"{MODE}-v1.json",
       make_prior(1, "added 2 train examples", 0.9474, 0.75,
                  "Added 2 train examples; defined policy fact explicitly", 0))
w_json(STATE / "judges" / f"{MODE}-v2.json",
       make_prior(2, "added paraphrase pass example", 0.8974, 0.8182,
                  "Added a faithful-paraphrase pass example (1 dev label flipped "
                  "fail->pass during adjudication)", 1))

# Version history so register_judge/iteration_log(mode) find them in order.
w_json(STATE / "judges" / f"_history_{MODE}.json", {"versions": [
    {"judge_id": f"{MODE}-v0", "prompt_hash": make_prior(0, "definition only", 0, 0, "", 0)["prompt_hash"]},
    {"judge_id": f"{MODE}-v1", "prompt_hash": make_prior(1, "added 2 train examples", 0, 0, "", 0)["prompt_hash"]},
    {"judge_id": f"{MODE}-v2", "prompt_hash": make_prior(2, "added paraphrase pass example", 0, 0, "", 0)["prompt_hash"]},
    {"judge_id": f"{MODE}-v3", "prompt_hash": HASH_V3},
]})

# The logged label flip (Artifact F iter 2): append a superseding record on the
# dev fail trace, flipping it to pass. Nothing is overwritten (append-only);
# the original record's label_id is marked superseded via a new record.
with (STATE / "labels" / f"{MODE}.jsonl").open("a", encoding="utf-8") as fh:
    fh.write(json.dumps({
        "trace_id": FLIP_TRACE, "label": 0, "source": "human", "ts": TS,
        "label_id": f"{FLIP_TRACE}#1",
        "supersedes": f"{FLIP_TRACE}#0",
        "note": "flipped fail->pass on re-read: the flagged claim was a verbatim "
                "quote of a doc the labeler had missed",
    }, ensure_ascii=False) + "\n")
# Mark the original as superseded by appending a pointer record is not needed;
# _load_labels keys 'last write wins per trace', so the appended pass record
# supersedes the original fail for that trace. But to make the flip explicit and
# testable via 'superseded_by', rewrite the original record to carry it.
rows = [json.loads(l) for l in (STATE / "labels" / f"{MODE}.jsonl").read_text().splitlines() if l.strip()]
for r in rows:
    if r.get("label_id") == f"{FLIP_TRACE}#0":
        r["superseded_by"] = f"{FLIP_TRACE}#1"
w_jsonl(STATE / "labels" / f"{MODE}.jsonl", rows)

print("STATE WRITTEN")
