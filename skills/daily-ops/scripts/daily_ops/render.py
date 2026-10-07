"""Self-contained, offline report surfaces. Imported task text is always data."""

import base64
from datetime import date as calendar_date
from hashlib import sha256
from html import escape
import json
import re

from .plan_checks import assess_plan
from .report_assets import CSS, WORKSHEET_JS


def _text(value):
    return "" if value is None else str(value)


def _e(value):
    return escape(_text(value), quote=True)


def _anchor(task_id):
    """Stable fragment IDs never contain user-supplied markup."""
    return "task-" + _text(task_id).encode("utf-8", errors="replace").hex()


def _hash(value):
    return base64.b64encode(sha256(value.encode("utf-8")).digest()).decode("ascii")


def _json_data(value):
    return (json.dumps(value, ensure_ascii=True, separators=(",", ":"))
            .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))


def _document(title, body, navigation, worksheet=None):
    script_policy = "'none'" if worksheet is None else "'sha256-" + _hash(WORKSHEET_JS) + "'"
    policy = ("default-src 'none'; connect-src 'none'; img-src 'none'; "
              "style-src 'sha256-" + _hash(CSS) + "'; script-src " + script_policy +
              "; base-uri 'none'; form-action 'none'; object-src 'none'")
    nav = "".join(f'<a href="#{_e(target)}">{_e(label)}</a>' for target, label in navigation)
    scripts = ""
    if worksheet is not None:
        scripts = ('<script id="report-data" type="application/json">' + _json_data(worksheet) +
                   '</script><script>' + WORKSHEET_JS + '</script>')
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="referrer" content="no-referrer">'
        f'<meta http-equiv="Content-Security-Policy" content="{_e(policy)}">'
        f'<title>{_e(title)} · Daily Ops</title><style>{CSS}</style></head><body>'
        '<a class="skip" href="#main">Skip to report</a><div class="layout">'
        '<aside class="sidebar"><div class="brand">Daily Ops<span aria-hidden="true"> /</span></div>'
        '<p>A little more room to think.</p>'
        f'<nav aria-label="Report sections">{nav}</nav>'
        '<p class="sidebar-note">Local snapshot.<br>No calendar connection.<br>Nothing applied by viewing.</p>'
        f'</aside><main id="main">{body}</main></div>{scripts}</body></html>\n'
    )


def _stat(value, label):
    return f'<div class="stat"><strong>{_e(value)}</strong><span>{_e(label)}</span></div>'


def _entries(report):
    return [(group, entry, entry.get("task", entry))
            for group in ("selected", "deferred", "blocked")
            for entry in report.get(group) or []]


def _worksheet_data(report, concerns):
    revision = report.get("revision")
    if type(revision) is not int or revision < 0:
        return None
    tasks = []
    seen = set()
    for group, entry, task in _entries(report):
        task_id = task.get("id")
        # Legacy/display-only reports remain readable without creating invalid proposals.
        if not isinstance(task_id, str) or not re.fullmatch(r"T[0-9]{4,}", task_id) or len(task_id) > 64:
            return None
        if int(task_id[1:]) < 1 or task_id != f"T{int(task_id[1:]):04d}" or task_id in seen:
            return None
        if type(task.get("minutes")) is not int or not 1 <= task["minutes"] <= 1440:
            return None
        if task.get("status") != "open":
            return None
        seen.add(task_id)
        item = {key: task.get(key) for key in ("id", "title", "minutes", "due", "not_before", "blocked_by", "notes")}
        item.update(placement={"selected": "Selected", "deferred": "For later", "blocked": "Waiting"}[group],
                    plan_reason=entry.get("reason", ""))
        tasks.append(item)
    if not tasks:
        return None
    return {"revision": revision, "date": report.get("date"), "budget_minutes": report.get("budget_minutes"),
            "tasks": tasks, "concerns": concerns}


def _response_controls(task):
    anchor = _anchor(task.get("id"))
    blocked = bool(task.get("blocked_by"))
    options = [("unreviewed", "Unreviewed"), ("keep", "Keep current (reviewed, not approved)"),
               ("estimate", "Change estimate"), ("due", "Move or set deadline"),
               ("remove_due", "Remove deadline"), ("defer", "Defer until a date"),
               ("block", "Mark waiting with a reason")]
    if blocked:
        options.append(("unblock", "Unblock this task"))
    select = "".join(f'<option value="{value}">{label}</option>' for value, label in options)
    fields = [
        ("estimate", "minutes", "New estimate · minutes", "number", task.get("minutes"), ' min="1" max="1440" step="1"'),
        ("due", "due", "New deadline", "text", task.get("due"), ' placeholder="YYYY-MM-DD" inputmode="numeric"'),
        ("defer", "until", "Do not plan before", "text", task.get("not_before"), ' placeholder="YYYY-MM-DD" inputmode="numeric"'),
    ]
    body = (
        '<details class="worksheet" hidden><summary>Review this task</summary>'
        '<fieldset><legend>Choose one response. Opening this panel records nothing.</legend>'
        f'<label for="{anchor}-choice">Your response</label>'
        f'<select id="{anchor}-choice" data-choice>{select}</select>'
    )
    for choice, name, label, kind, value, attrs in fields:
        body += (
            f'<div class="response-field" data-for-choice="{choice}" hidden>'
            f'<label for="{anchor}-{name}">{label}</label>'
            f'<input id="{anchor}-{name}" data-field="{name}" type="{kind}" value="{_e(value)}"{attrs}>'
            '</div>'
        )
    body += (
        '<div class="response-field" data-for-choice="block" hidden>'
        f'<label for="{anchor}-reason">What are you waiting for?</label>'
        f'<textarea id="{anchor}-reason" data-field="reason" rows="3">{_e(task.get("blocked_by"))}</textarea>'
        '<p class="help">A concrete reason, up to 20000 characters.</p></div>'
        '<p class="response-message" data-response-message aria-live="polite"></p></fieldset></details>'
    )
    return body


def _task_html(entry, selected=False, concerns=None, worksheet=False, anchored=True):
    task = entry.get("task", entry)
    task_id = task.get("id", "")
    parts = []
    if task.get("minutes") is not None:
        parts.append(f'{_e(task["minutes"])} estimated min')
    for key, label in (("priority", "Priority"), ("due", "Due"), ("not_before", "Available"),
                       ("status", "Status:"), ("completed", "Completed")):
        if task.get(key) is not None:
            parts.append(label + " " + _e(task[key]))
    blocked = task.get("blocked_by")
    if blocked:
        reason = ", ".join(_text(item) for item in blocked) if isinstance(blocked, list) else blocked
        parts.append("Waiting reason: " + _e(reason))
    attrs = f' id="{_anchor(task_id)}"' if anchored else ""
    if worksheet:
        attrs += f' data-review-task="{_e(task_id)}"'
    body = (
        f'<li class="task"{attrs}><div class="task-top"><code>{_e(task_id)}</code>'
        + ('<span class="review-status" data-review-status>Unreviewed</span>' if worksheet else "")
        + f'</div><h3>{_e(task.get("title", "Untitled task"))}</h3>'
        + '<div class="facts">' + "".join(f'<span>{part}</span>' for part in parts) + '</div>'
    )
    if task.get("notes"):
        body += f'<p class="notes">{_e(task["notes"])}</p>'
    if entry.get("reason"):
        body += f'<p class="reason">{_e(entry["reason"])}</p>'
    for concern in concerns or []:
        body += (f'<div class="concern"><p>{_e(concern["message"])}</p>'
                 f'<p class="question">{_e(concern["question"])}</p></div>')
    if selected:
        body += (
            '<p class="request">Copy into your assistant if you want help:'
            f'<code>{_e("Help me start task " + _text(task_id) + ". Keep its status unchanged.")}</code></p>'
        )
    if worksheet:
        body += _response_controls(task)
    return body + "</li>"


def _group(title, entries, empty, target, selected=False, concerns=None, worksheet=False):
    entries = entries or []
    body = f'<section id="{target}" class="section{" selected" if selected else ""}"><h2>{_e(title)} <span class="count">{len(entries)}</span></h2>'
    if entries:
        body += '<ul class="task-list">'
        for entry in entries:
            task = entry.get("task", entry)
            matching = [item for item in concerns or [] if item.get("task_id") == task.get("id")]
            body += _task_html(entry, selected, matching, worksheet)
        body += "</ul>"
    else:
        body += f'<p class="empty">{_e(empty)}</p>'
    return body + "</section>"


def _decisions(report, concerns, target="decisions"):
    tasks = {_text(task.get("id")): task for _, _, task in _entries(report)}
    body = f'<section class="section notice" id="{target}"><h2>Needs a decision</h2>'
    if not concerns and not report.get("conflicts"):
        return body + '<p>No specific planning concerns were detected in this snapshot. Review the estimates and commitments before relying on the plan.</p></section>'
    grouped = {}
    for item in concerns:
        grouped.setdefault(_text(item.get("task_id")), []).append(item)
    body += '<ul class="decisions">'
    for task_id, items in grouped.items():
        label = f'<code>{_e(task_id)}</code>'
        if task_id in tasks:
            label = f'<a href="#{_anchor(task_id)}">{label} · {_e(tasks[task_id].get("title"))}</a>'
        elif items[0].get("title"):
            label += " · " + _e(items[0]["title"])
        body += f'<li>{label}'
        for item in items:
            body += f'<p>{_e(item.get("message"))}</p><p class="question">{_e(item.get("question"))}</p>'
        body += '</li>'
    for item in report.get("conflicts") or []:
        task_id = _text(item.get("id"))
        if task_id in grouped:
            continue
        label = f'<code>{_e(task_id)}</code>'
        if task_id in tasks:
            label = f'<a href="#{_anchor(task_id)}">{label}</a>'
        body += f'<li>{label}<p>{_e(item.get("reason"))}</p></li>'
    return body + "</ul></section>"


def _preview_command(report):
    """Interpolate only calendar-checked dates and bounded integer minutes."""
    plan_date, minutes = report.get("date"), report.get("budget_minutes")
    valid_date = isinstance(plan_date, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", plan_date)
    if valid_date:
        try:
            calendar_date.fromisoformat(plan_date)
        except ValueError:
            valid_date = False
    valid_minutes = type(minutes) is int and 0 <= minutes <= 1440
    complete = bool(valid_date and valid_minutes)
    date_argument = plan_date if valid_date else "YYYY-MM-DD"
    minute_argument = str(minutes) if valid_minutes else "MINUTES"
    command = ('python3 "/path/to/daily-ops/skills/daily-ops/scripts/run.py" '
               '--workspace "/path/to/workspace" preview "/path/to/changes.json" '
               f'--date {date_argument} --minutes {minute_argument} --output reports/change.html')
    return command, complete


def _review_tools(report, enabled):
    command, complete_context = _preview_command(report)
    command_context = (
        "The date and minute budget below match this snapshot."
        if complete_context else
        "This snapshot has incomplete planning inputs. Replace YYYY-MM-DD or MINUTES placeholders with a valid date and a whole-number budget from 0 to 1440."
    )
    body = (
        '<section class="section export-panel" id="worksheet"><h2>Your review worksheet</h2>'
        '<p>Review each task on its card. Keep current records that you reviewed it; it does not approve '
        'the plan. A proposed change is separate from the saved task.</p>'
        '<p>Choices and reader notes live only in this page’s memory and are lost on reload or close. '
        'Export to keep them. Viewing, scrolling, or opening a card does not count as review.</p>'
    )
    if enabled:
        body += (
            '<noscript><p>The plan above is fully readable without JavaScript. The optional worksheet '
            'requires JavaScript; you can also return task IDs and requested changes to your assistant.</p></noscript>'
            '<div class="review-tools" hidden><p id="review-progress" class="progress" aria-live="polite"></p>'
            '<label for="reader-notes">Reader notes (optional)</label>'
            '<textarea id="reader-notes" rows="4" placeholder="Questions, context, or a decision to revisit"></textarea>'
            '<p class="help">Reader notes are included in review.md only; they do not update task notes.</p>'
            '<div class="actions"><button id="download-changes" type="button" disabled>Download changes.json</button>'
            '<button id="download-review" type="button" class="secondary">Download review.md</button></div>'
            '<p class="help">Changes download becomes available after at least one valid change. Unreviewed '
            'tasks stay unchanged. Each task can contribute at most one action; at most 1000 actions per proposal.</p>'
            '<p id="export-status" role="status" aria-live="polite"></p></div>'
        )
    else:
        body += '<p>This snapshot has no tasks eligible for the interactive worksheet. Use task IDs with your assistant, or generate a current Daily Ops plan.</p>'
    body += (
        '<details><summary>What happens after download?</summary>'
        '<p>Return changes.json and, optionally, review.md to your assistant. Ask to preview the proposal '
        'against your current workspace. Preview shows exact changes and can compare plans for the same date and budget.</p>'
        '<p>A download prepares a proposal. It does not save tasks or apply changes. The CLI checks the current '
        'revision and rejects stale proposals; regenerate and review again if the workspace has changed.</p>'
        '<p>From a terminal, use your actual workspace path and the downloaded proposal path:</p>'
        f'<p>{command_context}</p><pre>{_e(command)}</pre>'
        '</details></section>'
    )
    return body


def render_plan(report):
    """Render complete plan facts plus an optional explicit review worksheet."""
    concerns = assess_plan(report)
    worksheet = _worksheet_data(report, concerns)
    body = (
        '<header id="overview"><div class="eyebrow">Your daily plan</div>'
        '<h1>Make room for what matters today.</h1>'
        f'<p class="meta">{_e(report.get("date", "Date not supplied"))} · State revision {_e(report.get("revision", "unknown"))}</p>'
        '<p class="intro">A starting point for the time you have. All selected, deferred, and waiting tasks '
        'remain visible below. This snapshot does not change your tasks.</p></header>'
    )
    selected = report.get("selected") or []
    if selected:
        first = selected[0].get("task", selected[0])
        body += (
            '<section class="hero" aria-label="First task"><div class="eyebrow">Start with one thing</div>'
            f'<h2><a href="#{_anchor(first.get("id"))}">{_e(first.get("title", "Untitled task"))}</a></h2>'
            f'<p class="meta">{_e(first.get("id"))} · {_e(first.get("minutes"))} estimated min</p>'
            '<p>The first task selected by this plan. Open its card for the recorded context and your review response.</p></section>'
        )
    else:
        body += '<section class="hero"><div class="eyebrow">Start with a decision</div><h2>No task is selected yet.</h2><p>Review what is waiting or does not fit before changing the budget or a commitment.</p></section>'
    body += (
        '<div class="stats" aria-label="Planning minutes">'
        + _stat(report.get("budget_minutes", 0), "Task budget · min")
        + _stat(report.get("planned_minutes", 0), "Selected estimates · min")
        + _stat(report.get("remaining_minutes", 0), "Unallocated · min")
        + '</div><p class="arithmetic">'
        + f'{_e(report.get("budget_minutes", 0))} budget − {_e(report.get("planned_minutes", 0))} selected = {_e(report.get("remaining_minutes", 0))} unallocated minutes.'
        + ' Waiting and deferred tasks are outside the selected total.</p>'
    )
    body += _decisions(report, concerns)
    body += _group("Selected for today", selected, "No tasks selected. A lighter day is a valid plan.", "selected",
                   selected=True, concerns=concerns, worksheet=worksheet is not None)
    body += _group("For later", report.get("deferred"), "No tasks deferred from this plan.", "deferred",
                   concerns=concerns, worksheet=worksheet is not None)
    body += _group("Waiting", report.get("blocked"), "No waiting tasks in this plan.", "waiting",
                   concerns=concerns, worksheet=worksheet is not None)
    body += _review_tools(report, worksheet is not None)
    body += '<section class="section" id="context"><h2>How this plan was put together</h2>'
    if report.get("tradeoffs"):
        body += '<ul>' + "".join(f'<li>{_e(item)}</li>' for item in report["tradeoffs"]) + '</ul>'
    body += (
        '<p>Estimated minutes are planning inputs, not measured work or time saved. This plan does not '
        'check your calendar or guarantee that deadlines can be met.</p></section>'
        '<footer class="footer"><p>Local snapshot. No workspace changes occur when you open this report. '
        'Exported responses are proposals for separate CLI preview and apply. Regenerate after changes.</p></footer>'
    )
    return _document("Daily plan", body, [("overview", "Today at a glance"), ("decisions", "Decisions"),
                     ("selected", "Selected"), ("deferred", "For later"), ("waiting", "Waiting"),
                     ("worksheet", "Your review"), ("context", "Plan context")], worksheet)


def render_review(report):
    """Render recorded outcomes while keeping estimates distinct from measurements."""
    completed = report.get("completed") or []
    open_tasks = report.get("open") or []
    dropped = report.get("dropped") or []
    period = "Since " + _text(report["since"]) if report.get("since") else "All recorded completions"
    body = (
        '<header id="overview"><div class="eyebrow">Your review</div><h1>Take stock. Choose what comes next.</h1>'
        f'<p class="meta">{_e(period)} · State revision {_e(report.get("revision", "unknown"))}</p>'
        '<p class="intro">A record of task outcomes, without a productivity score. '
        'Unfinished work stays available for your next plan.</p></header><div class="stats">'
        + _stat(len(completed), "Tasks recorded complete")
        + _stat(report.get("total_completed_minutes", 0), "Completed task estimates · min")
        + _stat(len(open_tasks), "Tasks still open")
        + '</div>'
        + _group("Completed", completed, "No tasks recorded complete in this review.", "completed")
        + _group("Still open", open_tasks, "No open tasks in this snapshot.", "open")
        + _group("Dropped", dropped, "No dropped tasks in this review.", "dropped")
        + '<footer class="footer"><p>Minutes attached to completed tasks are their estimates. '
        'They are not measured working time or evidence of time saved.</p>'
        '<p>Read-only local snapshot. Recording or reviewing an outcome sends no messages '
        'and does not change any external system.</p></footer>'
    )
    return _document("Review", body, [("overview", "Review at a glance"), ("completed", "Completed"),
                                     ("open", "Still open"), ("dropped", "Dropped")])


_MISSING = object()
_FIELD_LABELS = {
    "id": "Task ID", "title": "Title", "minutes": "Estimate · minutes",
    "priority": "Priority", "due": "Deadline", "not_before": "Available from",
    "status": "Status", "notes": "Notes", "blocked_by": "Waiting reason",
    "completed": "Completed on",
}


def _value(value):
    """Use JSON notation to distinguish null, absent fields, strings and numbers."""
    if value is _MISSING:
        return '<span class="muted">Field not present</span>'
    if value is None:
        return '<span class="muted">None</span>'
    return _e(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _plan_consequences(plan, label):
    body = (f'<section><h3>{_e(label)}</h3>'
            f'<p class="meta">{_e(plan.get("date"))} · Revision {_e(plan.get("revision"))}</p>'
            f'<p>{_e(plan.get("budget_minutes"))} budget − {_e(plan.get("planned_minutes"))} selected = '
            f'{_e(plan.get("remaining_minutes"))} unallocated min</p>')
    for group, title in (("selected", "Selected"), ("deferred", "For later"), ("blocked", "Waiting")):
        entries = plan.get(group) or []
        body += f'<h4>{title} · {len(entries)}</h4><ul class="flow-list">'
        for entry in entries:
            task = entry.get("task", entry)
            body += (f'<li><code>{_e(task.get("id"))}</code><strong>{_e(task.get("title"))}</strong>'
                     f'<p>{_e(task.get("minutes"))} estimated min</p><p>{_e(entry.get("reason"))}</p></li>')
        body += '</ul>' if entries else '</ul><p class="muted">None in this group.</p>'
    concerns = assess_plan(plan)
    if concerns:
        body += '<h4>Planning concerns</h4><ul>'
        body += "".join(f'<li><code>{_e(item.get("task_id"))}</code>: {_e(item.get("message"))} {_e(item.get("question"))}</li>' for item in concerns)
        body += '</ul>'
    for tradeoff in plan.get("tradeoffs") or []:
        body += f'<p class="help">{_e(tradeoff)}</p>'
    return body + '</section>'


def render_preview(preview):
    """Show exact snapshot diffs, with optional same-input plan consequences."""
    before = {task["id"]: task for task in preview.get("before", {}).get("tasks", [])}
    after = {task["id"]: task for task in preview.get("after", {}).get("tasks", [])}
    task_ids = list(dict.fromkeys(list(before) + list(after)))
    changed = [tid for tid in task_ids if before.get(tid) != after.get(tid)]
    body = (
        '<header id="overview"><div class="eyebrow">Change preview · proposal only</div>'
        '<h1>See what would change.</h1>'
        f'<p class="meta">Base revision {_e(preview.get("base_revision"))} → Proposed revision {_e(preview.get("proposed_revision"))}</p>'
        '<p class="intro">These are proposed changes, not applied changes. The comparison below comes from '
        'the before and after snapshots. Your saved workspace has not changed.</p></header>'
        '<div class="stats">'
        + _stat(len(preview.get("actions") or []), "Proposed actions")
        + _stat(len(changed), "Tasks with factual changes")
        + _stat(len([tid for tid in after if tid not in before]), "New tasks")
        + '</div><section class="section notice"><h2>Before you apply</h2>'
        '<p>Check the field changes and the resulting plan. A preview does not approve the proposal. '
        'Apply is a separate explicit step, and the CLI checks the workspace revision again.</p></section>'
        '<section class="section" id="changes"><h2>Exact task changes</h2>'
    )
    if not changed:
        body += '<p class="empty">No task fields differ between the supplied snapshots.</p>'
    for tid in changed:
        left, right = before.get(tid), after.get(tid)
        state = "New task" if left is None else "Removed from snapshot" if right is None else "Changed task"
        task = right if right is not None else left
        body += (f'<article class="task section" id="{_anchor(tid)}"><div class="task-top"><code>{_e(tid)}</code>'
                 f'<span class="tag">{state}</span></div><h3>{_e(task.get("title", "Untitled task"))}</h3>'
                 '<ul class="diff-list">')
        keys = list(dict.fromkeys(list(left or {}) + list(right or {})))
        for key in keys:
            old = left.get(key, _MISSING) if left is not None else _MISSING
            new = right.get(key, _MISSING) if right is not None else _MISSING
            if old == new:
                continue
            body += (
                f'<li><strong>{_e(_FIELD_LABELS.get(key, key))}</strong><div class="diff-values">'
                f'<div><span class="value-label">Before</span><div class="value">{_value(old)}</div></div>'
                f'<div><span class="value-label">Proposed</span><div class="value">{_value(new)}</div></div>'
                '</div></li>'
            )
        body += '</ul></article>'
    body += '</section><section class="section" id="consequences"><h2>What it means for the plan</h2>'
    if preview.get("before_plan") is not None and preview.get("after_plan") is not None:
        body += '<div class="pair">' + _plan_consequences(preview["before_plan"], "Before") + _plan_consequences(preview["after_plan"], "With the proposal") + '</div>'
    else:
        body += '<p class="empty">Plan consequences were not calculated for this preview. Generate a preview with an explicit date and minute budget to compare what fits.</p>'
    body += (
        '</section><section class="section" id="actions"><h2>Proposed action data</h2>'
        '<details><summary>Inspect the proposal</summary><pre>'
        + _e(json.dumps(preview.get("actions") or [], ensure_ascii=False, indent=2))
        + '</pre></details></section><footer class="footer">'
        '<p>Preview only. Nothing applied. The comparison is a snapshot, not a live view of your workspace. '
        'Re-preview if the state changes before applying.</p>'
        '<p>Estimated minutes are planning inputs, not measured working time or evidence of time saved.</p></footer>'
    )
    return _document("Change preview", body, [("overview", "Proposal at a glance"), ("changes", "Exact changes"),
                     ("consequences", "Plan consequences"), ("actions", "Action data")])


def _md(value):
    text = escape(" ".join(_text(value).split()), quote=False)
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~:\-])", r"\\\1", text)


def render_markdown(state):
    """Return a human-readable snapshot, not an importable replacement for JSON."""
    lines = [
        "# Daily Ops task snapshot", "",
        f'State revision: {_md(state.get("revision", "unknown"))}', "",
        "Human-readable view. Use the JSON export for validated import and resume.", "",
    ]
    tasks = state.get("tasks") or []
    if not tasks:
        lines.extend(["No tasks yet.", ""])
    for task in tasks:
        marker = "x" if task.get("status") in ("done", "completed") else " "
        lines.append(f'- [{marker}] {_md(task.get("title", "Untitled task"))}')
        details = [f'ID: {_md(task.get("id", ""))}', f'Status: {_md(task.get("status", "open"))}']
        if task.get("minutes") is not None:
            details.append(f'{_md(task["minutes"])} estimated min')
        for key, label in (("priority", "Priority"), ("due", "Due"), ("not_before", "Available"), ("completed", "Completed")):
            if task.get(key) is not None:
                details.append(f'{label}: {_md(task[key])}')
        lines.append("  " + " · ".join(details))
        if task.get("blocked_by"):
            lines.append("  Waiting reason: " + _md(task["blocked_by"]))
        if task.get("notes"):
            lines.append("  Notes: " + _md(task["notes"]))
        lines.append("")
    lines.extend(["Estimates are not measured work or time saved.", ""])
    return "\n".join(lines)
