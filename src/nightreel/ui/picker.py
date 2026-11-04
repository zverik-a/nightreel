"""Thin, generic wrapper around fzf. Every list in the UI goes through :func:`pick`."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass, field

from ..config import Config
from . import theme

SEP = "\t"


@dataclass
class Selection:
    key: str  # "" for Enter, otherwise the --expect key that was pressed
    ids: list[str] = field(default_factory=list)

    @property
    def first(self) -> str:
        return self.ids[0] if self.ids else ""


class FzfMissingError(RuntimeError):
    pass


def pick(
    rows: Sequence[tuple[str, str]],
    cfg: Config,
    *,
    prompt: str = "",
    header: str = "",
    label: str = "",
    multi: bool = False,
    preview: str | None = None,
    expect: Sequence[str] = (),
    extra: Sequence[str] = (),
    cursor: str | None = None,
) -> Selection | None:
    """Show ``(id, text)`` rows in fzf. Returns ``None`` when the user cancels (Esc / Ctrl-C).

    ``cursor`` is the id of the row to start on (e.g. to stay in place after an action).
    """
    keys = [k for k in (cfg.panic_key, *expect) if k]
    cmd = [
        "fzf",
        *theme.fzf_args(cfg),
        f"--delimiter={SEP}",
        "--with-nth=2..",
        "--ansi",
        "--no-sort",
    ]
    if prompt:
        cmd.append(f"--prompt={prompt} › ")
    if header:
        cmd += [f"--header={header}", "--header-first"]
    if label:
        cmd.append(f"--border-label= {label} ")
    if multi:
        cmd.append("--multi")
    if preview:
        cmd += [f"--preview={preview}", "--preview-window=right,45%,wrap,border-left"]
    if keys:
        cmd.append(f"--expect={','.join(dict.fromkeys(keys))}")
    if cursor is not None:
        index = next((i for i, (rid, _) in enumerate(rows) if rid == cursor), None)
        if index:
            cmd.append(f"--bind=load:pos({index + 1})")
    cmd += list(extra)

    payload = "\n".join(f"{rid}{SEP}{text}" for rid, text in rows)
    try:
        proc = subprocess.run(cmd, input=payload, stdout=subprocess.PIPE, text=True, check=False)
    except FileNotFoundError as exc:
        raise FzfMissingError("fzf is not installed") from exc
    if proc.returncode in (1, 130) and not proc.stdout.strip():
        return None
    lines = proc.stdout.split("\n")
    key = lines[0] if keys else ""
    chosen = lines[1:] if keys else lines
    ids = [line.split(SEP, 1)[0] for line in chosen if line.strip()]
    if not ids and not key:
        return None
    return Selection(key=key, ids=ids)


def menu(
    options: Sequence[tuple[str, str]], cfg: Config, *, title: str, header: str = ""
) -> str | None:
    """Small fixed menu. Returns the chosen id, ``"panic"`` or ``None``."""
    sel = pick(
        options,
        cfg,
        label=title,
        header=header,
        extra=["--height=~60%", "--no-info", "--exact"],
    )
    if sel is None:
        return None
    if sel.key and sel.key == cfg.panic_key:
        return "panic"
    return sel.first or None
