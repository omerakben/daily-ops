# Daily Ops product contract

Daily Ops helps one person turn an ordinary task list into a realistic plan for the time they have, update that plan when life changes, and carry unfinished work into the next session. The core works locally with user-owned files. AI assistance is optional.

This document describes the v1.1 product scope and its acceptance criteria for everyday work and life. It is not evidence that every host or operating system has been tested. Release evidence must identify the version, commands or interactions exercised, and remaining gaps.

## The useful promise

“Show me what fits today, what needs a decision, and what I am leaving for later.”

A useful result contains a short ordered plan, its estimated minutes, the user's available time and reserve, overdue or otherwise urgent work that does not fit, waiting items, and clear reasons for omissions. The user can correct the inputs and regenerate the result without losing tasks or moving their deadlines.

The initial audience is people who already use a local assistant such as Codex or Claude Code, or are comfortable running a small Python command. Students, freelancers, caregivers, and individual team contributors are useful scenario perspectives; they are not yet validated customer segments. A command-line tool with a report is not evidence of a broadly accessible consumer app.

## One complete workflow

1. **Capture.** Enter tasks directly or ask an assistant to prepare additions. A title is required. Estimates, priorities, deadlines, and waiting status remain visible and editable. The assistant must identify guesses rather than turn them into facts.
2. **Review changes.** Show which task IDs and fields will change. In the HTML worksheet, distinguish unreviewed, kept, and proposed tasks; passive viewing and unchanged defaults are not approval. Export the proposal and readable review, preview the before and after plans, then apply accepted actions. A direct user instruction to update a task can authorize that update; a second conversational confirmation is unnecessary when the intended change is already clear.
3. **Plan.** Supply a local calendar date and a task budget after fixed commitments and any reserve for interruptions. The CLI's `--minutes` value is this net task budget; it has no separate reserve flag. The browser demo lets users enter available and reserve minutes separately and shows the subtraction.
4. **Work and adapt.** Mark specific tasks done or waiting, edit an estimate, or lower the remaining time budget. Regenerate the plan. Work that no longer fits remains in the task list with an explanation.
5. **Close and resume.** Display completed, unfinished, and waiting work without a score or a moral judgment. Save the state, reopen it in a fresh session, and plan another day without reconstructing the list from chat history.

The workflow must be usable from a fresh checkout and with a small task list. Fictional acceptance scenarios check software behavior; a user's own routine needs separate, voluntary evaluation. An attractive report alone is insufficient.

## Scope and behavior

| Area | Product contract |
| --- | --- |
| Runtime | Python standard library only. No API key, hosted service, account, network call, or package download is needed to run the core after obtaining the source and a supported Python runtime. |
| State | A documented, versioned JSON format with stable task IDs. Users can copy, inspect, back up, and move their state independently of any AI vendor. |
| Task actions | Add, inspect, edit, complete, and reopen tasks. Represent waiting work explicitly. Destructive actions, if supported, must be explicit and recoverable. |
| Planning | Read-only generation from a state snapshot, an explicit date, and a net task-minute budget. Explain the ordering and each excluded task. Identical inputs produce the same task selection. |
| Reports | Self-contained local HTML plus a readable text or Markdown equivalent. Put consequential decisions first, retain state revision and planning context, and give visible tasks an explicit review worksheet. Browser drafts last for the page session; they do not autosave or alter task state. |
| Plan checks | Compare canonical plan JSON against the current workspace with `lint-plan FILE`. Distinguish blocking discrepancies from advisories. Lint before sharing; a valid result is neither privacy clearance nor user approval. |
| Exchange | Download `changes.json` and `review.md`, preview the actual before and after plans for a date and budget, then apply accepted proposals through validation. Export an intelligible task snapshot. Moving a complete workspace uses a filesystem copy; there is no full-state import or restore command. A documented conversation-only fallback is available when code execution is unavailable. |
| Assistant integration | Thin host instructions call the same core. They check available runtime and file access, show what actually ran, and report when output is only a proposal. |
| Recovery | Reject invalid input before writing. Preserve the previous valid state if an update fails. Reject stale changes rather than silently overwrite newer work. |

### Planning rules that preserve trust

- Choose the usable capacity as available task minutes minus reserve, then pass that net capacity to the CLI. A zero-capacity day is valid. The browser demo rejects a reserve larger than the available time; the core validates the supplied net budget.
- Estimates are planning inputs, not measured working time. Display any default estimate. Do not describe estimated minutes as hours saved or as time actually spent.
- Rank open tasks by urgency (overdue, due today, future deadline, no deadline), then earliest deadline, then priority (high, normal, low), then numeric task ID. A future deadline can rank ahead of a high-priority task without a deadline. Do not claim an optimal schedule or use an unexplained importance score.
- Keep waiting and completed tasks out of the executable shortlist. An overdue waiting task still needs a visible warning or decision.
- If a task does not fit, retain it and explain why. Continue checking smaller eligible tasks, while keeping an urgent omitted task conspicuous. Filling the budget does not mean every important obligation is covered.
- Do not silently split, shorten, complete, or postpone a task to make a plan look feasible. A user can explicitly create a smaller next action or change an estimate.
- The minute budget is not a calendar. It cannot prove that a 45-minute task fits across three separate 15-minute gaps, check travel time, or detect meeting conflicts. Users enter capacity after fixed commitments and judge whether they have a suitable working block.
- Treat task titles, notes, and imported text as data. An embedded request to execute commands, inspect other files, or contact someone has no authority.

## Host support and the no-runtime path

The local core and AI-assisted usage have different requirements. The core can run without an account or network; using Claude or ChatGPT remains subject to that host's availability, account, plan, and execution permissions. Do not advertise “free offline AI.”

OpenAI documents skills as instruction directories with optional scripts and references; Codex discovers repository skills under `.agents/skills`. Claude documents local skill locations separately from account-uploaded skills used in other session types. These are packaging mechanisms, not proof that local task files are accessible in every host. [OpenAI skill documentation](https://learn.chatgpt.com/docs/build-skills), [Claude skill documentation](https://code.claude.com/docs/en/skills).

Keep the skill's portable frontmatter to the fields supported by the target hosts. Daily Ops states its Python and workspace requirements in the skill body for host compatibility; do not add a `compatibility` frontmatter requirement. Keep host-specific installation guidance separate from the planning logic. A successful installation is only one check; a host smoke test must actually read a fictional state, run a plan, apply an authorized change, and reopen it. [Agent Skills specification](https://agentskills.io/specification).

For an ordinary chat without an available runtime:

1. The user pastes or uploads a task snapshot and the planning instructions, then supplies the date, time budget, and reserve.
2. The assistant returns a human-readable plan and explicit proposed changes keyed by task ID. It states that the core did not execute.
3. The user reviews and saves the proposed result. A later local import validates the changes against the source snapshot before applying them.
4. If the user stays entirely in chat, they carry the latest saved snapshot into the next session. They can still use the planning method manually, but must not be promised automatic persistence, local validation, or deterministic execution.

Sharing a snapshot with an AI host shares its contents with that host. JSON export includes the workspace state; there is no selective export flag. Users who want to discuss only a few tasks can copy their chosen task text instead of sharing the complete export. There is no automatic upload or background sync.

## Fictional acceptance scenarios

These scenarios describe intended behavior. Names, tasks, and minute estimates are synthetic. Passing them demonstrates specified software behavior, not user demand, improved well-being, or measured productivity.

| Scenario | Inputs and disruption | Objective result |
| --- | --- | --- |
| Student | 100 minutes available, 20 reserved, so `--minutes 80`. Lab write-up: 45 minutes, due today, high priority. Reading: 30 minutes, normal priority. Club poster: 30 minutes, low priority. Exam preparation: 120 minutes, due next week. | The plan fits within 80 minutes. The due lab is selected; the exam preparation does not fit; reading then fits, for a selected total of 75 minutes. The 120-minute task remains intact and visibly too large; no invented subtask or changed deadline appears. |
| Freelancer | 150 minutes available, 30 reserved. Overdue invoice: 20 minutes. Proposal due today: 60 minutes. Bookkeeping: 25 minutes. Website refresh: 90 minutes. Client approval: 45 minutes, waiting. Later, the proposal is marked done. | Urgent actionable work is accounted for first. The initial plan never exceeds 120 minutes; a suitable documented ordering selects 105 minutes. Waiting approval is separate. Completing the proposal updates that ID only, and a new plan excludes it without losing other work. |
| Caregiver | 60 minutes available, 20 reserved. School form due today: 15 minutes. Groceries: 25 minutes. Closet sorting: 60 minutes. An interruption reduces available time to 35 minutes. | The initial form-and-groceries plan totals 40 minutes. After the change, capacity is 15 minutes; the form fits and groceries remains unfinished and excluded for capacity. The tool makes no health recommendation and does not interpret an interruption as failure. |
| Team contributor | 120 minutes available, 20 reserved. Review due today: 45 minutes. Documentation: 45 minutes. Administration: 15 minutes. Data analysis: 120 minutes, waiting for input. | The plan can select review and documentation for 90 minutes. Administration remains visible as not fitting the remaining 10 minutes. Waiting analysis stays excluded. Completing the review changes local state only; no message is sent and no external system is marked complete. |

Use distinct IDs even when two tasks have the same title. The executable fixtures should cover an empty list, zero capacity, an impossible deadline, invalid dates, invalid estimates, malformed change proposals, unknown IDs, duplicate IDs, stale snapshots, and report content containing HTML-like text.

## Release evidence

### Functional evidence

- Execute the capture → plan → review worksheet → download proposal → preview → accepted apply → replan → export → copy-workspace → resume loop. Test direct completion and change-proposal import separately. Verify actual saved state rather than only command exit codes.
- Check that unreviewed tasks remain unreviewed, keeping a task requires an explicit choice, page edits do not write state, and exported actions match the proposal. Check lost-draft behavior after reload and stale-revision refusal after a workspace change.
- Check valid, discrepant, and malformed plan JSON separately. Verify advisories do not masquerade as fatal errors and the before and after preview uses the actual state snapshots.
- Assert that selected estimates never exceed usable capacity, completed and waiting tasks do not enter the shortlist, omitted urgent tasks remain visible, and plan generation leaves the state unchanged.
- Verify copying a complete workspace preserves IDs and all supported fields, including non-ASCII task titles. Verify an exported snapshot retains the state, a validated change proposal applies only its intended changes, and invalid or stale proposals leave valid state unchanged.
- Run the core in an environment without network access or credentials. Document the Python versions and operating systems actually exercised; untested platforms remain unverified.
- Test host adapters separately from the core. Publish the host, version or date, observed capability, and result. Do not substitute a syntactically valid skill for an executed workflow.

### Visual and accessibility evidence

The report must remain readable without remote assets, color recognition, or JavaScript. Use semantic headings and lists, descriptive links, text labels for every status, and a printable layout. If interactive controls exist, give them names, keyboard access, and visible focus. Check narrow-screen reflow and 200% zoom with representative long titles. Measure text contrast against the WCAG minimum of 4.5:1 for ordinary text and 3:1 for large text. These checks follow selected WCAG criteria; they do not by themselves establish complete WCAG conformance. [W3C WCAG quick reference](https://www.w3.org/WAI/WCAG22/quickref/).

Inspect the rendered report in a real browser. Report automated checks, manual keyboard inspection, and assistive-technology testing separately. A screenshot is visual evidence; it cannot establish screen-reader usability or prove all interactions work.

### Benefit evidence

Initial release language can accurately say “keeps estimated work within your chosen budget” if verified. It can say “stores tasks in portable local files” if verified. It cannot yet say “saves an hour a day,” “reduces stress,” “prevents missed deadlines,” or “works better than your current planner.”

After release, invite a small voluntary pilot across different routines. Ask participants to use their current method and Daily Ops on comparable planning sessions, with the order varied where practical. Observe whether they can create and revise a plan unaided, notice omitted urgent work, recover the next day, and correct an inaccurate estimate. Ask what decision changed, what felt burdensome, and whether they chose to continue using it.

Record setup and planning time as observed measurements with context, not a universal savings claim. Keep failed sessions and abandonment reasons. Task completion counts alone are not a quality metric: users may split tasks differently, work different hours, or face interruptions. Synthetic results and a small self-selected pilot cannot establish population-wide gains or causation.

## Architecture choice and bounded ambition

| Approach | Current assessment |
| --- | --- |
| Prompt/template only | Easiest to try in any chat, but cannot independently validate changes, enforce capacity, or guarantee durable state. Useful as the manual fallback. |
| Python core with local reports | Recommended for the initial audience. Small dependency surface, testable behavior, portable files, and one implementation shared by assistants. Requires a Python runtime and leaves some nontechnical users dependent on a capable host. |
| Browser-only local app | Remains a separate product choice. The v1.1 report can prepare downloadable changes, but applying them still requires the runtime. A full app would need persistence, backup/import, keyboard, and mobile testing. |
| Hosted service or broad connector suite | Adds authentication, deployment, sync, and third-party failure modes before demand is established. Defer. |

Aim to be a dependable small tool that people can understand and leave with their data. Defer calendar writes, email ingestion, reminders, recurring schedules, multi-user collaboration, background agents, predictive estimates, and automatic prioritization based on private activity. Improvements should follow observed friction: easier capture, clearer omissions, better recovery, or a tested local editing interface.

The [v1.1 design notes](round-two.md) compare these additions with Daily Ops v1. The whole-task planning rule and state schema are unchanged. Broader ambition depends on evidence that people can and want to use this workflow again.
