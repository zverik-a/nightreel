<h1 align="center">nightreel</h1>

<p align="center">
A fast, private, keyboard-driven terminal browser for adult video sites.<br>
Search, preview, stream and download — powered by <b>fzf</b>, <b>mpv</b> and <b>yt-dlp</b>.
</p>

<p align="center">
<img src="https://img.shields.io/badge/python-3.11%2B-blue">
<img src="https://img.shields.io/badge/os-linux%20%7C%20macOS-lightgrey">
<img src="https://img.shields.io/badge/license-MIT-green">
</p>

> **18+ only.** This tool gives access to adult content. Use it only if you are an adult and
> it is legal where you live, and respect the terms of the sites you use.

## Features

- **Interactive UI** — search, featured, trending, top rated, newest, categories, favorites and
  history, all in fzf with a live preview (duration, views, rating, tags, optional thumbnail).
- **Stream in mpv** with a quality cap, hardware decoding and **resume where you left off**.
- **Downloads** through yt-dlp with a progress bar, quality presets (best/1080/720/480/360),
  custom folder and filename template, batch files and multi-select.
- **Favorites & history** stored locally in SQLite. Nothing leaves your machine.
- **Incognito mode** (`-i`): no history, thumbnails only in a temp folder that's deleted on exit.
- **Panic key** (`ctrl-x` by default) works in the menus *and* inside mpv: quits instantly and
  wipes the terminal.
- **Scriptable**: every list command has `--json`.
- **Proxy support** for networks where the site is blocked.
- **`doctor`** command that checks everything and tells you how to fix it.
- Uses the site's official JSON API (no fragile HTML scraping) behind a **provider interface**,
  so other sites can be added as plugins.

## Install

Requirements: Python 3.11+, `mpv`, `fzf`. Recommended: `ffmpeg` (merging streams), `chafa`
(thumbnails).

```bash
pipx install git+https://github.com/zverik-a/nightreel
nightreel doctor
```

From a clone: `pipx install .` (or `pip install -e '.[dev]'` for development).

## Usage

```bash
nightreel                       # interactive UI
nightreel -i                    # incognito
nightreel --min 10 --max 30     # only 10–30 minute videos
```

Keys in result lists:

| key | action |
| --- | --- |
| `enter` | actions menu (watch, download, favorite, open, copy) |
| `tab` | select multiple (watch as a playlist, batch download) |
| `ctrl-n` / `ctrl-p` | next / previous page |
| `ctrl-f` | toggle favorite |
| `ctrl-d` | download at the default quality |
| `ctrl-o` | open in browser |
| `ctrl-y` | copy link |
| `ctrl-x` | panic: quit and clear the screen |

### Commands

```bash
nightreel search red dress --sort rated --period month
nightreel browse --sort newest --category amateur --json | jq '.[].title'
nightreel categories
nightreel info <id|url>
nightreel play <id|url> [...]          # resumes where you stopped; --restart to start over
nightreel download <id|url> [...] -q 720 -o ~/clips
nightreel download --batch list.txt
nightreel fav add|ls|rm ...
nightreel history [--limit 20] | nightreel history clear
nightreel config init|show|path
nightreel doctor
```

## Configuration

`nightreel config init` writes `~/.config/nightreel/config.toml` with every option:

```toml
quality = "1080"                  # best | 1080 | 720 | 480 | 360
download_dir = "~/Videos/nightreel"
output_template = "%(title)s [%(id)s].%(ext)s"
player = "mpv"                    # other players get a resolved direct stream URL
player_args = []
hwdec = "auto"
resume = true
cookies_from_browser = ""         # e.g. "firefox", only if you need your login
proxy = ""                        # e.g. "socks5://127.0.0.1:9050"
incognito = false
theme = "default"                 # default | ocean | mono
fzf_colors = ""                   # raw fzf --color string, overrides theme
thumbnails = true                 # needs chafa
thumbnail_format = "symbols"      # symbols | sixels | kitty | iterm | auto
panic_key = "ctrl-x"
```

Every option can also be set with an environment variable: `NIGHTREEL_QUALITY=720`,
`NIGHTREEL_PROXY=...`, and so on.

## Writing a provider

Implement the `Provider` protocol in `src/nightreel/providers/base.py` and register a factory
`(Config) -> Provider` under the `nightreel.providers` entry point group in your package's
`pyproject.toml`. Then select it with `provider = "yourname"` in the config.

## Development

```bash
uv venv && uv pip install -e '.[dev]'
pytest && ruff check . && mypy src
```

Renaming the project: `python scripts/rename.py newname` (add `--dry-run` to preview).

## License

MIT
