"""Provider interface. A provider knows how to talk to one site."""

from __future__ import annotations

from typing import Protocol

from ..models import Category, Page, Period, Sort, Video


class ProviderError(RuntimeError):
    """Network or API failure the user should see as a friendly message."""


class NotFoundError(ProviderError):
    pass


class Provider(Protocol):
    name: str

    def search(
        self,
        query: str | None = None,
        *,
        page: int = 1,
        sort: Sort = Sort.FEATURED,
        period: Period = Period.ALL,
        category: str | None = None,
    ) -> Page: ...

    def categories(self) -> list[Category]: ...

    def video(self, video_id: str) -> Video: ...

    def url_for(self, video_id: str) -> str: ...

    def parse_ref(self, ref: str) -> str:
        """Turn a video id or page URL into a video id."""
        ...

    def close(self) -> None: ...
