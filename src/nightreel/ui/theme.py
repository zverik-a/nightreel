"""fzf / rich colour themes."""

from __future__ import annotations

from ..config import Config

_THEMES: dict[str, str] = {
    "default": (
        "fg:#c8c8d0,bg:-1,hl:#ff6b81,fg+:#ffffff,bg+:#2a2a35,hl+:#ff8fa3,"
        "info:#8a8aa0,prompt:#ff6b81,pointer:#ff6b81,marker:#ffd166,spinner:#ffd166,"
        "header:#8a8aa0,border:#44445a,label:#ff8fa3"
    ),
    "ocean": (
        "fg:#c0d0e0,bg:-1,hl:#4fc3f7,fg+:#ffffff,bg+:#1e2a38,hl+:#81d4fa,"
        "info:#78909c,prompt:#4fc3f7,pointer:#4fc3f7,marker:#ffd54f,spinner:#ffd54f,"
        "header:#78909c,border:#37474f,label:#81d4fa"
    ),
    "mono": "bw",
}

ACCENT = {"default": "#ff6b81", "ocean": "#4fc3f7", "mono": "white"}


def names() -> list[str]:
    return sorted(_THEMES)


def fzf_args(cfg: Config) -> list[str]:
    colors = cfg.fzf_colors or _THEMES.get(cfg.theme, _THEMES["default"])
    return [
        f"--color={colors}",
        "--pointer=▶",
        "--marker=+",
        "--prompt=› ",
        "--border=rounded",
        "--layout=reverse",
        "--height=100%",
        "--cycle",
        "--info=inline-right",
    ]


def accent(cfg: Config) -> str:
    return ACCENT.get(cfg.theme, ACCENT["default"])
