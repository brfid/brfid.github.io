# Agent notes (repo workflow)

## Virtualenv-only

- Use the repo-local venv at `.venv/` for all Python commands.
- Do not install anything globally or modify system Python.

## Commit cadence

Commit at significant milestones so the history stays readable and bisectable. Examples:

- Landing page / UX milestone complete
- VAX stage milestone complete (local mode, then docker/SIMH mode)
- CI workflow changes
- Artifact format changes (`resume.vax.yaml`, transcript parsing, manifest format)

Before committing:

- Run `.venv/bin/python -m pytest -q`
- Run `.venv/bin/python -m ruff check .`
- Run `.venv/bin/python -m mypy resume_generator tests`

## No accidental publishing

- GitHub Pages deploy is tag-triggered (`publish` / `publish-*`). Avoid creating/pushing those tags unless you intend to deploy.

