"""Provider backed by the site's public JSON "webmasters" API (no HTML scraping)."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

from ..__about__ import USER_AGENT
from ..models import Category, Page, Period, Sort, Video, parse_duration
from .base import NotFoundError, ProviderError

BASE_URL = "https://www.pornhub.com"
PAGE_SIZE = 30

_SORT = {
    Sort.FEATURED: "featured",
    Sort.NEWEST: "newest",
    Sort.VIEWS: "mostviewed",
    Sort.RATED: "rating",
}
_PERIOD = {Period.WEEK: "weekly", Period.MONTH: "monthly", Period.ALL: "alltime"}
_ID_RE = re.compile(r"^[A-Za-z0-9]+$")

# API error codes
_NO_RESULTS = "2001"
_NO_VIDEO = "2002"


class WebmastersProvider:
    name = "webmasters"

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        timeout: float = 15.0,
        proxy: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            proxy=proxy or None,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            transport=httpx.HTTPTransport(retries=2),
            follow_redirects=True,
        )

    # -- HTTP ---------------------------------------------------------------

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            resp = self._client.get(path, params={k: v for k, v in params.items() if v})
        except httpx.TimeoutException as exc:
            raise ProviderError("the site took too long to respond (retry or use --proxy)") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"network error: {exc}") from exc
        if resp.status_code in (403, 451):
            raise ProviderError(
                f"access denied (HTTP {resp.status_code}); the site may be blocked in your "
                "region, try --proxy"
            )
        if resp.status_code >= 400:
            raise ProviderError(f"site returned HTTP {resp.status_code}")
        if "json" not in resp.headers.get("content-type", ""):
            raise ProviderError(
                "unexpected non-JSON response (age/region gate or captcha?); try --proxy"
            )
        try:
            data = resp.json()
        except ValueError as exc:
            raise ProviderError("invalid JSON from site") from exc
        if not isinstance(data, dict):
            raise ProviderError("unexpected API response shape")
        return data

    # -- API ----------------------------------------------------------------

    def search(
        self,
        query: str | None = None,
        *,
        page: int = 1,
        sort: Sort = Sort.FEATURED,
        period: Period = Period.ALL,
        category: str | None = None,
    ) -> Page:
        params: dict[str, Any] = {
            "search": (query or "").strip(),
            "page": max(page, 1),
            "ordering": _SORT[sort],
            "category": category,
            "thumbsize": "large",
        }
        # The API only accepts a period together with views/rating ordering.
        if sort in (Sort.VIEWS, Sort.RATED) and period is not Period.ALL:
            params["period"] = _PERIOD[period]
        data = self._get("/webmasters/search", params)
        if str(data.get("code")) == _NO_RESULTS:
            return Page(items=[], number=page, has_next=False)
        raw = data.get("videos")
        if not isinstance(raw, list):
            raise ProviderError(str(data.get("message") or "unexpected search response"))
        videos = [self._video(item) for item in raw if isinstance(item, dict)]
        return Page(items=videos, number=page, has_next=len(raw) >= PAGE_SIZE)

    def categories(self) -> list[Category]:
        data = self._get("/webmasters/categories", {})
        raw = data.get("categories")
        if not isinstance(raw, list):
            raise ProviderError("unexpected categories response")
        cats = [
            Category(id=str(c["category"]), name=str(c["category"]).replace("-", " ").title())
            for c in raw
            if isinstance(c, dict) and c.get("category")
        ]
        return sorted(cats, key=lambda c: c.name.lower())

    def video(self, video_id: str) -> Video:
        data = self._get("/webmasters/video_by_id", {"id": video_id, "thumbsize": "large"})
        if str(data.get("code")) == _NO_VIDEO:
            raise NotFoundError(f"no video with id {video_id!r}")
        raw = data.get("video")
        if not isinstance(raw, dict):
            raise ProviderError(str(data.get("message") or "unexpected video response"))
        return self._video(raw)

    def url_for(self, video_id: str) -> str:
        return f"{self.base_url}/view_video.php?viewkey={video_id}"

    def parse_ref(self, ref: str) -> str:
        ref = ref.strip()
        if ref.startswith(("http://", "https://")):
            keys = parse_qs(urlparse(ref).query).get("viewkey")
            if keys and _ID_RE.match(keys[0]):
                return keys[0]
            raise ValueError(f"could not find a video id in URL: {ref}")
        if _ID_RE.match(ref):
            return ref
        raise ValueError(f"not a video id or URL: {ref!r}")

    def close(self) -> None:
        self._client.close()

    # -- parsing ------------------------------------------------------------

    def _video(self, raw: dict[str, Any]) -> Video:
        vid = str(raw.get("video_id") or "")
        return Video(
            id=vid,
            title=str(raw.get("title") or "").strip(),
            url=str(raw.get("url") or self.url_for(vid)),
            provider=self.name,
            duration=parse_duration(raw.get("duration")),
            views=_int(raw.get("views")),
            rating=_float(raw.get("rating")),
            thumb=str(raw.get("default_thumb") or raw.get("thumb") or ""),
            published=str(raw.get("publish_date") or ""),
            tags=_names(raw.get("tags"), "tag_name"),
            categories=_names(raw.get("categories"), "category"),
            performers=_names(raw.get("pornstars"), "pornstar_name"),
        )


def _names(items: Any, key: str) -> list[str]:
    if not isinstance(items, list):
        return []
    return [str(i[key]) for i in items if isinstance(i, dict) and i.get(key)]


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _float(value: Any) -> float:
    try:
        return round(float(value), 1)
    except (TypeError, ValueError):
        return 0.0
