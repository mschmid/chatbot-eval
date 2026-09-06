# Review Loop

This is the live interactive phase of the first half (discovery). The review app is running and the human is open-coding traces. You are an active participant, not a bystander. You watch the annotations file, organize the human's notes into a taxonomy in real time, scan the whole store for more instances of each named mode, and propose new traces to read.

Read [SKILL.md](SKILL.md) first for the whole method and the one rule (the human notices and decides; you build, organize, compute, and scale). This file covers the moment-to-moment work of the review session.

## The two modes: breadth and depth

Error analysis alternates between two modes.

**Breadth.** Cover as much of the store as possible. Pick diverse traces, fill cluster gaps, add random traces. The goal is to find different failure modes.

**Depth.** Once a mode is found, examine it thoroughly. Scan all traces for instances, re-review earlier traces, and sharpen the definition. The goal is to understand one failure mode well.

Alternate between these. Review broadly until the human notices something, examine that mode in depth, then go broad again. A depth scan happens whenever a mode earns it, not at a fixed step.

## Progress updates

Tell the human what you are doing at each step. When you group new notes, name the proposed modes. When you search for another mode, explain the retrieval method. When you propose new traces, explain the selection reason. Do not go silent while a background scan runs.

## Launch and monitor

1. Start the Python server in the background: `python analysis/server.py`. For the demo, add `--replay state/demo_annotations.json` so the canned Cartwheel annotations replay on a timer and the whole watcher pipeline fires on stage even if live annotation fails.
2. Open the app in the browser and tell the human it is ready. Explain the interaction in one or two sentences: read a trace, select the text where the first failure shows, type a short note, press Enter.
3. **Watch the local annotation mirror.** Use a small polling process that reads `analysis/state/annotations.json` every 2 seconds and compares the contents with the preceding read. Accepted annotations are written through to Langfuse, while the mirror provides a resumable event stream. Each change should report the total count, the number of traces touched, and the latest note. Use the coding environment's background process facility when one is available.

## Process annotations as they arrive

Open coding is the human reading a trace carefully and writing a short freeform note about the first thing that went wrong, in their own words, with no predefined categories. When new annotations appear:

1. Read all annotations from `state/annotations.json`.
2. Group each note into a failure mode: match it to an existing mode or draft a new candidate mode from the note. You group only what the human wrote. You never add a mode from your own reading of the traces.
3. Maintain a running taxonomy in the shape `{mode_name: {definition, status, count, example_trace_ids, example_quotes, created_from}}`. `created_from` holds the human annotation ids the mode came from, which is what proves the mode has a human origin.
4. Push the updated taxonomy to `POST /api/patterns` (which writes `state/patterns.json`). The progress view picks it up on its next poll, so the human sees their notes sort themselves as they type.
5. Track which traces have been reviewed and which clusters or dimensions are covered.

The test for whether two notes are one mode or two is always "does fixing one fix the other?" If the same fix clears both, group them. If the fixes differ, split them. For example, "agent said refund processed when the tool said queued" and "agent said 5 to 10 business days before any eligibility check ran" both group under a tool-result-misreport mode, but "agent invented a store-credit fallback" splits into its own mode, because one is misreading data the agent has and the other is asserting data that does not exist, and the fixes differ. You propose the grouping and the name and a draft definition. The human renames, merges, splits, or rejects, and owns the taxonomy.

## Depth mode: scan for more instances of a named mode

When a mode is named (or an existing one becomes clearer), scan **all** traces for instances, both reviewed and unreviewed.

Run one search task per failure mode. Give the task the mode name, its definition, and the human's example quotes. The task returns suggested annotations in the shape `{trace_id, text, start, end}`. Independent search tasks may run in parallel when the coding environment supports parallel work, but the workflow must also operate sequentially.

When a subagent returns, merge its suggestions and push them to `POST /api/suggestions` (which writes `state/suggestions.json`). The UI polls for suggestions and shows them in the progress view queue and as distinct dashed highlights in the trace view.

There are two kinds of suggestions:

1. **On already-reviewed traces.** The human may have missed an instance because the mode was not yet in their head when they read the trace. This is criteria drift.
2. **On unreviewed traces.** New coverage. Add these traces to the sample if they are not already in it.

Suggestions are not ground truth. The human accepts or dismisses each one. Favor recall over precision: dismissing a false suggestion is one click, and missing a real instance costs coverage. When the human accepts a suggestion, it becomes a human-confirmed annotation and a label with source `accepted_suggestion` is written; you never count a suggestion as a label until the human accepts it.

## Breadth mode: propose new traces

After the human works through a batch, propose the next one with `select_traces` (see SKILL.md phase 4):

1. **Cover gaps.** Sample from unreviewed clusters, roles, or feature regions.
2. **Random exploration.** Always include a few random picks, because the clustering does not capture every dimension.
3. Push the new traces to `POST /api/samples` (which writes `state/samples.json`). The app shows a banner.
4. Tell the human what was added and why.

## Encourage re-review

Do not treat review as one pass. The human's criteria shift as they see more traces (criteria drift). Your depth-scan subagents handle part of this automatically by scanning already-reviewed traces and pushing suggestions, but you cannot catch everything. After the human has found new modes, explicitly prompt them to re-read earlier traces. Say something like: "You have found three new failure modes since you reviewed the first five traces, including sycophantic_opener. Worth a second pass. You will likely spot instances you read past the first time." Re-review is how coverage catches up with the human's own learning, not rework.

The canonical example: twenty traces in, the human notices that nearly every reply opens with "I completely understand your frustration," and once seen it is everywhere, including in traces already reviewed and marked clean. The new mode enters the taxonomy late, your depth scan retro-labels the earlier traces, and the mode's count jumps.

## Labeling and counting

As the taxonomy stabilizes, the human marks each mode present or absent per trace (a column per mode, 1 or 0). Prevalence is the fraction of traces in which a mode appears. Open coding uses the first-failure convention (one note per trace, on the most upstream failure), which undercounts modes that occur late in traces. So once a mode is being tracked for fixing, go back and mark all instances of it, which is exactly what the depth scans automate. The first-failure count and the any-instance count are both worth reporting, and they differ.

## Report and converge

Periodically:

- Report the taxonomy with confirmed and suggested counts per mode.
- Report coverage: traces reviewed, clusters or dimensions covered, what remains.
- Report the discovery-rate curve: how many of the recent traces produced a brand-new mode versus a repeat of a known one.
- When the discovery rate drops toward zero, the human is near theoretical saturation. Suggest stopping the naming, or narrowing focus to a depth scan. Counting continues on new data forever; naming stops when new names stop appearing. Two serious passes over the data usually get close.

## Key principles

1. **The human notices, you organize.** Free-text notes become a structured taxonomy. Do not make the human categorize.
2. **You propose coverage.** Propose new traces from what has been found and what is missing.
3. **Live feedback loop.** Poll the local mirror and react as notes arrive.
4. **Include random samples.** Always include random picks alongside cluster-based ones, so you do not miss what the clustering did not capture.
5. **Multiple passes.** The human's criteria shift over time. Encourage re-review of earlier traces.
6. **You suggest, the human confirms.** Suggestions are visually distinct and require an explicit accept or dismiss. Favor recall over precision.
7. **Breadth then depth, repeat.** Review broadly to find modes, examine each mode in depth, then go broad again.
8. **Everything persists.** The taxonomy, the annotations, and the suggestion decisions all live under `state/`, so the next session resumes from the current state instead of from scratch. That persistence is the fix for the reuse failure of the naive "evaluate my app" prompt.

When the human is ready to stop discovering and start measuring, hand off to the second half of [SKILL.md](SKILL.md) (phases 6 to 11): select three subjective modes, collect enough human judgments for each mode, refine each judge on development data, freeze each prompt, test once, use DocETL to evaluate a representative sample, and compute corrected prevalence for trusted judges.
