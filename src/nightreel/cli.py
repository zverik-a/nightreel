"""Command-line entry point."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from . import config as config_mod
from .__about__ import APP_NAME, __version__
from .config import QUALITIES, Config, data_dir
from .models import Filters, Period, Sort, Video, format_count
from .player import PlayStatus
from .providers import NotFoundError, Provider, ProviderError, create
from .store import Store

app = typer.Typer(
    name=APP_NAME,
    help="Browse, stream and download from the terminal. Run without a command for the "
    "interactive UI.",
    no_args_is_help=False,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)
fav_app = typer.Typer(help="Manage favorites.", no_args_is_help=True)
history_app = typer.Typer(help="Show or clear watch history.", invoke_without_command=True)
config_app = typer.Typer(help="Inspect or create the config file.", no_args_is_help=True)
app.add_typer(fav_app, name="fav")
app.add_typer(history_app, name="history")
app.add_typer(config_app, name="config")

out = Console()
err = Console(stderr=True)


class State:
    cfg: Config
    config_path: Path | None = None
    assume_yes: bool = False
    _provider: Provider | None = None
    _store: Store | None = None

    def provider(self) -> Provider:
        if self._provider is None:
            self._provider = create(self.cfg)
        return self._provider

    def store(self) -> Store:
        if self._store is None:
            self._store = Store(data_dir() / "library.db", incognito=self.cfg.incognito)
        return self._store


state = State()


def _fail(message: str, code: int = 1) -> typer.Exit:
    err.print(f"[red]error:[/] {message}")
    return typer.Exit(code)


def _age_gate() -> None:
    if state.cfg.age_confirmed:
        return
    if state.assume_yes:
        return
    if not sys.stdin.isatty():
        raise _fail(
            "first run: confirm you are an adult with --yes, or set age_confirmed = true in "
            f"{state.config_path or config_mod.default_config_path()}"
        )
    err.print(
        "[bold]This tool gives access to adult content.[/]\n"
        "Continue only if you are at least 18 (or the age of majority where you live) and it is "
        "legal for you to view such content."
    )
    if not typer.confirm("Are you 18 or older?", default=False, err=True):
        raise typer.Exit(1)
    state.cfg.age_confirmed = True
    config_mod.update_file({"age_confirmed": True}, state.config_path)


def _version_cb(value: bool) -> None:
    if value:
        out.print(f"{APP_NAME} {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def root(
    ctx: typer.Context,
    proxy: Annotated[str | None, typer.Option(help="HTTP/SOCKS proxy URL.")] = None,
    incognito: Annotated[
        bool, typer.Option("--incognito", "-i", help="Don't record history or cache thumbnails.")
    ] = False,
    quality: Annotated[
        str | None, typer.Option("--quality", "-q", help=f"One of: {', '.join(QUALITIES)}.")
    ] = None,
    config_path: Annotated[
        Path | None, typer.Option("--config", help="Use a different config file.")
    ] = None,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Confirm the 18+ notice.")] = False,
    min_minutes: Annotated[int | None, typer.Option("--min", help="Minimum minutes.")] = None,
    max_minutes: Annotated[int | None, typer.Option("--max", help="Maximum minutes.")] = None,
    version: Annotated[
        bool, typer.Option("--version", callback=_version_cb, is_eager=True)
    ] = False,
) -> None:
    try:
        cfg = config_mod.load(config_path)
    except (ValueError, OSError) as exc:
        raise _fail(f"config: {exc}") from exc
    if proxy:
        cfg.proxy = proxy
    if incognito:
        cfg.incognito = True
    if quality:
        cfg.quality = quality
    try:
        cfg.validate()
    except ValueError as exc:
        raise _fail(str(exc)) from exc
    state.cfg = cfg
    state.config_path = config_path
    state.assume_yes = yes
    ctx.obj = Filters(min_minutes, max_minutes)

    if ctx.invoked_subcommand in ("config", "doctor"):
        return
    _age_gate()
    if ctx.invoked_subcommand is None:
        from .ui.app import App
        from .ui.picker import FzfMissingError

        try:
            App(cfg, state.provider(), state.store(), filters=ctx.obj).run()
        except FzfMissingError as exc:
            raise _fail(f"{exc}; run `{APP_NAME} doctor`") from exc
        except ProviderError as exc:
            raise _fail(str(exc)) from exc


# -- output helpers -----------------------------------------------------------


def _emit_json(data: Any) -> None:
    sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def _print_videos(videos: list[Video], as_json: bool) -> None:
    if as_json:
        _emit_json([v.to_dict() for v in videos])
        return
    if not videos:
        err.print("[dim]no results[/]")
        return
    # rich collapses columns when titles are long, so size everything explicitly
    id_w = max(len(v.id) for v in videos)
    title_w = max(out.width - id_w - 7 - 6 - 7 - 8, 20)
    table = Table(box=None, header_style="bold", pad_edge=False)
    table.add_column("id", style="dim", no_wrap=True, min_width=id_w)
    table.add_column("time", justify="right", no_wrap=True, min_width=7)
    table.add_column("views", justify="right", no_wrap=True, min_width=5)
    table.add_column("rating", justify="right", no_wrap=True, min_width=6)
    table.add_column("title", overflow="ellipsis", no_wrap=True, max_width=title_w)
    for v in videos:
        table.add_row(v.id, v.duration_str, format_count(v.views), f"{v.rating:g}%", v.title)
    out.print(table)


def _resolve(ref: str) -> Video:
    provider = state.provider()
    try:
        return provider.video(provider.parse_ref(ref))
    except ValueError as exc:
        raise _fail(str(exc)) from exc
    except NotFoundError as exc:
        raise _fail(str(exc)) from exc


def _guard(fn: Any, *args: Any, **kwargs: Any) -> Any:
    try:
        return fn(*args, **kwargs)
    except ProviderError as exc:
        raise _fail(str(exc)) from exc


# -- commands -----------------------------------------------------------------

JsonOpt = Annotated[bool, typer.Option("--json", help="Print JSON for scripting.")]
MinOpt = Annotated[int | None, typer.Option("--min", help="Minimum minutes.")]
MaxOpt = Annotated[int | None, typer.Option("--max", help="Maximum minutes.")]


def _filters(ctx: typer.Context, lo: int | None, hi: int | None) -> Filters:
    base: Filters = ctx.obj
    return Filters(
        lo if lo is not None else base.min_minutes, hi if hi is not None else base.max_minutes
    )


PageOpt = Annotated[int, typer.Option("--page", "-p", min=1)]


@app.command()
def search(
    ctx: typer.Context,
    query: Annotated[list[str], typer.Argument(help="Search words.")],
    sort: Annotated[Sort, typer.Option("--sort", "-s")] = Sort.FEATURED,
    period: Annotated[Period, typer.Option(help="Only with --sort views|rated.")] = Period.ALL,
    category: Annotated[str | None, typer.Option("--category", "-c")] = None,
    page: PageOpt = 1,
    min_minutes: MinOpt = None,
    max_minutes: MaxOpt = None,
    as_json: JsonOpt = False,
) -> None:
    """Search videos."""
    result = _guard(
        state.provider().search,
        " ".join(query),
        page=page,
        sort=sort,
        period=period,
        category=category,
    )
    _print_videos(_filters(ctx, min_minutes, max_minutes).apply(result.items), as_json)


@app.command()
def browse(
    ctx: typer.Context,
    sort: Annotated[Sort, typer.Option("--sort", "-s")] = Sort.VIEWS,
    period: Annotated[Period, typer.Option()] = Period.WEEK,
    category: Annotated[str | None, typer.Option("--category", "-c")] = None,
    page: PageOpt = 1,
    min_minutes: MinOpt = None,
    max_minutes: MaxOpt = None,
    as_json: JsonOpt = False,
) -> None:
    """List videos without a query (trending, newest, top rated, by category)."""
    result = _guard(
        state.provider().search, None, page=page, sort=sort, period=period, category=category
    )
    _print_videos(_filters(ctx, min_minutes, max_minutes).apply(result.items), as_json)


@app.command()
def categories(as_json: JsonOpt = False) -> None:
    """List categories (use the id with --category)."""
    cats = _guard(state.provider().categories)
    if as_json:
        _emit_json([{"id": c.id, "name": c.name} for c in cats])
    else:
        for c in cats:
            out.print(f"{c.id:<28} [dim]{c.name}[/]")


@app.command()
def info(ref: str, as_json: JsonOpt = False) -> None:
    """Show details for a video id or URL."""
    v = _guard(_resolve, ref)
    if as_json:
        _emit_json(v.to_dict())
        return
    from rich.text import Text

    from .ui.preview import render_text

    out.print(Text.from_ansi(render_text(v)))
    out.print(f"\n{v.url}")


@app.command("play")
def play_cmd(
    refs: Annotated[list[str], typer.Argument(help="Video ids or URLs.")],
    restart: Annotated[bool, typer.Option("--restart", help="Ignore saved position.")] = False,
) -> None:
    """Stream one or more videos in the player (resumes where you stopped)."""
    if restart:
        state.cfg.resume = False
    from .watch import watch

    videos = [_guard(_resolve, r) for r in refs]
    status = err.status("Fetching stream…")
    status.start()
    try:
        result = watch(videos, state.cfg, state.store(), on_launch=status.stop)
    finally:
        status.stop()
    if result.status is PlayStatus.PANIC:
        from .system import clear_screen

        clear_screen()
    elif result.status is PlayStatus.FAILED:
        raise _fail(f"playback failed: {result.message}")


@app.command()
def download(
    refs: Annotated[list[str] | None, typer.Argument(help="Video ids or URLs.")] = None,
    batch: Annotated[
        Path | None, typer.Option("--batch", "-b", help="File with one id/URL per line.")
    ] = None,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Target folder.")] = None,
) -> None:
    """Download videos (quality from -q or config)."""
    items = list(refs or [])
    if batch:
        lines = batch.read_text().splitlines()
        items += [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]
    if not items:
        raise _fail("nothing to download")
    if output:
        state.cfg.download_dir = str(output)
    provider = state.provider()
    try:
        urls = [provider.url_for(provider.parse_ref(r)) for r in items]
    except ValueError as exc:
        raise _fail(str(exc)) from exc
    from .ui.progress import download_with_progress

    results = download_with_progress(urls, state.cfg, err)
    if not all(r.ok for r in results):
        raise typer.Exit(1)


@fav_app.command("ls")
def fav_ls(as_json: JsonOpt = False) -> None:
    """List favorites."""
    _print_videos(state.store().favorites(), as_json)


@fav_app.command("add")
def fav_add(refs: list[str]) -> None:
    """Add videos to favorites."""
    for r in refs:
        v = _guard(_resolve, r)
        state.store().add_favorite(v)
        out.print(f"[green]♥[/] {v.title}")


@fav_app.command("rm")
def fav_rm(refs: list[str]) -> None:
    """Remove videos from favorites."""
    provider = state.provider()
    for r in refs:
        try:
            vid = provider.parse_ref(r)
        except ValueError as exc:
            raise _fail(str(exc)) from exc
        removed = state.store().remove_favorite(provider.name, vid)
        out.print(f"{'removed' if removed else 'not a favorite'}: {vid}")


@history_app.callback()
def history_cb(
    ctx: typer.Context,
    limit: Annotated[int, typer.Option("--limit", "-n")] = 50,
    as_json: JsonOpt = False,
) -> None:
    """Show recently watched videos."""
    if ctx.invoked_subcommand is None:
        _print_videos(state.store().history(limit), as_json)


@history_app.command("clear")
def history_clear() -> None:
    """Delete all watch history."""
    n = state.store().clear_history()
    out.print(f"cleared {n} entries")


@config_app.command("path")
def config_path_cmd() -> None:
    """Print the config file location."""
    out.print(str(state.config_path or config_mod.default_config_path()))


@config_app.command("show")
def config_show() -> None:
    """Print the effective configuration."""
    from dataclasses import asdict

    import tomli_w

    out.print(tomli_w.dumps(asdict(state.cfg)), highlight=False, markup=False)


@config_app.command("init")
def config_init(force: Annotated[bool, typer.Option("--force")] = False) -> None:
    """Write a config file with all defaults."""
    path = state.config_path or config_mod.default_config_path()
    if path.exists() and not force:
        raise _fail(f"{path} exists (use --force to overwrite)")
    out.print(f"wrote {config_mod.save(state.cfg, path)}")


@app.command()
def doctor(offline: Annotated[bool, typer.Option(help="Skip the network check.")] = False) -> None:
    """Check dependencies and site reachability."""
    from .doctor import run_checks

    checks = run_checks(state.cfg, network=not offline)
    table = Table(box=None, show_header=False)
    for c in checks:
        mark = "[green]✓[/]" if c.ok else ("[red]✗[/]" if c.required else "[yellow]![/]")
        table.add_row(mark, f"[bold]{c.name}[/]", c.detail)
        if c.hint:
            table.add_row("", "", f"[dim]{c.hint}[/]")
    out.print(table)
    if not all(c.ok for c in checks if c.required):
        raise typer.Exit(1)


def main() -> None:
    try:
        app()
    finally:
        if state._provider is not None:
            state._provider.close()
        if state._store is not None:
            state._store.close()


if __name__ == "__main__":
    main()
