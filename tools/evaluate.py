#!/usr/bin/env python3
"""Run reproducible fictional scenarios; never infer human productivity gains."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "daily-ops" / "scripts"))
from daily_ops.core import Workspace, make_plan  # noqa: E402
from daily_ops import __version__  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_scenarios() -> dict:
    fixture = json.loads((ROOT / "examples" / "scenarios.json").read_text(encoding="utf-8"))
    outcomes = []
    for scenario in fixture["scenarios"]:
        with tempfile.TemporaryDirectory(prefix="daily-ops-eval-") as temp:
            workspace = Workspace(Path(temp).resolve() / "tasks")
            state = workspace.init()
            proposal = {
                "schema_version": 1,
                "base_revision": state["revision"],
                "actions": [{"action": "add", **task} for task in scenario["tasks"]],
            }
            preview = workspace.preview(proposal, today=fixture["date"])
            require(workspace.load() == state, "Preview mutated the original state")
            require(preview["proposed_revision"] > state["revision"], "Preview lacks a future revision")
            state = workspace.apply(proposal, today=fixture["date"])
            before = json.dumps(state, sort_keys=True)
            report = make_plan(state, fixture["date"], scenario["budget"])
            selected = [entry["task"]["id"] for entry in report["selected"]]
            blocked = [entry["task"]["id"] for entry in report["blocked"]]
            require(selected == scenario["selected"], f"{scenario['id']}: unexpected selection {selected}")
            require(blocked == scenario["blocked"], f"{scenario['id']}: waiting work changed")
            require(report["planned_minutes"] == scenario["planned_minutes"], "Incorrect planned minutes")
            require(report["planned_minutes"] <= scenario["budget"], "Plan exceeded capacity")
            require(json.dumps(workspace.load(), sort_keys=True) == before, "Planning changed task state")
            covered = {
                entry["task"]["id"]
                for group in ("selected", "deferred", "blocked")
                for entry in report[group]
            }
            require(covered == {task["id"] for task in state["tasks"]}, "Plan hid an unfinished task")
            if "interruption_budget" in scenario:
                reduced = make_plan(state, fixture["date"], scenario["interruption_budget"])
                require([entry["task"]["id"] for entry in reduced["selected"]] == scenario["interruption_selected"], "Interruption did not produce expected tradeoff")
                require(json.dumps(workspace.load(), sort_keys=True) == before, "Replanning changed deadlines or tasks")
            completed = selected[0]
            workspace.transact([{"action": "complete", "id": completed}], base_revision=state["revision"], today=fixture["date"])
            resumed = Workspace(Path(temp).resolve() / "tasks").load()
            again = make_plan(resumed, fixture["date"], scenario["budget"])
            require(completed not in [entry["task"]["id"] for entry in again["selected"]], "Completed work returned after resume")
            require(len(resumed["tasks"]) == len(scenario["tasks"]), "Resume lost task records")
            outcomes.append({
                "scenario": scenario["id"], "status": "passed",
                "input_tasks": len(state["tasks"]), "budget_minutes": scenario["budget"],
                "planned_minutes": report["planned_minutes"], "selected": selected,
                "waiting": blocked, "visible_unselected": len(report["deferred"]) + len(report["blocked"]),
                "state_unchanged_by_planning": True, "resume_verified": True,
                "interruption_tested": "interruption_budget" in scenario,
            })
    return {
        "schema_version": 1, "release": __version__, "fixture_date": fixture["date"],
        "evidence_type": "deterministic fictional acceptance scenarios",
        "claims": ["Plans respect supplied task capacity", "Unfinished work remains visible", "Planning preserves state", "Explicit completion persists across sessions"],
        "not_measured": ["time saved", "stress reduction", "human adoption", "native host skill discovery"],
        "results": outcomes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optionally save the fictional scenario evidence as JSON")
    args = parser.parse_args()
    result = run_scenarios()
    encoded = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
