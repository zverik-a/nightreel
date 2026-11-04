"""Launch a media player.

Streams are resolved with yt-dlp *here* and handed to the player as direct URLs together with
the exact HTTP headers yt-dlp used. Letting mpv run yt-dlp itself does not work for some sites:
its hook drops headers the CDN checks, and the server answers ``410 Gone``.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .config import Config, state_dir
from .downloader import ydl_options

PANIC_EXIT_CODE = 42
SCRIPT_ID = "reelhelper"

# Generated mpv helper: panic key + report the playback position of each file on unload.
_HELPER_LUA = """\
local opts = {{ posfile = "" }}
require("mp.options").read_options(opts, "{sid}")
{panic}
mp.add_hook("on_unload", 50, function()
    if opts.posfile == "" then return end
    local idx = mp.get_property_number("playlist-pos")
    local pos = mp.get_property_number("time-pos")
    if idx == nil or pos == nil then return end
    local dur = mp.get_property_number("duration") or 0
    local f = io.open(opts.posfile, "a")
    if f then
        f:write(string.format("%d %.1f %.1f\\n", idx, pos, dur))
        f:close()
    end
end)
"""
_PANIC_LUA = (
    'mp.add_forced_key_binding("{key}", "panic-quit", function() mp.command("quit {code}") end)'
)


class PlayStatus(Enum):
    OK = "ok"
    FAILED = "failed"
    PANIC = "panic"


@dataclass
class Stream:
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    audio_url: str = ""
    title: str = ""
    start: float = 0.0


@dataclass
class PlayResult:
    status: PlayStatus
    message: str = ""
    # playlist index -> (position, duration) in seconds, when the player reported them
    positions: dict[int, tuple[float, float]] = field(default_factory=dict)


def stream_format(quality: str) -> str:
    """Prefer a direct HTTP(S) file over HLS, a muxed stream over split video+audio.

    Direct files play reliably in mpv and seek instantly; HLS playlists on some CDNs are
    rejected (410) when requested outside yt-dlp, so they are only a fallback.
    """
    h = "" if quality == "best" else f"[height<={quality}]"
    return f"best{h}[protocol^=http]/best{h}/bestvideo{h}+bestaudio/best"


def resolve(url: str, cfg: Config) -> Stream:
    import yt_dlp

    opts = ydl_options(cfg) | {"format": stream_format(cfg.quality)}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info: dict[str, Any] = ydl.extract_info(url, download=False)
    parts = info.get("requested_formats") or [info]
    video = parts[0]
    if not video.get("url"):
        raise RuntimeError("could not resolve a stream URL")
    audio = parts[1].get("url", "") if len(parts) > 1 else ""
    headers = {str(k): str(v) for k, v in (video.get("http_headers") or {}).items()}
    return Stream(url=str(video["url"]), headers=headers, audio_url=str(audio))


def _helper_script(cfg: Config) -> Path:
    panic = ""
    if cfg.panic_key:
        key = cfg.panic_key.replace("-", "+")  # fzf syntax -> mpv syntax
        panic = _PANIC_LUA.format(key=key, code=PANIC_EXIT_CODE)
    content = _HELPER_LUA.format(sid=SCRIPT_ID, panic=panic)
    path = state_dir() / f"{SCRIPT_ID}.lua"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text() != content:
        path.write_text(content)
    return path


def mpv_command(streams: list[Stream], cfg: Config, *, posfile: Path | None = None) -> list[str]:
    cmd = [
        "mpv",
        f"--hwdec={cfg.hwdec}",
        "--msg-level=all=error,ffmpeg=fatal",
        "--term-status-msg=",
        "--no-resume-playback",  # signed URLs change every time; we track positions ourselves
        "--no-ytdl",  # already resolved
        f"--script={_helper_script(cfg)}",
    ]
    if posfile is not None:
        cmd.append(f"--script-opts-append={SCRIPT_ID}-posfile={posfile}")
    cmd += cfg.player_args
    for s in streams:
        # mpv per-file option group: --{ <options> <file> --}
        group = ["--{"]
        if s.title:
            group.append(f"--force-media-title={s.title}")
        if s.start > 0:
            group.append(f"--start={s.start:.0f}")
        for key, value in s.headers.items():
            if key.lower() == "user-agent":
                group.append(f"--user-agent={value}")
            else:
                # one option per header: values like Accept contain commas
                group.append(f"--http-header-fields-append={key}: {value}")
        if s.audio_url:
            group.append(f"--audio-file={s.audio_url}")
        group += [s.url, "--}"]
        cmd += group
    return cmd


def _read_positions(path: Path) -> dict[int, tuple[float, float]]:
    out: dict[int, tuple[float, float]] = {}
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return out
    for line in lines:
        parts = line.split()
        if len(parts) == 3:
            try:
                out[int(parts[0])] = (float(parts[1]), float(parts[2]))
            except ValueError:
                continue
    return out


def play(
    urls: list[str],
    cfg: Config,
    *,
    titles: list[str] | None = None,
    starts: list[float] | None = None,
    on_resolve: Callable[[int, int], None] | None = None,
    on_launch: Callable[[], None] | None = None,
) -> PlayResult:
    """Play ``urls`` as one playlist.

    ``on_resolve(i, n)`` runs before resolving each URL, ``on_launch()`` right before the player
    starts (use it to stop spinners so they don't draw over the player's terminal).
    """
    player = cfg.player or "mpv"
    if shutil.which(player) is None:
        return PlayResult(PlayStatus.FAILED, f"player {player!r} not found in PATH")

    streams: list[Stream] = []
    for i, url in enumerate(urls):
        if on_resolve:
            on_resolve(i, len(urls))
        try:
            s = resolve(url, cfg)
        except Exception as exc:  # yt-dlp raises many types
            if on_launch:
                on_launch()
            return PlayResult(PlayStatus.FAILED, _clean(str(exc)))
        if titles and i < len(titles):
            s.title = titles[i]
        if starts and i < len(starts):
            s.start = starts[i]
        streams.append(s)

    with tempfile.TemporaryDirectory() as tmp:
        posfile = Path(tmp) / "positions"
        if player == "mpv":
            cmd = mpv_command(streams, cfg, posfile=posfile)
        else:
            cmd = [player, *cfg.player_args, *(s.url for s in streams)]
        if on_launch:
            on_launch()
        try:
            code = subprocess.call(cmd)
        except KeyboardInterrupt:
            code = 0
        positions = _read_positions(posfile)

    if code == PANIC_EXIT_CODE:
        return PlayResult(PlayStatus.PANIC)
    # mpv: 0 = ok/quit, 4 = quit by signal; 1-3 = init / playback errors
    if code == 0 or (player == "mpv" and code == 4):
        return PlayResult(PlayStatus.OK, positions=positions)
    return PlayResult(PlayStatus.FAILED, f"{player} exited with code {code}", positions=positions)


def _clean(msg: str) -> str:
    return msg.replace("\x1b[0;31mERROR:\x1b[0m ", "").replace("ERROR: ", "").strip()
