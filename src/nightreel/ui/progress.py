"""Rich progress display for downloads, shared by the CLI and the interactive UI."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from ..config import Config
from ..downloader import Downloader, DownloadResult


def download_with_progress(
    urls: list[str], cfg: Config, console: Console, quality: str | None = None
) -> list[DownloadResult]:
    progress = Progress(
        TextColumn("[bold]{task.description}", justify="left"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=False,
    )
    tasks: dict[str, TaskID] = {}

    def hook(d: dict[str, Any]) -> None:
        name = str(d.get("filename", "?"))
        info = d.get("info_dict") or {}
        title = str(info.get("title") or name)[:50]
        if name not in tasks:
            tasks[name] = progress.add_task(title, total=None)
        task = tasks[name]
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        if d.get("status") == "downloading":
            progress.update(task, completed=d.get("downloaded_bytes") or 0, total=total)
        elif d.get("status") == "finished":
            progress.update(task, completed=total or d.get("downloaded_bytes") or 0, total=total)

    console.print(f"[dim]Saving to {cfg.download_path}[/]")
    with progress:
        results = Downloader(cfg, on_progress=hook).download(urls, quality)
    for r in results:
        if r.ok:
            console.print(f"[green]✓[/] {r.path or r.url}")
        else:
            console.print(f"[red]✗[/] {r.url}: {r.error}")
    return results
