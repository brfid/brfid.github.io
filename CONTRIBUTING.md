# Contributing

Thanks for your interest in improving this repository.

## Branching and history

- Default branch is `main`.
- Prefer small, focused commits with clear messages.
- Do not rewrite shared history on `main` unless explicitly requested by the repo owner.
- Do not create/push deploy tags unless intentionally publishing.

## Tag hygiene

- Deploy tags are operational, not release history.
- Keep only a short rolling window of timestamp deploy tags (`publish-fast-*`, dated
  `publish-vax-*`, dated `publish-vax-logs-*`).
- Keep milestone/version tags (`publish-v*`, `publish-vax-v*`, named pipeline milestones)
  unless explicitly retired.

## Local validation

Use the repo-local virtualenv only:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check resume_generator
.venv/bin/python -m mypy resume_generator host_logging tests
```

Run Hugo preview from repo root:

```bash
hugo server --source hugo
```

## Security and secrets

- Never commit credentials, API keys, or private keys.
- Secret scanning runs in GitHub Actions (`Secret Scan`).
