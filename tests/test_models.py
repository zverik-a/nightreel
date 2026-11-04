from nightreel.models import Filters, Video, format_count, format_duration, parse_duration


def test_parse_duration() -> None:
    assert parse_duration("10:30") == 630
    assert parse_duration("1:02:03") == 3723
    assert parse_duration(42) == 42
    assert parse_duration(None) == 0
    assert parse_duration("bad") == 0


def test_format() -> None:
    assert format_duration(630) == "10:30"
    assert format_duration(3723) == "1:02:03"
    assert format_count(999) == "999"
    assert format_count(1500) == "1.5K"
    assert format_count(2_000_000) == "2M"


def test_filters() -> None:
    vids = [Video(id=str(m), title="", url="", duration=m * 60) for m in (5, 15, 40)]
    assert [v.id for v in Filters(min_minutes=10).apply(vids)] == ["15", "40"]
    assert [v.id for v in Filters(max_minutes=20).apply(vids)] == ["5", "15"]
    assert [v.id for v in Filters(10, 20).apply(vids)] == ["15"]


def test_video_roundtrip_ignores_unknown_keys() -> None:
    v = Video(id="x", title="t", url="u", tags=["a"])
    assert Video.from_dict(v.to_dict() | {"future_field": 1}) == v
