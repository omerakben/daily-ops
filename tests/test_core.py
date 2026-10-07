"""Synthetic checks for planning contracts and filesystem transaction behavior."""

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "daily-ops" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from daily_ops import core
from daily_ops.core import DailyOpsError, Workspace, load_change, make_plan, make_review


class WorkspaceCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.workspace = Workspace(self.root / "workspace")
        self.workspace.init()

    def tearDown(self):
        self.temporary.cleanup()

    def add(self, title="Synthetic task", minutes=30, **fields):
        return self.workspace.transact([{"action": "add", "title": title, "minutes": minutes, **fields}],
                                       today="2026-10-01")

    def assert_code(self, code, operation):
        with self.assertRaises(DailyOpsError) as caught:
            operation()
        self.assertEqual(caught.exception.code, code)

    def symlink(self, source, destination, *, directory=False):
        try:
            destination.symlink_to(source, target_is_directory=directory)
        except (OSError, NotImplementedError):
            self.skipTest("This host does not permit symlink creation.")

    def test_initialization_preserves_state(self):
        expected = self.add()
        self.assert_code("already_initialized", self.workspace.init)
        self.assertEqual(self.workspace.load(), expected)

    def test_roundtrip_ids_and_single_revision_for_batch(self):
        state = self.workspace.transact([
            {"action": "add", "title": "Synthetic A", "minutes": 25},
            {"action": "add", "title": "Synthetic B", "minutes": 10},
        ], today="2026-10-01")
        self.assertEqual(state["revision"], 1)
        self.assertEqual([task["id"] for task in state["tasks"]], ["T0001", "T0002"])
        self.assertEqual(Workspace(self.workspace.path).load(), state)
        self.workspace.transact([{"action": "drop", "id": "T0002"}])
        self.assertEqual(self.add("Synthetic C")["tasks"][-1]["id"], "T0003")

    def test_dates_minutes_and_unknown_fields_rejected(self):
        for change in ({"minutes": 0}, {"minutes": 1441}, {"minutes": True},
                       {"minutes": 2.5}, {"due": "2026-02-30"}, {"due": "20261001"},
                       {"not_before": "2026-13-01"}, {"priority": "urgent"},
                       {"title": "  "}, {"shell": "never executed"}):
            with self.subTest(change=change):
                action = {"action": "add", "title": "Synthetic", "minutes": 10, **change}
                self.assert_code("invalid_data", lambda: self.workspace.transact([action]))
        self.assertEqual(self.workspace.load()["revision"], 0)

    def test_invalid_unicode_is_a_structured_error(self):
        self.assert_code("invalid_data", lambda: self.add(title="Synthetic " + chr(0xD800)))
        self.assertEqual(self.workspace.load()["revision"], 0)

    def test_non_json_values_report_validation_errors(self):
        for actions in (None, [], [None], [{"action": []}], [{"action": "nope"}]):
            with self.subTest(actions=actions):
                self.assert_code("invalid_data", lambda: self.workspace.transact(actions))

    def test_all_or_nothing_invalid_later_action(self):
        before = self.add()
        actions = [{"action": "add", "title": "Synthetic new", "minutes": 20},
                   {"action": "complete", "id": "T9999"}]
        self.assert_code("task_not_found", lambda: self.workspace.transact(actions))
        self.assertEqual(self.workspace.load(), before)

    def test_duplicate_task_and_add_actions_rejected(self):
        before = self.add()
        for actions in ([{"action": "complete", "id": "T0001"}, {"action": "drop", "id": "T0001"}],
                        [{"action": "add", "title": "Same", "minutes": 10}] * 2):
            self.assert_code("invalid_data", lambda: self.workspace.transact(actions))
        self.assertEqual(self.workspace.load(), before)

    def test_preview_readonly_and_apply_stale_revision(self):
        self.add()
        change = {"schema_version": 1, "base_revision": 1,
                  "actions": [{"action": "complete", "id": "T0001"}]}
        state_file = self.workspace.path / ".daily-ops" / "state.json"
        before_bytes = state_file.read_bytes()
        before_mtime = state_file.stat().st_mtime_ns
        preview = self.workspace.preview(change, today="2026-10-03")
        self.assertEqual(preview["after"]["tasks"][0]["completed"], "2026-10-03")
        self.assertEqual(state_file.read_bytes(), before_bytes)
        self.assertEqual(state_file.stat().st_mtime_ns, before_mtime)
        self.workspace.apply(change, today="2026-10-03")
        self.assert_code("stale_revision", lambda: self.workspace.apply(change))
        self.assert_code("stale_revision", lambda: self.workspace.preview(change))

    def test_complete_reopen_block_defer_update(self):
        self.add()
        self.workspace.transact([{"action": "block", "id": "T0001", "reason": "Synthetic response"}])
        self.workspace.transact([{"action": "unblock", "id": "T0001"}])
        self.workspace.transact([{"action": "defer", "id": "T0001", "until": "2026-11-01"}])
        self.workspace.transact([{"action": "complete", "id": "T0001"}], today="2026-10-07")
        self.assert_code("invalid_transition", lambda: self.workspace.transact([{"action": "complete", "id": "T0001"}]))
        self.workspace.transact([{"action": "reopen", "id": "T0001"}])
        state = self.workspace.transact([{"action": "update", "id": "T0001", "minutes": 45,
                                          "title": "Revised synthetic task", "not_before": None}])
        task = state["tasks"][0]
        self.assertIsNone(task["completed"])
        self.assertIsNone(task["blocked_by"])
        self.assertIsNone(task["not_before"])
        self.assertEqual(task["minutes"], 45)
        self.assertEqual(task["title"], "Revised synthetic task")

    def test_waiting_task_can_be_captured_explicitly(self):
        state = self.add("Synthetic initially waiting", 20, blocked_by="Synthetic reviewer")
        self.assertEqual(state["tasks"][0]["blocked_by"], "Synthetic reviewer")
        self.assertEqual(len(make_plan(state, "2026-10-07", 30)["blocked"]), 1)

    def test_explicit_budget_whole_estimates_and_urgent_conflicts(self):
        self.add("Synthetic overdue large", 90, due="2026-10-01")
        self.add("Synthetic overdue fit", 20, due="2026-10-02")
        state = self.add("Synthetic current fit", 30, priority="high")
        before = deepcopy(state)
        plan = make_plan(state, "2026-10-07", 50)
        self.assertEqual([entry["task"]["id"] for entry in plan["selected"]], ["T0002", "T0003"])
        self.assertEqual(plan["planned_minutes"], 50)
        self.assertEqual(plan["remaining_minutes"], 0)
        self.assertEqual(plan["deferred"][0]["task"]["minutes"], 90)
        self.assertEqual(plan["conflicts"][0]["id"], "T0001")
        self.assertIn("never shortened", " ".join(plan["tradeoffs"]))
        self.assertEqual(state, before)

    def test_waiting_future_start_and_closed_tasks(self):
        self.add("Synthetic waiting", 20, due="2026-10-06")
        self.workspace.transact([{"action": "block", "id": "T0001", "reason": "Synthetic reviewer"}])
        self.add("Synthetic later", 20, due="2026-10-07", not_before="2026-10-08")
        self.add("Synthetic done", 20)
        self.workspace.transact([{"action": "complete", "id": "T0003"}])
        self.add("Synthetic dropped", 20)
        state = self.workspace.transact([{"action": "drop", "id": "T0004"}])
        plan = make_plan(state, "2026-10-07", 60)
        self.assertEqual(plan["planned_minutes"], 0)
        self.assertEqual(len(plan["blocked"]), 1)
        self.assertEqual(len(plan["deferred"]), 1)
        self.assertEqual(len(plan["conflicts"]), 2)
        self.assertEqual(plan["remaining_minutes"], 60)

    def test_deterministic_urgency_priority_id_order(self):
        for title, priority, due in (("Synthetic no date high", "high", None),
                                     ("Synthetic future low", "low", "2026-10-20"),
                                     ("Synthetic today low", "low", "2026-10-07"),
                                     ("Synthetic overdue", "low", "2026-10-06"),
                                     ("Synthetic today high A", "high", "2026-10-07"),
                                     ("Synthetic today high B", "high", "2026-10-07")):
            state = self.add(title, 10, priority=priority, due=due)
        plan = make_plan(state, "2026-10-07", 100)
        self.assertEqual([entry["task"]["id"] for entry in plan["selected"]],
                         ["T0004", "T0005", "T0006", "T0003", "T0002", "T0001"])
        self.assertEqual(plan, make_plan(state, "2026-10-07", 100))

    def test_plan_budget_bounds_and_zero_budget(self):
        state = self.add()
        self.assertEqual(make_plan(state, "2026-10-07", 0)["selected"], [])
        for budget in (-1, 1441, True, 1.5):
            self.assert_code("invalid_data", lambda: make_plan(state, "2026-10-07", budget))
        self.assert_code("invalid_data", lambda: make_plan(state, "2026-02-30", 10))

    def test_review_filters_completion_date_and_labels_estimates(self):
        self.add("Synthetic older", 10)
        self.workspace.transact([{"action": "complete", "id": "T0001"}], today="2026-10-02")
        self.add("Synthetic recent", 20)
        self.workspace.transact([{"action": "complete", "id": "T0002"}], today="2026-10-07")
        self.add("Synthetic open", 30)
        review = make_review(self.workspace.load(), "2026-10-05")
        self.assertEqual([task["id"] for task in review["completed"]], ["T0002"])
        self.assertEqual(review["total_completed_minutes"], 20)
        self.assertIn("not measured", " ".join(review["notes"]))
        self.assertEqual(len(review["open"]), 1)

    def test_json_duplicate_keys_and_nonfinite_numbers_rejected(self):
        change_file = self.root / "change.json"
        for content in ('{"schema_version":1,"schema_version":1}', '{"value":NaN}', '{bad', '\ufeff{}'):
            change_file.write_text(content, encoding="utf-8")
            self.assert_code("invalid_data", lambda: load_change(change_file))

    def test_invalid_state_preserved(self):
        state_file = self.workspace.path / ".daily-ops" / "state.json"
        state_file.write_text('{"schema_version": 99}', encoding="utf-8")
        before = state_file.read_bytes()
        self.assert_code("invalid_data", self.workspace.load)
        self.assert_code("invalid_data", lambda: self.add())
        self.assertEqual(state_file.read_bytes(), before)

    def test_symlink_workspace_and_existing_ancestor_refused(self):
        link = self.root / "linked"
        self.symlink(self.workspace.path, link, directory=True)
        self.assert_code("unsafe_path", Workspace(link).load)
        self.assert_code("unsafe_path", Workspace(link / "child").init)
        self.assertFalse((self.workspace.path / "child").exists())

    def test_symlink_state_leaf_refused_and_target_preserved(self):
        state_file = self.workspace.path / ".daily-ops" / "state.json"
        outside = self.root / "outside.json"
        state_file.rename(outside)
        self.symlink(outside, state_file)
        before = outside.read_bytes()
        self.assert_code("unsafe_path", self.workspace.load)
        self.assert_code("unsafe_path", lambda: self.add())
        self.assertEqual(outside.read_bytes(), before)

    def test_symlink_store_lock_and_change_file_refused(self):
        store = self.workspace.path / ".daily-ops"
        lock_file = store / ".lock"
        lock_file.unlink()
        outside = self.root / "outside.lock"
        outside.write_text("preserve", encoding="utf-8")
        self.symlink(outside, lock_file)
        self.assert_code("unsafe_path", lambda: self.add())
        self.assertEqual(outside.read_text(encoding="utf-8"), "preserve")
        change_file = self.root / "change.json"
        self.symlink(outside, change_file)
        self.assert_code("unsafe_path", lambda: load_change(change_file))
        alternate = self.root / "alternate"
        alternate.mkdir()
        self.symlink(store, alternate / ".daily-ops", directory=True)
        self.assert_code("unsafe_path", Workspace(alternate).load)

    def test_hardlinked_state_refused(self):
        state_file = self.workspace.path / ".daily-ops" / "state.json"
        try:
            os.link(state_file, self.root / "alias.json")
        except OSError:
            self.skipTest("Host filesystem does not support hard links.")
        self.assert_code("unsafe_path", self.workspace.load)

    def test_writer_lock_prevents_concurrent_process(self):
        with self.workspace._store(write=True):
            result = subprocess.run([sys.executable, str(SCRIPTS / "run.py"), "--workspace",
                                     str(self.workspace.path), "add", "Synthetic concurrent", "--minutes", "10"],
                                    text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr)["error"]["code"], "workspace_busy")
        self.assertEqual(self.workspace.load()["revision"], 0)
        self.assertEqual(self.add()["revision"], 1)

    def test_external_edit_detected_before_replacement(self):
        expected = self.add()
        original_apply = core._apply_actions
        state_file = self.workspace.path / ".daily-ops" / "state.json"
        externally_changed = deepcopy(expected)
        externally_changed["revision"] = 50

        def competing_edit(*args, **kwargs):
            state_file.write_text(json.dumps(externally_changed), encoding="utf-8")
            return original_apply(*args, **kwargs)

        with patch.object(core, "_apply_actions", side_effect=competing_edit):
            self.assert_code("concurrent_change", lambda: self.add("Synthetic raced"))
        self.assertEqual(self.workspace.load(), externally_changed)

    def test_atomic_replace_failure_preserves_original_and_cleans_temp(self):
        expected = self.add()
        with patch.object(core, "_replace_at", side_effect=OSError("Synthetic failure")):
            with self.assertRaises(OSError):
                self.add("Synthetic failure")
        self.assertEqual(self.workspace.load(), expected)
        self.assertFalse(list((self.workspace.path / ".daily-ops").glob("*.tmp")))

    @unittest.skipUnless(os.name == "posix", "Directory synchronization is a POSIX durability step.")
    def test_sync_failure_reports_uncertain_durability_after_commit(self):
        original_sync = os.fsync

        def failing_directory_sync(descriptor):
            import stat
            if stat.S_ISDIR(os.fstat(descriptor).st_mode):
                raise OSError("Synthetic disk synchronization error")
            return original_sync(descriptor)

        with patch.object(core.os, "fsync", side_effect=failing_directory_sync):
            self.assert_code("durability_uncertain", lambda: self.add())
        self.assertEqual(self.workspace.load()["revision"], 1)
        self.assertFalse(list((self.workspace.path / ".daily-ops").glob("*.tmp")))

    def test_report_write_scoped_atomic_and_no_state_revision(self):
        before = self.add()
        output = self.workspace.write_report("reports/today.html", "<html>Synthetic</html>")
        self.assertEqual(Path(output).read_text(encoding="utf-8"), "<html>Synthetic</html>")
        self.workspace.write_report("reports/today.html", "replacement")
        self.assertEqual(Path(output).read_text(encoding="utf-8"), "replacement")
        self.assertEqual(self.workspace.load(), before)
        for path in ("../escape.html", ".daily-ops/state.json", ".DAILY-OPS/state.json", ".daily-ops. /state.json",
                     "reports/file:stream", "reports/NUL", str(self.root / "absolute.html")):
            self.assert_code("unsafe_path", lambda: self.workspace.write_report(path, "bad"))

    def test_report_symlink_parent_and_leaf_refused(self):
        outside = self.root / "outside"
        outside.mkdir()
        self.symlink(outside, self.workspace.path / "linked-reports", directory=True)
        self.assert_code("unsafe_path", lambda: self.workspace.write_report("linked-reports/a.html", "bad"))
        report = self.workspace.path / "report.html"
        target = outside / "keep.html"
        target.write_text("preserve", encoding="utf-8")
        self.symlink(target, report)
        self.assert_code("unsafe_path", lambda: self.workspace.write_report("report.html", "bad"))
        self.assertEqual(target.read_text(encoding="utf-8"), "preserve")

    def test_portable_path_branch_roundtrip_and_symlink_rejection(self):
        with patch.object(core, "_portable", return_value=True):
            workspace = Workspace(self.root / "portable")
            workspace.init()
            state = workspace.transact([{"action": "add", "title": "Synthetic portable", "minutes": 10}])
            self.assertEqual(workspace.load(), state)
            output = workspace.write_report("reports/a.html", "Synthetic portable")
            self.assertTrue(Path(output).is_file())
            link = self.root / "portable-link"
            self.symlink(workspace.path, link, directory=True)
            self.assert_code("unsafe_path", Workspace(link).load)


if __name__ == "__main__":
    unittest.main()
