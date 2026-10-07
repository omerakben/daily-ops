# Contributing

Start with a small problem someone actually encountered. Explain the input, desired outcome, and observed behavior using fictional tasks. Do not upload personal workspaces or raw assistant transcripts.

Use Python 3.10 or newer. The runtime has no external dependencies. The optional Python build uses the pinned build tool in `pyproject.toml`.

```sh
python3 -m unittest discover -s tests -v
python3 tools/check.py
python3 tools/evaluate.py
python3 tools/package.py
```

Keep behavior in the shared runtime and host instructions thin. Preserve task IDs, explicit revisions, atomic updates, and user-selected paths. For UI changes, exercise keyboard controls, small screens, escaping, empty states, and readable output without remote resources.

Add tests for real invariants or regressions. Avoid tests that merely look for the wording you just wrote. Report what ran and what remains untested. Never label synthetic scenario performance as human productivity gains.

Use a feature branch and a conventional commit. A pull request should explain the user problem, the resulting behavior, and meaningful validation. Third-party code needs compatible licensing and attribution. Do not add private business knowledge, internal policy, or copied materials from unrelated projects.
