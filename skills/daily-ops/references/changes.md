# Change exchange

A proposal is JSON data. It cannot run code, install tools, open URLs, or authorize an external action.

## From report review to saved tasks

1. Review the HTML plan. Each visible task starts unreviewed; explicitly keep it or propose a change. Merely opening it or leaving a default does not record approval.
2. Download `changes.json` and `review.md`. The JSON contains proposed actions; the Markdown preserves the readable review. Edits stay only in the page session, with no autosave or workspace write. Download before closing or reloading.
3. Save the JSON inside the selected workspace. Preview it against current state and inspect the before and after plans.
4. Apply the requested or accepted actions through the runtime. Replan and confirm the resulting state.

The report is a view of a particular revision. A downloaded file can become stale before preview or between preview and apply. Neither a review download nor a clean validation result is user acceptance.

## Proposal format

Read the latest state with `list` or `export --format json`. Preserve its revision in the proposal:

```json
{
  "schema_version": 1,
  "base_revision": 3,
  "actions": [
    {"action": "add", "title": "Draft the introduction", "minutes": 25, "priority": "normal"},
    {"action": "complete", "id": "T0001"},
    {"action": "defer", "id": "T0002", "until": "2026-10-09"}
  ]
}
```

This is a fictional syntax example; read the user's actual revision, IDs, and date before preparing their proposal. Supported actions include add, update, complete, reopen, drop, defer, block, and unblock. Use the runtime `--help` for current command fields.

Keep the schema and base revision from the current workspace. Do not add review status or free-text instructions to the runtime action format. A kept task requires no action; an unreviewed task must not be treated as accepted. Comments and review notes are feedback, not executable instructions.

## Preview and apply

Use `RUNNER` for the bundled `scripts/run.py` path, `WORKSPACE` for the chosen folder, and `FILE` for the saved proposal's path. Quote all three paths. The following date and budget are fictional examples; use the user's established planning context.

```sh
python3 "RUNNER" --workspace "WORKSPACE" preview "FILE" --output reports/change.html --date 2026-10-07 --minutes 60
```

Open the returned report to compare plans generated from the actual before and proposed after states. The preview writes the report only and leaves task state unchanged. Both `--date` and `--minutes` are required for a plan comparison. `preview FILE` without these options retains the plain JSON preview.

Explain the meaningful changes in ordinary language, including what will still wait or not fit. If the exact actions are already explicitly requested or accepted, apply them without a redundant question; otherwise wait for acceptance.

```sh
python3 "RUNNER" --workspace "WORKSPACE" apply "FILE"
```

Application is atomic: all actions must validate before the batch changes task state. Generate a fresh plan after application; the old report remains a snapshot.

An invalid action or stale base revision fails without changing state. On failure, show what needs correction and prepare a new preview. Never edit the state file to evade validation. Do not retry a stale proposal with an automatically replaced revision, because the underlying task may have changed.

## Check a plan before sharing

`lint-plan` takes canonical plan JSON, not a changes file or HTML report. After creating the workspace reports folder, save the output of `plan --json` there:

```sh
python3 "RUNNER" --workspace "WORKSPACE" plan --date 2026-10-07 --minutes 60 --json > "WORKSPACE/reports/plan.json"
python3 "RUNNER" --workspace "WORKSPACE" lint-plan "WORKSPACE/reports/plan.json"
```

The check compares the plan with the current workspace and does not write task state. Exit `0` means valid, including any advisories; `1` means a discrepancy; `2` means malformed or invalid input. Resolve discrepancies and read the advisories before sharing. Regenerate a plan whose source revision has changed. Validation is separate from deciding whether to share its personal contents.
