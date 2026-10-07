"""Release boundaries and installation behavior, using fictional fixtures only."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

from tools import check, install, package


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="daily-ops-package-test-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / "public source"
        self.root.mkdir()
        for relative in package.archive_members(package.ROOT, "source").values():
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(package.ROOT / relative, destination)

    def symlink(self, link: Path, target: Path, directory=False):
        try:
            link.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"Symlink creation is unavailable: {error}")

    def test_reproducible_archives_and_checksums(self):
        first = self.base / "first build"
        second = self.base / "second build"
        originals = package.build_all(self.root, first)
        for relative in package.archive_members(self.root, "source").values():
            path = self.root / relative
            if path.suffix in package.TEXT_SUFFIXES or path.name == "LICENSE":
                path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
            os.utime(path, (1700000000, 1700000000))
        repeated = package.build_all(self.root, second)
        self.assertEqual([p.read_bytes() for p in originals], [p.read_bytes() for p in repeated])
        check.check_archives(self.root, first)
        self.assertEqual((first / "SHA256SUMS").read_bytes(), (second / "SHA256SUMS").read_bytes())
        for path in originals:
            self.assertIn(hashlib.sha256(path.read_bytes()).hexdigest(), (first / "SHA256SUMS").read_text())

    def test_only_allowlisted_files_are_packaged(self):
        for relative in ("AGENTS.md", ".env", "workspace/notes.md", "docs/private.md", "tools/__pycache__/cache.py", "skills/daily-ops/extra.py", "site/examples/generated.html"):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("This file must stay outside release archives.")
        archives = package.build_all(self.root, self.base / "dist")
        for path in archives:
            with zipfile.ZipFile(path) as archive:
                contents = "\n".join(archive.namelist())
                for excluded in ("AGENTS.md", ".env", "workspace/", "private.md", "__pycache__", "extra.py", "site/examples/"):
                    self.assertNotIn(excluded, contents)
        with zipfile.ZipFile(archives[0]) as archive:
            self.assertIn(".claude-plugin/plugin.json", archive.namelist())
            self.assertNotIn("plugin.json", archive.namelist())
        with zipfile.ZipFile(archives[1]) as archive:
            self.assertIn("daily-ops/SKILL.md", archive.namelist())
            self.assertIn("daily-ops/LICENSE", archive.namelist())
        with zipfile.ZipFile(archives[2]) as archive:
            self.assertIn(f"daily-ops-{package.VERSION}/.github/workflows/ci.yml", archive.namelist())

    def test_source_symlink_is_rejected_without_following(self):
        source = self.root / "skills/daily-ops/SKILL.md"
        source.unlink()
        self.symlink(source, self.base / "not-present.md")
        with self.assertRaises(package.PackageError):
            package.archive_members(self.root, "skill")

    def test_directory_symlink_is_rejected(self):
        self.symlink(self.root / "tools/linked", self.base, directory=True)
        with self.assertRaises(package.PackageError):
            package.archive_members(self.root, "source")

    def test_existing_installation_is_preserved(self):
        target = self.base / "selected skills"
        result = install.install_skill(self.root, target)
        marker = result / "personal-note.txt"
        marker.write_text("Existing installation must remain unchanged.")
        before = (result / "SKILL.md").read_bytes()
        with self.assertRaises(package.PackageError):
            install.install_skill(self.root, target)
        self.assertEqual((result / "SKILL.md").read_bytes(), before)
        self.assertTrue(marker.exists())

    def test_explicit_target_with_spaces_via_cli(self):
        target = self.base / "folder with spaces" / "skills"
        result = subprocess.run([sys.executable, str(self.root / "tools/install.py"), "--target", str(target)], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((target / "daily-ops/SKILL.md").read_bytes(), package.read_public_file(self.root, "skills/daily-ops/SKILL.md"))
        self.assertTrue((target / "daily-ops/scripts/run.py").is_file())
        self.assertFalse((target / "daily-ops/AGENTS.md").exists())
        smoke = subprocess.run([sys.executable, str(target / "daily-ops/scripts/run.py"), "--help"], capture_output=True, text=True, check=False)
        self.assertEqual(smoke.returncode, 0, smoke.stderr)
        self.assertIn("workspace", smoke.stdout)

    def test_install_refuses_symlink_parent(self):
        real = self.base / "real target"
        real.mkdir()
        link = self.base / "linked target"
        self.symlink(link, real, directory=True)
        with self.assertRaises(package.PackageError):
            install.install_skill(self.root, link)
        self.assertFalse((real / "daily-ops").exists())

    def test_install_rejects_zip_as_source(self):
        archive = self.base / "untrusted.zip"
        with zipfile.ZipFile(archive, "w") as stream:
            stream.writestr("../outside.txt", "not extracted")
        with self.assertRaises((package.PackageError, OSError)):
            install.install_skill(archive, self.base / "target")
        self.assertFalse((self.base / "outside.txt").exists())

    def test_archive_with_unexpected_entry_is_rejected(self):
        output = self.base / "skill.zip"
        package.build_archive(self.root, output, "skill")
        with zipfile.ZipFile(output, "a") as archive:
            archive.writestr("../outside.txt", "not extracted")
        with self.assertRaises(package.PackageError):
            package.validate_archive(self.root, output, "skill")

    def test_checksums_detect_changed_file(self):
        output = self.base / "dist"
        package.build_all(self.root, output)
        (output / "SHA256SUMS").write_text("incorrect\n")
        with self.assertRaises(package.PackageError):
            check.check_archives(self.root, output)

    def test_public_text_checks_do_not_print_sensitive_values(self):
        examples = (
            "/" + "Users" + "/fictional-person/notes.txt",
            "fictional-person" + "@" + "example.test",
            "sk-" + "q" * 30,
        )
        for value in examples:
            self.assertTrue(package.public_text_issues(value))
            self.assertNotIn(value, str(package.public_text_issues(value)))
        self.assertFalse(package.public_text_issues("https://github.com/omerakben/daily-ops"))

    def test_repository_versions_and_frontmatter(self):
        self.assertGreater(check.validate_repository(self.root), 10)
        manifest = self.root / "plugin.json"
        manifest.write_text(manifest.read_text().replace(f'"{package.VERSION}"', '"9.0.0"'))
        with self.assertRaises(package.PackageError):
            check.validate_repository(self.root)
        with self.assertRaises(package.PackageError):
            check.frontmatter("---\nname: first\nname: second\n---\nText")

    def test_absolute_and_parent_source_paths_are_rejected(self):
        for path in (Path("../outside.txt"), self.base / "outside.txt"):
            with self.assertRaises(package.PackageError):
                package.read_public_file(self.root, path)


if __name__ == "__main__":
    unittest.main()
