"""Provider-independent data models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Sort(StrEnum):
    FEATURED = "featured"
    NEWEST = "newest"
    VIEWS = "views"
    RATED = "rated"


class Period(StrEnum):
    WEEK = "week"
    MONTH = "month"
    ALL = "all"


def parse_duration(text: str | int | None) -> int:
    """Parse ``"1:02:03"`` / ``"10:30"`` / seconds into seconds."""
    if text is None or text == "":
        return 0
    if isinstance(text, int):
        return text
    total = 0
    for part in str(text).strip().split(":"):
        if not part.isdigit():
            return 0
        total = total * 60 + int(part)
    return total


def format_duration(seconds: int) -> str:
    h, rem = divmod(max(seconds, 0), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def format_count(n: int) -> str:
    for unit, div in (("B", 1_000_000_000), ("M", 1_000_000), ("K", 1_000)):
        if n >= div:
            return f"{n / div:.1f}{unit}".replace(".0", "")
    return str(n)


@dataclass(frozen=True)
class Category:
    id: str
    name: str


@dataclass
class Video:
    id: str
    title: str
    url: str
    provider: str = ""
    duration: int = 0
    views: int = 0
    rating: float = 0.0
    thumb: str = ""
    published: str = ""
    tags: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    performers: list[str] = field(default_factory=list)

    @property
    def duration_str(self) -> str:
        return format_duration(self.duration)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Video:
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class Page:
    items: list[Video]
    number: int = 1
    has_next: bool = False


@dataclass(frozen=True)
class Filters:
    min_minutes: int | None = None
    max_minutes: int | None = None

    def apply(self, videos: list[Video]) -> list[Video]:
        out = videos
        if self.min_minutes is not None:
            out = [v for v in out if v.duration >= self.min_minutes * 60]
        if self.max_minutes is not None:
            out = [v for v in out if v.duration <= self.max_minutes * 60]
        return out
