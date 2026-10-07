"""Read-only plan integrity checks and factual planning advisories."""

from __future__ import annotations

import os
from pathlib import Path

from .core import (
    DailyOpsError, SCHEMA_VERSION, _decode, _directory, _read_at, iso_date,
    make_plan, validate_state,
)


MALFORMED_PLAN_CODES = frozenset({
    "invalid_report", "invalid_kind", "invalid_schema", "invalid_revision",
    "invalid_date", "invalid_budget",
})
CATEGORIES = ("selected", "deferred", "blocked")


def load_plan(path):
    """Load bounded UTF-8 JSON using the runtime's regular-file protections."""
    path = Path(os.path.expanduser(os.fspath(path)))
    with _directory(path.parent) as directory:
        return _decode(_read_at(directory, path.name))


def _date(value):
    try:
        return iso_date(value)
    except DailyOpsError:
        return None


def assess_plan(plan):
    """Return deterministic advisories from facts, without modifying the plan.

    Sparse display fixtures are tolerated. These advisories are not an integrity
    verdict; check_plan compares a full report against the actual workspace.
    """
    if not isinstance(plan, dict):
        return []
    date = _date(plan.get("date"))
    budget = plan.get("budget_minutes")
    budget = budget if type(budget) is int and 0 <= budget <= 1440 else None
    advisories = []
    seen = set()

    def add(code, task, message, question):
        key = (code, task["id"])
        if key not in seen:
            seen.add(key)
            advisories.append({
                "code": code, "task_id": task["id"], "title": task["title"],
                "message": message, "question": question,
            })

    for category in CATEGORIES:
        entries = plan.get(category, [])
        if not isinstance(entries, list):
            continue
        for entry in entries:
            task = entry.get("task") if isinstance(entry, dict) else None
            if (not isinstance(task, dict) or not isinstance(task.get("id"), str)
                    or not isinstance(task.get("title"), str)):
                continue
            due = _date(task.get("due"))
            available = _date(task.get("not_before"))
            waiting = task.get("blocked_by")
            urgent = due and date and due <= date
            if urgent and category != "selected":
                if isinstance(waiting, str) and waiting.strip():
                    add("waiting_urgent", task,
                        f"Due {due} and still waiting: {waiting}",
                        "Who can resolve the wait, or does the due date need an explicit change?")
                else:
                    add("urgent_omission", task,
                        f"Due {due} but not scheduled in this plan.",
                        "Should you add time, revise the estimate, or explicitly move the due date?")
            if due and available and available > due:
                add("availability_after_deadline", task,
                    f"Available from {available}, after its due date of {due}.",
                    "Should availability or the due date be explicitly changed?")
            minutes = task.get("minutes")
            if type(minutes) is int and budget is not None and minutes > budget:
                add("oversized_task", task,
                    f"The {minutes}-minute estimate exceeds the {budget}-minute plan budget.",
                    "Can you reserve more time, or explicitly revise the task estimate?")
    return advisories


def _same(actual, expected):
    """Compare JSON values exactly, including integer versus boolean types."""
    pending = [(actual, expected)]
    while pending:
        actual, expected = pending.pop()
        if type(actual) is not type(expected):
            return False
        if isinstance(expected, dict):
            if actual.keys() != expected.keys():
                return False
            pending.extend((actual[key], value) for key, value in expected.items())
        elif isinstance(expected, list):
            if len(actual) != len(expected):
                return False
            pending.extend(zip(actual, expected))
        elif actual != expected:
            return False
    return True


def check_plan(state, report):
    """Check a report against the canonical current-state plan without writes."""
    validate_state(state)
    result = {
        "kind": "plan_check", "ok": False, "revision": state["revision"],
        "errors": [], "warnings": [],
    }
    errors = result["errors"]

    def error(code, message, field=None, task_id=None):
        item = {"code": code, "message": message}
        if field is not None:
            item["field"] = field
        if task_id is not None:
            item["task_id"] = task_id
        errors.append(item)

    if not isinstance(report, dict):
        error("invalid_report", "Plan report must be a JSON object.")
        return result
    if report.get("kind") != "plan":
        error("invalid_kind", "Report kind must be plan.", "kind")
    if type(report.get("schema_version")) is not int or report["schema_version"] != SCHEMA_VERSION:
        error("invalid_schema", "Plan schema_version must be the supported integer version.", "schema_version")
    revision = report.get("revision")
    if type(revision) is not int or revision < 0:
        error("invalid_revision", "Plan revision must be a nonnegative integer.", "revision")
    date = _date(report.get("date"))
    if date is None:
        error("invalid_date", "Plan date must be a valid YYYY-MM-DD calendar date.", "date")
    budget = report.get("budget_minutes")
    if type(budget) is not int or not 0 <= budget <= 1440:
        error("invalid_budget", "Plan budget_minutes must be an integer from 0 to 1440.", "budget_minutes")
    if date is None or type(budget) is not int or not 0 <= budget <= 1440:
        return result

    expected = make_plan(state, date, budget)
    result["warnings"] = assess_plan(expected)
    if type(revision) is int and revision >= 0 and revision != state["revision"]:
        error("stale_revision", "Plan revision does not match the current workspace. Generate a fresh plan.", "revision")
    for field in sorted(set(report) - set(expected) - {"report_path"}):
        error("unexpected_field", "Plan contains an unsupported field.", field)
    if "report_path" in report and (not isinstance(report["report_path"], str) or not report["report_path"].strip()):
        error("invalid_report_path", "Presentation report_path must be a nonempty string.", "report_path")
    for field in expected:
        if field not in report:
            error("missing_field", "Plan is missing a canonical field.", field)
    for field in ("planned_minutes", "remaining_minutes", "conflicts", "tradeoffs"):
        if field in report and not _same(report[field], expected[field]):
            code = "arithmetic_mismatch" if field.endswith("_minutes") else field + "_mismatch"
            error(code, "Plan field differs from the canonical current-state plan.", field)

    expected_entries = {
        entry["task"]["id"]: (category, entry)
        for category in CATEGORIES for entry in expected[category]
    }
    seen = set()
    for category in CATEGORIES:
        if category not in report:
            continue
        entries = report[category]
        if not isinstance(entries, list):
            error("invalid_category", "Plan task groups must be arrays.", category)
            continue
        actual_order = []
        for index, entry in enumerate(entries):
            location = f"{category}[{index}]"
            if not isinstance(entry, dict):
                error("invalid_entry", "Plan entry must contain a task snapshot and reason.", location)
                continue
            if set(entry) != {"task", "reason"}:
                error("entry_fields_mismatch", "Plan entry must contain exactly task and reason.", location)
            task = entry.get("task")
            task_id = task.get("id") if isinstance(task, dict) else None
            if not isinstance(task_id, str):
                error("invalid_task", "Plan entry must contain a task snapshot with its stable ID.", location + ".task")
                continue
            actual_order.append(task_id)
            if task_id in seen:
                error("duplicate_task", "A task appears more than once in the plan.", location, task_id)
            seen.add(task_id)
            canonical = expected_entries.get(task_id)
            if canonical is None:
                error("unknown_task", "Task is not open in the current workspace.", location, task_id)
                continue
            expected_category, expected_entry = canonical
            if category != expected_category:
                error("selection_mismatch", "Task is assigned to the wrong plan group.", location, task_id)
            if not _same(task, expected_entry["task"]):
                error("task_snapshot_mismatch", "Task snapshot differs from the current workspace.", location + ".task", task_id)
            if not _same(entry.get("reason"), expected_entry["reason"]):
                error("reason_mismatch", "Task reason differs from the canonical planner reason.", location + ".reason", task_id)
        if actual_order != [entry["task"]["id"] for entry in expected[category]]:
            error("task_order_mismatch", "Task membership or order differs from the canonical plan.", category)
    for task_id in expected_entries:
        if task_id not in seen:
            error("missing_task", "An open workspace task is missing from the plan.", task_id=task_id)
    result["ok"] = not errors
    return result
