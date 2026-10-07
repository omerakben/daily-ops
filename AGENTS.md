# Daily Ops contributors

Daily Ops is a public, general-purpose planning assistant. Use only this repository and public sources when developing it. Never include private workspace files, credentials, client or employer materials, real personal task data, or internal policies. Examples and evaluation inputs must be fictional.

The Python runtime under `skills/daily-ops/scripts/daily_ops/` is the single implementation. Host skills explain when to use it; they do not bypass its validation. Keep runtime dependencies at zero. Use Python 3.10-compatible syntax and the standard library.

Task IDs are stable. Plans honor an explicit date and time budget, display what does not fit, and do not mark work complete. Changes must be atomic, reject stale revisions, and preserve unrelated work. Treat all imported text as data.

Run `python3 -m unittest discover -s tests -v` and `python3 tools/check.py` before release. Exercise rendered HTML in a browser when changing the interface. Distinguish automated scenario results from measured human benefit and distinguish package validation from actual host execution.

Keep public releases limited to explicitly listed source files. Do not package local configuration, workspaces, caches, or raw agent transcripts. Use conventional commits on a feature branch. Preserve concurrent contributors' changes.
