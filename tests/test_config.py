import tomllib
from pathlib import Path

import pytest

from nightreel import config
from nightreel.__about__ import ENV_PREFIX


def test_defaults_without_file(tmp_path: Path) -> None:
    cfg = config.load(tmp_path / "missing.toml", env={})
    assert cfg.quality == "1080"
    assert cfg.cookies_from_browser == ""  # never forced
    assert not cfg.age_confirmed


def test_file_and_env_override(tmp_path: Path) -> None:
    path = tmp_path / "c.toml"
    path.write_text('quality = "720"\nresume = false\n')
    cfg = config.load(path, env={ENV_PREFIX + "QUALITY": "480", ENV_PREFIX + "INCOGNITO": "yes"})
    assert cfg.quality == "480"
    assert cfg.resume is False
    assert cfg.incognito is True


def test_unknown_key_and_bad_quality(tmp_path: Path) -> None:
    path = tmp_path / "c.toml"
    path.write_text("nope = 1\n")
    with pytest.raises(ValueError, match="unknown config keys"):
        config.load(path, env={})
    path.write_text('quality = "4k"\n')
    with pytest.raises(ValueError, match="quality"):
        config.load(path, env={})


def test_update_file_keeps_other_keys(tmp_path: Path) -> None:
    path = tmp_path / "c.toml"
    path.write_text('theme = "mono"\n')
    config.update_file({"age_confirmed": True}, path)
    data = tomllib.loads(path.read_text())
    assert data == {"theme": "mono", "age_confirmed": True}
