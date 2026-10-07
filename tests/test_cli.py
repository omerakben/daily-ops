"""Exercise the installed script boundary using temporary synthetic workspaces."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

RUN = Path(__file__).resolve().parents[1] / "skills" / "daily-ops" / "scripts" / "run.py"


class CliCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.workspace = self.root / "workspace"
        self.run_cli("init")

    def tearDown(self):
        self.temporary.cleanup()

    def run_cli(self, *arguments, expected=0):
        result = subprocess.run([sys.executable, str(RUN), "--workspace", str(self.workspace), *arguments],
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, expected, result.stderr)
        return result

    def test_full_lifecycle_and_plan(self):
        state = json.loads(self.run_cli("add", "Synthetic CLI task", "--minutes", "25",
                                        "--due", "2026-10-07").stdout)
        self.assertEqual(state["tasks"][0]["id"], "T0001")
        plan = json.loads(self.run_cli("plan", "--date", "2026-10-07", "--minutes", "20").stdout)
        self.assertEqual(plan["planned_minutes"], 0)
        self.assertEqual(len(plan["conflicts"]), 1)
        self.run_cli("update", "T0001", "--minutes", "15", "--clear-due")
        state = json.loads(self.run_cli("complete", "T0001").stdout)
        self.assertEqual(state["tasks"][0]["status"], "done")
        self.run_cli("reopen", "T0001")
        self.run_cli("block", "T0001", "--reason", "Synthetic reviewer")
        self.run_cli("unblock", "T0001")
        self.run_cli("defer", "T0001", "--until", "2026-11-01")
        self.run_cli("drop", "T0001")
        self.assertEqual(len(json.loads(self.run_cli("review").stdout)["dropped"]), 1)

    def test_json_flag_and_explicit_waiting_capture(self):
        state = json.loads(self.run_cli("add", "Synthetic waiting", "--minutes", "10",
                                       "--blocked-by", "Synthetic response", "--json").stdout)
        self.assertEqual(state["tasks"][0]["blocked_by"], "Synthetic response")
        self.assertEqual(json.loads(self.run_cli("--json", "list").stdout), state)

    def test_structured_usage_and_data_errors(self):
        for arguments in (("add", "Synthetic", "--minutes", "no"),
                          ("plan", "--minutes", "10"),
                          ("plan", "--date", "2026-10-07", "--minutes", "-1"),
                          ("complete", "T9999"),
                          ("update", "T0001", "--due", "2026-10-07", "--clear-due"),
                          ("preview", str(self.root / "missing.json"))):
            with self.subTest(arguments=arguments):
                result = self.run_cli(*arguments, expected=2)
                self.assertEqual(result.stdout, "")
                self.assertIn("error", json.loads(result.stderr))
                self.assertNotIn("Traceback", result.stderr)

    def test_preview_and_apply_protocol(self):
        change = {"schema_version": 1, "base_revision": 0,
                  "actions": [{"action": "add", "title": "Synthetic proposed", "minutes": 20}]}
        change_file = self.root / "change.json"
        change_file.write_text(json.dumps(change), encoding="utf-8")
        preview = json.loads(self.run_cli("preview", str(change_file)).stdout)
        self.assertEqual(preview["proposed_revision"], 1)
        self.assertEqual(json.loads(self.run_cli("list").stdout)["tasks"], [])
        self.run_cli("apply", str(change_file))
        result = self.run_cli("apply", str(change_file), expected=2)
        self.assertEqual(json.loads(result.stderr)["error"]["code"], "stale_revision")

    def test_json_and_markdown_exports_preserve_data(self):
        self.run_cli("add", "Synthetic ``` title", "--minutes", "10", "--notes", "Synthetic note")
        state = json.loads(self.run_cli("export", "--format", "json").stdout)
        markdown = self.run_cli("export", "--format", "markdown").stdout
        exported = json.loads(markdown.split("```json\n", 1)[1].split("\n```", 1)[0])
        self.assertEqual(exported, state)
        self.assertEqual(state["revision"], 1)

    def test_workspace_is_explicit(self):
        result = subprocess.run([sys.executable, str(RUN), "list"], text=True,
                                capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr)["error"]["code"], "usage")

    def test_task_text_is_data_not_shell(self):
        marker = self.root / "must-not-exist"
        literal = f"$(touch {marker}) <script>alert('synthetic')</script>"
        state = json.loads(self.run_cli("add", literal, "--minutes", "10").stdout)
        self.assertEqual(state["tasks"][0]["title"], literal)
        self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
