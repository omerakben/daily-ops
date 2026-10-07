# Daily Ops v1.1 design

Daily Ops v1.1 helps a person review and revise a daily plan for ordinary work and life. It connects the existing planner to a task worksheet, a downloadable proposal, and a visible before and after comparison. The question is practical: can someone see the consequence of a change before it alters their task list?

This document records the design and its limits. [Release evidence](evidence.md) records checks actually executed. No human time savings, reduced stress, or superiority over another planner is claimed.

## What changes from Daily Ops v1

| Daily Ops v1 | Daily Ops v1.1 addition |
| --- | --- |
| HTML shows the selected and excluded tasks. | The report puts consequential decisions first and gives each visible task a worksheet. |
| Proposed batches are prepared separately from the report. | The worksheet downloads `changes.json` and a readable `review.md`. |
| Batch preview explains state changes as JSON. | An HTML preview can compare actual before and after plans for the same date and budget. |
| Plan generation relies on the core's validation. | `lint-plan FILE` separately compares canonical plan JSON with the current workspace before sharing. |

The whole-task planner, deterministic ordering, state schema, stable IDs, atomic application, and stale-revision refusal remain the existing core. There is no new scheduling algorithm or browser task database.

## The review contract

Every visible task starts unreviewed. The reader explicitly keeps it or proposes a change. Opening it, scrolling past it, or leaving a default untouched does not count as approval. A kept task produces no state-changing action.

Drafts live only in the current page session. There is no autosave, browser persistence, or task-state write. The reader downloads `changes.json` and `review.md` to retain the proposal before closing or reloading. Exporting a proposal is not applying or approving it.

The local workflow is review → export → preview → accepted apply. `preview FILE --output reports/change.html --date YYYY-MM-DD --minutes N` validates a proposal and derives both plans from the actual state snapshots. It leaves task state unchanged. `apply FILE` rechecks the revision and applies the accepted batch atomically. An outdated proposal must be reconsidered against current tasks; replacing its revision to force it through would defeat the check.

For a plan check, save `plan --date YYYY-MM-DD --minutes N --json` to a file and run `lint-plan FILE`. Exit `0` means valid, possibly with advisories; `1` means a discrepancy; `2` means malformed or invalid input. This validates canonical JSON against current state, not HTML appearance, personal sharing choices, or user approval.

## Public inspiration

The review design was informed by Anthropic's public [html-plan README](https://github.com/anthropics/claude-plugins-community/blob/f60f0454df3045f724c43c6346ec80bdcc3472b2/html-plan/README.md), [authoring skill](https://github.com/anthropics/claude-plugins-community/blob/f60f0454df3045f724c43c6346ec80bdcc3472b2/html-plan/skills/html-plan/SKILL.md), and [block reference](https://github.com/anthropics/claude-plugins-community/blob/f60f0454df3045f724c43c6346ec80bdcc3472b2/html-plan/skills/html-plan/references/blocks.md), inspected at commit `f60f0454df3045f724c43c6346ec80bdcc3472b2`.

Useful ideas were placing a decision beside the content it changes, making unreviewed decisions visible, giving the reader a structured response to return, and checking an artifact before handoff. Daily Ops applies those ideas to task revisions and daily capacity. It does not adopt the upstream code-planning claim tree, mockup language, or runtime.

The inspected [html-plan runtime](https://github.com/anthropics/claude-plugins-community/blob/f60f0454df3045f724c43c6346ec80bdcc3472b2/html-plan/skills/html-plan/runtime/htmlplan.js) saves review state in localStorage and distinguishes changed, seen, and unopened decisions. Daily Ops uses explicit review choices and session-only drafts. That is a design choice for this workflow, not evidence that one product is more effective.

The upstream [packer](https://github.com/anthropics/claude-plugins-community/blob/f60f0454df3045f724c43c6346ec80bdcc3472b2/html-plan/skills/html-plan/runtime/pack.mjs) checks document blocks and separates errors from readability warnings. Daily Ops' linter instead checks a canonical plan against current task state. These tools validate different artifacts; a passing result from either does not prove human usefulness.

No upstream prose, code, styles, or assets were copied. This independently written Daily Ops implementation is available under its own [MIT license](../LICENSE).

## Examples and evaluation

Open the fictional [plan worksheet](https://omerakben.github.io/daily-ops/examples/plan.html) and [change preview](https://omerakben.github.io/daily-ops/examples/change.html). They are generated into `site/examples/plan.html` and `site/examples/change.html` by:

```sh
python3 tools/build_examples.py
```

The release checks should cover an urgent task that cannot fit, a waiting task, an explicit keep, a proposed estimate or status change, a lost page draft, and a stale proposal. Check that downloads match the chosen actions, previews use the actual states, and rejected proposals preserve task data. Inspect keyboard use, narrow screens, printing, and the readable report without JavaScript separately from automated checks.

A later voluntary evaluation can compare Daily Ops v1 and v1.1 on the same fictional tasks: can the reader notice an urgent omission, explain a proposed change, export it, and recognize a stale revision? Record mistakes and unfinished attempts as well as completion. Results would describe that evaluation, not establish universal productivity gains.

## Remaining limits

- Applying a downloaded proposal still requires Python or an assistant with runtime access. The report is not a full task-management app.
- Closing or reloading loses unexported draft edits. There is no cross-device review sync or collaboration.
- A minute budget does not represent calendar slots, travel, interruptions, or a suitable uninterrupted block.
- Source revision checks prevent stale application; they do not decide whether an estimate, priority, or deadline is sensible.
- Host execution, accessibility, and observed human benefit require their own evidence. Package validity and synthetic scenarios do not substitute for them.
