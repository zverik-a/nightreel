"""Downloads through yt-dlp used as a library."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .config import Config


def format_for(quality: str) -> str:
    if quality == "best":
        return "bestvideo+bestaudio/best"
    return f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best"


def ydl_options(cfg: Config) -> dict[str, Any]:
    opts: dict[str, Any] = {"quiet": True, "no_warnings": True, "noplaylist": True}
    if cfg.proxy:
        opts["proxy"] = cfg.proxy
    if cfg.cookies_from_browser:
        opts["cookiesfrombrowser"] = (cfg.cookies_from_browser,)
    return opts


@dataclass
class DownloadResult:
    url: str
    ok: bool
    path: str = ""
    error: str = ""


@dataclass
class Downloader:
    cfg: Config
    on_progress: Callable[[dict[str, Any]], None] | None = None
    results: list[DownloadResult] = field(default_factory=list)

    def options(self, quality: str) -> dict[str, Any]:
        out_dir = self.cfg.download_path
        out_dir.mkdir(parents=True, exist_ok=True)
        opts = ydl_options(self.cfg) | {
            "format": format_for(quality),
            "outtmpl": str(out_dir / self.cfg.output_template),
            "merge_output_format": "mp4",
            "noprogress": True,
        }
        if self.on_progress:
            opts["progress_hooks"] = [self.on_progress]
        return opts

    def download(self, urls: list[str], quality: str | None = None) -> list[DownloadResult]:
        import yt_dlp

        quality = quality or self.cfg.quality
        results: list[DownloadResult] = []
        with yt_dlp.YoutubeDL(self.options(quality)) as ydl:
            for url in urls:
                try:
                    info = ydl.extract_info(url, download=True)
                    path = ""
                    if isinstance(info, dict):
                        downloads = info.get("requested_downloads") or []
                        path = downloads[0].get("filepath", "") if downloads else ""
                        path = path or ydl.prepare_filename(info)
                    results.append(DownloadResult(url, True, path=path))
                except Exception as exc:  # yt-dlp raises DownloadError and others
                    results.append(DownloadResult(url, False, error=_clean(str(exc))))
        self.results.extend(results)
        return results


def _clean(msg: str) -> str:
    return msg.replace("\x1b[0;31mERROR:\x1b[0m ", "").replace("ERROR: ", "").strip()
