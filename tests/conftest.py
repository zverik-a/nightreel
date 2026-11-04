from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


@pytest.fixture(autouse=True)
def isolated_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Never touch the real user config/data dirs during tests."""
    for var in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME"):
        monkeypatch.setenv(var, str(tmp_path / var.lower()))
    return tmp_path


def api_video(i: int = 1, **over: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "video_id": f"abc{i:03d}",
        "title": f"Sample video {i}",
        "url": f"https://example.test/view_video.php?viewkey=abc{i:03d}",
        "duration": "12:34",
        "views": 1500 * i,
        "rating": "87.456",
        "default_thumb": f"https://img.example.test/{i}.jpg",
        "publish_date": "2026-10-30 00:30:05",
        "tags": [{"tag_name": "one"}, {"tag_name": "two"}],
        "categories": [{"category": "cat-a"}],
        "pornstars": [{"pornstar_name": "Someone"}],
    }
    data.update(over)
    return data
