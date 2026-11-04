"""Watch videos: resume from the stored position, play, remember where the user stopped."""

from __future__ import annotations

from collections.abc import Callable

from .config import Config
from .models import Video
from .player import PlayResult, PlayStatus, play
from .store import Store

MIN_RESUME = 15.0  # don't bother resuming the first seconds
END_MARGIN = 30.0  # closer than this to the end counts as finished


def resume_point(position: float, duration: float) -> float | None:
    """Position worth saving, or ``None`` when the video should start from the beginning."""
    if position < MIN_RESUME:
        return None
    if duration > 0 and duration - position < END_MARGIN:
        return None
    return position


def watch(
    videos: list[Video],
    cfg: Config,
    store: Store,
    *,
    on_resolve: Callable[[int, int], None] | None = None,
    on_launch: Callable[[], None] | None = None,
) -> PlayResult:
    use_resume = cfg.resume and not cfg.incognito
    starts = [store.position(v.provider, v.id) if use_resume else 0.0 for v in videos]
    for v in videos:
        store.add_history(v)
    result = play(
        [v.url for v in videos],
        cfg,
        titles=[v.title for v in videos],
        starts=starts,
        on_resolve=on_resolve,
        on_launch=on_launch,
    )
    if use_resume and result.status is not PlayStatus.PANIC:
        for idx, (pos, dur) in result.positions.items():
            if 0 <= idx < len(videos):
                v = videos[idx]
                store.set_position(v.provider, v.id, resume_point(pos, dur or v.duration))
    return result
