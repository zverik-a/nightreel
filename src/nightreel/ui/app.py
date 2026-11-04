"""Interactive fzf-driven interface."""

from __future__ import annotations

import contextlib
import json
import shlex
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

from rich.console import Console

from .. import system
from ..config import QUALITIES, Config, cache_dir
from ..models import Filters, Page, Period, Sort, Video, format_count
from ..player import PlayStatus
from ..providers import Provider, ProviderError
from ..store import Store
from ..watch import watch
from . import picker
from .progress import download_with_progress

NEXT, PREV = "__next__", "__prev__"
KEY_NEXT, KEY_PREV = "ctrl-n", "ctrl-p"
KEY_FAV, KEY_DL, KEY_OPEN, KEY_COPY = "ctrl-f", "ctrl-d", "ctrl-o", "ctrl-y"

Fetch = Callable[[int], Page]


class Panic(Exception):
    """Raised when the panic key is pressed anywhere: exit at once and wipe the screen."""


class App:
    def __init__(
        self, cfg: Config, provider: Provider, store: Store, *, filters: Filters | None = None
    ) -> None:
        self.cfg = cfg
        self.provider = provider
        self.store = store
        self.filters = filters or Filters()
        self.console = Console()
        self._tmp = tempfile.TemporaryDirectory(prefix="reel-")
        self.preview_file = Path(self._tmp.name) / "preview.json"
        self.thumb_cache = (
            Path(self._tmp.name) / "thumbs" if cfg.incognito else cache_dir() / "thumbs"
        )

    # -- entry ---------------------------------------------------------------

    def run(self) -> None:
        try:
            self._home()
        except Panic:
            system.clear_screen()
        finally:
            self._tmp.cleanup()

    def _home(self) -> None:
        options = [
            ("search", "  Search"),
            ("featured", "  Featured"),
            ("trending", "  Most viewed this week"),
            ("top", "  Top rated this month"),
            ("newest", "  Newest"),
            ("categories", "  Categories"),
            ("favorites", "  Favorites"),
            ("history", "  History"),
            ("quit", "  Quit"),
        ]
        while True:
            mode = " · incognito" if self.cfg.incognito else ""
            choice = self._menu(options, title=f"home{mode}")
            if choice in (None, "quit"):
                return
            if choice == "search":
                query = self._ask("Search")
                if query:
                    self._browse(f"Search: {query}", self._search(query, Sort.FEATURED))
            elif choice == "featured":
                self._browse("Featured", self._search(None, Sort.FEATURED))
            elif choice == "trending":
                self._browse("Most viewed", self._search(None, Sort.VIEWS, Period.WEEK))
            elif choice == "top":
                self._browse("Top rated", self._search(None, Sort.RATED, Period.MONTH))
            elif choice == "newest":
                self._browse("Newest", self._search(None, Sort.NEWEST))
            elif choice == "categories":
                self._categories()
            elif choice == "favorites":
                self._browse("Favorites", lambda _p: Page(self.store.favorites()), local=True)
            elif choice == "history":
                self._browse("History", lambda _p: Page(self.store.history()), local=True)

    # -- data sources ----------------------------------------------------------

    def _search(
        self,
        query: str | None,
        sort: Sort,
        period: Period = Period.ALL,
        category: str | None = None,
    ) -> Fetch:
        def fetch(page: int) -> Page:
            result = self.provider.search(
                query, page=page, sort=sort, period=period, category=category
            )
            result.items = self.filters.apply(result.items)
            return result

        return fetch

    def _categories(self) -> None:
        try:
            cats = self.provider.categories()
        except ProviderError as exc:
            self._error(str(exc))
            return
        while True:
            sel = picker.pick(
                [(c.id, c.name) for c in cats], self.cfg, prompt="Category", label="categories"
            )
            if sel is None:
                return
            self._check_panic(sel.key)
            cat = next((c for c in cats if c.id == sel.first), None)
            if cat:
                self._browse(cat.name, self._search(None, Sort.FEATURED, category=cat.id))

    # -- browsing --------------------------------------------------------------

    def _browse(self, title: str, fetch: Fetch, *, local: bool = False) -> None:
        number = 1
        cache: dict[int, Page] = {}  # remote pages don't change while browsing
        while True:
            try:
                if local or number not in cache:
                    with self.console.status("Loading…", spinner="dots"):
                        cache[number] = fetch(number)
                page = cache[number]
            except ProviderError as exc:
                self._error(str(exc))
                return
            if not page.items and number == 1:
                self._error("Nothing found.")
                return
            videos = {v.id: v for v in page.items}
            self._write_preview(videos)

            rows = [(v.id, self._row(v)) for v in page.items]
            if page.has_next:
                rows.append((NEXT, "\033[2m  → next page\033[0m"))
            if number > 1:
                rows.append((PREV, "\033[2m  ← previous page\033[0m"))

            header = "enter: actions · tab: multi-select · ^f fav · ^d download · ^o open · ^y copy"
            if not local:
                header += " · ^n/^p page"
            sel = picker.pick(
                rows,
                self.cfg,
                prompt=title if local else f"{title} [{number}]",
                label=title,
                header=header,
                multi=True,
                preview=self._preview_cmd(),
                expect=[KEY_NEXT, KEY_PREV, KEY_FAV, KEY_DL, KEY_OPEN, KEY_COPY],
            )
            if sel is None:
                return
            self._check_panic(sel.key)

            if sel.key == KEY_NEXT or (not sel.key and sel.first == NEXT):
                number += 1 if page.has_next else 0
                continue
            if sel.key == KEY_PREV or (not sel.key and sel.first == PREV):
                number = max(1, number - 1)
                continue

            chosen = [videos[i] for i in sel.ids if i in videos]
            if not chosen:
                continue
            action = {KEY_FAV: "fav", KEY_DL: "download", KEY_OPEN: "open", KEY_COPY: "copy"}.get(
                sel.key
            ) or self._actions(chosen)
            if action:
                self._do(action, chosen)

    def _row(self, v: Video) -> str:
        star = "\033[33m♥\033[0m" if self.store.is_favorite(v.provider, v.id) else " "
        meta = f"{v.duration_str:>8} {format_count(v.views):>6} {v.rating:>5.1f}%"
        return f"\033[2m{meta}\033[0m {star} {v.title}"

    def _actions(self, chosen: list[Video]) -> str | None:
        many = len(chosen) > 1
        fav = all(self.store.is_favorite(v.provider, v.id) for v in chosen)
        options = [
            ("watch", f"▶  Watch{f' all ({len(chosen)})' if many else ''}"),
            ("download", f"↓  Download ({self.cfg.quality})"),
            ("download_q", "↓  Download, choose quality…"),
            ("fav", "♥  Remove from favorites" if fav else "♥  Add to favorites"),
            ("open", "↗  Open in browser"),
            ("copy", "⧉  Copy link"),
            ("back", "←  Back"),
        ]
        title = chosen[0].title[:60] if not many else f"{len(chosen)} videos"
        choice = self._menu(options, title=title)
        return None if choice in (None, "back") else choice

    def _do(self, action: str, chosen: list[Video]) -> None:
        urls = [v.url for v in chosen]
        if action == "watch":
            status = self.console.status("Fetching stream…", spinner="dots")
            status.start()

            def progress(i: int, n: int) -> None:
                status.update(f"Fetching stream {i + 1}/{n}…" if n > 1 else "Fetching stream…")

            try:
                result = watch(
                    chosen, self.cfg, self.store, on_resolve=progress, on_launch=status.stop
                )
            finally:
                status.stop()
            if result.status is PlayStatus.PANIC:
                raise Panic
            if result.status is PlayStatus.FAILED:
                self._error(f"Playback failed: {result.message}")
        elif action in ("download", "download_q"):
            quality: str | None = self.cfg.quality
            if action == "download_q":
                quality = self._menu(
                    [(q, q if q == "best" else f"{q}p") for q in QUALITIES], title="quality"
                )
                if quality in (None, "panic"):
                    self._check_panic(quality or "")
                    return
            download_with_progress(urls, self.cfg, self.console, quality)
            self._pause()
        elif action == "fav":
            fav = all(self.store.is_favorite(v.provider, v.id) for v in chosen)
            for v in chosen:
                if fav:
                    self.store.remove_favorite(v.provider, v.id)
                else:
                    self.store.add_favorite(v)
        elif action == "open":
            for u in urls:
                system.open_in_browser(u)
        elif action == "copy":
            text = "\n".join(urls)
            if not system.copy_to_clipboard(text):
                self.console.print(text)
                self._pause()

    # -- helpers ---------------------------------------------------------------

    def _write_preview(self, videos: dict[str, Video]) -> None:
        payload = {
            "videos": {k: v.to_dict() for k, v in videos.items()},
            "hints": {NEXT: "Load the next page", PREV: "Back to the previous page"},
            "thumbnails": self.cfg.thumbnails,
            "thumb_cache": str(self.thumb_cache),
            "thumbnail_format": self.cfg.thumbnail_format,
        }
        self.preview_file.write_text(json.dumps(payload))

    def _preview_cmd(self) -> str:
        module = f"{__package__}.preview"
        return (
            f"{shlex.quote(sys.executable)} -m {module} {shlex.quote(str(self.preview_file))} {{1}}"
        )

    def _menu(self, options: list[tuple[str, str]], *, title: str) -> str | None:
        choice = picker.menu(options, self.cfg, title=title)
        if choice == "panic":
            raise Panic
        return choice

    def _check_panic(self, key: str) -> None:
        if key and key == self.cfg.panic_key:
            raise Panic

    def _ask(self, label: str) -> str:
        try:
            return self.console.input(f"[bold]{label}[/] › ").strip()
        except (EOFError, KeyboardInterrupt):
            return ""

    def _error(self, message: str) -> None:
        self.console.print(f"[red]✗[/] {message}")
        self._pause()

    def _pause(self) -> None:
        with contextlib.suppress(EOFError, KeyboardInterrupt):
            self.console.input("[dim]press Enter to continue[/]")
