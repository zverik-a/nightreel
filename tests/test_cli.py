from __future__ import annotations

import json
from typing import Any

import pytest
from typer.testing import CliRunner

from nightreel import cli
from nightreel.models import Category, Page, Video


class FakeProvider:
    name = "fake"

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def search(self, query: str | None = None, **kw: Any) -> Page:
        self.calls.append({"query": query, **kw})
        vids = [
            Video(id=f"v{m}", title=f"Video {m}", url=f"u{m}", provider="fake", duration=m * 60)
            for m in (5, 20)
        ]
        return Page(vids)

    def categories(self) -> list[Category]:
        return [Category("a", "A")]

    def video(self, video_id: str) -> Video:
        return Video(id=video_id, title="One", url=f"u{video_id}", provider="fake")

    def url_for(self, video_id: str) -> str:
        return f"u{video_id}"

    def parse_ref(self, ref: str) -> str:
        return ref

    def close(self) -> None:
        pass


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeProvider:
    provider = FakeProvider()
    monkeypatch.setattr(cli, "create", lambda cfg: provider)
    cli.state._provider = None
    cli.state._store = None
    return provider


runner = CliRunner()


def test_age_gate_blocks_non_interactive(fake: FakeProvider) -> None:
    result = runner.invoke(cli.app, ["search", "x"])
    assert result.exit_code == 1
    assert "--yes" in result.output


def test_search_json_and_filters(fake: FakeProvider) -> None:
    result = runner.invoke(cli.app, ["-y", "search", "two", "words", "--min", "10", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert [v["id"] for v in data] == ["v20"]
    assert fake.calls[0]["query"] == "two words"


def test_fav_roundtrip(fake: FakeProvider) -> None:
    assert runner.invoke(cli.app, ["-y", "fav", "add", "v1"]).exit_code == 0
    cli.state._store = None
    data = json.loads(runner.invoke(cli.app, ["-y", "fav", "ls", "--json"]).stdout)
    assert [v["id"] for v in data] == ["v1"]
    cli.state._store = None
    assert "removed" in runner.invoke(cli.app, ["-y", "fav", "rm", "v1"]).output


def test_config_commands_skip_age_gate(fake: FakeProvider) -> None:
    result = runner.invoke(cli.app, ["config", "path"])
    assert result.exit_code == 0 and result.output.strip().endswith("config.toml")


def test_bad_quality(fake: FakeProvider) -> None:
    result = runner.invoke(cli.app, ["-q", "4k", "categories"])
    assert result.exit_code == 1
