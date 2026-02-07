# Build and publish workflows

This file documents the workflows that currently exist in `.github/workflows/`.

## 1) CI checks (`ci.yml`)

- Trigger: push to `main`, pull requests
- Runs:
  - `ruff` (excluding `test_infra`)
  - `mypy resume_generator tests`
  - `pytest -q`
  - `pylint resume_generator tests -sn`
  - `vulture --config pyproject.toml resume_generator`

## 2) Feature-branch test workflow (`test.yml`)

- Trigger: push to non-`main` branches, pull requests
- Jobs:
  - quality checks (same toolchain as CI)
  - ARPANET Phase 1 docker bring-up test (`docker-compose.arpanet.phase1.yml`)
  - uploads test artifacts/logs

## 3) Publish workflow (`deploy.yml`)

- Trigger:
  - tags: `publish`, `publish-*`, `publish-arpanet*`, `publish-full*`
  - manual dispatch
- Runs quality checks, generates site artifacts, deploys to GitHub Pages.

### Important mode note

The CLI currently supports `--vax-mode local` and `--vax-mode docker`.
If a workflow path sets `vax_mode=arpanet`, that is a workflow-level label, not a CLI mode.
Use `local` for publish runs unless/until the workflow is updated to map labels to supported CLI modes.

## Operational guidance

- Normal development: push branches and use CI/test workflow feedback.
- Publishing: create a publish tag only when intentional (see AGENTS.md warning about accidental publish).
- For reproducibility, prefer documenting exact tag and workflow run URL in release notes.
