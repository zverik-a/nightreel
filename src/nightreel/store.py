"""Local favorites and watch history (SQLite). Nothing is written in incognito mode."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from .models import Video

_SCHEMA = """
CREATE TABLE IF NOT EXISTS favorites (
    provider TEXT NOT NULL,
    id TEXT NOT NULL,
    added_at REAL NOT NULL,
    data TEXT NOT NULL,
    PRIMARY KEY (provider, id)
);
CREATE TABLE IF NOT EXISTS history (
    provider TEXT NOT NULL,
    id TEXT NOT NULL,
    watched_at REAL NOT NULL,
    data TEXT NOT NULL,
    PRIMARY KEY (provider, id)
);
CREATE TABLE IF NOT EXISTS positions (
    provider TEXT NOT NULL,
    id TEXT NOT NULL,
    seconds REAL NOT NULL,
    updated_at REAL NOT NULL,
    PRIMARY KEY (provider, id)
);
"""


class Store:
    def __init__(self, path: Path | None, *, incognito: bool = False) -> None:
        """``path=None`` keeps everything in memory (used for incognito and tests)."""
        self.incognito = incognito
        if path is not None and not incognito:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(path)
        else:
            self._db = sqlite3.connect(":memory:")
        self._db.executescript(_SCHEMA)

    def close(self) -> None:
        self._db.close()

    # favorites ---------------------------------------------------------------

    def add_favorite(self, video: Video) -> None:
        with self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO favorites VALUES (?, ?, ?, ?)",
                (video.provider, video.id, time.time(), json.dumps(video.to_dict())),
            )

    def remove_favorite(self, provider: str, video_id: str) -> bool:
        with self._db:
            cur = self._db.execute(
                "DELETE FROM favorites WHERE provider = ? AND id = ?", (provider, video_id)
            )
        return cur.rowcount > 0

    def is_favorite(self, provider: str, video_id: str) -> bool:
        row = self._db.execute(
            "SELECT 1 FROM favorites WHERE provider = ? AND id = ?", (provider, video_id)
        ).fetchone()
        return row is not None

    def favorites(self) -> list[Video]:
        rows = self._db.execute("SELECT data FROM favorites ORDER BY added_at DESC").fetchall()
        return [Video.from_dict(json.loads(r[0])) for r in rows]

    # history -----------------------------------------------------------------

    def add_history(self, video: Video) -> None:
        if self.incognito:
            return
        with self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO history VALUES (?, ?, ?, ?)",
                (video.provider, video.id, time.time(), json.dumps(video.to_dict())),
            )

    def history(self, limit: int = 200) -> list[Video]:
        rows = self._db.execute(
            "SELECT data FROM history ORDER BY watched_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [Video.from_dict(json.loads(r[0])) for r in rows]

    def clear_history(self) -> int:
        with self._db:
            cur = self._db.execute("DELETE FROM history")
            self._db.execute("DELETE FROM positions")
        return cur.rowcount

    # resume positions --------------------------------------------------------

    def position(self, provider: str, video_id: str) -> float:
        row = self._db.execute(
            "SELECT seconds FROM positions WHERE provider = ? AND id = ?", (provider, video_id)
        ).fetchone()
        return float(row[0]) if row else 0.0

    def set_position(self, provider: str, video_id: str, seconds: float | None) -> None:
        """Store a resume point; ``None`` clears it (e.g. the video was watched to the end)."""
        with self._db:
            if seconds is None:
                self._db.execute(
                    "DELETE FROM positions WHERE provider = ? AND id = ?", (provider, video_id)
                )
            else:
                self._db.execute(
                    "INSERT OR REPLACE INTO positions VALUES (?, ?, ?, ?)",
                    (provider, video_id, seconds, time.time()),
                )
