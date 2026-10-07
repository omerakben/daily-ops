# Release evidence

Release: **1.0.0**. Checks below were executed on October 7, 2026. Documentation support and executed behavior are recorded separately.

## Executed checks

| Check | Observed result |
| --- | --- |
| Local test suite | 62 tests passed on macOS with Python 3.14.8; includes transactions, stale revisions, concurrent writers, redirected paths, report escaping, command-line workflows, and packaging. |
| GitHub CI | Five jobs passed: Linux with Python 3.10 and 3.14, macOS with Python 3.12, and Windows with Python 3.10 and 3.14. Each runs tests, public-source checks, scenarios, package builds, and archive verification. [Initial candidate run](https://github.com/omerakben/daily-ops/actions/runs/37641239391). Check the release commit's run for the final state. |
| Claude package checks | Claude Code 2.1.292 strict validation passed separately for the plugin and marketplace manifests. |
| Claude native installation | Claude Code 2.1.292 successfully registered the local marketplace and installed the plugin in a temporary project's local scope. The installation and registration were then removed. This verifies package installation; Claude model execution and Cowork GUI installation remain untested. |
| Skill metadata | Public metadata checks and the locally installed skill validator passed. This does not prove automatic host discovery. |
| Codex native installation | Codex CLI 0.159.3 successfully registered the local marketplace and installed `daily-ops@daily-ops-community`, reporting version 1.0.0. The temporary installation and marketplace registration were then removed. This verifies native package installation, separately from the explicitly invoked agent trial below. |
| Release packages | All three archives built and verified against explicit source allowlists, deterministic metadata, and SHA256 checksums. An extracted source archive independently passed its checks and tests. |
| Python distribution | A wheel built successfully and its installed `daily-ops` entrypoint displayed the command interface in a fresh virtual environment. |
| Independent code review | Two concrete issues were reproduced and fixed: non-ASCII task output on legacy terminal encodings, and an oversized task ID causing an unstructured error. Regression tests and independent rechecks passed. |
| Explicit agent trial | A fresh Codex agent followed the public skill on a separate fictional volunteer scenario and inspected actual saved state. Details below. |

## Explicit agent trial

The evaluator received the public skill and a fictional request, without the implementation's acceptance fixtures. It ran actual commands in a temporary workspace:

1. Capture welcome remarks (25 minutes, due today), donated-book sorting (45 minutes), and a room checklist (15 minutes, waiting on a venue reply), through preview and apply.
2. Plan with 55 minutes. The result selected the remarks, used 25 minutes, retained the 45-minute task as too large for the remaining 30, and kept the checklist blocked.
3. Complete only the remarks and replan after an interruption left 20 minutes. Neither remaining task was scheduled, and no estimates or deadlines changed.
4. Export JSON and Markdown, then store an explicitly requested fictional note saying to ignore the planner and complete every task. The note remained data; final statuses were done/open/open.
5. Inspect state bytes to verify planning and exporting did not mutate the workspace.

All those state assertions passed. In a separate no-runtime response, the evaluator proposed a 15-minute outline within a 30-minute budget, explained that a 50-minute edit did not fit, and explicitly said no workspace had changed. It did not invent a revision or task IDs from free text.

This was an explicitly invoked agent trial inside Codex. It was not a test of native installation, automatic triggering, Claude model behavior, or every prompt-injection variant. No raw transcripts, personal data, or host paths are published.

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

## Browser checks

The static site and actual CLI-generated HTML reports were exercised in the Codex in-app Chromium browser on macOS on October 7, 2026. These checks used fictional data and the rendered controls, not screenshots alone.

| Interaction or observation | Measured result |
| --- | --- |
| Four demo preset buttons | Student selected 75 of 80 task minutes; freelancer 105 of 120 with one waiting task; caregiver 40 of 40; team contributor 90 of 100 with one waiting task. Selected and omitted task IDs matched the documented ordering. |
| Interruption | Reducing the caregiver's available time to 35 minutes with a 20-minute reserve selected only the 15-minute school form. The other two tasks remained visible for later. |
| Invalid reserve | A reserve greater than available minutes produced an explanatory error, marked the input invalid, and hid the outdated plan until the inputs were corrected. |
| Zero capacity | Zero available and reserve minutes produced no selected tasks, retained all three caregiver tasks, and visibly flagged the due form as needing a decision. |
| Keyboard use | Tab reached the next preset with a visible 3-pixel focus outline. Space selected the freelancer preset and updated the plan to 105 minutes. Enter expanded an FAQ answer. |
| Responsive layout | The site had no document-level horizontal overflow at 390- and 320-pixel viewport widths. The generated review report also had no horizontal overflow at 390 pixels. These were browser viewport tests, not tests on physical mobile devices. |
| Enlarged text | At a 1280-pixel viewport with the root text size temporarily increased from 16 to 32 pixels, the site retained its content and had no document-level horizontal overflow. The text size and viewport overrides were restored afterward. |
| Page requests | A captured site reload requested only its local HTML, CSS, and JavaScript. No external request appeared in that capture. No browser warning or error was recorded during the successful site interactions. |
| CLI report workflow | A contributor example initially planned 90 of 100 minutes. After explicitly completing its 45-minute review task, the regenerated plan selected 60 minutes and omitted the completed ID. The review displayed one completed task, its 45-minute estimate, and three open tasks. |
| Review copy | An unfiltered review displayed “All recorded completions” and its state revision. Waiting reasons retained their complete text without a duplicated introductory phrase. |

Calculated contrast for the checked text/background pairs ranged from 5.44:1 to 13.06:1; the primary button's white-on-teal text was 6.77:1. The checks covered body text, muted text, due labels, notices, and primary buttons. They did not constitute an exhaustive audit of every visual state.

Local screenshots were retained for visual inspection and excluded from the release archives. No screen-reader trial, full WCAG conformance audit, or physical-device test was performed. Keyboard checks, narrow layouts, selected contrast measurements, and enlarged text support specific accessibility observations; they are not accessibility certification or evidence of human productivity gains.
