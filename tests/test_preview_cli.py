"""Read-only lint and proposal preview CLI checks using fictional workspaces."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "daily-ops" / "scripts"
RUN = SCRIPTS / "run.py"
sys.path.insert(0, str(SCRIPTS))
from daily_ops.core import MAX_FILE_BYTES, make_plan


class PreviewCliCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.workspace = self.root / "workspace"
        self.run_cli("init")

    def tearDown(self):
        self.temporary.cleanup()

    def run_cli(self, *arguments, expected=0):
        result = subprocess.run(
            [sys.executable, str(RUN), "--workspace", str(self.workspace), *arguments],
            text=True, capture_output=True, timeout=15,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        return result

    def write_json(self, name, value):
        target = self.root / name
        target.write_text(json.dumps(value), encoding="utf-8")
        return str(target)

    def saved_state(self):
        path = self.workspace / ".daily-ops" / "state.json"
        return path.read_bytes(), path.stat().st_mtime_ns

    def test_lint_valid_zero_budget_and_read_only_integrity_failure(self):
        self.run_cli("add", "Fictional long task", "--minutes", "50", "--due", "2026-10-07")
        plan = json.loads(self.run_cli("plan", "--date", "2026-10-07", "--minutes", "0").stdout)
        source = self.write_json("plan.json", plan)
        before = self.saved_state()
        result = json.loads(self.run_cli("lint-plan", source, "--json").stdout)
        self.assertTrue(result["ok"])
        self.assertTrue(result["warnings"])
        self.assertEqual(self.saved_state(), before)
        self.assertEqual(json.loads(Path(source).read_text()), plan)
        plan["remaining_minutes"] = 100
        source = self.write_json("plan.json", plan)
        result = json.loads(self.run_cli("lint-plan", source, expected=1).stdout)
        self.assertFalse(result["ok"])
        self.assertIn("arithmetic_mismatch", {error["code"] for error in result["errors"]})
        self.assertEqual(self.saved_state(), before)

    def test_lint_empty_plan_report_path_and_stale_revision(self):
        plan = json.loads(self.run_cli(
            "plan", "--date", "2026-10-07", "--minutes", "0",
            "--output", "reports/plan.html",
        ).stdout)
        self.assertEqual(Path(plan["report_path"]), self.workspace / "reports" / "plan.html")
        source = self.write_json("plan.json", plan)
        self.assertTrue(json.loads(self.run_cli("lint-plan", source).stdout)["ok"])
        self.run_cli("add", "Fictional later task", "--minutes", "10")
        before = self.saved_state()
        result = json.loads(self.run_cli("lint-plan", source, expected=1).stdout)
        self.assertEqual(result["revision"], 1)
        self.assertIn("stale_revision", {item["code"] for item in result["errors"]})
        self.assertEqual(self.saved_state(), before)

    def test_lint_malformed_json_and_header_exit_two_without_writes(self):
        before = self.saved_state()
        samples = [
            b"{", b'{"kind":"plan","kind":"review"}', b'{"x": NaN}',
            b"\xff", b"[" * 1500 + b"]" * 1500, b"{} " + b" " * MAX_FILE_BYTES,
        ]
        for index, raw in enumerate(samples):
            source = self.root / f"malformed-{index}.json"
            source.write_bytes(raw)
            with self.subTest(index=index):
                result = self.run_cli("lint-plan", str(source), expected=2)
                self.assertEqual(result.stdout, "")
                self.assertEqual(json.loads(result.stderr)["error"]["code"], "invalid_data")
                self.assertEqual(self.saved_state(), before)
        plan = json.loads(self.run_cli("plan", "--date", "2026-10-07", "--minutes", "0").stdout)
        for field, value in (("revision", True), ("schema_version", True), ("budget_minutes", True),
                             ("date", "2026-02-30"), ("kind", "review")):
            report = deepcopy(plan)
            report[field] = value
            with self.subTest(field=field):
                result = self.run_cli("lint-plan", self.write_json("header.json", report), expected=2)
                self.assertEqual(result.stdout, "")
                self.assertEqual(json.loads(result.stderr)["error"]["code"], "invalid_data")
        self.assertEqual(self.saved_state(), before)

    def test_lint_io_and_symlink_failures_are_structured(self):
        source = self.root / "missing.json"
        self.run_cli("lint-plan", str(source), expected=2)
        source.symlink_to(self.workspace / ".daily-ops" / "state.json")
        result = self.run_cli("lint-plan", str(source), expected=2)
        self.assertEqual(result.stdout, "")
        self.assertIn("error", json.loads(result.stderr))
        self.run_cli("lint-plan", str(self.workspace), expected=2)

    def test_plain_preview_preserves_existing_json_contract_and_state(self):
        change = {"schema_version": 1, "base_revision": 0, "actions": [
            {"action": "add", "title": "Fictional proposed task", "minutes": 20},
        ]}
        before = self.saved_state()
        result = json.loads(self.run_cli("preview", self.write_json("change.json", change)).stdout)
        self.assertEqual(set(result), {
            "schema_version", "kind", "base_revision", "proposed_revision", "actions", "before", "after",
        })
        self.assertEqual(result["base_revision"], 0)
        self.assertEqual(result["proposed_revision"], 1)
        self.assertEqual(result["before"]["tasks"], [])
        self.assertEqual(result["after"]["tasks"][0]["title"], "Fictional proposed task")
        self.assertEqual(self.saved_state(), before)

    def test_preview_uses_actual_snapshots_for_before_and_after_plans(self):
        self.run_cli("add", "Fictional outline", "--minutes", "30", "--due", "2026-10-07")
        self.run_cli("add", "Fictional waiting task", "--minutes", "20", "--due", "2026-10-07",
                     "--blocked-by", "Fictional response")
        self.run_cli("add", "Fictional follow-up", "--minutes", "15")
        change = {"schema_version": 1, "base_revision": 3, "actions": [
            {"action": "update", "id": "T0001", "minutes": 60},
            {"action": "unblock", "id": "T0002"},
            {"action": "defer", "id": "T0003", "until": "2026-10-08"},
        ]}
        source = self.write_json("change.json", change)
        before = self.saved_state()
        result = json.loads(self.run_cli(
            "preview", source, "--date", "2026-10-07", "--minutes", "45",
            "--output", "reports/change.html",
        ).stdout)
        self.assertEqual(result["before_plan"], make_plan(result["before"], "2026-10-07", 45))
        self.assertEqual(result["after_plan"], make_plan(result["after"], "2026-10-07", 45))
        self.assertEqual(result["before_plan"]["planned_minutes"], 45)
        self.assertEqual(result["after_plan"]["planned_minutes"], 20)
        self.assertEqual([item["task"]["id"] for item in result["after_plan"]["selected"]], ["T0002"])
        target = self.workspace / "reports" / "change.html"
        self.assertEqual(result["report_path"], str(target))
        self.assertIn("<!doctype html>", target.read_text().lower())
        self.assertIn("Fictional outline", target.read_text())
        self.assertEqual(self.saved_state(), before)
        self.assertEqual(json.loads(Path(source).read_text()), change)

    def test_preview_can_render_without_a_budget_or_compare_without_a_report(self):
        source = self.write_json("change.json", {
            "schema_version": 1, "base_revision": 0,
            "actions": [{"action": "add", "title": "Fictional task", "minutes": 10}],
        })
        before = self.saved_state()
        result = json.loads(self.run_cli("preview", source, "--output", "reports/change.html").stdout)
        self.assertNotIn("before_plan", result)
        self.assertTrue(Path(result["report_path"]).is_file())
        result = json.loads(self.run_cli("preview", source, "--date", "2026-10-07", "--minutes", "0").stdout)
        self.assertNotIn("report_path", result)
        self.assertEqual(result["after_plan"]["planned_minutes"], 0)
        self.assertEqual(self.saved_state(), before)

    def test_preview_argument_and_output_validation_never_writes_report(self):
        source = self.write_json("change.json", {
            "schema_version": 1, "base_revision": 0,
            "actions": [{"action": "add", "title": "Fictional task", "minutes": 10}],
        })
        before = self.saved_state()
        for arguments in (
            ("--date", "2026-10-07"), ("--minutes", "30"),
            ("--date", "2026-02-30", "--minutes", "30"),
            ("--date", "2026-10-07", "--minutes", "-1"),
            ("--output", "reports/change.txt"), ("--output", "../escape.html"),
            ("--output", ".daily-ops/change.html"),
        ):
            with self.subTest(arguments=arguments):
                result = self.run_cli("preview", source, *arguments, expected=2)
                self.assertEqual(result.stdout, "")
        self.assertFalse((self.workspace / "reports").exists())
        self.assertFalse((self.root / "escape.html").exists())
        self.assertEqual(self.saved_state(), before)

    def test_stale_proposal_emits_no_report_and_preserves_existing_report(self):
        source = self.write_json("change.json", {
            "schema_version": 1, "base_revision": 0,
            "actions": [{"action": "add", "title": "Fictional stale task", "minutes": 10}],
        })
        self.run_cli("add", "Fictional intervening task", "--minutes", "10")
        before = self.saved_state()
        result = self.run_cli("preview", source, "--output", "reports/change.html",
                              "--date", "2026-10-07", "--minutes", "30", expected=2)
        self.assertEqual(json.loads(result.stderr)["error"]["code"], "stale_revision")
        self.assertFalse((self.workspace / "reports").exists())
        reports = self.workspace / "reports"
        reports.mkdir()
        existing = reports / "change.html"
        existing.write_text("Fictional existing report")
        self.run_cli("preview", source, "--output", "reports/change.html", expected=2)
        self.assertEqual(existing.read_text(), "Fictional existing report")
        self.assertEqual(self.saved_state(), before)


if __name__ == "__main__":
    unittest.main()
