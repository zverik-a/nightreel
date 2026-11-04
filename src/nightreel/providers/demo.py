"""Offline provider with neutral sample data, for demos, screenshots and trying the UI.

Select it with ``provider = "demo"`` in the config or the ``<PREFIX>PROVIDER=demo`` env var.
Playback and downloads don't work with it (the URLs point nowhere).
"""

from __future__ import annotations

import hashlib

from ..models import Category, Page, Period, Sort, Video

PAGE_SIZE = 20

_SUBJECTS = [
    ("Sunset timelapse over the bay", "nature", ["sunset", "timelapse", "ocean"]),
    ("Mountain hike to the hidden lake", "travel", ["hiking", "mountains", "lake"]),
    ("Rainy night drive through the city", "city", ["rain", "night", "driving"]),
    ("Northern lights, full night", "nature", ["aurora", "night", "sky"]),
    ("Slow morning in a seaside village", "travel", ["coast", "morning", "village"]),
    ("Fireplace with crackling logs", "ambient", ["fire", "cozy", "winter"]),
    ("Tokyo street walk at dusk", "city", ["tokyo", "walk", "dusk"]),
    ("Forest stream, birds and wind", "nature", ["forest", "water", "birds"]),
    ("Train ride across the countryside", "travel", ["train", "fields", "window"]),
    ("Thunderstorm over the plains", "nature", ["storm", "lightning", "sky"]),
    ("Night market food tour", "city", ["food", "market", "night"]),
    ("Snowfall in an empty park", "ambient", ["snow", "park", "quiet"]),
    ("Desert dunes at golden hour", "nature", ["desert", "dunes", "sunset"]),
    ("Harbor boats at dawn", "travel", ["harbor", "boats", "dawn"]),
    ("Lo-fi rooftop evening", "ambient", ["rooftop", "music", "evening"]),
    ("Waterfall from above, drone", "nature", ["waterfall", "drone", "river"]),
    ("Old town tram ride", "city", ["tram", "old town", "streets"]),
    ("Campfire under the stars", "ambient", ["campfire", "stars", "night"]),
    ("Island ferry crossing", "travel", ["ferry", "sea", "island"]),
    ("Cherry blossoms in the wind", "nature", ["spring", "blossoms", "wind"]),
]
_PARTS = ["", " (part 2)", " — extended cut", " in 4K", " — director's edit", " (remastered)"]


def _catalog() -> list[Video]:
    videos = []
    for n, part in enumerate(_PARTS):
        for i, (title, cat, tags) in enumerate(_SUBJECTS):
            seed = int(hashlib.sha1(f"{title}{part}".encode()).hexdigest(), 16)
            vid = f"demo{n:01d}{i:02d}"
            videos.append(
                Video(
                    id=vid,
                    title=title + part,
                    url=f"https://example.com/watch?v={vid}",
                    provider="demo",
                    duration=180 + seed % 3400,
                    views=1_000 + seed % 4_000_000,
                    rating=round(70 + (seed % 300) / 10, 1),
                    published=f"2026-{1 + seed % 10:02d}-{1 + seed % 27:02d} 12:00:00",
                    tags=tags,
                    categories=[cat],
                    performers=[],
                )
            )
    return videos


class DemoProvider:
    name = "demo"

    def __init__(self) -> None:
        self._videos = _catalog()

    def search(
        self,
        query: str | None = None,
        *,
        page: int = 1,
        sort: Sort = Sort.FEATURED,
        period: Period = Period.ALL,
        category: str | None = None,
    ) -> Page:
        items = self._videos
        if query:
            words = query.lower().split()
            items = [
                v
                for v in items
                if any(w in v.title.lower() or w in " ".join(v.tags) for w in words)
            ]
        if category:
            items = [v for v in items if category in v.categories]
        if sort is Sort.NEWEST:
            items = sorted(items, key=lambda v: v.published, reverse=True)
        elif sort is Sort.VIEWS:
            items = sorted(items, key=lambda v: v.views, reverse=True)
        elif sort is Sort.RATED:
            items = sorted(items, key=lambda v: v.rating, reverse=True)
        start = (max(page, 1) - 1) * PAGE_SIZE
        chunk = items[start : start + PAGE_SIZE]
        return Page(items=chunk, number=page, has_next=start + PAGE_SIZE < len(items))

    def categories(self) -> list[Category]:
        names = sorted({c for v in self._videos for c in v.categories})
        return [Category(id=n, name=n.title()) for n in names]

    def video(self, video_id: str) -> Video:
        from .base import NotFoundError

        for v in self._videos:
            if v.id == video_id:
                return v
        raise NotFoundError(f"no video with id {video_id!r}")

    def url_for(self, video_id: str) -> str:
        return f"https://example.com/watch?v={video_id}"

    def parse_ref(self, ref: str) -> str:
        return ref.rsplit("v=", 1)[-1].strip()

    def close(self) -> None:
        pass
