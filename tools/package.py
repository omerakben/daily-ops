"""Build reproducible, allowlisted release archives using only the standard library."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
import zipfile


ROOT = Path(__file__).absolute().parents[1]
VERSION = "1.0.0"
SKILL_ROOT = Path("skills/daily-ops")
SKILL_FILES = (
    "SKILL.md", "agents/openai.yaml", "references/changes.md",
    "references/manual-exchange.md", "scripts/run.py",
    "scripts/daily_ops/__init__.py", "scripts/daily_ops/__main__.py",
    "scripts/daily_ops/cli.py", "scripts/daily_ops/core.py",
    "scripts/daily_ops/render.py",
)
ROOT_FILES = (
    "README.md", "LICENSE", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md",
    "pyproject.toml", "plugin.json", ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json",
)
DOC_FILES = (
    "docs/platform-support.md", "docs/chat-project.md", "docs/architecture.md",
    "docs/product.md", "docs/evidence.md", "docs/install.md", "docs/scenario-results.json",
)
# Public source trees, with explicit file types. This never scans the repository root.
SOURCE_TREES = {
    "tools": {".py"}, "tests": {".py"},
    "examples": {".json", ".md", ".txt"},
    "site": {".html", ".css", ".js", ".svg", ".png", ".webp", ".ico"},
    ".github/workflows": {".yml", ".yaml"},
}
IGNORED_NAMES = {
    "__pycache__", "dist", "build", "workspace", "workspaces", "node_modules",
    "test-results", "playwright-report",
}
TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".toml", ".yaml", ".yml", ".html", ".css", ".js", ".svg"}
FIXED_TIME = (1980, 1, 1, 0, 0, 0)


class PackageError(ValueError):
    """A release input or archive violates the public packaging contract."""


def reject_symlinks(path: Path) -> None:
    """Reject symlink components before reading or writing a selected path."""
    for component in (path, *path.parents):
        if component.is_symlink():
            raise PackageError(f"Symlink paths are not supported: {component.name}")


def public_text_issues(text: str) -> list[str]:
    """Catch common accidental private material, without claiming a full secret scan."""
    patterns = {
        "personal home path": r"(?:/Users/|/home/)[A-Za-z0-9_.-]+/|[A-Za-z]:\\Users\\[^\\\s]+\\",
        "email address": r"\b[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+\b",
        "credential-like token": r"\b(?:sk-(?:proj-)?[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9]{24,}|github_pat_[A-Za-z0-9_]{24,}|xox[baprs]-[A-Za-z0-9-]{20,})\b",
        "private key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    }
    return [label for label, pattern in patterns.items() if re.search(pattern, text)]


def read_public_file(root: Path, relative: str | Path) -> bytes:
    relative = Path(relative)
    if relative.is_absolute() or ".." in relative.parts:
        raise PackageError("Source files must stay within the public repository")
    path = root / relative
    reject_symlinks(path)
    if not path.is_file():
        raise PackageError(f"Missing public release file: {relative}")
    data = path.read_bytes()
    if path.suffix in TEXT_SUFFIXES or path.name == "LICENSE":
        try:
            text = data.decode("utf-8").replace("\r\n", "\n")
        except UnicodeDecodeError as error:
            raise PackageError(f"Expected UTF-8 text: {relative}") from error
        issues = public_text_issues(text)
        if issues:
            raise PackageError(f"Public-content check failed for {relative}: {', '.join(issues)}")
        # Canonical line endings keep Windows and Unix release bytes identical.
        data = text.encode("utf-8")
    return data


def skill_files(root: Path) -> dict[str, Path]:
    files = {name: SKILL_ROOT / name for name in SKILL_FILES}
    # Include the license in standalone installations, too.
    files["LICENSE"] = Path("LICENSE")
    for path in files.values():
        read_public_file(root, path)
    return files


def walk_public_tree(root: Path, relative: str, suffixes: set[str]) -> list[Path]:
    start = root / relative
    if not start.exists() and not start.is_symlink():
        return []
    reject_symlinks(start)
    found: list[Path] = []
    pending = [start]
    while pending:
        directory = pending.pop()
        for child in sorted(directory.iterdir()):
            if child.name.startswith(".") or child.name in IGNORED_NAMES:
                continue
            reject_symlinks(child)
            if child.is_dir():
                pending.append(child)
            elif child.is_file() and child.suffix in suffixes:
                found.append(child.relative_to(root))
    return found


def archive_members(root: Path, kind: str) -> dict[str, Path]:
    """Map archive names to explicitly permitted source files."""
    root = root.absolute()
    reject_symlinks(root)
    skills = skill_files(root)
    if kind == "skill":
        members = {f"daily-ops/{name}": path for name, path in skills.items()}
    elif kind == "claude-plugin":
        members = {f"skills/daily-ops/{name}": path for name, path in skills.items() if name != "LICENSE"}
        members.update({name: Path(name) for name in (".claude-plugin/plugin.json", "README.md", "LICENSE")})
    elif kind == "source":
        paths = {*(SKILL_ROOT / name for name in SKILL_FILES), *(Path(name) for name in ROOT_FILES)}
        paths.update(Path(name) for name in DOC_FILES if (root / name).exists())
        for directory, suffixes in SOURCE_TREES.items():
            paths.update(walk_public_tree(root, directory, suffixes))
        members = {f"daily-ops-{VERSION}/{path.as_posix()}": path for path in paths}
    else:
        raise PackageError(f"Unknown archive kind: {kind}")
    for path in members.values():
        read_public_file(root, path)
    return dict(sorted(members.items()))


def validate_member_name(name: str) -> None:
    path = PurePosixPath(name)
    if not name or path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name:
        raise PackageError(f"Unsafe archive member: {name!r}")


def build_archive(root: Path, output: Path, kind: str) -> Path:
    members = archive_members(root, kind)
    reject_symlinks(output.absolute())
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".daily-ops-", suffix=".zip", dir=output.parent)
    os.close(descriptor)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_STORED) as archive:
            for name, source in members.items():
                validate_member_name(name)
                info = zipfile.ZipInfo(name, FIXED_TIME)
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                info.compress_type = zipfile.ZIP_STORED
                archive.writestr(info, read_public_file(root, source))
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return output


def validate_archive(root: Path, archive_path: Path, kind: str) -> None:
    reject_symlinks(archive_path.absolute())
    expected = archive_members(root, kind)
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        names = [entry.filename for entry in infos]
        if names != list(expected) or archive.comment:
            raise PackageError(f"Unexpected or duplicate files in {archive_path.name}")
        for info in infos:
            validate_member_name(info.filename)
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode) or info.flag_bits & 1:
                raise PackageError("Symlink or encrypted archive member")
            if (info.date_time != FIXED_TIME or mode != (stat.S_IFREG | 0o644)
                    or info.create_system != 3 or info.compress_type != zipfile.ZIP_STORED
                    or info.extra or info.comment):
                raise PackageError("Archive metadata is not reproducible")
            source = read_public_file(root, expected[info.filename])
            if info.file_size != len(source) or archive.read(info) != source:
                raise PackageError(f"Archive content differs from source: {info.filename}")


def build_all(root: Path, output: Path) -> list[Path]:
    archives = []
    for kind in ("claude-plugin", "skill", "source"):
        destination = output / f"daily-ops-{VERSION}-{kind}.zip"
        build_archive(root, destination, kind)
        validate_archive(root, destination, kind)
        archives.append(destination)
    checksums = "".join(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n" for path in archives)
    destination = output / "SHA256SUMS"
    reject_symlinks(destination.absolute())
    descriptor, temporary = tempfile.mkstemp(prefix=".daily-ops-checksums-", dir=output)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(checksums)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return archives


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist", help="Release output directory")
    args = parser.parse_args(argv)
    try:
        try:
            from .check import validate_repository
        except ImportError:
            from check import validate_repository
        validate_repository(ROOT)
        for path in build_all(ROOT, args.output.absolute()):
            print(path)
        print(args.output / "SHA256SUMS")
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        parser.exit(1, f"Package build failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
