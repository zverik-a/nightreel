import json
from pathlib import Path

import pytest

from nightreel.models import Video
from nightreel.ui import preview


def test_preview_main(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    v = Video(
        id="a1", title="Title here", url="u", duration=90, views=2500, rating=91.0, tags=["x", "y"]
    )
    data = tmp_path / "p.json"
    data.write_text(
        json.dumps(
            {"videos": {"a1": v.to_dict()}, "hints": {"__next__": "Next"}, "thumbnails": False}
        )
    )
    preview.main([str(data), "a1"])
    out = capsys.readouterr().out
    assert "Title here" in out and "1:30" in out and "2.5K" in out and "x, y" in out
    preview.main([str(data), "__next__"])
    assert "Next" in capsys.readouterr().out
    assert preview.main([str(tmp_path / "missing.json"), "a1"]) == 0


def test_pick_cursor(monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess

    from nightreel.config import Config
    from nightreel.ui import picker

    seen: list[list[str]] = []

    def fake_run(cmd: list[str], **kw: object) -> subprocess.CompletedProcess[str]:
        seen.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="\nb\tB\n")

    monkeypatch.setattr(picker.subprocess, "run", fake_run)
    rows = [("a", "A"), ("b", "B"), ("c", "C")]
    sel = picker.pick(rows, Config(), cursor="c")
    assert sel is not None and sel.first == "b"
    assert "--bind=load:pos(3)" in seen[0]
    picker.pick(rows, Config(), cursor="a")  # first row: no bind needed
    assert not any(c.startswith("--bind=load") for c in seen[1])
