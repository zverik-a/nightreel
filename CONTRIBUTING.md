# Contributing

```bash
uv venv && uv pip install -e '.[dev]'
uv run pytest && uv run ruff check . && uv run ruff format --check . && uv run mypy src
```

- Tests never hit the network: mock HTTP with `respx` (see `tests/test_webmasters.py`).
- Inside `src/`, use relative imports and `APP_NAME` from `__about__.py`. Never hardcode the
  project name (a test enforces this, so `scripts/rename.py` keeps working).
- New sites go in `providers/` and implement the `Provider` protocol from `providers/base.py`.
- Keep UI text neutral and short.
