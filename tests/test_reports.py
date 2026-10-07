import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

RUNNER = Path(__file__).resolve().parents[1] / "skills" / "daily-ops" / "scripts" / "run.py"


class ReportIntegration(unittest.TestCase):
    def test_generated_report_and_review_preserve_state(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve() / "task folder"

            def run(*arguments):
                result = subprocess.run([sys.executable, str(RUNNER), "--workspace", str(root), *arguments], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                return json.loads(result.stdout)

            run("init")
            state = run("add", "Read <script>alert(1)</script> notes", "--minutes", "20")
            plan = run("plan", "--date", "2026-10-07", "--minutes", "25", "--output", "reports/today.html")
            self.assertEqual(plan["planned_minutes"], 20)
            report = (root / "reports" / "today.html").read_text(encoding="utf-8")
            self.assertIn("T0001", report)
            self.assertNotIn("<script>alert(1)</script>", report)
            self.assertEqual(run("list"), state)
            run("complete", "T0001")
            review = run("review", "--output", "reports/review.html")
            self.assertEqual(review["total_completed_minutes"], 20)
            self.assertTrue((root / "reports" / "review.html").is_file())

    def test_report_cannot_overwrite_state_or_escape_workspace(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve() / "work"
            prefix = [sys.executable, str(RUNNER), "--workspace", str(root)]
            subprocess.run(prefix + ["init"], check=True, capture_output=True)
            original = (root / ".daily-ops" / "state.json").read_bytes()
            for path in ("../outside.html", ".daily-ops/state.html", ".daily-ops/state.json"):
                failed = subprocess.run(prefix + ["plan", "--date", "2026-10-07", "--minutes", "10", "--output", path], capture_output=True)
                self.assertNotEqual(failed.returncode, 0)
                self.assertEqual((root / ".daily-ops" / "state.json").read_bytes(), original)
            self.assertFalse((root.parent / "outside.html").exists())


if __name__ == "__main__":
    unittest.main()
