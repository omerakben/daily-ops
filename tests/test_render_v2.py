"""Report facts, explicit response affordances, and offline trust boundaries."""

import base64
import copy
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import shlex
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "daily-ops" / "scripts"))

from daily_ops.render import render_plan, render_preview, render_review
from daily_ops.report_assets import WORKSHEET_JS


class Document(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.ids = []
        self.links = []
        self.tags = []
        self.scripts = []
        self.styles = []
        self.csp = ""
        self.text = []
        self.active = None
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if "id" in attrs:
            self.ids.append(attrs["id"])
        self.links.extend(value for name, value in attrs.items() if name in ("src", "href"))
        if tag == "meta" and attrs.get("http-equiv") == "Content-Security-Policy":
            self.csp = attrs["content"]
        if tag == "script":
            self.scripts.append({"attrs": attrs, "body": ""})
            self.active = "script"
        if tag == "style":
            self.styles.append("")
            self.active = "style"

    def handle_endtag(self, tag):
        if tag == self.active:
            self.active = None

    def handle_data(self, value):
        if self.active == "script":
            self.scripts[-1]["body"] += value
        elif self.active == "style":
            self.styles[-1] += value
        else:
            self.text.append(value)


def task(tid, title, minutes=25, **kwargs):
    result = dict(id=tid, title=title, minutes=minutes, priority="normal", due=None,
                  not_before=None, status="open", notes=None, blocked_by=None, completed=None)
    result.update(kwargs)
    return result


def plan():
    return dict(schema_version=1, kind="plan", revision=7, date="2026-10-07", budget_minutes=60,
                planned_minutes=25, remaining_minutes=35,
                selected=[dict(task=task("T0001", "Prepare a library workshop"), reason="Fits the budget")],
                deferred=[dict(task=task("T0002", "Renew membership", 50, due="2026-10-07"), reason="Needs 50 minutes; 35 remain")],
                blocked=[dict(task=task("T0003", "Confirm picnic venue", blocked_by="Awaiting the venue reply", due="2026-10-07"), reason="Waiting: Awaiting the venue reply")],
                conflicts=[dict(id="T0002", reason="Needs 50 minutes; 35 remain"), dict(id="T0003", reason="Waiting: Awaiting the venue reply")],
                tradeoffs=["Due-date urgency is considered before priority."])


class PlanSurfaceTests(unittest.TestCase):
    def test_every_fragment_resolves_and_tasks_stay_visible_without_script(self):
        source = render_plan(plan())
        document = Document(source)
        self.assertEqual(len(document.ids), len(set(document.ids)))
        for href in document.links:
            self.assertTrue(href.startswith("#"), href)
            self.assertIn(href[1:], document.ids)
        readable = " ".join(document.text)
        for value in ("Prepare a library workshop", "Renew membership", "Confirm picnic venue",
                      "Needs 50 minutes; 35 remain", "Awaiting the venue reply", "State revision 7",
                      "60 budget − 25 selected = 35 unallocated", "2026-10-07"):
            self.assertIn(value, readable)
        self.assertLess(source.index("Start with one thing"), source.index('id="decisions"'))
        self.assertLess(source.index('id="decisions"'), source.index('id="selected"'))

    def test_only_exact_trusted_runtime_is_executable_and_hashed(self):
        document = Document(render_plan(plan()))
        executable = [script for script in document.scripts if script["attrs"].get("type") != "application/json"]
        self.assertEqual([script["body"] for script in executable], [WORKSHEET_JS])
        for content in [WORKSHEET_JS, *document.styles]:
            digest = base64.b64encode(sha256(content.encode()).digest()).decode()
            self.assertIn("'sha256-" + digest + "'", document.csp)
        for policy in ("default-src 'none'", "connect-src 'none'", "img-src 'none'", "form-action 'none'"):
            self.assertIn(policy, document.csp)
        self.assertNotIn("unsafe-inline", document.csp)
        self.assertNotIn("unsafe-eval", document.csp)
        for tag, attrs in document.tags:
            self.assertFalse(any(key.startswith("on") for key in attrs))
            self.assertNotIn(tag, ("img", "iframe", "object", "embed"))
        for dangerous in ("innerHTML", "outerHTML", "eval(", "fetch(", "XMLHttpRequest", "localStorage", "sessionStorage", "navigator.sendBeacon"):
            self.assertNotIn(dangerous, WORKSHEET_JS)

    def test_script_terminators_and_questions_remain_inert_data(self):
        report = plan()
        attack = '</script><script>alert("x")</script><img src="https://invalid.example/x"> & \u2028\u2029'
        for group in ("selected", "deferred", "blocked"):
            report[group][0]["task"].update(title=attack, notes=attack)
            report[group][0]["reason"] = attack
        report["blocked"][0]["task"]["blocked_by"] = attack
        concern = dict(code="test", task_id="T0001", title=attack, message=attack, question=attack)
        before = copy.deepcopy(report)
        with patch("daily_ops.render.assess_plan", return_value=[concern]):
            source = render_plan(report)
        document = Document(source)
        self.assertEqual(len(document.scripts), 2)
        data = next(script["body"] for script in document.scripts if script["attrs"].get("type") == "application/json")
        self.assertNotIn("<", data)
        self.assertNotIn("\u2028", data)
        self.assertNotIn("\u2029", data)
        decoded = json.loads(data)
        self.assertEqual(decoded["tasks"][0]["title"], attack)
        self.assertEqual(decoded["concerns"][0]["question"], attack)
        self.assertEqual(report, before)
        self.assertFalse(any(tag == "img" for tag, _ in document.tags))
        self.assertTrue(all(link.startswith("#") for link in document.links))

    def test_decisions_group_findings_by_task_without_repeating_task_title(self):
        report = plan()
        report["deferred"][0]["task"]["minutes"] = 90
        source = render_plan(report)
        decision_content = source.split('id="decisions"', 1)[1].split("</section>", 1)[0]
        self.assertEqual(decision_content.count("Renew membership"), 1)
        self.assertIn("90-minute estimate exceeds", decision_content)
        self.assertIn("Due 2026-10-07 but not scheduled", decision_content)
        card = source.split('id="task-5430303032"', 1)[1].split("</li>", 1)[0]
        self.assertEqual(card.count("Renew membership"), 1)

    def test_defaults_never_indicate_approval_or_saved_work(self):
        document = Document(render_plan(plan()))
        text = " ".join(document.text)
        self.assertEqual(text.count("Opening this panel records nothing."), 3)
        self.assertIn("lost on reload or close", text)
        self.assertIn("Keep current (reviewed, not approved)", text)
        self.assertIn("Download changes.json", text)
        self.assertIn("Download review.md", text)
        self.assertIn("rejects stale proposals", text)
        choices = [attrs for tag, attrs in document.tags if tag == "option"]
        self.assertEqual(sum(attrs.get("value") == "unreviewed" for attrs in choices), 3)
        self.assertEqual(sum(attrs.get("value") == "unblock" for attrs in choices), 1)
        self.assertFalse(any(attrs.get("value") in ("complete", "drop") for attrs in choices))
        buttons = [attrs for tag, attrs in document.tags if tag == "button"]
        self.assertIn("disabled", next(attrs for attrs in buttons if attrs["id"] == "download-changes"))

    def test_continuation_command_uses_real_runner_and_cli_flags(self):
        from daily_ops.cli import _parser
        document = Document(render_plan(plan()))
        command = next(text for text in document.text if text.startswith("python3 "))
        arguments = shlex.split(command)
        self.assertEqual(arguments[:2], ["python3", "/path/to/daily-ops/skills/daily-ops/scripts/run.py"])
        actual_runner = Path(__file__).resolve().parents[1] / "skills/daily-ops/scripts/run.py"
        self.assertTrue(actual_runner.is_file())
        parsed = _parser().parse_args(arguments[2:])
        self.assertEqual(parsed.command, "preview")
        self.assertEqual(parsed.workspace, "/path/to/workspace")
        self.assertEqual(parsed.file, "/path/to/changes.json")
        self.assertEqual(parsed.date, "2026-10-07")
        self.assertEqual(parsed.minutes, plan()["budget_minutes"])
        self.assertEqual(parsed.output, "reports/change.html")
        self.assertNotIn("Prepare a library workshop", command)

    def test_continuation_never_interpolates_unvalidated_shell_inputs(self):
        for invalid_date in ('2026-10-07; echo unsafe', '2026-02-29', '0000-01-01', '2026-W41-3'):
            report = plan()
            report["date"] = invalid_date
            report["budget_minutes"] = '60; echo unsafe'
            document = Document(render_plan(report))
            command = next(text for text in document.text if text.startswith("python3 "))
            self.assertIn("--date YYYY-MM-DD --minutes MINUTES", command)
            self.assertNotIn("unsafe", command)
            self.assertIn("incomplete planning inputs", " ".join(document.text))
        for invalid_minutes in (-1, 1441, True, 60.0, None):
            report = plan()
            report["budget_minutes"] = invalid_minutes
            document = Document(render_plan(report))
            command = next(text for text in document.text if text.startswith("python3 "))
            self.assertIn("--minutes MINUTES", command)
        for valid_minutes in (0, 45, 1440):
            report = plan()
            report["date"] = "2024-02-29"
            report["budget_minutes"] = valid_minutes
            document = Document(render_plan(report))
            command = next(text for text in document.text if text.startswith("python3 "))
            self.assertIn(f"--date 2024-02-29 --minutes {valid_minutes}", command)
            self.assertIn("match this snapshot", " ".join(document.text))

    def test_legacy_report_is_readable_without_invalid_proposal(self):
        report = plan()
        report["selected"][0]["task"]["id"] = "old-task"
        document = Document(render_plan(report))
        self.assertEqual(document.scripts, [])
        self.assertIn("Prepare a library workshop", " ".join(document.text))
        self.assertIn("script-src 'none'", document.csp)

    def test_reviews_have_no_runtime_and_all_groups(self):
        report = dict(revision=9, completed=[task("T0001", "Sent invitation", status="done", completed="2026-10-07")],
                      open=[task("T0002", "Choose refreshments")], dropped=[task("T0003", "Old idea", status="dropped")], total_completed_minutes=25)
        document = Document(render_review(report))
        self.assertEqual(document.scripts, [])
        for expected in ("Sent invitation", "Choose refreshments", "Old idea", "not measured working time"):
            self.assertIn(expected, " ".join(document.text))
        for href in document.links:
            self.assertIn(href[1:], document.ids)


class PreviewSurfaceTests(unittest.TestCase):
    def preview(self):
        old = task("T0001", "Reserve meeting room", minutes=45, due="2026-10-08")
        after = dict(old, minutes=25, due=None, status="done", completed="2026-10-07")
        added = task("T0002", "Bring printed handouts", minutes=15)
        return dict(schema_version=1, kind="preview", base_revision=7, proposed_revision=8,
                    actions=[dict(action="update", id="T0001", minutes=25)],
                    before=dict(tasks=[old]), after=dict(tasks=[after, added]))

    def test_diff_uses_snapshots_even_if_actions_are_incomplete(self):
        preview = self.preview()
        original = copy.deepcopy(preview)
        document = Document(render_preview(preview))
        text = " ".join(document.text)
        for value in ("Base revision 7 → Proposed revision 8", "45", "25", '"2026-10-08"', "None", '"done"', '"open"', "New task", "Bring printed handouts", "Field not present", "Preview only. Nothing applied."):
            self.assertIn(value, text)
        # Unchanged title is the card heading, not falsely listed as a changed field.
        first_card = render_preview(preview).split('<ul class="diff-list">', 1)[1].split('</article>', 1)[0]
        self.assertNotIn('<strong>Title</strong>', first_card)
        self.assertIn('<strong>Status</strong>', first_card)
        self.assertEqual(preview, original)
        self.assertEqual(document.scripts, [])

    def test_preview_preserves_type_changes_and_hostile_values(self):
        preview = self.preview()
        attack = '<script>oops()</script><img src="https://example.invalid/track">'
        preview["after"]["tasks"][0].update(title=attack, notes=attack)
        preview["actions"][0]["notes"] = attack
        document = Document(render_preview(preview))
        self.assertFalse(any(tag in ("script", "img") for tag, _ in document.tags))
        self.assertIn(attack, " ".join(document.text))
        self.assertTrue(all(href.startswith("#") for href in document.links))

    def test_before_after_plans_include_all_membership_and_reasons(self):
        preview = self.preview()
        preview["before_plan"] = plan()
        preview["after_plan"] = plan()
        preview["after_plan"].update(revision=8, planned_minutes=50, remaining_minutes=10)
        preview["after_plan"]["deferred"][0]["reason"] = "Still outside this plan after the proposed change"
        document = Document(render_preview(preview))
        text = " ".join(document.text)
        for value in ("60 budget − 25 selected = 35 unallocated", "60 budget − 50 selected = 10 unallocated", "Waiting", "Confirm picnic venue", "Still outside this plan after the proposed change", "With the proposal"):
            self.assertIn(value, text)
        for href in document.links:
            self.assertIn(href[1:], document.ids)

    def test_diff_labels_are_readable_without_collapsing_distinct_values(self):
        preview = self.preview()
        preview["before"]["tasks"][0]["blocked_by"] = "Awaiting reply"
        preview["after"]["tasks"][0]["blocked_by"] = None
        preview["before"]["tasks"][0]["notes"] = None
        preview["after"]["tasks"][0]["notes"] = "null"
        output = render_preview(preview)
        visible_diff = output.split('id="changes"', 1)[1].split('id="consequences"', 1)[0]
        text = " ".join(Document(visible_diff).text)
        self.assertIn("Waiting reason", text)
        self.assertIn("Estimate · minutes", text)
        self.assertIn("Deadline", text)
        self.assertIn("None", text)
        self.assertIn('"null"', text)
        self.assertNotIn("blocked_by", text)

    def test_missing_plan_context_is_explicit(self):
        output = render_preview(self.preview())
        self.assertIn("Plan consequences were not calculated", output)
        self.assertIn("explicit date and minute budget", output)



_WORKSHEET_HARNESS = r"""
const fs = require('fs');
const vm = require('vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
class Element {
  constructor(value = '') { this.value = value; this.textContent = ''; this.hidden = false; this.disabled = false; this.dataset = {}; this.events = {}; }
  addEventListener(name, callback) { this.events[name] = callback; }
}
const nodes = new Map();
for (const id of ['report-data', 'download-changes', 'download-review', 'review-progress', 'export-status', 'reader-notes']) nodes.set(id, new Element());
nodes.get('report-data').textContent = JSON.stringify(input.report);
const cards = input.report.tasks.map(task => {
  const card = new Element();
  card.dataset.reviewTask = task.id;
  card.choice = new Element('unreviewed');
  card.status = new Element();
  card.message = new Element();
  card.fields = {minutes: new Element(String(task.minutes)), due: new Element(task.due || ''), until: new Element(task.not_before || ''), reason: new Element(task.blocked_by || '')};
  card.wrappers = ['estimate', 'due', 'defer', 'block'].map(choice => { const element = new Element(); element.dataset.forChoice = choice; return element; });
  card.querySelector = selector => {
    if (selector === '[data-choice]') return card.choice;
    if (selector === '[data-review-status]') return card.status;
    if (selector === '[data-response-message]') return card.message;
    return card.fields[selector.match(/data-field="([^"]+)"/)[1]];
  };
  card.querySelectorAll = () => card.wrappers;
  return card;
});
const blobs = [];
const downloads = [];
const document = {
  getElementById: id => nodes.get(id),
  querySelectorAll: selector => selector === '[data-review-task]' ? cards : [],
  body: {appendChild: () => {}},
  createElement: () => ({click() { downloads.push({filename: this.download, content: blobs[Number(this.href)].content}); }, remove() {}})
};
vm.runInNewContext(input.runtime, {
  document,
  Blob: class { constructor(parts) { this.content = parts.join(''); } },
  URL: {createObjectURL(blob) { blobs.push(blob); return String(blobs.length - 1); }, revokeObjectURL() {}},
  setTimeout: callback => callback()
});
const snapshot = () => ({
  disabled: nodes.get('download-changes').disabled,
  progress: nodes.get('review-progress').textContent,
  statuses: cards.map(card => card.status.textContent),
  messages: cards.map(card => card.message.textContent),
  visibleFields: cards.map(card => card.wrappers.filter(field => !field.hidden).map(field => field.dataset.forChoice)),
  downloads: downloads.slice()
});
const results = [snapshot()];
for (const operation of input.operations) {
  if (operation.task) {
    const card = cards.find(item => item.dataset.reviewTask === operation.task);
    if (operation.choice !== undefined) card.choice.value = operation.choice;
    for (const [key, value] of Object.entries(operation.fields || {})) card.fields[key].value = value;
    card.events.input();
  }
  if (operation.notes !== undefined) { nodes.get('reader-notes').value = operation.notes; nodes.get('reader-notes').events.input(); }
  if (operation.download) nodes.get('download-' + operation.download).events.click();
  results.push(snapshot());
}
process.stdout.write(JSON.stringify(results));
"""


@unittest.skipUnless(shutil.which("node"), "Optional Node runtime for isolated worksheet logic checks")
class WorksheetBehaviorTests(unittest.TestCase):
    def run_worksheet(self, operations):
        document = Document(render_plan(plan()))
        report = json.loads(next(script["body"] for script in document.scripts
                                 if script["attrs"].get("type") == "application/json"))
        result = subprocess.run(
            ["node", "-e", _WORKSHEET_HARNESS],
            input=json.dumps(dict(runtime=WORKSHEET_JS, report=report, operations=operations)),
            capture_output=True, text=True, check=True,
        )
        return json.loads(result.stdout)

    def test_explicit_single_actions_round_trip_exact_contract_and_reset(self):
        results = self.run_worksheet([
            dict(task="T0001", choice="keep"),
            dict(task="T0002", choice="estimate", fields=dict(minutes="35")),
            dict(task="T0003", choice="unblock"),
            dict(download="changes"),
            dict(task="T0002", choice="unreviewed"),
            dict(task="T0003", choice="keep"),
            dict(download="changes"),
        ])
        self.assertTrue(results[0]["disabled"])
        self.assertEqual(results[0]["statuses"], ["Unreviewed"] * 3)
        self.assertEqual(results[1]["statuses"][0], "Kept current")
        proposal = json.loads(results[4]["downloads"][0]["content"])
        self.assertEqual(proposal, dict(schema_version=1, base_revision=7, actions=[
            dict(action="update", id="T0002", minutes=35), dict(action="unblock", id="T0003")]))
        from daily_ops.core import validate_change
        self.assertEqual(validate_change(proposal), proposal)
        self.assertTrue(results[-1]["disabled"])
        self.assertEqual(len(results[-1]["downloads"]), 1)
        self.assertIn("1 unreviewed · 2 kept current · 0 changes proposed", results[-1]["progress"])

    def test_calendar_validity_estimate_bounds_and_unchanged_actions(self):
        cases = [
            ("due", dict(due="2026-02-29"), True),
            ("due", dict(due="2024-02-29"), False),
            ("due", dict(due="1900-02-29"), True),
            ("due", dict(due="2000-02-29"), False),
            ("due", dict(due="0000-01-01"), True),
            ("due", dict(due="0001-01-01"), False),
            ("due", dict(due="9999-12-31"), False),
            ("due", dict(due="10000-01-01"), True),
            ("due", dict(due="2026-04-31"), True),
            ("estimate", dict(minutes="1.5"), True),
            ("estimate", dict(minutes="0"), True),
            ("estimate", dict(minutes="1441"), True),
            ("estimate", dict(minutes="25"), True),
            ("estimate", dict(minutes="1440"), False),
            ("estimate", dict(minutes="1"), False),
            ("remove_due", {}, True),
            ("defer", dict(until="2026-10-09"), False),
        ]
        results = self.run_worksheet([dict(task="T0001", choice=choice, fields=fields) for choice, fields, _ in cases])
        for result, (choice, fields, disabled) in zip(results[1:], cases):
            self.assertEqual(result["disabled"], disabled, (choice, fields))
        self.assertEqual(results[13]["statuses"][0], "Unchanged entry")

    def test_reasons_match_python_codepoint_limit_and_reject_invalid_text(self):
        reasons = ["", " \t\n", "\u0085", "x" * 20000, "x" * 20001, "😀" * 20000,
                   "😀" * 20001, "bad\x00text", "\ud800", " Awaiting a reply "]
        results = self.run_worksheet([
            dict(task="T0001", choice="block", fields=dict(reason=reason)) for reason in reasons
        ] + [dict(download="changes")])
        for result, valid in zip(results[1:], [False, False, False, True, False, True, False, False, False, True]):
            self.assertEqual(result["disabled"], not valid)
        proposal = json.loads(results[-1]["downloads"][0]["content"])
        self.assertEqual(proposal["actions"], [dict(action="block", id="T0001", reason="Awaiting a reply")])
        from daily_ops.core import validate_change
        validate_change(proposal)

    def test_hidden_fields_do_not_add_actions_and_review_notes_stay_data(self):
        results = self.run_worksheet([
            dict(task="T0001", choice="estimate", fields=dict(minutes="15")),
            dict(task="T0001", choice="due", fields=dict(due="2026-10-10", minutes="bad")),
            dict(download="changes"),
            dict(notes="<script>bad()</script>\n# not a heading"),
            dict(download="review"),
        ])
        self.assertEqual(results[2]["visibleFields"][0], ["due"])
        proposal = json.loads(results[3]["downloads"][0]["content"])
        self.assertEqual(proposal["actions"], [dict(action="update", id="T0001", due="2026-10-10")])
        review = results[-1]["downloads"][-1]["content"]
        self.assertIn("Snapshot revision: 7", review)
        self.assertIn("Reader notes", review)
        self.assertIn("&lt;script&gt;", review)
        self.assertNotIn("<script>", review)
        self.assertNotIn("\n# not a heading", review)
        self.assertEqual(results[-1]["downloads"][-1]["filename"], "review.md")


if __name__ == "__main__":
    unittest.main()
