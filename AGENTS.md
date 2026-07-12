# Agent Instructions

- Preserve the architecture boundaries in `promptguard/`.
- Keep test definitions safe, synthetic, and original.
- Never commit `.env`, databases, reports, evidence, caches, screenshots, or credentials.
- Do not weaken validation, redaction, or authorization checks to make tests pass.
- Run `ruff check .`, `ruff format --check .`, `mypy promptguard`, and `pytest` before finishing substantial changes.
