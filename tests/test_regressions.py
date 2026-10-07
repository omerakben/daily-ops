import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

RUNNER = Path(__file__).resolve().parents[1] / "skills" / "daily-ops" / "scripts" / "run.py"


class ReleaseRegressions(unittest.TestCase):
    def test_legacy_stdout_encoding_cannot_report_a_committed_add_as_failed(self):
        with tempfile.TemporaryDirectory() as temp:
            prefix = [sys.executable, str(RUNNER), "--workspace", str(Path(temp).resolve() / "work")]
            environment = dict(os.environ, PYTHONIOENCODING="ascii")
            subprocess.run(prefix + ["init"], env=environment, capture_output=True, check=True)
            result = subprocess.run(prefix + ["add", "Write résumé 📝", "--minutes", "10"], env=environment, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads(result.stdout.decode("ascii"))
            self.assertEqual(len(state["tasks"]), 1)
            self.assertEqual(state["tasks"][0]["title"], "Write résumé 📝")

    def test_oversized_task_id_is_a_structured_error_and_preserves_state(self):
        with tempfile.TemporaryDirectory() as temp:
            prefix = [sys.executable, str(RUNNER), "--workspace", str(Path(temp).resolve() / "work")]
            subprocess.run(prefix + ["init"], capture_output=True, check=True)
            result = subprocess.run(prefix + ["complete", "T" + "1" * 5000], capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("error", json.loads(result.stderr))
            state = subprocess.run(prefix + ["list"], capture_output=True, check=True)
            self.assertEqual(json.loads(state.stdout)["revision"], 0)


if __name__ == "__main__":
    unittest.main()
