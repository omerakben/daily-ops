"""Validated planning data and atomic local transactions.

Only this runtime's writes are confined to the selected workspace. This is not
a sandbox for an assistant, editor, or other process using the same account.
"""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import date as Date
import errno
import json
import os
from pathlib import Path
import re
import stat
import uuid
from typing import NoReturn

try:
    import fcntl
except ImportError:
    fcntl = None

try:
    import msvcrt
except ImportError:
    msvcrt = None


SCHEMA_VERSION = 1
MAX_FILE_BYTES = 10 * 1024 * 1024
TASK_FIELDS = {
    "id", "title", "minutes", "priority", "due", "not_before", "status",
    "blocked_by", "notes", "created", "completed",
}
EDIT_FIELDS = {"title", "minutes", "priority", "due", "not_before", "notes"}


class DailyOpsError(Exception):
    """A predictable, user-correctable runtime failure."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _fail(message: str, code: str = "invalid_data") -> NoReturn:
    raise DailyOpsError(code, message)


def _integer(value, field, minimum=0, maximum=None):
    if type(value) is not int or value < minimum or (maximum is not None and value > maximum):
        limit = f" to {maximum}" if maximum is not None else " or greater"
        _fail(f"{field} must be an integer from {minimum}{limit}.")
    return value


def _text(value, field, *, optional=False, maximum=20000):
    if optional and value is None:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        _fail(f"{field} must be nonempty text of at most {maximum} characters.")
    if "\x00" in value:
        _fail(f"{field} cannot contain a null character.")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        _fail(f"{field} must contain valid Unicode text.")
    return value.strip()


def iso_date(value, field="date", *, optional=False):
    if optional and value is None:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        _fail(f"{field} must use YYYY-MM-DD.")
    try:
        Date.fromisoformat(value)
    except ValueError:
        _fail(f"{field} must be a valid calendar date.")
    return value


def _task_id(value):
    if not isinstance(value, str) or len(value) > 64 or not re.fullmatch(r"T[0-9]{4,}", value):
        _fail("Task id must look like T0001.")
    number = int(value[1:])
    if number < 1 or value != f"T{number:04d}":
        _fail("Task id is not canonical.")
    return value


def _fields(value, allowed, required, label):
    if not isinstance(value, dict):
        _fail(f"{label} must be an object.")
    if set(value) - allowed:
        _fail(f"{label} contains unsupported fields.")
    if required - set(value):
        _fail(f"{label} is missing required fields.")


def _editable(field, value):
    if field == "title":
        return _text(value, field, maximum=1000)
    if field == "minutes":
        return _integer(value, field, 1, 1440)
    if field == "priority":
        if value not in ("high", "normal", "low"):
            _fail("priority must be high, normal, or low.")
        return value
    if field in ("due", "not_before"):
        return iso_date(value, field, optional=True)
    return _text(value, field, optional=True)


def validate_state(state):
    fields = {"schema_version", "revision", "next_id", "tasks"}
    _fields(state, fields, fields, "State")
    if type(state["schema_version"]) is not int or state["schema_version"] != SCHEMA_VERSION:
        _fail("Unsupported state schema version.")
    _integer(state["revision"], "revision")
    _integer(state["next_id"], "next_id", 1)
    if not isinstance(state["tasks"], list):
        _fail("tasks must be an array.")
    ids = set()
    for task in state["tasks"]:
        _fields(task, TASK_FIELDS, TASK_FIELDS, "Task")
        tid = _task_id(task["id"])
        if tid in ids:
            _fail("State contains a duplicate task id.")
        ids.add(tid)
        if int(tid[1:]) >= state["next_id"]:
            _fail("next_id must be greater than every existing task id.")
        for field in EDIT_FIELDS:
            _editable(field, task[field])
        if task["status"] not in ("open", "done", "dropped"):
            _fail("Task status is invalid.")
        _text(task["blocked_by"], "blocked_by", optional=True)
        iso_date(task["created"], "created")
        iso_date(task["completed"], "completed", optional=True)
        if (task["status"] == "done") != (task["completed"] is not None):
            _fail("Only completed tasks must have a completed date.")
    return state


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("JSON contains a duplicate object key.")
        result[key] = value
    return result


def _decode(raw):
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                          parse_constant=lambda value: _fail("JSON contains a nonfinite number."))
    except (UnicodeDecodeError, ValueError, RecursionError):
        _fail("File must contain valid UTF-8 JSON.")


def _portable():
    return fcntl is None or not hasattr(os, "O_NOFOLLOW") or os.open not in os.supports_dir_fd


def _checked_path(path, *, create=False):
    """Portable preflight, including Windows junction/reparse point rejection.

    Preflight cannot defeat a hostile process swapping paths concurrently.
    The descriptor-based path on POSIX avoids following swapped ancestors.
    """
    path = Path(os.path.expanduser(os.fspath(path)))
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.is_absolute() or ".." in path.parts:
        _fail("Choose a path without '..' components.", "unsafe_path")
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current /= component
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            if create:
                try:
                    current.mkdir(mode=0o700)
                except FileExistsError:
                    pass
                metadata = current.lstat()
            else:
                continue
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
            _fail("Paths cannot contain symlinks or Windows reparse points.", "unsafe_path")
    return path


def _mkdir_at(directory, name):
    if isinstance(directory, int):
        os.mkdir(name, mode=0o700, dir_fd=directory)
    else:
        _checked_path(directory / name).mkdir(mode=0o700)


def _unlink_at(directory, name):
    if isinstance(directory, int):
        os.unlink(name, dir_fd=directory)
    else:
        _checked_path(directory / name).unlink()


def _replace_at(directory, source, destination, *, exclusive=False):
    if isinstance(directory, int):
        if exclusive:
            os.link(source, destination, src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
        else:
            os.replace(source, destination, src_dir_fd=directory, dst_dir_fd=directory)
    else:
        source_path = _checked_path(directory / source)
        destination_path = _checked_path(directory / destination)
        if exclusive:
            os.link(source_path, destination_path)
        else:
            os.replace(source_path, destination_path)


def _sync_directory(directory):
    if isinstance(directory, int):
        try:
            os.fsync(directory)
        except OSError:
            _fail("File was written, but filesystem synchronization failed. Reload before retrying.",
                  "durability_uncertain")


@contextmanager
def _directory(path, *, create=False):
    """Walk from the filesystem root using no-follow directory descriptors."""
    if _portable():
        checked = _checked_path(path, create=create)
        if not checked.is_dir():
            _fail("Selected directory does not exist.", "not_found")
        yield checked
        return
    path = Path(os.path.expanduser(os.fspath(path)))
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.is_absolute() or ".." in path.parts:
        _fail("Choose a workspace path without '..' components.", "unsafe_path")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(path.anchor, flags)
    try:
        for component in path.parts[1:]:
            if create:
                try:
                    os.mkdir(component, mode=0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            try:
                child = os.open(component, flags, dir_fd=fd)
            except OSError as exc:
                if exc.errno in (errno.ELOOP, errno.ENOTDIR):
                    _fail("Workspace paths must contain real directories, never symlinks.", "unsafe_path")
                raise
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


def _open_regular(directory, name, flags=os.O_RDONLY, mode=0o600):
    try:
        if isinstance(directory, int):
            fd = os.open(name, flags | os.O_NOFOLLOW | os.O_NONBLOCK, mode, dir_fd=directory)
        else:
            checked = _checked_path(directory / name)
            if checked.exists() and not checked.is_file():
                _fail("Runtime files must be regular files.", "unsafe_path")
            fd = os.open(checked, flags | getattr(os, "O_BINARY", 0), mode)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            _fail("Runtime files cannot be symlinks.", "unsafe_path")
        raise
    metadata = os.fstat(fd)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        os.close(fd)
        _fail("Runtime files must be regular files with one link.", "unsafe_path")
    return fd


def _read_at(directory, name):
    fd = _open_regular(directory, name)
    with os.fdopen(fd, "rb") as stream:
        raw = stream.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        _fail("JSON file is too large.")
    return raw


def load_change(path):
    """Read an explicitly selected change file without following symlinks."""
    path = Path(os.path.expanduser(os.fspath(path)))
    with _directory(path.parent) as directory:
        change = _decode(_read_at(directory, path.name))
    validate_change(change)
    return change


def validate_change(change):
    fields = {"schema_version", "base_revision", "actions"}
    _fields(change, fields, fields, "Change file")
    if type(change["schema_version"]) is not int or change["schema_version"] != SCHEMA_VERSION:
        _fail("Unsupported change schema version.")
    _integer(change["base_revision"], "base_revision")
    _validate_actions(change["actions"])
    return change


def _validate_actions(actions):
    if not isinstance(actions, list) or not 1 <= len(actions) <= 1000:
        _fail("actions must be an array containing 1 to 1000 actions.")
    seen_ids, seen_adds = set(), set()
    for action in actions:
        if not isinstance(action, dict) or not isinstance(action.get("action"), str):
            _fail("Each action must be an object with an action name.")
        kind = action["action"]
        if kind == "add":
            _fields(action, EDIT_FIELDS | {"action", "blocked_by"}, {"action", "title", "minutes"}, "Add action")
            for field in set(action) - {"action"}:
                _editable(field, action[field])
            identity = json.dumps(action, sort_keys=True)
            if identity in seen_adds:
                _fail("A batch cannot contain duplicate add actions.")
            seen_adds.add(identity)
            continue
        extras = {"update": EDIT_FIELDS, "defer": {"until"}, "block": {"reason"},
                  "complete": set(), "reopen": set(), "drop": set(), "unblock": set()}
        if kind not in extras:
            _fail("Unknown action name.")
        required = {"action", "id"} | ({"until"} if kind == "defer" else {"reason"} if kind == "block" else set())
        _fields(action, {"action", "id"} | extras[kind], required, "Action")
        tid = _task_id(action["id"])
        if tid in seen_ids:
            _fail("A batch may change each existing task only once.")
        seen_ids.add(tid)
        if kind == "update":
            if not set(action) & EDIT_FIELDS:
                _fail("An update requires at least one editable field.")
            for field in set(action) & EDIT_FIELDS:
                _editable(field, action[field])
        elif kind == "defer":
            iso_date(action["until"], "until")
        elif kind == "block":
            _text(action["reason"], "reason")


def _apply_actions(state, actions, today=None):
    _validate_actions(actions)
    today = iso_date(today if today is not None else Date.today().isoformat(), "today")
    result = deepcopy(state)
    by_id = {task["id"]: task for task in result["tasks"]}
    for action in actions:
        kind = action["action"]
        if kind == "add":
            task = {"id": f"T{result['next_id']:04d}", "title": None, "minutes": None,
                    "priority": "normal", "due": None, "not_before": None,
                    "status": "open", "blocked_by": None, "notes": None,
                    "created": today, "completed": None}
            for field in set(action) & (EDIT_FIELDS | {"blocked_by"}):
                task[field] = _editable(field, action[field])
            result["tasks"].append(task)
            result["next_id"] += 1
            continue
        task = by_id.get(action["id"])
        if task is None:
            _fail("Action refers to a task that does not exist.", "task_not_found")
        if kind == "reopen":
            if task["status"] == "open":
                _fail("Task is already open.", "invalid_transition")
            task.update(status="open", completed=None)
        elif kind == "update":
            for field in set(action) & EDIT_FIELDS:
                task[field] = _editable(field, action[field])
        else:
            if task["status"] != "open":
                _fail("Reopen the task before changing its workflow status.", "invalid_transition")
            if kind == "complete":
                task.update(status="done", completed=today)
            elif kind == "drop":
                task.update(status="dropped", completed=None)
            elif kind == "defer":
                task["not_before"] = action["until"]
            elif kind == "block":
                task["blocked_by"] = _text(action["reason"], "reason")
            elif kind == "unblock":
                if task["blocked_by"] is None:
                    _fail("Task is not blocked.", "invalid_transition")
                task["blocked_by"] = None
    result["revision"] += 1
    return validate_state(result)


class Workspace:
    """Access one explicitly selected workspace, with cooperative writer locking."""

    def __init__(self, path):
        self.path = Path(path).expanduser()

    @contextmanager
    def _store(self, *, create=False, write=False):
        with _directory(self.path, create=create) as workspace:
            if create:
                try:
                    _mkdir_at(workspace, ".daily-ops")
                except FileExistsError:
                    pass
            try:
                if isinstance(workspace, int):
                    directory = os.open(".daily-ops", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                        dir_fd=workspace)
                else:
                    directory = _checked_path(workspace / ".daily-ops")
                    if not directory.is_dir():
                        _fail("Workspace is not initialized. Run init first.", "not_initialized")
            except FileNotFoundError:
                _fail("Workspace is not initialized. Run init first.", "not_initialized")
            except OSError as exc:
                if exc.errno in (errno.ELOOP, errno.ENOTDIR):
                    _fail("The state directory cannot be a symlink.", "unsafe_path")
                raise
            lock = None
            try:
                if write:
                    lock = _open_regular(directory, ".lock", os.O_RDWR | os.O_CREAT)
                    try:
                        if fcntl is not None:
                            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        elif msvcrt is not None:
                            getattr(msvcrt, "locking")(lock, getattr(msvcrt, "LK_NBLCK"), 1)
                        else:
                            _fail("No supported file locking API is available.", "unsupported_platform")
                    except OSError as exc:
                        if exc.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                            _fail("Another Daily Ops writer is active. Retry after it finishes.", "workspace_busy")
                        raise
                yield directory
            finally:
                if lock is not None:
                    os.close(lock)
                if isinstance(directory, int):
                    os.close(directory)

    def _read(self, directory):
        try:
            raw = _read_at(directory, "state.json")
        except FileNotFoundError:
            _fail("Workspace is not initialized. Run init first.", "not_initialized")
        return validate_state(_decode(raw)), raw

    def _write(self, directory, state, expected=None):
        raw = (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        if len(raw) > MAX_FILE_BYTES:
            _fail("State would exceed the local file size limit.")
        temporary = f".state-{uuid.uuid4().hex}.tmp"
        fd = _open_regular(directory, temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            if expected is None:
                try:
                    _replace_at(directory, temporary, "state.json", exclusive=True)
                except FileExistsError:
                    _fail("Workspace is already initialized; existing state was preserved.", "already_initialized")
            else:
                try:
                    current = _read_at(directory, "state.json")
                except FileNotFoundError:
                    _fail("State changed during this operation. Reload before retrying.", "concurrent_change")
                if current != expected:
                    _fail("State changed during this operation. Reload before retrying.", "concurrent_change")
                _replace_at(directory, temporary, "state.json")
            _sync_directory(directory)
        finally:
            try:
                _unlink_at(directory, temporary)
            except FileNotFoundError:
                pass

    def init(self):
        state = {"schema_version": SCHEMA_VERSION, "revision": 0, "next_id": 1, "tasks": []}
        with self._store(create=True, write=True) as directory:
            self._write(directory, state)
        return state

    def load(self):
        with self._store() as directory:
            state, _ = self._read(directory)
        return state

    def transact(self, actions, base_revision=None, today=None):
        if base_revision is not None:
            _integer(base_revision, "base_revision")
        with self._store(write=True) as directory:
            state, raw = self._read(directory)
            if base_revision is not None and state["revision"] != base_revision:
                _fail("Change file is stale. Reload state and preview a new change file.", "stale_revision")
            updated = _apply_actions(state, actions, today)
            self._write(directory, updated, raw)
        return updated

    def preview(self, change, today=None):
        validate_change(change)
        before = self.load()
        if before["revision"] != change["base_revision"]:
            _fail("Change file is stale. Reload state and preview a new change file.", "stale_revision")
        after = _apply_actions(before, change["actions"], today)
        return {"schema_version": SCHEMA_VERSION, "kind": "preview", "base_revision": before["revision"],
                "proposed_revision": after["revision"], "actions": deepcopy(change["actions"]),
                "before": before, "after": after}

    def apply(self, change, today=None):
        validate_change(change)
        return self.transact(change["actions"], change["base_revision"], today)

    def write_report(self, relative_path, content):
        """Atomically write UTF-8 report text under this initialized workspace.

        Reports cannot target runtime state. Existing symlink ancestors and leaf
        files are refused. This controls runtime writes, not other applications.
        """
        relative = Path(relative_path)
        reserved = {"CON", "PRN", "AUX", "NUL"} | {f"{prefix}{n}" for prefix in ("COM", "LPT") for n in range(1, 10)}
        if (relative.is_absolute() or relative.drive or not relative.parts or ".." in relative.parts
                or relative.parts[0].casefold() == ".daily-ops"
                or any(":" in part or "\\" in part or part.endswith((" ", "."))
                       or part.split(".")[0].upper() in reserved for part in relative.parts)):
            _fail("Report path must be relative, inside the workspace, and outside .daily-ops.", "unsafe_path")
        if not isinstance(content, str):
            _fail("Report content must be text.")
        encoded = content.encode("utf-8")
        if len(encoded) > MAX_FILE_BYTES:
            _fail("Report is too large.")
        with self._store(write=True) as store:
            self._read(store)
            with _directory(self.path / relative.parent, create=True) as directory:
                try:
                    existing = _open_regular(directory, relative.name)
                except FileNotFoundError:
                    pass
                else:
                    os.close(existing)
                temporary = f".report-{uuid.uuid4().hex}.tmp"
                descriptor = _open_regular(directory, temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
                try:
                    with os.fdopen(descriptor, "wb") as stream:
                        stream.write(encoded)
                        stream.flush()
                        os.fsync(stream.fileno())
                    # A swapped symlink leaf is replaced, never followed on POSIX;
                    # the portable implementation repeats its path preflight.
                    _replace_at(directory, temporary, relative.name)
                    _sync_directory(directory)
                finally:
                    try:
                        _unlink_at(directory, temporary)
                    except FileNotFoundError:
                        pass
        return str(self.path.absolute() / relative)


def make_plan(state, date, minutes):
    """Greedy, deterministic whole-task selection without changing state."""
    validate_state(state)
    date = iso_date(date)
    _integer(minutes, "minutes", 0, 1440)
    report = {"schema_version": SCHEMA_VERSION, "kind": "plan", "revision": state["revision"],
              "date": date, "budget_minutes": minutes, "planned_minutes": 0,
              "remaining_minutes": minutes, "selected": [], "deferred": [], "blocked": [],
              "conflicts": [], "tradeoffs": []}

    def rank(task):
        due = task["due"]
        urgency = 0 if due and due < date else 1 if due == date else 2 if due else 3
        return urgency, due or "9999-12-31", {"high": 0, "normal": 1, "low": 2}[task["priority"]], int(task["id"][1:])

    for task in sorted((task for task in state["tasks"] if task["status"] == "open"), key=rank):
        if task["blocked_by"]:
            category, reason = "blocked", "Waiting: " + task["blocked_by"]
        elif task["not_before"] and task["not_before"] > date:
            category, reason = "deferred", "Not available before " + task["not_before"] + "."
        elif task["minutes"] > report["remaining_minutes"]:
            category = "deferred"
            reason = f"Needs {task['minutes']} minutes; {report['remaining_minutes']} minutes remain. Estimate kept whole."
        else:
            category = "selected"
            urgency = "overdue" if task["due"] and task["due"] < date else "due today" if task["due"] == date else "upcoming due date" if task["due"] else "no due date"
            reason = f"Fits the budget; {urgency}, {task['priority']} priority."
            report["planned_minutes"] += task["minutes"]
            report["remaining_minutes"] -= task["minutes"]
        report[category].append({"task": deepcopy(task), "reason": reason})
        if category != "selected" and task["due"] and task["due"] <= date:
            report["conflicts"].append({"id": task["id"], "reason": reason})
    report["tradeoffs"].append("Due-date urgency is considered before priority; equal ranks use stable task IDs.")
    if report["deferred"]:
        report["tradeoffs"].append("Deferred tasks need a later plan, more explicit time, or an explicitly revised estimate; estimates are never shortened automatically.")
    if report["blocked"]:
        report["tradeoffs"].append("Waiting tasks consume no planned time and require an explicit unblock action.")
    if report["conflicts"]:
        report["tradeoffs"].append("Some tasks due by this date remain unscheduled; the plan does not resolve those commitments.")
    if report["remaining_minutes"]:
        report["tradeoffs"].append(f"{report['remaining_minutes']} minutes remain unassigned; remaining whole tasks may not fit or be available.")
    return report


def make_review(state, since=None):
    validate_state(state)
    since = iso_date(since, "since", optional=True)
    completed = [deepcopy(task) for task in state["tasks"]
                 if task["status"] == "done" and (since is None or task["completed"] >= since)]
    return {"schema_version": SCHEMA_VERSION, "kind": "review", "revision": state["revision"],
            "since": since, "completed": completed,
            "open": [deepcopy(task) for task in state["tasks"] if task["status"] == "open"],
            "dropped": [deepcopy(task) for task in state["tasks"] if task["status"] == "dropped"],
            "total_completed_minutes": sum(task["minutes"] for task in completed),
            "notes": ["Completed minutes are current task estimates, not measured time or time saved.",
                      "The since date filters completions only. Open and dropped tasks reflect current state."]}
