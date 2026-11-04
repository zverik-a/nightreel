"""The project name must live in one place so renaming stays easy."""

import shutil
import subprocess
import sys
from pathlib import Path

from nightreel.__about__ import APP_NAME

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "src" / APP_NAME.replace("-", "_")


def test_name_only_in_about() -> None:
    offenders = [
        str(p.relative_to(ROOT))
        for p in PKG.rglob("*.py")
        if p.name != "__about__.py" and APP_NAME in p.read_text()
    ]
    assert offenders == [], f"hardcoded project name in: {offenders} (use APP_NAME)"


def test_rename_script(tmp_path: Path) -> None:
    copy = tmp_path / "repo"
    shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", ".venv", "*cache*"))
    script = copy / "scripts" / "rename.py"
    subprocess.run(
        [sys.executable, str(script), "other-name", "--root", str(copy)],
        check=True,
        capture_output=True,
    )
    assert (copy / "src" / "other_name" / "__about__.py").exists()
    assert not (copy / "src" / APP_NAME).exists()
    assert 'APP_NAME = "other-name"' in (copy / "src/other_name/__about__.py").read_text()
    pyproject = (copy / "pyproject.toml").read_text()
    assert 'other-name = "other_name.cli:main"' in pyproject
    assert APP_NAME not in pyproject
    assert "from other_name.models import" in (copy / "tests/test_models.py").read_text()
    readme = (copy / "README.md").read_text()
    assert "other-name doctor" in readme and "other_name.providers" in readme
    assert "OTHER_NAME_QUALITY" in readme
