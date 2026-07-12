# Threat Model

## Assets

Secrets, target responses, evidence, reports, and database records.

## Threats

- Secret exposure through logs, reports, or SQLite.
- Unsafe rendering of model output.
- SSRF through generic REST target configuration.
- Path traversal in evidence and report output.
- Regex denial of service in test definitions.
- Misleading compliance claims.

## Controls

PromptGuard uses redaction, safe YAML loading, URL scheme validation, escaped dashboard/report rendering, bounded concurrency, deterministic mock targets, and explicit authorization confirmation.
