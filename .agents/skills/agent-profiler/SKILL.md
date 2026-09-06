---
name: agent-profiler
description: Review Cartwheel model call costs and propose measured cost reductions. Use for Homework 10 after profile/results/calls.csv and profile/results/profile.json have been created.
---

# Agent cost review

Read `homework/module-5/hw10.md`, `profile/results/calls.csv`, `profile/results/profile.json`, and `profile/models.json`. Stop and name the missing file when an input is absent.

Use `rg` to find the Python file and line that starts each model call named in `calls.csv`. Check the surrounding prompt, tools, retrieval, conversation history, and model choice. Do not infer a call site from its name when the code does not support the match.

Write `reports/optimization_plan.md`. Separate suggestions for customer conversation cost from suggestions for judge cost, and do not add the two costs into one total. Order suggestions by estimated saving within each category, and include the following fields for every suggestion:

- `Cost category`: `customer_conversation` or `judge`.
- `Code`: the file and line affected.
- `Measured cost`: the call count, tokens, or cost from the saved report.
- `Suggested change`: one specific change.
- `Estimated saving`: the arithmetic from the measured cost to the estimate.
- `Assumptions`: every value not measured in the saved report.
- `Risk`: the agent behavior that could get worse.
- `Check`: the exact development and safety commands that would test the change.
- `Decision`: leave `accept` or `reject` for the student to complete.

Do not claim a saving when the trace report lacks the required measurement. Mark the estimate `unknown`, and state which trace field or experiment would provide the missing value.

Treat a change as lower risk when a code check covers the affected behavior, and treat it as higher risk when no saved check or Homework 5 judge covers the behavior. Never suggest weakening permissions, confirmation before data changes, human approval, or the Homework 8 safety protections.

Do not edit the agent, graders, tests, or saved results. The skill produces suggestions only.
