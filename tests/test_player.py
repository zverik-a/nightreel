from pathlib import Path

import pytest

from nightreel import player
from nightreel.config import Config
from nightreel.player import PlayStatus, Stream, mpv_command, stream_format


def test_stream_format() -> None:
    assert stream_format("best") == "best[protocol^=http]/best/bestvideo+bestaudio/best"
    assert stream_format("720").startswith("best[height<=720][protocol^=http]/best[height<=720]/")


def test_mpv_command_per_file_groups(tmp_path: Path) -> None:
    streams = [
        Stream(
            url="https://cdn/a.mp4",
            headers={"User-Agent": "UA", "Accept": "text/html,*/*;q=0.8", "Referer": "https://r/"},
            title="First",
            start=42.4,
        ),
        Stream(url="https://cdn/v.mp4", audio_url="https://cdn/a.m4a"),
    ]
    cfg = Config(player_args=["--volume=50"])
    cmd = mpv_command(streams, cfg, posfile=tmp_path / "pos")
    assert cmd[0] == "mpv" and "--no-ytdl" in cmd and "--volume=50" in cmd
    assert f"--script-opts-append=reelhelper-posfile={tmp_path / 'pos'}" in cmd
    first = cmd[cmd.index("--{") : cmd.index("--}") + 1]
    assert "--force-media-title=First" in first and "--start=42" in first
    assert "--user-agent=UA" in first
    # each header is its own option, commas inside values survive
    assert "--http-header-fields-append=Accept: text/html,*/*;q=0.8" in first
    assert "--http-header-fields-append=Referer: https://r/" in first
    assert first[-2] == "https://cdn/a.mp4"
    assert cmd[-3:] == ["--audio-file=https://cdn/a.m4a", "https://cdn/v.mp4", "--}"]


def test_helper_script_contents() -> None:
    cmd = mpv_command([Stream(url="u")], Config())
    script = Path(next(c for c in cmd if c.startswith("--script=")).split("=", 1)[1])
    text = script.read_text()
    assert 'mp.add_forced_key_binding("ctrl+x"' in text and "on_unload" in text
    cmd = mpv_command([Stream(url="u")], Config(panic_key=""))
    script = Path(next(c for c in cmd if c.startswith("--script=")).split("=", 1)[1])
    assert "add_forced_key_binding" not in script.read_text()


def test_read_positions(tmp_path: Path) -> None:
    f = tmp_path / "p"
    f.write_text("0 12.5 300.0\nbad line\n1 99.0 0.0\n")
    assert player._read_positions(f) == {0: (12.5, 300.0), 1: (99.0, 0.0)}
    assert player._read_positions(tmp_path / "missing") == {}


def test_play_reports_resolve_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(player.shutil, "which", lambda _: "/usr/bin/mpv")

    def boom(url: str, cfg: Config) -> Stream:
        raise RuntimeError("ERROR: gone")

    monkeypatch.setattr(player, "resolve", boom)
    launched: list[bool] = []
    result = player.play(["u"], Config(), on_launch=lambda: launched.append(True))
    assert result.status is PlayStatus.FAILED and result.message == "gone"
    assert launched == [True]  # spinner gets stopped on failure too
