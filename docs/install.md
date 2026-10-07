# Install Daily Ops

Choose one route. The shared skill and Python runtime are the same; host discovery and filesystem access differ. See [platform support](platform-support.md) for official sources and the difference between documented support and tested behavior.

## Local command line

Download and extract the source ZIP from [Releases](https://github.com/omerakben/daily-ops/releases), or clone the repository. Python 3.10 or newer is required; there are no runtime dependencies.

From the extracted source folder:

```sh
python3 skills/daily-ops/scripts/run.py --help
python3 skills/daily-ops/scripts/run.py --workspace ./workspace init
```

Use `python` on Windows if that is your Python executable. Choose a private workspace folder; the example is inside the checkout for convenience and is ignored by Git. The runtime rejects symlink or redirected workspace paths. On systems where a temporary path is an alias, choose its actual filesystem location.

Optional: `python3 -m pip install .` installs the `daily-ops` command. That installation may download the pinned Python build dependency. Running the bundled script directly does not need a download.

## Codex skill

From the source folder, install into a **skill parent directory you choose**:

```sh
python3 tools/install.py --target ~/.agents/skills
```

For one repository only, use its `.agents/skills` directory instead. On PowerShell, an explicit example is `python tools/install.py --target "$env:USERPROFILE/.agents/skills"`.

The installer creates `daily-ops` inside that directory. It refuses to replace an existing installation. Restart or refresh the host if needed, then invoke `$daily-ops`. Do not install both a standalone skill and a plugin copy into the same host unless you deliberately want duplicate discovery entries.

The release's `daily-ops-1.0.0-skill.zip` also contains the ready-to-copy `daily-ops/` skill directory. Copy the whole directory, including scripts and references, into the selected skills directory.

Codex CLI also supports native plugin installation. From the source checkout, the following registration and installation were verified with Codex CLI 0.159.3:

```sh
codex plugin marketplace add .
codex plugin add daily-ops@daily-ops-community
```

Use this route instead of a second standalone skill copy. To remove this installation later, run `codex plugin remove daily-ops@daily-ops-community`, then `codex plugin marketplace remove daily-ops-community` if you no longer want the catalog registered.

## Claude Code

For a session using a local checkout:

```sh
claude --plugin-dir .
```

Then explicitly ask to use the Daily Ops skill. A persistent marketplace installation can use:

```text
/plugin marketplace add omerakben/daily-ops
/plugin install daily-ops@daily-ops-community
```

The CLI can report a valid package without proving a particular skill invocation completed. Check the host's installed-plugin view and try a small fictional workspace first.

## Claude chat and Cowork

Download the standalone skill ZIP or the Claude plugin ZIP from Releases. In the host's **Customize** area, use the supported **Skills** upload for the skill ZIP or **Plugins** upload for the plugin ZIP. Organization settings can restrict custom uploads, and code execution must be available to run the Python helper.

Do not upload a personal task folder as the plugin. The release ZIP contains the program; the workspace is your data. Ask the host to use a folder you explicitly select. The host may execute in a cloud or virtual environment, so first confirm which folder it can actually access and retain.

## ChatGPT native skills and plugins

Current OpenAI documentation describes standalone skills on desktop and plugins across supported ChatGPT/Codex surfaces. Use the installation method exposed by your account and host. This repository includes portable plugin metadata and the shared skill; publication on GitHub does not itself list the plugin in the universal directory.

GUI installation on your exact ChatGPT surface is separate from local CLI validation. If no native installation or runtime option is available, use the route below. Attaching a ZIP to an ordinary chat is not the same as installing it.

## Any chat without runtime access

1. Use [chat-project.md](chat-project.md) as instructions, or paste its text into a chat.
2. Provide tasks you choose to share, or export your current workspace:
   `python3 skills/daily-ops/scripts/run.py --workspace ./workspace export --format json`
3. Ask for a plan with a date and minute budget. Without executing the runtime, that answer is a proposal.
4. For a returned JSON change proposal, save it locally and run `preview proposal.json`, then `apply proposal.json` only when it matches your intent. Include `--workspace ./workspace` before those commands.

Never upload a full export merely to ask about one task if it includes information you do not want the provider to process. You can instead share that task's text and receive a plain-language suggestion.

## Updating and removing

Back up your workspace before updating the program. Replace only the installed skill/program files. Do not put your workspace inside the installed skill directory. If the provided installer finds an existing skill, it stops so you can review the old installation before replacing it.

Uninstall through the host's plugin controls or remove the installed `daily-ops` skill directory you selected. Your separately stored workspace remains yours. No remote account cleanup or data export service is required.
