"""Rebuild public HTML examples from a fictional fixture and the actual runtime."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/daily-ops/scripts"))

from daily_ops.core import Workspace, make_plan
from daily_ops.plan_checks import check_plan
from daily_ops.render import render_plan, render_preview


def build_examples(output: Path) -> dict:
    """Use temporary state; generated reports never contain a host path."""
    fixture = json.loads((ROOT / "examples/plan-review.json").read_text(encoding="utf-8"))
    try:
        from .package import reject_symlinks
    except ImportError:
        from package import reject_symlinks
    reject_symlinks(output.absolute())
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="daily-ops-example-") as temporary:
        workspace = Workspace(Path(temporary).resolve())
        workspace.init()
        for action in fixture["tasks"]:
            workspace.transact([action], today=fixture["date"])
        state_file = Path(temporary) / ".daily-ops/state.json"
        before_bytes = state_file.read_bytes()
        plan = make_plan(workspace.load(), fixture["date"], fixture["minutes"])
        checked = check_plan(workspace.load(), plan)
        if not checked["ok"]:
            raise ValueError("Generated example failed plan validation")
        preview = workspace.preview(fixture["proposal"], today=fixture["date"])
        preview["before_plan"] = plan
        preview["after_plan"] = make_plan(preview["after"], fixture["date"], fixture["minutes"])
        if state_file.read_bytes() != before_bytes:
            raise ValueError("Read-only example generation changed task state")
        for name, html in (("plan.html", render_plan(plan)), ("change.html", render_preview(preview))):
            path = output / name
            reject_symlinks(path.absolute())
            path.write_text(html, encoding="utf-8", newline="\n")
        summary = {
            "fictional": True, "date": fixture["date"], "revision": plan["revision"],
            "budget_minutes": plan["budget_minutes"],
            "before_selected": [item["task"]["id"] for item in plan["selected"]],
            "before_minutes": plan["planned_minutes"],
            "after_selected": [item["task"]["id"] for item in preview["after_plan"]["selected"]],
            "after_minutes": preview["after_plan"]["planned_minutes"],
            "advisory_codes": [item["code"] for item in checked["warnings"]],
            "state_unchanged": True,
        }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "site/examples")
    args = parser.parse_args()
    print(json.dumps(build_examples(args.output), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
