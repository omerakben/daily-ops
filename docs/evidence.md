# Release evidence

Release candidate: **1.0.0**. This record is updated from executed checks before publication.

The acceptance scenarios in `examples/scenarios.json` are fictional. Run `python3 tools/evaluate.py` to reproduce them. Each scenario checks real saved state, planning arithmetic, visibility of omitted work, explicit completion, and resuming in a new workspace object. The interruption scenario also checks that reducing the budget does not modify tasks or deadlines.

## Claims this release can test

- Selected task estimates do not exceed the supplied capacity.
- Waiting, deferred, and oversized tasks remain visible.
- Planning and previews do not mutate task state.
- Explicit updates preserve stable IDs and survive a new session.
- Invalid batches and stale revisions preserve existing state.
- Release packages contain the shared runtime and referenced skill resources.

## Claims requiring further evidence

No human time savings, stress reduction, adoption, or long-term productivity study has been performed. No claim of an optimal schedule or universal benefit is made. Estimated completed minutes are estimates attached to tasks, not tracked effort.

Native discovery, successful installation, actual model execution, and GUI behavior are separate checks. The [platform matrix](platform-support.md) records documentation support. A valid manifest or an explicit agent trial does not establish automatic skill discovery or successful GUI installation on every surface.

## Reproduction

```sh
python3 -m unittest discover -s tests -v
python3 tools/check.py
python3 tools/evaluate.py
python3 tools/package.py
```

Use fictional workspaces for evaluation. Never publish raw task exports, global agent settings, authentication output, or full transcripts that might contain private context. Public results should identify the tested behavior and limitations without exposing local paths or accounts.
