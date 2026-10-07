"""Fictional plans exercise advisories separately from integrity validation."""

from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "daily-ops" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from daily_ops.core import Workspace, make_plan
from daily_ops.plan_checks import assess_plan, check_plan


class PlanCheckCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.workspace = Workspace(Path(self.temporary.name).resolve() / "workspace")
        self.workspace.init()
        self.state = self.workspace.transact([
            {"action": "add", "title": "Fictional outline", "minutes": 20, "due": "2026-10-07"},
            {"action": "add", "title": "Fictional long draft", "minutes": 50, "due": "2026-10-07"},
            {"action": "add", "title": "Fictional review", "minutes": 10, "due": "2026-10-06",
             "blocked_by": "Fictional reviewer"},
            {"action": "add", "title": "Fictional delayed work", "minutes": 10,
             "due": "2026-10-08", "not_before": "2026-10-09"},
            {"action": "add", "title": "Fictional short task", "minutes": 5},
        ], today="2026-10-01")
        self.plan = make_plan(self.state, "2026-10-07", 30)

    def tearDown(self):
        self.temporary.cleanup()

    def codes(self, report):
        return {error["code"] for error in check_plan(self.state, report)["errors"]}

    def test_canonical_report_and_advisories_are_pure_and_deterministic(self):
        original_state, original_plan = deepcopy(self.state), deepcopy(self.plan)
        checked = check_plan(self.state, self.plan)
        self.assertTrue(checked["ok"])
        self.assertEqual(checked["kind"], "plan_check")
        self.assertEqual(checked["revision"], self.state["revision"])
        self.assertEqual(checked["warnings"], assess_plan(self.plan))
        self.assertEqual(checked, check_plan(self.state, self.plan))
        self.assertEqual(self.state, original_state)
        self.assertEqual(self.plan, original_plan)
        self.assertEqual(
            {(item["code"], item["task_id"]) for item in checked["warnings"]},
            {("urgent_omission", "T0002"), ("oversized_task", "T0002"),
             ("waiting_urgent", "T0003"), ("availability_after_deadline", "T0004")},
        )
        for item in checked["warnings"]:
            self.assertEqual(set(item), {"code", "task_id", "title", "message", "question"})

    def test_empty_and_zero_budget_are_valid(self):
        empty = Workspace(Path(self.temporary.name).resolve() / "empty").init()
        for state in (empty, self.state):
            for minutes in (0, 30):
                with self.subTest(tasks=len(state["tasks"]), minutes=minutes):
                    result = check_plan(state, make_plan(state, "2026-10-07", minutes))
                    self.assertTrue(result["ok"], result)
        self.assertTrue(check_plan(self.state, make_plan(self.state, "2026-10-07", 0))["warnings"])

    def test_advisories_derive_from_facts_and_tolerate_sparse_display_data(self):
        report = deepcopy(self.plan)
        report["deferred"][0]["reason"] = "Waiting: fabricated text"
        report["deferred"][0]["task"]["title"] = '<script>fictional & literal</script>'
        warnings = assess_plan(report)
        item = next(item for item in warnings if item["task_id"] == "T0002")
        self.assertEqual(item["code"], "urgent_omission")
        self.assertEqual(item["title"], '<script>fictional & literal</script>')
        self.assertEqual(assess_plan({}), [])
        self.assertEqual(assess_plan(None), [])
        self.assertEqual(assess_plan({
            "date": "<script>", "budget_minutes": "text",
            "selected": None, "deferred": [{"task": {"id": "T0001", "title": "Fictional", "minutes": "text"}},
                                         None, {"task": []}],
        }), [])

    def test_missing_canonical_fields_are_never_silently_accepted(self):
        for field in self.plan:
            report = deepcopy(self.plan)
            del report[field]
            with self.subTest(field=field):
                self.assertFalse(check_plan(self.state, report)["ok"])

    def test_malformed_header_types_and_values(self):
        for field, value, code in (
            ("schema_version", True, "invalid_schema"),
            ("schema_version", 2, "invalid_schema"),
            ("kind", "review", "invalid_kind"),
            ("revision", True, "invalid_revision"),
            ("revision", 1.0, "invalid_revision"),
            ("revision", -1, "invalid_revision"),
            ("date", "2026-02-30", "invalid_date"),
            ("date", None, "invalid_date"),
            ("budget_minutes", True, "invalid_budget"),
            ("budget_minutes", 30.0, "invalid_budget"),
            ("budget_minutes", -1, "invalid_budget"),
            ("budget_minutes", 1441, "invalid_budget"),
        ):
            with self.subTest(field=field, value=value):
                report = deepcopy(self.plan)
                report[field] = value
                self.assertIn(code, self.codes(report))
        self.assertEqual(self.codes([]), {"invalid_report"})

    def test_stale_revision_is_distinguished_from_other_discrepancies(self):
        report = deepcopy(self.plan)
        report["revision"] = 0
        self.assertEqual(self.codes(report), {"stale_revision"})
        self.assertEqual(check_plan(self.state, report)["revision"], 1)

    def test_every_numeric_and_narrative_field_is_compared(self):
        for field, value, code in (
            ("planned_minutes", 24, "arithmetic_mismatch"),
            ("remaining_minutes", 6, "arithmetic_mismatch"),
            ("planned_minutes", 25.0, "arithmetic_mismatch"),
            ("conflicts", [], "conflicts_mismatch"),
            ("tradeoffs", ["Everything will fit."], "tradeoffs_mismatch"),
        ):
            report = deepcopy(self.plan)
            report[field] = value
            with self.subTest(field=field):
                self.assertIn(code, self.codes(report))

    def test_missing_duplicate_unknown_and_reordered_tasks(self):
        report = deepcopy(self.plan)
        report["selected"].pop()
        self.assertIn("missing_task", self.codes(report))
        report = deepcopy(self.plan)
        report["selected"].append(deepcopy(report["selected"][0]))
        self.assertIn("duplicate_task", self.codes(report))
        report = deepcopy(self.plan)
        report["selected"][0]["task"]["id"] = "T9999"
        self.assertIn("unknown_task", self.codes(report))
        report = deepcopy(self.plan)
        report["selected"].reverse()
        self.assertEqual(self.codes(report), {"task_order_mismatch"})

    def test_selection_task_copies_and_reasons_are_checked(self):
        report = deepcopy(self.plan)
        report["deferred"].append(report["selected"].pop())
        self.assertIn("selection_mismatch", self.codes(report))
        for field, value in (("title", "Fabricated task"), ("minutes", 20.0),
                             ("status", "done"), ("notes", "Fabricated note"),
                             ("action", "complete")):
            report = deepcopy(self.plan)
            report["selected"][0]["task"][field] = value
            with self.subTest(field=field):
                self.assertIn("task_snapshot_mismatch", self.codes(report))
        report = deepcopy(self.plan)
        del report["selected"][0]["task"]["notes"]
        self.assertIn("task_snapshot_mismatch", self.codes(report))
        report = deepcopy(self.plan)
        report["selected"][0]["reason"] = "This task is complete."
        self.assertIn("reason_mismatch", self.codes(report))
        report = deepcopy(self.plan)
        del report["selected"][0]["reason"]
        self.assertIn("reason_mismatch", self.codes(report))
        self.assertIn("entry_fields_mismatch", self.codes(report))

    def test_only_known_presentation_metadata_is_permitted(self):
        report = deepcopy(self.plan)
        report["report_path"] = "/fictional/workspace/reports/plan.html"
        self.assertTrue(check_plan(self.state, report)["ok"])
        report["actions"] = [{"action": "drop", "id": "T0001"}]
        self.assertIn("unexpected_field", self.codes(report))
        del report["actions"]
        report["report_path"] = {"action": "drop"}
        self.assertIn("invalid_report_path", self.codes(report))
        report = deepcopy(self.plan)
        report["selected"][0]["action"] = "complete"
        self.assertIn("entry_fields_mismatch", self.codes(report))

    def test_malformed_groups_and_task_entries_do_not_raise(self):
        for value in (None, {}, [None], [{}], [{"task": []}], [{"task": {"id": []}}]):
            report = deepcopy(self.plan)
            report["selected"] = value
            with self.subTest(value=value):
                self.assertFalse(check_plan(self.state, report)["ok"])

    def test_warnings_use_current_canonical_facts_not_altered_report(self):
        report = deepcopy(self.plan)
        report["blocked"][0]["task"]["due"] = None
        checked = check_plan(self.state, report)
        self.assertFalse(checked["ok"])
        self.assertEqual(checked["warnings"], assess_plan(self.plan))


if __name__ == "__main__":
    unittest.main()
