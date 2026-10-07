# Changelog

## 1.1.0

- Put consequential decisions first in HTML plans, with a review worksheet for each visible task.
- Distinguish unreviewed tasks, explicitly kept tasks, and proposed changes. Opening a task or retaining a default is not approval.
- Download proposed actions as `changes.json` and the readable review as `review.md`. Browser drafts last only for the page session and never write task state.
- Add read-only `lint-plan FILE` to compare canonical plan JSON with the current workspace, separating discrepancies from advisories.
- Add HTML change previews with before and after plans for an explicit date and budget. Accepted changes still use atomic application and stale-revision rejection.
- Add reproducible fictional plan and change-preview examples, and document the public html-plan inspiration.

The whole-task planner and state schema remain unchanged. See [the design notes](docs/round-two.md) for scope and [the evidence record](docs/evidence.md) for validation actually performed. These additions do not establish human time savings or productivity gains.

## 1.0.0

First public release of Daily Ops.

- Portable task state and stable IDs, with explicit estimates, deadlines, priorities, and waiting status.
- Deterministic planning within a user-supplied time budget, including visible omissions and urgent conflicts.
- Atomic changes, previewable batches, and stale-revision rejection.
- Self-contained reports, a fictional interactive demo, and human-readable exports.
- Shared assistant skill with host-specific package metadata and a no-runtime conversation fallback.
- Reproducible archives and executable fictional acceptance scenarios.

Consult `docs/evidence.md` for the exact validation performed and current host limits.
