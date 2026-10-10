# Contributing

Thanks for wanting to improve transcribe! Issues and pull requests are welcome, in English or Spanish.

## Getting started

```bash
uv venv && uv pip install -e ".[dev]"
.venv/bin/pytest -q
.venv/bin/transcribe --help
```

The tests use a fake model, so they run offline in under a second. To try the real thing, `docs/demo/` has two short public-domain clips:

```bash
.venv/bin/transcribe docs/demo/quijote.ogg docs/demo/armstrong.ogg -l auto -t
```

## Guidelines

- **Keep it light:** the runtime dependencies are faster-whisper, numpy, questionary and Rich. New ones need a good reason.
- **Tests:** add or update tests in `tests/`. Pure formatting goes in `test_formats.py`, file discovery in `test_finder.py`, flags and the GPU fallback in `test_cli.py`. Never commit real recordings — `.gitignore` blocks audio outside `docs/demo/`.
- **UI text:** add every string to both languages in `src/ross_transcribe/i18n.py` (a test checks that both have the same keys).
- **Style:** `ruff check .` and `ruff format .` (line length 100).

## Pull requests

1. Fork and create a branch from `main`.
2. Make sure `pytest` and `ruff` pass.
3. Describe what changes and why; a short terminal recording or screenshot helps for UI changes.
