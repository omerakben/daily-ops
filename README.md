# Daily Ops

**A realistic plan for the time you actually have.**

Daily Ops turns a task list into a small, explainable plan. Tell it your available minutes. It shows what fits, what needs a decision, and what you are leaving for later. Use it with Claude, Codex, or ChatGPT, or run the local tool without an AI account.

[Try the interactive demo](https://omerakben.github.io/daily-ops/) · [Download a release](https://github.com/omerakben/daily-ops/releases) · [Installation](docs/install.md) · [Evidence](docs/evidence.md)

## Why use it?

- **See the tradeoff.** A 120-minute task cannot disappear into a 45-minute day. Urgent work that does not fit stays visible.
- **Keep your decisions.** Stable task IDs and a portable workspace survive a new chat or a different assistant.
- **Start something useful.** Ask your assistant to help with one task. Get an outline, a first draft, or a small next action.
- **Change plans safely.** Preview batches, reject stale changes, and preserve the whole list when an import fails.
- **Keep control of your data.** No telemetry, account connectors, background uploads, or required hosted service in the runtime.

Daily Ops uses explicit estimates and a documented rule, not an opaque productivity score. It does not send messages, alter calendars, or claim to know how much free time you have.

## Try the local workflow

Requires **Python 3.10+**. No runtime dependencies or API key.

```sh
git clone https://github.com/omerakben/daily-ops.git
cd daily-ops
python3 skills/daily-ops/scripts/run.py --workspace ./workspace init
python3 skills/daily-ops/scripts/run.py --workspace ./workspace add "Outline the presentation" --minutes 30 --priority high
python3 skills/daily-ops/scripts/run.py --workspace ./workspace add "Organize reference notes" --minutes 20
python3 skills/daily-ops/scripts/run.py --workspace ./workspace plan --date 2026-10-07 --minutes 40 --output reports/today.html
```

The date above is an example; use the date you want to plan. On Windows, use `python` if `python3` is unavailable. Open `workspace/reports/today.html`: the 30-minute task fits, the 20-minute task waits, and both remain in your list. The budget is task time **after** meetings, breaks, and a reserve for interruptions.

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
python3 tools/package.py
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for development and [the product contract](docs/product.md) for scope. Feedback describing a real task, expected result, and observed friction is especially useful. Please use fictional or redacted data in public issues.

MIT licensed. Built for people who want a plan they can understand and revise.
