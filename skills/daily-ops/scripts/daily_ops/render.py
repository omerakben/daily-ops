"""Readable, self-contained views of Daily Ops snapshots.

Renderers never mutate state, execute task content, or load remote resources.
"""

from html import escape
import re


_CSS = """
:root{color-scheme:light;--paper:#f6f5f0;--ink:#202c35;--muted:#51616a;--line:#d3dbd6;--teal:#206658;--blue:#25578a}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:1100px;margin:auto;padding:48px 28px 64px}header{border-bottom:1px solid var(--line);padding-bottom:28px;margin-bottom:28px}
.eyebrow{font-size:.75rem;font-weight:750;letter-spacing:.12em;text-transform:uppercase;color:var(--teal)}h1{font-size:clamp(2rem,5vw,3.3rem);line-height:1.15;letter-spacing:-.04em;margin:12px 0}h2{font-size:1.25rem;margin:0 0 16px}h3{font-size:1rem;line-height:1.5;margin:4px 0 10px}
p{margin:8px 0}.muted,.meta{color:var(--muted)}.intro{max-width:65ch}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:24px 0}.stat{background:white;border:1px solid var(--line);border-radius:12px;padding:18px}.stat strong{display:block;font-size:2rem;font-weight:650;letter-spacing:-.03em}.stat span{font-size:.85rem;color:var(--muted)}
.columns{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(0,1fr);gap:28px}.column{min-width:0}.group{margin-bottom:28px}.task-list{list-style:none;padding:0;margin:0;display:grid;gap:12px}.task{border:1px solid var(--line);border-radius:12px;background:#fff;padding:18px;overflow-wrap:anywhere}.task .meta{font-size:.8rem}.task .reason{font-size:.9rem;margin-top:12px}.task .notes{white-space:pre-wrap;font-size:.9rem}.task .request{font-size:.82rem;margin-top:12px;border-top:1px solid var(--line);padding-top:12px}.task .request code{display:block;margin-top:4px;user-select:all}.selected .task{border-left:4px solid var(--teal)}.count{font-weight:400;color:var(--muted);font-size:.9rem;margin-left:8px}.empty{border:1px dashed var(--line);border-radius:12px;padding:18px;color:var(--muted)}
.notice{border:1px solid #d7bf8e;background:#fff8e8;border-radius:12px;padding:18px;margin:24px 0}.notice h2{font-size:1rem;margin-bottom:8px}.notice ul,.tradeoffs ul{padding-left:22px;margin:0}.tradeoffs{margin:24px 0}.footer{border-top:1px solid var(--line);padding-top:20px;margin-top:30px;font-size:.85rem;color:var(--muted)}code{font: .86em ui-monospace,SFMono-Regular,Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere}a{color:var(--blue)}a:focus-visible{outline:3px solid var(--blue);outline-offset:4px}.skip{position:absolute;left:12px;top:-100px;background:white;padding:10px}.skip:focus{top:12px}
@media(max-width:700px){main{padding:28px 18px}.columns{grid-template-columns:1fr;gap:0}.stats{gap:8px}.stat{padding:12px}.stat strong{font-size:1.6rem}.stat span{font-size:.75rem}}
@media print{body{background:white}main{padding:0;max-width:none}.columns{display:block}.stats{display:flex}.stat{flex:1}.task,.notice{break-inside:avoid}.skip{display:none}h2,h3{break-after:avoid}.request{display:none}}
"""


def _text(value):
    return "" if value is None else str(value)


def _e(value):
    return escape(_text(value), quote=True)


def _document(title, body):
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="referrer" content="no-referrer">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
        "style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'\">"
        f'<title>{_e(title)} · Daily Ops</title><style>{_CSS}</style></head>'
        '<body><a class="skip" href="#main">Skip to report</a>'
        f'<main id="main">{body}</main></body></html>\n'
    )


def _task_html(entry, selected=False):
    task = entry.get("task", entry)
    task_id = task.get("id", "")
    parts = [f'<code>{_e(task_id)}</code>']
    if task.get("minutes") is not None:
        parts.append(f'{_e(task["minutes"])} estimated min')
    if task.get("priority") is not None:
        parts.append(f'Priority {_e(task["priority"])}')
    if task.get("due"):
        parts.append(f'Due {_e(task["due"])}')
    if task.get("not_before"):
        parts.append(f'Available {_e(task["not_before"])}')
    if task.get("status"):
        parts.append(f'Status: {_e(task["status"])}')
    if task.get("completed"):
        parts.append(f'Completed {_e(task["completed"])}')
    blocked_by = task.get("blocked_by") or []
    if blocked_by:
        if not isinstance(blocked_by, list):
            blocked_by = [blocked_by]
        parts.append("Waiting reason: " + ", ".join(_e(item) for item in blocked_by))
    content = (
        f'<li class="task"><div class="meta">{" · ".join(parts)}</div>'
        f'<h3>{_e(task.get("title", "Untitled task"))}</h3>'
    )
    if task.get("notes"):
        content += f'<p class="notes">{_e(task["notes"])}</p>'
    if entry.get("reason"):
        content += f'<p class="reason">{_e(entry["reason"])}</p>'
    if selected:
        content += (
            '<p class="request">Copy into your assistant if you want help:'
            f'<code>{_e("Help me start task " + _text(task_id) + ". Keep its status unchanged.")}</code></p>'
        )
    return content + "</li>"


def _group(title, entries, empty, selected=False):
    entries = entries or []
    marker = " selected" if selected else ""
    content = f'<section class="group{marker}"><h2>{_e(title)} <span class="count">{len(entries)}</span></h2>'
    if entries:
        content += '<ul class="task-list">' + "".join(_task_html(item, selected) for item in entries) + "</ul>"
    else:
        content += f'<p class="empty">{_e(empty)}</p>'
    return content + "</section>"


def _stat(value, label):
    return f'<div class="stat"><strong>{_e(value)}</strong><span>{_e(label)}</span></div>'


def render_plan(report):
    """Render a read-only plan without trusting any text in the report."""
    body = (
        '<header><div class="eyebrow">Daily Ops · Your daily plan</div>'
        '<h1>A plan for the time you have.</h1>'
        f'<p class="muted">{_e(report.get("date", "Date not supplied"))} · State revision {_e(report.get("revision", "unknown"))}</p>'
        '<p class="intro">Start with what fits. Keep the rest visible. This is a snapshot of estimated work; '
        'generating it does not change your tasks.</p></header>'
        '<div class="stats" aria-label="Planning minutes">'
        + _stat(report.get("budget_minutes", 0), "Task budget · min")
        + _stat(report.get("planned_minutes", 0), "Selected estimates · min")
        + _stat(report.get("remaining_minutes", 0), "Unallocated · min")
        + "</div>"
    )
    conflicts = report.get("conflicts") or []
    if conflicts:
        body += '<section class="notice"><h2>Needs a decision</h2><ul>'
        body += "".join(
            f'<li><code>{_e(item.get("id", ""))}</code>: {_e(item.get("reason", ""))}</li>'
            for item in conflicts
        )
        body += "</ul></section>"
    body += '<div class="columns"><div class="column">'
    body += _group("Start here", report.get("selected"), "No tasks selected. A lighter day is a valid plan.", selected=True)
    body += '</div><div class="column">'
    body += _group("For later", report.get("deferred"), "No tasks deferred from this plan.")
    body += _group("Waiting", report.get("blocked"), "No waiting tasks in this plan.")
    body += "</div></div>"
    if report.get("tradeoffs"):
        body += '<section class="tradeoffs"><h2>How to read this plan</h2><ul>'
        body += "".join(f'<li>{_e(item)}</li>' for item in report["tradeoffs"])
        body += "</ul></section>"
    body += (
        '<footer class="footer"><p>Estimated minutes are planning inputs, not measured work or time saved. '
        'This plan does not check your calendar or guarantee that deadlines can be met.</p>'
        '<p>Read-only local report. To update a task, use its ID in Daily Ops or ask your assistant. '
        'Regenerate this report after changes.</p></footer>'
    )
    return _document("Daily plan", body)


def render_review(report):
    """Render recorded outcomes while keeping estimates distinct from measurements."""
    completed = report.get("completed") or []
    open_tasks = report.get("open") or []
    dropped = report.get("dropped") or []
    period = "Since " + _text(report["since"]) if report.get("since") else "All recorded completions"
    body = (
        '<header><div class="eyebrow">Daily Ops · Review</div><h1>Take stock. Choose what comes next.</h1>'
        f'<p class="muted">{_e(period)} · State revision {_e(report.get("revision", "unknown"))}</p>'
        '<p class="intro">A record of task outcomes, without a productivity score. '
        'Unfinished work stays available for your next plan.</p></header><div class="stats">'
        + _stat(len(completed), "Tasks recorded complete")
        + _stat(report.get("total_completed_minutes", 0), "Completed task estimates · min")
        + _stat(len(open_tasks), "Tasks still open")
        + '</div><div class="columns"><div class="column">'
        + _group("Completed", completed, "No tasks recorded complete in this review.")
        + '</div><div class="column">'
        + _group("Still open", open_tasks, "No open tasks in this snapshot.")
        + _group("Dropped", dropped, "No dropped tasks in this review.")
        + '</div></div><footer class="footer"><p>Minutes attached to completed tasks are their estimates. '
        'They are not measured working time or evidence of time saved.</p>'
        '<p>Read-only local snapshot. Recording or reviewing an outcome sends no messages '
        'and does not change any external system.</p></footer>'
    )
    return _document("Review", body)


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
