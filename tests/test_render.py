"""Report views must preserve facts without interpreting task text as markup."""

import copy
from html.parser import HTMLParser
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "daily-ops" / "scripts"))

from daily_ops.render import render_markdown, render_plan, render_review


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.links.extend(value for name, value in attrs if name in ("src", "href"))


class RendererTests(unittest.TestCase):
    def report(self):
        task = {"id": "t-001", "title": "Finish application", "minutes": 35, "priority": 1, "status": "open", "notes": "Bring the draft", "due": "2026-10-07"}
        return {"kind": "plan", "schema_version": 1, "revision": 4, "date": "2026-10-07", "budget_minutes": 50, "planned_minutes": 35, "remaining_minutes": 15, "selected": [{"task": task, "reason": "Due today"}], "deferred": [], "blocked": [], "conflicts": [], "tradeoffs": []}

    def test_plan_preserves_exact_facts_and_does_not_mutate(self):
        report = self.report()
        before = copy.deepcopy(report)
        output = render_plan(report)
        for expected in ("t-001", "Finish application", "35 estimated min", "2026-10-07", "State revision 4", "<strong>50</strong>", "<strong>35</strong>", "<strong>15</strong>", "Help me start task t-001. Keep its status unchanged."):
            self.assertIn(expected, output)
        self.assertEqual(report, before)

    def test_untrusted_text_cannot_create_html_or_remote_links(self):
        report = self.report()
        malicious = '<img src="https://example.invalid/track" onerror="alert(1)"><script>alert(2)</script>'
        report["selected"][0]["task"].update({"id": malicious, "title": malicious, "minutes": malicious, "priority": malicious, "due": malicious, "not_before": malicious, "status": malicious, "blocked_by": [malicious], "notes": malicious, "completed": malicious})
        report["selected"][0]["reason"] = malicious
        report["conflicts"] = [{"id": malicious, "reason": malicious}]
        report["tradeoffs"] = [malicious]
        report["date"] = malicious
        report["revision"] = malicious
        output = render_plan(report)
        parsed = Tags()
        parsed.feed(output)
        self.assertNotIn("script", parsed.tags)
        self.assertNotIn("img", parsed.tags)
        self.assertEqual(parsed.links, ["#main"])
        self.assertIn("&lt;img", output)
        self.assertNotIn(malicious, output)

    def test_empty_plan_remains_complete_and_readable(self):
        output = render_plan({"kind": "plan", "budget_minutes": 0, "selected": [], "deferred": [], "blocked": []})
        self.assertIn("No tasks selected", output)
        self.assertIn("No tasks deferred", output)
        self.assertIn("No waiting tasks", output)
        self.assertIn("<strong>0</strong>", output)
        self.assertIn('lang="en"', output)

    def test_deferred_and_blocked_preserve_reasons(self):
        report = self.report()
        report["deferred"] = [{"task": {"id": "t-002", "title": "Read", "minutes": 60}, "reason": "Does not fit the remaining 15 minutes"}]
        report["blocked"] = [{"task": {"id": "t-003", "title": "Publish draft", "blocked_by": ["t-002"]}, "reason": "Waiting for review"}]
        output = render_plan(report)
        for expected in ("t-002", "t-003", "Does not fit the remaining 15 minutes", "Waiting for review", "Waiting for t-002"):
            self.assertIn(expected, output)

    def test_review_labels_completed_minutes_as_estimates(self):
        report = {"kind": "review", "revision": 5, "since": "2026-10-01", "completed": [{"id": "t-001", "title": "Sent draft", "minutes": 35, "status": "done", "completed": "2026-10-07"}], "open": [], "dropped": [], "total_completed_minutes": 35}
        output = render_review(report)
        self.assertIn("<strong>35</strong>", output)
        self.assertIn("Completed task estimates", output)
        self.assertIn("not measured working time", output)
        self.assertIn("t-001", output)
        self.assertIn("No open tasks", output)

    def test_unfiltered_review_has_a_meaningful_period(self):
        output = render_review({"kind": "review", "since": None, "revision": 8})
        self.assertIn("All recorded completions · State revision 8", output)
        self.assertNotIn("Since  ·", output)

    def test_markdown_is_readable_and_does_not_promote_html_or_links(self):
        task = {"id": "t-004", "title": "[click](https://example.invalid) <script>x</script>", "status": "done", "minutes": 20, "notes": "first\n# injected heading"}
        output = render_markdown({"revision": 3, "tasks": [task]})
        self.assertIn("- [x]", output)
        self.assertIn("20 estimated min", output)
        self.assertIn(r"ID: t\-004", output)
        self.assertIn(r"\[click\]\(https\:", output)
        self.assertNotIn("<script>", output)
        self.assertNotIn("\n# injected", output)
        self.assertIn("No tasks yet.", render_markdown({"tasks": []}))

    def test_markdown_preserves_waiting_reason_as_one_string(self):
        output = render_markdown({"revision": 1, "tasks": [{"id": "T0001", "title": "Prepare handover", "blocked_by": "Waiting for client approval"}]})
        self.assertIn("Waiting for: Waiting for client approval", output)
        self.assertNotIn("W, a, i", output)


if __name__ == "__main__":
    unittest.main()
