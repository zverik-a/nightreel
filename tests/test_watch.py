import pytest

from nightreel import watch as watch_mod
from nightreel.config import Config
from nightreel.models import Video
from nightreel.player import PlayResult, PlayStatus
from nightreel.store import Store
from nightreel.watch import resume_point, watch


def test_resume_point() -> None:
    assert resume_point(5, 600) is None  # too early
    assert resume_point(590, 600) is None  # basically finished
    assert resume_point(120, 600) == 120
    assert resume_point(120, 0) == 120  # unknown duration


def test_watch_resumes_and_saves(monkeypatch: pytest.MonkeyPatch) -> None:
    store = Store(None)
    a = Video(id="a", title="A", url="ua", provider="p", duration=600)
    b = Video(id="b", title="B", url="ub", provider="p", duration=600)
    store.set_position("p", "a", 100.0)
    store.set_position("p", "b", 200.0)
    seen: dict[str, object] = {}

    def fake_play(urls: list[str], cfg: Config, **kw: object) -> PlayResult:
        seen.update(kw, urls=urls)
        return PlayResult(PlayStatus.OK, positions={0: (250.0, 600.0), 1: (595.0, 600.0)})

    monkeypatch.setattr(watch_mod, "play", fake_play)
    watch([a, b], Config(), store)
    assert seen["urls"] == ["ua", "ub"] and seen["starts"] == [100.0, 200.0]
    assert seen["titles"] == ["A", "B"]
    assert store.position("p", "a") == 250.0
    assert store.position("p", "b") == 0.0  # finished -> cleared
    assert {v.id for v in store.history()} == {"a", "b"}


def test_watch_without_resume(monkeypatch: pytest.MonkeyPatch) -> None:
    store = Store(None)
    v = Video(id="a", title="A", url="ua", provider="p")
    store.set_position("p", "a", 100.0)
    seen: dict[str, object] = {}

    def fake_play(urls: list[str], cfg: Config, **kw: object) -> PlayResult:
        seen.update(kw)
        return PlayResult(PlayStatus.OK, positions={0: (300.0, 600.0)})

    monkeypatch.setattr(watch_mod, "play", fake_play)
    watch([v], Config(resume=False), store)
    assert seen["starts"] == [0.0]
    assert store.position("p", "a") == 100.0  # untouched
