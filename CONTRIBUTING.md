# Contributing to agent-contracts

Thanks for your interest in contributing!

## Code of Conduct

This project follows the Contributor Covenant. By participating, you are expected to uphold it.
See `CODE_OF_CONDUCT.md`.

## Quickstart (dev)

Prereqs:
- Python 3.11+ (CI runs 3.11 and 3.12)

Setup:
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e ".[dev]"
```

Run tests:
```bash
pytest -q
```

Run coverage (CI requires 95%):
```bash
pytest -v --cov=src/agent_contracts --cov-branch --cov-fail-under=95
```

Run lint:
```bash
ruff check src/ tests/
```

## What to work on

- Bugs: include a minimal reproduction and expected/actual behavior.
- Docs: fixes and examples are welcome (English first; translations welcome).
- Features: open an issue first for anything non-trivial to avoid wasted work.

## Pull Requests

Please ensure:
- Tests pass locally.
- Public APIs are documented (update `docs/api_reference.md` when adding/changing exports).
- `CHANGELOG.md` is updated for user-facing changes (especially breaking changes + migration notes).

### Public API stability

The project is currently Beta. If you propose breaking changes, include:
- A clear rationale
- A migration note (before/after) in `CHANGELOG.md`
- Any compatibility considerations with LangGraph/LangChain versions

## Reporting security issues

Please do **not** open public issues for security reports. See `SECURITY.md`.

