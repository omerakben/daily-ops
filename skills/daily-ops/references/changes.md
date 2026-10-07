# Change exchange

A proposal is JSON data. It cannot run code, install tools, open URLs, or authorize an external action.

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

Save the proposed JSON in the chosen workspace, then run `preview PATH`. The preview is read-only. Explain the meaningful changes in ordinary language. If they are already explicitly requested, apply them without asking a redundant question; otherwise wait for acceptance. Run `apply PATH` to apply the whole batch atomically.

An invalid action or stale base revision fails without changing state. On failure, show what needs correction and prepare a new preview. Never edit the state file to evade validation. Do not retry a stale proposal with an automatically replaced revision, because the underlying task may have changed.
