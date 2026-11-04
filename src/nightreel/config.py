"""User configuration: TOML file + environment overrides."""

from __future__ import annotations

import os
import tomllib
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

import platformdirs
import tomli_w

from .__about__ import APP_NAME, ENV_PREFIX

QUALITIES = ("best", "1080", "720", "480", "360")


def config_dir() -> Path:
    return Path(platformdirs.user_config_dir(APP_NAME))


def data_dir() -> Path:
    return Path(platformdirs.user_data_dir(APP_NAME))


def cache_dir() -> Path:
    return Path(platformdirs.user_cache_dir(APP_NAME))


def state_dir() -> Path:
    return Path(platformdirs.user_state_dir(APP_NAME))


def default_config_path() -> Path:
    return config_dir() / "config.toml"


def _default_download_dir() -> str:
    return str(Path(platformdirs.user_videos_dir()) / APP_NAME)


@dataclass
class Config:
    provider: str = "webmasters"
    quality: str = "1080"
    download_dir: str = field(default_factory=_default_download_dir)
    output_template: str = "%(title)s [%(id)s].%(ext)s"
    player: str = "mpv"
    player_args: list[str] = field(default_factory=list)
    hwdec: str = "auto"
    resume: bool = True
    cookies_from_browser: str = ""
    proxy: str = ""
    timeout: float = 15.0
    incognito: bool = False
    theme: str = "default"
    fzf_colors: str = ""
    thumbnails: bool = True
    thumbnail_format: str = "symbols"
    panic_key: str = "ctrl-x"
    age_confirmed: bool = False

    @property
    def download_path(self) -> Path:
        return Path(os.path.expanduser(self.download_dir))

    def validate(self) -> None:
        if self.quality not in QUALITIES:
            raise ValueError(f"quality must be one of {', '.join(QUALITIES)}, got {self.quality!r}")


def _coerce(value: str, template: Any) -> Any:
    if isinstance(template, bool):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(template, float):
        return float(value)
    if isinstance(template, int):
        return int(value)
    if isinstance(template, list):
        return value.split()
    return value


def load(path: Path | None = None, env: dict[str, str] | None = None) -> Config:
    """Load config from ``path`` (or the default location), then apply ``<PREFIX>_<KEY>`` env."""
    path = path or default_config_path()
    env = dict(os.environ) if env is None else env
    cfg = Config()
    names = {f.name for f in fields(Config)}
    if path.exists():
        with path.open("rb") as fh:
            data = tomllib.load(fh)
        unknown = set(data) - names
        if unknown:
            raise ValueError(f"unknown config keys in {path}: {', '.join(sorted(unknown))}")
        for key, value in data.items():
            setattr(cfg, key, value)
    for name in names:
        raw = env.get(ENV_PREFIX + name.upper())
        if raw is not None:
            setattr(cfg, name, _coerce(raw, getattr(cfg, name)))
    cfg.validate()
    return cfg


def save(cfg: Config, path: Path | None = None) -> Path:
    path = path or default_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tomli_w.dumps(asdict(cfg)))
    return path


def update_file(updates: dict[str, Any], path: Path | None = None) -> Path:
    """Change only the given keys in the config file, keeping the rest as the user wrote it."""
    path = path or default_config_path()
    data: dict[str, Any] = {}
    if path.exists():
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    data.update(updates)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tomli_w.dumps(data))
    return path
