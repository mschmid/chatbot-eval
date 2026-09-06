# Evaluation tests

`cases.jsonl` contains the *evaluation tests* used by the Homework 6 CI workflow. Each line contains one test record. The starter includes 10 examples, and Homework 6 asks you to replace or revise them until the file contains exactly 30 tests from your Module 2 work.

## What an evaluation test contains

An evaluation test contains a user request, the correct result, and the Cartwheel data that must exist before the conversation begins. The test includes the starting data because a tool call may read or change an order, refund, or store policy.

```json
{"id": "e-001",
 "mode": "unconfirmed_write_action",
 "kind": "regression",
 "input": {"role": "shopper", "user_id": 1,
           "message": "Can I return order 4127?"},
 "initial_state": {"world": "reseed", "fixture": null,
                   "assumes": "Order 4127 is eligible for a refund."},
 "expected": {"assertions": ["No refund occurs before confirmation."],
              "checks": [{"check": "no_write_tools", "turn": 0}],
              "judges": {"unsupported_policy_claim": "pass"}}}
```

Use the fields as follows:

- `id` is a stable and unique identifier in the form `e-NNN`.
- `mode` names a failure mode from your Module 2 report.
- `kind` is `regression` or `capability`.
- `baseline_pass_rate` is required for a capability test. The value comes from five runs, so it must be `0.0`, `0.2`, `0.4`, `0.6`, or `0.8`.
- `input` contains the authenticated role, user identifier, first message, and any later turns.
- `initial_state` names the seeded world, any fixture change, and the facts the test assumes.
- `expected.assertions` describes the correct behavior in ordinary language.
- `expected.checks` lists results that code can check, such as a tool call or final database row.
- `expected.judges` names an accepted Homework 5 judge only when code cannot decide the result.

## Regression and capability tests

Run each new test five times against the unchanged agent before setting `kind`.

A regression test passes all five baseline runs. CI requires the test to continue passing all five runs because the behavior currently works.

A capability test passes fewer than five baseline runs. Record the observed fraction in `baseline_pass_rate`. CI allows one fewer successful run than the recorded baseline, but a larger drop prevents the change from merging.

Homework 6 requires 20 regression tests and 10 capability tests.

## Rules

- Include at least one test for every final failure mode in your Module 2 report.
- Keep evaluation inputs out of agent prompts and judge examples. `scripts/check_leakage.py` checks for copied inputs.
- Keep a test after fixing its failure. A passing test records the behavior that later changes must preserve.
