"""The public walkthrough must come from executable, reproducible runtime facts."""

from pathlib import Path
import tempfile
import unittest

from tools.build_examples import build_examples


class PublicExampleTests(unittest.TestCase):
    def test_generated_walkthrough_is_reproducible_and_read_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary).resolve() / "examples"
            summary = build_examples(output)
            first = {name: (output / name).read_bytes() for name in ("plan.html", "change.html")}
            self.assertEqual(summary["before_selected"], ["T0002", "T0004"])
            self.assertEqual(summary["after_selected"], ["T0001", "T0003"])
            self.assertEqual((summary["before_minutes"], summary["after_minutes"]), (45, 40))
            self.assertTrue(summary["state_unchanged"])
            self.assertFalse((output / ".daily-ops").exists())
            self.assertEqual(build_examples(output), summary)
            for name, content in first.items():
                self.assertEqual((output / name).read_bytes(), content)
                self.assertNotIn(temporary.encode(), content)
