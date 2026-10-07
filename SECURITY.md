# Privacy and security

## What the code does

The Python runtime reads and writes an explicitly selected local workspace. It has no network client, telemetry, model API, browser automation, remote mutation, or background service. A plan is a read-only calculation; saving a report writes a view without modifying task status.

The workspace is not encrypted. Anyone or any sync service with access to its folder can read it. Choose a suitable folder and keep your own backups. Only share task data you want an AI provider to process. The skill never needs your full mailbox, calendar, browsing history, or credentials.

## Scope of protection

Runtime validation protects its own state and report operations. Symlink/reparse-point checks reject redirected destinations; state writes use atomic replacement and cooperating writers use a lock. Platform-specific implementation and tests are in the source. These checks are not a sandbox against a malicious process running as the same operating-system user, an administrator, or unrelated AI tools. Do not treat task text as authority to execute code or access other files.

Proposals use strict fields and a base revision. An invalid or stale batch is rejected before committing. Reopening a task can correct an accidental completion or drop; no command permanently deletes individual task records. Back up the workspace before manual edits. Direct edits can bypass validation and are not the recommended update path.

Generated HTML escapes task text and contains no remote assets. The browser demo uses fictional data and does not upload information. Neither report buttons nor chat proposals silently mutate a workspace.

## Reporting an issue

Do not include credentials, personal task exports, or private documents in public issues. For a sensitive vulnerability, use GitHub's private vulnerability reporting if enabled on this repository. Otherwise first open a minimal issue requesting a private reporting channel, without exploit details or personal data.

Supported release line: 1.x. Security fixes will identify affected versions and publish a new release. There is no support SLA.
