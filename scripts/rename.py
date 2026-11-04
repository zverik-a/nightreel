#!/usr/bin/env python3
"""Rename the project everywhere: ``python scripts/rename.py NEWNAME [--dry-run]``.

Replaces the current name (read from ``src/<name>/__about__.py``) in every text file of the
repository, in lower, UPPER and Title case, and renames the package directory.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "dist",
    "build",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
}
NAME_RE = re.compile(r"^[a-z][a-z0-9-]*[a-z0-9]$")


def current_name(root: Path) -> str:
    for about in (root / "src").glob("*/__about__.py"):
        match = re.search(r'^APP_NAME = "([^"]+)"', about.read_text(), re.M)
        if match:
            return match.group(1)
    raise SystemExit("could not find src/*/__about__.py with APP_NAME")


def text_files(root: Path) -> list[Path]:
    files = []
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS or part.endswith(".egg-info") for part in path.parts):
            continue
        if path.is_file():
            try:
                path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            files.append(path)
    return files


def rename(root: Path, new: str, *, dry_run: bool = False) -> list[str]:
    old = current_name(root)
    if not NAME_RE.match(new):
        raise SystemExit(f"invalid name {new!r}: use lowercase letters, digits and dashes")
    if new == old:
        return []
    old_mod, new_mod = old.replace("-", "_"), new.replace("-", "_")
    # Python module contexts need the underscore form; everything else the display form.
    module_ctx = re.compile(
        rf"(?<=from )({re.escape(old_mod)})\b"
        rf"|(?<=import )({re.escape(old_mod)})\b"
        rf"|(?<=src/)({re.escape(old_mod)})\b"
        rf"|\b({re.escape(old_mod)})(?=\.[a-z_])"
    )
    plain = re.compile(rf"(?<![\w-])({re.escape(old)}|{re.escape(old_mod)})(?![\w-])")

    def convert(text: str) -> str:
        text = text.replace(old_mod.upper() + "_", new_mod.upper() + "_")  # env prefix
        text = text.replace(old.title(), new.title())
        text = module_ctx.sub(new_mod, text)
        return plain.sub(new, text)

    changes: list[str] = []
    for path in text_files(root):
        text = path.read_text(encoding="utf-8")
        updated = convert(text)
        if updated != text:
            changes.append(f"edit   {path.relative_to(root)}")
            if not dry_run:
                path.write_text(updated, encoding="utf-8")
    pkg = root / "src" / old_mod
    if pkg.is_dir():
        changes.append(f"rename src/{old_mod} -> src/{new_mod}")
        if not dry_run:
            pkg.rename(root / "src" / new_mod)
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    changes = rename(args.root, args.name, dry_run=args.dry_run)
    print("\n".join(changes) or "nothing to change")
    if changes and not args.dry_run:
        print("\nDone. Reinstall the package (pip install -e .) so the new command exists.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
