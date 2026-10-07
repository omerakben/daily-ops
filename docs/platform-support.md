# Platform support and packaging

Documentation checked: **2026-10-07**. This document uses public vendor documentation and local CLI help only. Platform documentation can change independently of this project.

**Recommendation:** maintain one provider-neutral `SKILL.md` workflow with its templates and references. Offer native installation where the host supports it, plus a plain Markdown prompt for any chat. Make Python an optional enhancement, not a prerequisite for planning a day.

“Documented” below means an official source describes the capability. “Untested” means this research did not install or execute Daily Ops in that surface. Documentation support is not a claim that this release works there.

## Capability matrix

| Surface | Officially documented integration | Practical Daily Ops route | Evidence status |
| --- | --- | --- | --- |
| Claude chat, including Desktop Chat | Custom skill ZIP upload through **Customize → Skills**. Skills require code execution to be enabled. | Upload an individual skill archive; enable it and explicitly ask to use it. | Documented; Daily Ops GUI installation untested. |
| Claude Cowork | Plugins and their skills; custom plugin file upload. Plugin skills also work in chat. | Install the Claude plugin, or use the standalone skill. Supply notes or deliberately selected files. | Documented; Daily Ops Cowork execution untested. |
| Claude Code | Plugin directories with `.claude-plugin/plugin.json`; session-only loading with `--plugin-dir`; standalone skills. | Load the repository as a local plugin for development; distribute through a marketplace or skill folder. | Documented; local CLI help checked; model execution not performed by this research. |
| Codex app and CLI | Local Agent Skills; plugins; local/repository marketplaces. | Use the shared skill tree via `.agents/skills`, or a plugin manifest and marketplace. | Documented; local CLI help checked; model execution not performed by this research. |
| Codex IDE extension | Standalone skills. Current plugin documentation excludes the IDE extension. | Install skills in `.agents/skills`; do not promise plugin installation there. | Documented; Daily Ops IDE integration untested. |
| ChatGPT desktop | Standalone skills and plugins, with explicit skill selection by `@`. | Use the supported skill/plugin authoring and installation workflow, or the Markdown fallback. | Documented; Daily Ops desktop import untested. |
| ChatGPT web/mobile Chat and Work | Skills bundled in plugins from the universal plugin directory. Desktop-only plugins remain restricted to desktop. | Use a published compatible plugin if available; otherwise paste the workflow or place instructions and source files in a Project. | Documented; Daily Ops directory publication and installation untested. |
| Ordinary chat with no installed skill | A prompt can contain the planning procedure and user-supplied notes. | Paste the portable prompt and request a plan in the response. | Generic fallback; no native installation, automatic triggers, or local persistence implied. |

Sources: [Claude skill installation](https://support.claude.com/en/articles/12512180-use-skills-in-claude), [Claude plugins](https://support.claude.com/en/articles/13837440-use-plugins-in-claude), [Claude Code plugins](https://code.claude.com/docs/en/plugins), [OpenAI skills](https://learn.chatgpt.com/docs/build-skills), and [OpenAI plugin surfaces](https://learn.chatgpt.com/docs/plugins).

Do not describe ChatGPT as incapable of native skills. Current official documentation explicitly includes them. Equally, **attaching a ZIP to an ordinary chat is not a verified skill-installation method**. Uploading source material and installing a skill are separate operations. A ChatGPT Project can retain instructions and uploaded sources across chats; a cloud Project does not itself grant local-folder access. [Projects and chats](https://learn.chatgpt.com/docs/projects)

## Smallest honest package

Use a shared content directory and small host manifests:

```text
daily-ops/
├── plugin.json                    # Portable OpenAI-compatible plugin manifest
├── .claude-plugin/
│   └── plugin.json                 # Claude plugin manifest
├── skills/
│   └── daily-ops/
│       ├── SKILL.md
│       ├── references/             # Only resources that workflow needs
│       └── scripts/                # Optional deterministic helpers
└── docs/
    └── <portable-prompt>.md        # Ordinary-chat fallback
```

This is a recommended layout, not a list of files already shipped. One skill can cover the initial workflow. Add skills only when they represent meaningfully distinct tasks.

OpenAI now recommends root `plugin.json` using the Agent Plugins schema. Its `.codex-plugin/plugin.json` compatibility format is still supported. Portable packages discover the root `skills/` directory. Local catalogs use `.agents/plugins/marketplace.json`; their plugin paths are relative to the marketplace root. A public directory listing has a separate submission and review process. A GitHub release alone does not publish a plugin in that directory. [Package a plugin](https://developers.openai.com/plugins/build/plugins), [Submit plugins](https://developers.openai.com/plugins/deploy/submission)

Claude uses `.claude-plugin/plugin.json`, with skill directories beside that manifest directory. Its marketplace catalog is `.claude-plugin/marketplace.json`. These are different catalogs from the OpenAI format. Keep host manifests small and share the workflow files. Combined-manifest acceptance must still be exercised in each host. [Claude Code plugin structure](https://code.claude.com/docs/en/plugins)

For Claude standalone skill uploads, generate one ZIP per skill with this shape:

```text
daily-ops.zip
└── daily-ops/
    ├── SKILL.md
    └── references/...
```

The archive contains the skill directory, not only loose files at archive root. Include `name` and `description` frontmatter. Keep instructions free of product-specific tool names unless a step actually depends on that product. [Create custom Claude skills](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills)

For direct Codex installation, place skill directories under repository `.agents/skills/` or user `~/.agents/skills/`. Codex scans repository locations from the working directory to the repository root and supports symlinked skill folders. Use one discovery route per installation so duplicate copies do not appear as separate skills. [Codex skill locations](https://developers.openai.com/codex/skills)

## Runtime contract and fallback

The core workflow should accept pasted notes, a supplied date, available working time, fixed commitments, and task estimates. It should return a reviewable plan without running code or requiring a connector. A scripted helper may validate dates, calculate capacity, or write a file when that runtime is available.

| Environment | Runtime assumption to make |
| --- | --- |
| Local Claude Code or Codex CLI | The helper runs on the selected execution host. Check `python3 --version` before using a Python script; installing the agent does not prove Python is present. Document the actual script's minimum version. |
| Claude chat/Cowork | Anthropic documents executable skill scripts, including Python. Do not assume the user's host Python, host paths, package set, or persistent interpreter state is available. |
| ChatGPT Chat/Work | Use the tools exposed in that session. Native skill support does not establish that a particular Python version, local path, or connector exists. |
| No executable runtime | Follow the Markdown workflow, show calculations and assumptions, and return the plan as text for the user to save. |
| No model/network service | An installed local helper can still run if it needs no network. The user can also fill in the Markdown template manually. This is the offline fallback; cloud model reasoning is not offline. |

Claude documents Python/JavaScript scripts in skills, but not a universal Python version guarantee in the pages reviewed. Current Cowork documentation describes cloud sessions and, for some organization deployments, local sessions using a virtual machine. Check the actual session rather than hard-coding “Cowork always runs locally” or “files never leave the computer.” [Claude skill scripts](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills), [Cowork execution environment](https://support.claude.com/en/articles/13364135-use-claude-cowork-safely), [Cowork on Team and Enterprise](https://support.claude.com/en/articles/13455879-use-claude-cowork-on-team-and-enterprise-plans)

Prefer standard-library-only helpers when possible. Keep the human-readable method complete enough to work without them. Connector setup, calendar writes, scheduling, and persistent memory are separate optional capabilities; this package should not pretend they appeared because a skill was installed.

## Isolated skill evaluation

Evaluate synthetic material only: invented names, tasks, meetings, and deadlines. Copy the public package and fixtures into a disposable environment. Do not mount home directories, real calendars, mailboxes, personal notes, browser profiles, or private repositories. A temporary working directory by itself does not isolate an agent's user configuration or global skills.

Use two distinct checks:

1. **Deterministic checks:** parse manifests, check archive layout, validate referenced files, and test local helpers with fixed fixtures. These need no model or authentication.
2. **Model-backed checks:** exercise the actual installed skill with synthetic prompts. Record host version, requested and reported model, selected skill, input, output, duration, and rubric results. Do not call a pasted-prompt test proof of native discovery.

The recommended rubric covers impossible workload, fixed-event overlap, missing estimates, ambiguous dates/time zones, interrupted work, a request to send messages, and instructions embedded inside source notes. Compare against the same prompts without the skill. Judge actionable quality and constraint adherence as well as whether the expected sections exist.

### Claude Code

Local help was inspected for **Claude Code 2.1.292**. It includes `--bare`, `--restricted`, `--plugin-dir`, `--tools`, `--strict-mcp-config`, and `--no-session-persistence`.

Bare mode avoids auto-loaded hooks, memory, and other ambient context. It also disables subscription OAuth and keychain authentication: an authorized API credential or explicitly configured provider is needed. Explicit slash-skill invocation works in non-interactive mode. Consequently, a bare run can test explicit invocation but is not a normal automatic-trigger evaluation. [Claude programmatic execution](https://code.claude.com/docs/en/headless)

The following is a **proposed command, not an executed validation result**. Run it from a disposable checkout, with dedicated authentication already configured:

```sh
claude --bare --restricted \
  --plugin-dir . \
  --strict-mcp-config --mcp-config '{"mcpServers":{}}' \
  --tools '' --no-session-persistence \
  --permission-prompts none --output-format json \
  -p '/daily-ops:daily-ops Plan this synthetic day: 90 minutes available; task A needs 60 minutes; task B needs 60 minutes. Explain what will be deferred.'
```

Restricted mode confines file tools to the working directories and removes command tools unless explicitly re-enabled. `--tools ''` removes built-in tools for this instruction-only check. MCP configuration is separately constrained. Managed policies still apply. If the workflow needs script execution, use a disposable OS/container environment and explicitly enable only the tools that test needs. [Claude CLI reference](https://code.claude.com/docs/en/cli-reference)

### Codex CLI

Local help was inspected for **Codex CLI 0.159.3**. It includes `exec --ephemeral`, `--ignore-user-config`, `--sandbox read-only`, JSON events, and plugin management. CLI presence and help output do not prove authentication, model access, skill activation, or successful installation.

Use a clean container or dedicated OS account containing only the public checkout and synthetic fixtures. Install the skill in that environment's repository `.agents/skills/`, then start a fresh process. Avoid importing an existing user's configuration or authentication files into the public test artifacts.

Proposed command, after authorized authentication is configured in that isolated environment:

```sh
codex exec --ephemeral --ignore-user-config \
  --sandbox read-only --json \
  '$daily-ops Plan this synthetic day: 90 minutes available; task A needs 60 minutes; task B needs 60 minutes. Explain what will be deferred.'
```

`--ephemeral` suppresses session rollout persistence. `--ignore-user-config` skips the user config file; it is not documented as disabling every skill or instruction source. A read-only sandbox restricts mutations, not all reads. These flags complement environment isolation. [Codex non-interactive execution](https://developers.openai.com/codex/noninteractive)

Do not hard-code a model ranking into the package. Use the evaluator's selected model and record what actually ran. If authentication, model access, or isolation cannot be established, mark model evaluation **not run** and retain the deterministic results.

## Release evidence to add

Before claiming a host is tested, capture a fresh install, an explicit skill invocation, an automatic-trigger case where supported, and one no-runtime fallback. For graphical hosts, verify the visible installed skill and resulting output. Keep all fixtures and captures generic and publishable. Results from one host are not validation of another host.
