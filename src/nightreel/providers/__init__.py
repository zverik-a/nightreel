"""Provider registry. Third-party providers can register via the ``<app>.providers`` entry point."""

from __future__ import annotations

from collections.abc import Callable
from importlib.metadata import entry_points

from ..__about__ import APP_NAME
from ..config import Config
from .base import NotFoundError, Provider, ProviderError
from .webmasters import WebmastersProvider

__all__ = ["NotFoundError", "Provider", "ProviderError", "available", "create"]


def _builtin() -> dict[str, Callable[[Config], Provider]]:
    return {
        "webmasters": lambda cfg: WebmastersProvider(timeout=cfg.timeout, proxy=cfg.proxy or None),
    }


def available() -> dict[str, Callable[[Config], Provider]]:
    found = _builtin()
    for ep in entry_points(group=f"{APP_NAME.replace('-', '_')}.providers"):
        found.setdefault(ep.name, ep.load())
    return found


def create(cfg: Config) -> Provider:
    factories = available()
    try:
        factory = factories[cfg.provider]
    except KeyError:
        raise ProviderError(
            f"unknown provider {cfg.provider!r} (available: {', '.join(sorted(factories))})"
        ) from None
    return factory(cfg)
