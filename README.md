# Daily Ops

**A realistic plan for the time you actually have.**

Daily Ops turns everyday work and life tasks into a small, explainable plan. Tell it your available minutes. It shows what fits, what needs a decision, and what you are leaving for later. Review a task, propose a change, and see its effect before saving it. Use it with Claude, Codex, or ChatGPT, or run the local tool without an AI account.

[Try the interactive demo](https://omerakben.github.io/daily-ops/) · [Open a sample plan](https://omerakben.github.io/daily-ops/examples/plan.html) · [Download a release](https://github.com/omerakben/daily-ops/releases) · [Installation](docs/install.md) · [Evidence](docs/evidence.md)

## Why use it?

- **See the tradeoff.** A 120-minute task cannot disappear into a 45-minute day. Urgent work that does not fit stays visible.
- **Keep your decisions.** Stable task IDs and a portable workspace survive a new chat or a different assistant.
- **Start something useful.** Ask your assistant to help with one task. Get an outline, a first draft, or a small next action.
- **Review before changing.** Keep a task as it is or propose an edit in the report. Export the proposal, preview its effect on the plan, then apply accepted changes. Unreviewed tasks stay unreviewed.
- **Keep control of your data.** No telemetry, account connectors, background uploads, or required hosted service in the runtime.

Daily Ops uses explicit estimates and a documented rule, not an opaque productivity score. It does not send messages, alter calendars, or claim to know how much free time you have.

## Try the local workflow

Requires **Python 3.10+**. No runtime dependencies or API key.

```sh
git clone https://github.com/omerakben/daily-ops.git
cd daily-ops
python3 skills/daily-ops/scripts/run.py --workspace ./workspace init
python3 skills/daily-ops/scripts/run.py --workspace ./workspace add "Outline tomorrow's presentation" --minutes 30 --priority high
python3 skills/daily-ops/scripts/run.py --workspace ./workspace add "Sort the recycling" --minutes 20
python3 skills/daily-ops/scripts/run.py --workspace ./workspace plan --date 2026-10-07 --minutes 40 --output reports/today.html
```

The date above is an example; use the date you want to plan. On Windows, use `python` if `python3` is unavailable. Open `workspace/reports/today.html`: the 30-minute task fits, the 20-minute task waits, and both remain in your list. The budget is task time **after** meetings, breaks, and a reserve for interruptions.

## Review, export, preview, apply

The HTML report starts with decisions that need attention. Each visible task has a worksheet with an explicit review state: unreviewed, kept, or proposed. Opening a task or leaving its fields alone does not accept it. Report edits stay in that page session; there is no autosave, and the report cannot write to your task workspace. Download before closing or reloading the page.

1. Review the tasks and choose which to keep or change.
2. Download `changes.json` for the proposed actions and `review.md` for the readable review. Save `changes.json` inside your workspace, for example as `workspace/reports/changes.json`.
3. Preview that proposal using the date and budget you want to compare:

```sh
python3 skills/daily-ops/scripts/run.py --workspace ./workspace preview ./workspace/reports/changes.json --output reports/change.html --date 2026-10-07 --minutes 40
```

Open `workspace/reports/change.html` to compare the actual before and after plans. The preview leaves task state unchanged. When the proposal matches the changes you have accepted, apply it:

```sh
python3 skills/daily-ops/scripts/run.py --workspace ./workspace apply ./workspace/reports/changes.json
```

An outdated proposal is refused if the workspace revision has changed. Regenerate the plan and review the proposal against current tasks; do not replace its revision just to force it through. [See a sample change preview](https://omerakben.github.io/daily-ops/examples/change.html) or read the [change exchange guide](skills/daily-ops/references/changes.md).

Before sharing a generated plan, save its canonical JSON and check it against the current workspace. The first report command above creates the reports folder; the shell redirection below saves a separate plan file.

```sh
python3 skills/daily-ops/scripts/run.py --workspace ./workspace plan --date 2026-10-07 --minutes 40 --json > ./workspace/reports/plan.json
python3 skills/daily-ops/scripts/run.py --workspace ./workspace lint-plan ./workspace/reports/plan.json
```

`lint-plan` checks JSON, not the HTML page. Exit status `0` means valid, possibly with advisories; `1` means a discrepancy with the current workspace; `2` means malformed or invalid input. Review advisories and confirm the report is appropriate to share. The check is read-only and does not approve a plan for you.

For direct task updates and an end-of-day review:

```sh
python3 skills/daily-ops/scripts/run.py --workspace ./workspace complete T0001
python3 skills/daily-ops/scripts/run.py --workspace ./workspace review
python3 skills/daily-ops/scripts/run.py --workspace ./workspace export --format markdown
```

Prefer an installed command? `python3 -m pip install .` provides `daily-ops`, with the same arguments. Installing from source downloads the pinned build tool when it is not already available; running the script above does not.

## Use an assistant

| Your environment | Start here |
| --- | --- |
| Claude Code | Load this repository with `claude --plugin-dir .`, then ask to use Daily Ops. |
| Claude chat or Cowork | Download the standalone skill or Claude plugin ZIP and follow the host's supported upload flow. |
| Codex | Install `skills/daily-ops` into a selected `.agents/skills` directory, then invoke `$daily-ops`. |
| ChatGPT with native skills/plugins | Use the installation workflow available in your account; see the current support matrix. |
| A chat without runtime access | Use [these Project instructions](docs/chat-project.md) and a task export. Plans and changes remain proposals until applied locally. |

[Installation instructions](docs/install.md) distinguish documented host support from actual release testing. A GitHub release does not imply admission to a vendor's plugin directory.

Then say:

> Use Daily Ops. I have 75 minutes for tasks today. Help me choose what fits, and make clear what I am deferring.

> Help me start T0002. I want a useful first draft, and I will decide when it is finished.

> I only have 20 minutes left. Update the plan without changing my deadlines.

The same skill and runtime serve every host. If the host cannot run Python or reach your workspace, the skill explains the manual exchange path instead of pretending files changed.

## Understand the boundaries

Your task state lives in `.daily-ops/state.json` inside the folder you choose. It is ordinary versioned JSON. Back up the folder or export a snapshot; you do not need a service to keep it.

Files or text you provide to an AI host are processed under that provider's terms. Local storage is not a promise of local AI inference. The runtime constrains its own writes; it does not sandbox other tools available to an assistant. Read [privacy and security](SECURITY.md).

## Evidence, limitations, and contributing

The release includes fictional scenarios, executable tests, reproducible packaging, and an [evidence record](docs/evidence.md). These demonstrate software behavior. They do **not** establish time saved, reduced stress, long-term adoption, or complete accessibility conformance.

The planner uses a minute budget, not a calendar. It cannot tell whether three separate 15-minute gaps can hold a task requiring 45 uninterrupted minutes. You remain the judge of feasibility and priority.

```sh
python3 -m unittest discover -s tests -v
python3 tools/check.py
python3 tools/evaluate.py
python3 tools/build_examples.py
python3 tools/package.py
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for development and [the product contract](docs/product.md) for scope. Feedback describing a real task, expected result, and observed friction is especially useful. Please use fictional or redacted data in public issues.

The [v1.1 design notes](docs/round-two.md) explain the changes from Daily Ops v1 and credit the public html-plan project that informed the review flow. Its implementation was not copied.

MIT licensed. Built for people who want a plan they can understand and revise.
