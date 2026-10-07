"""Small command-line boundary with structured, non-sensitive failures."""

from __future__ import annotations

import argparse
import json
import sys

from .core import DailyOpsError, Workspace, load_change, make_plan, make_review
from .plan_checks import MALFORMED_PLAN_CODES, check_plan, load_plan


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise DailyOpsError("usage", message)


def _parser():
    parser = Parser(description="Local Daily Ops planning. Choose a workspace explicitly.")
    parser.add_argument("--workspace", required=True, help="Folder containing .daily-ops/state.json")
    parser.add_argument("--json", action="store_true", help="Emit JSON (the default for data commands)")
    commands = parser.add_subparsers(dest="command", required=True, parser_class=Parser)
    commands.add_parser("init", help="Initialize without overwriting existing state")
    commands.add_parser("list", help="Show all task data")
    for name in ("add", "update"):
        command = commands.add_parser(name)
        command.add_argument("title" if name == "add" else "id")
        if name == "update":
            command.add_argument("--title")
        command.add_argument("--minutes", type=int, required=name == "add")
        command.add_argument("--priority", choices=("high", "normal", "low"))
        command.add_argument("--due")
        command.add_argument("--not-before")
        command.add_argument("--notes")
        if name == "add":
            command.add_argument("--blocked-by", help="Explicit waiting reason")
        if name == "update":
            command.add_argument("--clear-due", action="store_true")
            command.add_argument("--clear-not-before", action="store_true")
            command.add_argument("--clear-notes", action="store_true")
    for name in ("complete", "reopen", "defer", "block", "unblock", "drop"):
        command = commands.add_parser(name)
        command.add_argument("id")
        if name == "defer":
            command.add_argument("--until", required=True)
        elif name == "block":
            command.add_argument("--reason", required=True)
    plan = commands.add_parser("plan")
    plan.add_argument("--date", required=True)
    plan.add_argument("--minutes", required=True, type=int)
    plan.add_argument("--output", help="Save an HTML report at this workspace-relative path")
    review = commands.add_parser("review")
    review.add_argument("--since")
    review.add_argument("--output", help="Save an HTML report at this workspace-relative path")
    export = commands.add_parser("export")
    export.add_argument("--format", choices=("json", "markdown"), default="json")
    for name in ("preview", "apply", "lint-plan"):
        command = commands.add_parser(name)
        command.add_argument("file")
        if name == "preview":
            command.add_argument("--output", help="Save an HTML preview at this workspace-relative path")
            command.add_argument("--date", help="Plan comparison date; requires --minutes")
            command.add_argument("--minutes", type=int, help="Plan comparison budget; requires --date")
    for subparser in commands.choices.values():
        subparser.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                               help="Emit machine-readable JSON")
    return parser


def _markdown(state):
    """Portable export preserving all fields as a JSON block for lossless recovery."""
    # Escape backticks as JSON Unicode sequences so task data cannot close a fence.
    data = json.dumps(state, ensure_ascii=False, indent=2).replace("`", "\\u0060")
    from .render import render_markdown
    return render_markdown(state) + f"\n## Portable JSON snapshot\n\n```json\n{data}\n```\n"


def _dispatch(args):
    workspace = Workspace(args.workspace)
    command = args.command
    if command == "init":
        return workspace.init()
    if command in ("list", "export"):
        state = workspace.load()
        if command == "export" and args.format == "markdown":
            return _markdown(state)
        return state
    if command in ("plan", "review"):
        from .render import render_plan, render_review
        state = workspace.load()
        report = make_plan(state, args.date, args.minutes) if command == "plan" else make_review(state, args.since)
        if args.output:
            if not args.output.lower().endswith(".html"):
                raise DailyOpsError("usage", "Report output must use an .html filename inside the workspace.")
            html = render_plan(report) if command == "plan" else render_review(report)
            report["report_path"] = workspace.write_report(args.output, html)
        return report
    if command == "lint-plan":
        result = check_plan(workspace.load(), load_plan(args.file))
        malformed = next((error for error in result["errors"]
                          if error["code"] in MALFORMED_PLAN_CODES), None)
        if malformed:
            raise DailyOpsError("invalid_data", malformed["message"])
        return result
    if command == "preview":
        if (args.date is None) != (args.minutes is None):
            raise DailyOpsError("usage", "Preview --date and --minutes must be supplied together.")
        if args.output and not args.output.lower().endswith(".html"):
            raise DailyOpsError("usage", "Report output must use an .html filename inside the workspace.")
        result = workspace.preview(load_change(args.file))
        if args.date is not None:
            result["before_plan"] = make_plan(result["before"], args.date, args.minutes)
            result["after_plan"] = make_plan(result["after"], args.date, args.minutes)
        if args.output:
            from .render import render_preview
            result["report_path"] = workspace.write_report(args.output, render_preview(result))
        return result
    if command == "apply":
        return workspace.apply(load_change(args.file))
    action = {"action": command}
    for field in ("id", "title", "minutes", "priority", "due", "not_before", "notes", "blocked_by", "until", "reason"):
        value = getattr(args, field, None)
        if value is not None:
            action[field] = value
    if command == "update":
        for field in ("due", "not_before", "notes"):
            if getattr(args, "clear_" + field):
                if field in action:
                    raise DailyOpsError("usage", f"Cannot set and clear {field} in the same command.")
                action[field] = None
    return workspace.transact([action])


def main(argv=None):
    try:
        args = _parser().parse_args(argv)
        result = _dispatch(args)
        print(result if isinstance(result, str) else json.dumps(result, ensure_ascii=True, indent=2))
        return 1 if args.command == "lint-plan" and not result["ok"] else 0
    except DailyOpsError as exc:
        print(json.dumps({"error": {"code": exc.code, "message": exc.message}}), file=sys.stderr)
        return 2
    except OSError as exc:
        code = "not_found" if isinstance(exc, FileNotFoundError) else "permission_denied" if isinstance(exc, PermissionError) else "io_error"
        # OS exception strings may include private paths. Keep diagnostics scoped.
        print(json.dumps({"error": {"code": code, "message": "Could not access the selected local files. Check the path and permissions."}}), file=sys.stderr)
        return 2
