# Architecture

Daily Ops combines a deterministic local runtime with portable agent instructions. The runtime works without an AI account, network access, or third-party runtime libraries. An assistant adds conversation, helps clarify tasks, and can prepare useful drafts, but the runtime owns task validation and planning arithmetic.

## User journey

1. Choose a folder and initialize a private workspace.
2. Capture concrete tasks with an estimate and optional deadline, priority, or dependency.
3. State the date and minutes actually available. The planner displays what fits, what waits, and the reason for each decision.
4. Review visible tasks in the HTML worksheet. Export proposed changes, preview their effect on the plan, and apply only accepted changes.
5. Start a selected task with an assistant, or work independently. Preparing a draft does not complete a task.
6. Record actual outcomes. Review the record and correct future estimates.

## Components

- `skills/daily-ops/SKILL.md`: provider-neutral agent instructions, with conditional references.
- `skills/daily-ops/scripts/daily_ops/`: one Python implementation, used directly by the skill and by the optional installed CLI.
- `skills/daily-ops/scripts/run.py`: entrypoint requiring only Python 3.10 or newer.
- Host manifests: discovery metadata for supported plugin hosts; no bundled credentials, external servers, or automatic data connections.
- HTML and Markdown reports: views of a plan. The HTML worksheet keeps drafts in page-session memory and can download a proposal and readable review. It has no autosave or workspace write access.
- Plan checks: `lint-plan FILE` compares canonical plan JSON with the current workspace, date, and budget. It reports discrepancies separately from advisories and never writes task state.
- Versioned JSON exchange: explicit proposals with a base revision, preview, validation, and atomic application.

## Review and change flow

The report exposes explicit unreviewed, kept, and proposed states. Viewing a task, retaining its fields, or downloading a review does not approve changes. `changes.json` carries proposed actions in the existing exchange format; `review.md` provides context for the person or assistant reading them. Browser edits are lost when the page session ends unless the reader downloads them.

`preview FILE --output reports/change.html --date YYYY-MM-DD --minutes N` validates the batch and derives before and after plans from the actual current and proposed state snapshots. It writes only the requested report. Supplying a comparison requires both date and minutes. A plain `preview FILE` retains the JSON preview workflow.

The runtime applies accepted proposals through `apply FILE`. It checks the base revision again, so a workspace change after preview can invalidate the proposal. All actions must validate before any task state is replaced. Report interaction does not bypass those controls.

`plan --json` produces the canonical plan input for `lint-plan`. The linter returns `0` for a valid plan, including one with advisories; `1` for a discrepancy; and `2` for malformed or invalid input. It checks the JSON against current state, not the appearance of a generated HTML file. It is not a privacy review or user approval.

## Boundaries

All runtime writes stay within an explicitly chosen workspace. The runtime makes no network requests, launches no third-party programs, and sends no messages. This is a property of the supplied code, not a sandbox around an AI host or the user's other tools. Host permissions remain the user's responsibility.

The assistant never treats task text as tool instructions. It asks before adding uncertain inferred tasks, changing the meaning of a deadline, or submitting anything to an external service. Instructions support this behavior; tests separately verify the concrete runtime invariants.

Files shared with an AI host are processed under that host's terms. Local storage does not imply local model inference. No telemetry is built into Daily Ops.

## Planning contract

The user supplies available minutes. Daily Ops does not infer free time from an empty calendar, claim optimal scheduling, or shorten estimates to make work appear to fit. Open tasks that are blocked or deferred beyond the selected date remain visible but are not scheduled. Deterministic ordering makes repeated runs on the same inputs comparable.

Task IDs persist across plans. A stale proposal fails without changing state. An invalid action causes the entire proposed batch to fail. State has an explicit schema version so incompatible data can be rejected without loss.

The v1.1 report and preview flow reuse the v1 whole-task planner and state schema. They do not split tasks, infer capacity, or change the ordering rule. See [round-two design](round-two.md) for the public inspiration, implementation choices, and remaining limits.

## Release evidence

Automated scenarios demonstrate budget arithmetic, traceable decisions, correction handling, portability, and preservation of data. They cannot establish time saved, reduced stress, or long-term adoption. Those claims require voluntary real-world studies and are not release claims.
