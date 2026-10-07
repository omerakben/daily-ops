"""Check portable metadata, public files, Python compatibility, and release archives."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

try:
    from .package import ROOT, VERSION, PackageError, archive_members, read_public_file, validate_archive
except ImportError:
    from package import ROOT, VERSION, PackageError, archive_members, read_public_file, validate_archive


SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise PackageError("SKILL.md needs delimited YAML frontmatter")
    fields = {}
    for line in text[4:].split("\n---\n", 1)[0].splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        if ":" not in line or line.startswith(" "):
            raise PackageError("This project's frontmatter must use simple key: value fields")
        key, value = line.split(":", 1)
        if key in fields:
            raise PackageError(f"Duplicate frontmatter field: {key}")
        fields[key] = value.strip().strip("\"'")
    return fields


def validate_repository(root: Path) -> int:
    members = archive_members(root, "source")
    for source in members.values():
        data = read_public_file(root, source)
        if source.suffix == ".py":
            ast.parse(data.decode("utf-8"), filename=str(source), feature_version=(3, 10))
    portable = json.loads(read_public_file(root, "plugin.json"))
    claude = json.loads(read_public_file(root, ".claude-plugin/plugin.json"))
    allowed = {"$schema", "name", "version", "description", "author", "homepage", "repository", "license", "keywords", "extensions"}
    if set(portable) - allowed or portable.get("$schema") != SCHEMA:
        raise PackageError("Portable plugin manifest has an unsupported schema or field")
    for manifest in (portable, claude):
        if manifest.get("name") != "daily-ops" or manifest.get("version") != VERSION:
            raise PackageError("Plugin names and release versions must agree")
    project = read_public_file(root, "pyproject.toml").decode("utf-8")
    if not re.search(rf'^version = "{re.escape(VERSION)}"$', project, re.MULTILINE):
        raise PackageError("Python package version does not match release version")
    skill_text = read_public_file(root, "skills/daily-ops/SKILL.md").decode("utf-8")
    metadata = frontmatter(skill_text)
    if metadata.get("name") != "daily-ops" or not 1 <= len(metadata.get("description", "")) <= 1024:
        raise PackageError("Skill name and description are required")
    if "<" in metadata["description"] or ">" in metadata["description"]:
        raise PackageError("Skill description must not contain XML tags")
    for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", skill_text):
        if "://" not in link and not link.startswith("#"):
            read_public_file(root, Path("skills/daily-ops") / link.split("#", 1)[0])
    for name in (".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json"):
        catalog = json.loads(read_public_file(root, name))
        if catalog.get("name") != "daily-ops-community" or len(catalog.get("plugins", [])) != 1:
            raise PackageError(f"Unexpected marketplace: {name}")
        if catalog["plugins"][0].get("name") != "daily-ops":
            raise PackageError(f"Marketplace must reference daily-ops: {name}")
    return len(members)


def check_archives(root: Path, directory: Path) -> None:
    expected = []
    for kind in ("claude-plugin", "skill", "source"):
        path = directory / f"daily-ops-{VERSION}-{kind}.zip"
        validate_archive(root, path, kind)
        expected.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    if (directory / "SHA256SUMS").read_text(encoding="utf-8").splitlines() != expected:
        raise PackageError("Release checksums do not match")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archives", type=Path, help="Also verify all generated release ZIPs and SHA256SUMS")
    parser.add_argument("--claude", action="store_true", help="Require installed Claude CLI and run its strict validator; no model call")
    args = parser.parse_args(argv)
    try:
        count = validate_repository(ROOT)
        if args.archives:
            check_archives(ROOT, args.archives)
        if args.claude:
            executable = shutil.which("claude")
            if not executable:
                raise PackageError("Claude CLI is not installed; omit --claude for portable checks")
            for relative in (".claude-plugin/plugin.json", ".claude-plugin/marketplace.json"):
                subprocess.run([executable, "plugin", "validate", str(ROOT / relative), "--strict"], check=True, timeout=60)
    except (OSError, ValueError, SyntaxError, zipfile.BadZipFile, subprocess.SubprocessError) as error:
        parser.exit(1, f"Check failed: {error}\n")
    print(f"Validated {count} public source files, portable metadata, and Python 3.10 syntax.")
    if args.archives:
        print("Release archive contents, metadata, and checksums match the source.")
    print("These checks do not establish model quality or successful host execution.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
