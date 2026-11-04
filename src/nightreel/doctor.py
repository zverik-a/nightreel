"""Environment checks with fix hints."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

from .config import Config
from .providers import ProviderError, create


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    hint: str = ""
    required: bool = True


_HINTS = {
    "mpv": "Arch: pacman -S mpv · Debian/Ubuntu: apt install mpv · macOS: brew install mpv",
    "fzf": "Arch: pacman -S fzf · Debian/Ubuntu: apt install fzf · macOS: brew install fzf",
    "ffmpeg": "needed to merge separate video/audio streams: install ffmpeg from your package "
    "manager",
    "chafa": "optional, for thumbnails: pacman -S chafa · apt install chafa · brew install chafa",
}


def _version(binary: str, flag: str = "--version") -> str:
    try:
        out = subprocess.run([binary, flag], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return "installed"
    for line in out.splitlines():
        if line.strip() and "unparsable" not in line:
            return line.split(" Copyright")[0].strip()[:60]
    return "installed"


def run_checks(cfg: Config, *, network: bool = True) -> list[Check]:
    checks: list[Check] = []
    for binary, required in (("mpv", True), ("fzf", True), ("ffmpeg", False), ("chafa", False)):
        if binary == "mpv" and cfg.player != "mpv":
            binary, required = cfg.player, True
        found = shutil.which(binary)
        checks.append(
            Check(
                binary,
                bool(found),
                _version(binary) if found else "not found",
                "" if found else _HINTS.get(binary, f"install {binary}"),
                required,
            )
        )

    try:
        import yt_dlp.version

        checks.append(Check("yt-dlp", True, str(yt_dlp.version.__version__)))
    except ImportError:
        checks.append(Check("yt-dlp", False, "python module missing", "pipx reinstall this tool"))

    if network:
        try:
            provider = create(cfg)
            try:
                count = len(provider.categories())
            finally:
                provider.close()
            checks.append(Check(f"api ({cfg.provider})", True, f"reachable, {count} categories"))
        except ProviderError as exc:
            checks.append(
                Check(f"api ({cfg.provider})", False, str(exc), "check your connection or --proxy")
            )
    return checks
