"""Small OS helpers: clipboard, browser, screen clearing."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import webbrowser

_CLIPBOARD_TOOLS: tuple[tuple[str, list[str]], ...] = (
    ("wl-copy", []),
    ("xclip", ["-selection", "clipboard"]),
    ("xsel", ["--clipboard", "--input"]),
    ("pbcopy", []),
)


def copy_to_clipboard(text: str) -> bool:
    for tool, args in _CLIPBOARD_TOOLS:
        if tool == "wl-copy" and not os.environ.get("WAYLAND_DISPLAY"):
            continue
        if shutil.which(tool):
            try:
                subprocess.run([tool, *args], input=text, text=True, check=True, timeout=5)
                return True
            except (subprocess.SubprocessError, OSError):
                continue
    return False


def open_in_browser(url: str) -> bool:
    try:
        return webbrowser.open(url, new=2)
    except webbrowser.Error:
        return False


def clear_screen() -> None:
    """Clear the screen *and* scrollback (used by the panic key)."""
    if sys.stdout.isatty():
        sys.stdout.write("\033[3J\033[H\033[2J")
        sys.stdout.flush()
