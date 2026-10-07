"""Install the bundled skill from source into an explicitly selected parent folder."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil

try:
    from .package import ROOT, PackageError, read_public_file, reject_symlinks, skill_files
except ImportError:
    from package import ROOT, PackageError, read_public_file, reject_symlinks, skill_files


def install_skill(root: Path, target: Path) -> Path:
    """Create target/daily-ops. Never replace an existing directory or symlink."""
    target = target.expanduser().absolute()
    reject_symlinks(target)
    files = {name: read_public_file(root, source) for name, source in skill_files(root).items()}
    destination = target / "daily-ops"
    reject_symlinks(destination)
    if destination.exists():
        raise PackageError("The daily-ops destination already exists; choose a new target or move it yourself.")
    target.mkdir(parents=True, exist_ok=True)
    # mkdir is the atomic no-overwrite claim; an existing path always fails.
    destination.mkdir()
    try:
        for name, data in files.items():
            path = destination / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(data)
    except BaseException:
        # This directory was created by this invocation, never an existing install.
        shutil.rmtree(destination)
        raise
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path, help="Skill parent directory; creates TARGET/daily-ops without overwriting")
    args = parser.parse_args(argv)
    try:
        result = install_skill(ROOT, args.target)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Install failed: {error}\n")
    print(f"Installed source skill: {result}")
    print("Start a fresh host session and select daily-ops. Installation does not verify host execution.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
