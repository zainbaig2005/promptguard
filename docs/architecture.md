# Architecture

PromptGuard separates test content, adapters, evaluators, execution, persistence, reporting, and dashboard views. Target secrets are referenced by environment variable names and are not stored in SQLite.
