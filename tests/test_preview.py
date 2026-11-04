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
