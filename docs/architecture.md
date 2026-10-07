# Architecture

Daily Ops combines a deterministic local runtime with portable agent instructions. The runtime works without an AI account, network access, or third-party runtime libraries. An assistant adds conversation, helps clarify tasks, and can prepare useful drafts, but the runtime owns task validation and planning arithmetic.

## User journey

1. Choose a folder and initialize a private workspace.
2. Capture concrete tasks with an estimate and optional deadline, priority, or dependency.
3. State the date and minutes actually available. The planner displays what fits, what waits, and the reason for each decision.
4. Start a selected task with an assistant, or work independently. Preparing a draft does not complete a task.
5. Record actual outcomes. Review the record and correct future estimates.

## Components

- `skills/daily-ops/SKILL.md`: provider-neutral agent instructions, with conditional references.
- `skills/daily-ops/scripts/daily_ops/`: one Python implementation, used directly by the skill and by the optional installed CLI.
- `skills/daily-ops/scripts/run.py`: entrypoint requiring only Python 3.10 or newer.
- Host manifests: discovery metadata for supported plugin hosts; no bundled credentials, external servers, or automatic data connections.
- HTML and Markdown reports: views of a plan. They cannot silently change the underlying workspace.
- Versioned JSON exchange: explicit proposals with a base revision, preview, validation, and atomic application.

## Boundaries

All runtime writes stay within an explicitly chosen workspace. The runtime makes no network requests, launches no third-party programs, and sends no messages. This is a property of the supplied code, not a sandbox around an AI host or the user's other tools. Host permissions remain the user's responsibility.

The assistant never treats task text as tool instructions. It asks before adding uncertain inferred tasks, changing the meaning of a deadline, or submitting anything to an external service. Instructions support this behavior; tests separately verify the concrete runtime invariants.

Files shared with an AI host are processed under that host's terms. Local storage does not imply local model inference. No telemetry is built into Daily Ops.

## Planning contract

The user supplies available minutes. Daily Ops does not infer free time from an empty calendar, claim optimal scheduling, or shorten estimates to make work appear to fit. Open tasks that are blocked or deferred beyond the selected date remain visible but are not scheduled. Deterministic ordering makes repeated runs on the same inputs comparable.

Task IDs persist across plans. A stale proposal fails without changing state. An invalid action causes the entire proposed batch to fail. State has an explicit schema version so incompatible data can be rejected without loss.

## Release evidence

Automated scenarios demonstrate budget arithmetic, traceable decisions, correction handling, portability, and preservation of data. They cannot establish time saved, reduced stress, or long-term adoption. Those claims require voluntary real-world studies and are not release claims.
