"""fzf preview helper: ``python -m <pkg>.ui.preview CACHE_JSON VIDEO_ID``.

Runs in a separate process for each highlighted row, so it must be quick and never crash.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from ..models import Video, format_count

BOLD, DIM, RESET, ACCENT = "\033[1m", "\033[2m", "\033[0m", "\033[38;5;210m"


def render_text(v: Video) -> str:
    lines = [
        f"{BOLD}{v.title}{RESET}",
        "",
        f"{ACCENT}⏱{RESET} {v.duration_str}   {ACCENT}👁{RESET} {format_count(v.views)}   "
        f"{ACCENT}★{RESET} {v.rating:g}%",
    ]
    if v.published:
        lines.append(f"{DIM}published {v.published[:10]}{RESET}")
    if v.performers:
        lines += ["", f"{BOLD}With:{RESET} " + ", ".join(v.performers[:6])]
    if v.categories:
        lines += ["", f"{BOLD}Categories:{RESET} " + ", ".join(v.categories[:8])]
    if v.tags:
        lines += ["", f"{BOLD}Tags:{RESET} {DIM}" + ", ".join(v.tags[:15]) + RESET]
    lines += ["", f"{DIM}{v.id}{RESET}"]
    return "\n".join(lines)


def _thumb(v: Video, cache: Path) -> Path | None:
    if not v.thumb:
        return None
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / (hashlib.sha1(v.thumb.encode()).hexdigest() + ".jpg")
    if path.exists():
        return path
    try:
        import httpx

        resp = httpx.get(v.thumb, timeout=5, follow_redirects=True)
        resp.raise_for_status()
        path.write_bytes(resp.content)
        return path
    except Exception:
        return None


def show_thumb(v: Video, cache: Path, fmt: str) -> None:
    if shutil.which("chafa") is None:
        return
    img = _thumb(v, cache)
    if img is None:
        return
    cols = int(os.environ.get("FZF_PREVIEW_COLUMNS", "40"))
    rows = max(int(os.environ.get("FZF_PREVIEW_LINES", "20")) // 2, 6)
    cmd = ["chafa", f"--size={cols}x{rows}", "--animate=off"]
    if fmt and fmt != "auto":
        cmd.append(f"--format={fmt}")
    subprocess.run([*cmd, str(img)], check=False, stderr=subprocess.DEVNULL)
    sys.stdout.flush()


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        return 0
    data_file, video_id = Path(argv[0]), argv[1]
    try:
        payload = json.loads(data_file.read_text())
    except (OSError, ValueError):
        return 0
    raw = payload.get("videos", {}).get(video_id)
    if raw is None:
        print(payload.get("hints", {}).get(video_id, ""))
        return 0
    v = Video.from_dict(raw)
    if payload.get("thumbnails"):
        show_thumb(v, Path(payload["thumb_cache"]), payload.get("thumbnail_format", "symbols"))
    print(render_text(v))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
