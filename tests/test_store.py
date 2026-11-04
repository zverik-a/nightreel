from pathlib import Path

from nightreel.models import Video
from nightreel.store import Store


def vid(i: str) -> Video:
    return Video(id=i, title=f"t{i}", url=f"u{i}", provider="p")


def test_favorites_and_history(tmp_path: Path) -> None:
    db = tmp_path / "lib.db"
    s = Store(db)
    s.add_favorite(vid("1"))
    s.add_favorite(vid("2"))
    s.add_history(vid("3"))
    assert s.is_favorite("p", "1")
    assert [v.id for v in s.favorites()] == ["2", "1"]
    assert s.remove_favorite("p", "1") and not s.remove_favorite("p", "1")
    s.close()

    s = Store(db)  # persisted
    assert [v.id for v in s.favorites()] == ["2"]
    assert [v.id for v in s.history()] == ["3"]
    assert s.clear_history() == 1 and s.history() == []


def test_incognito_writes_nothing(tmp_path: Path) -> None:
    db = tmp_path / "lib.db"
    s = Store(db, incognito=True)
    s.add_history(vid("1"))
    s.add_favorite(vid("2"))
    assert s.history() == []
    assert not db.exists()


def test_positions() -> None:
    s = Store(None)
    assert s.position("p", "1") == 0.0
    s.set_position("p", "1", 61.5)
    assert s.position("p", "1") == 61.5
    s.set_position("p", "1", None)
    assert s.position("p", "1") == 0.0
    s.set_position("p", "2", 10.0)
    s.add_history(vid("2"))
    s.clear_history()
    assert s.position("p", "2") == 0.0
