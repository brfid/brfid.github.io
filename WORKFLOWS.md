# Build and publish workflows

This file documents the workflows that currently exist in `.github/workflows/`.

## 1) CI checks (`ci.yml`)

- Trigger: push to `main`, pull requests
- Runs:
  - `ruff` (excluding `test_infra`)
  - `mypy resume_generator arpanet_logging tests`
  - `pytest -q -m "unit and not docker and not slow"`
  - `pylint resume_generator tests -sn`
  - `vulture --config pyproject.toml resume_generator`

## 2) Feature-branch test workflow (`test.yml`)

- Trigger: push to non-`main` branches, pull requests
- Jobs:
  - quality checks (same toolchain as CI)
  - integration lane:
    - `pytest -q -m "integration and not docker and not slow"`
  - ARPANET Phase 1 docker bring-up test (`docker-compose.arpanet.phase1.yml`)
  - uploads test artifacts/logs

## Test marker taxonomy

Markers are auto-assigned in `tests/conftest.py`:

- `tests/integration/**` → `integration`
- `tests/system/**` → `docker` + `slow`
- everything else under `tests/` → `unit`

This keeps the default quality lane fast, while preserving higher-fidelity integration/docker
coverage in separate jobs.

## 3) Publish workflow (`deploy.yml`)

- Trigger:
  - tags: `publish`, `publish-*`, `publish-arpanet*`, `publish-full*`
  - manual dispatch
- Runs quality checks, generates site artifacts, deploys to GitHub Pages.

### Important mode note (current behavior)

- `resume_generator` CLI currently supports `--vax-mode local` and `--vax-mode docker`.
- `deploy.yml` currently derives a workflow mode named `arpanet` for `publish-arpanet*` / `publish-full*` tags
  and passes it directly to `--vax-mode`.
- That mode name does **not** match the CLI argument choices today.

Operationally, that means:
- `publish` / `publish-*` tags use `local` mode (supported).
- `publish-arpanet*` / `publish-full*` tags and manual `vax_mode=arpanet` require workflow/CLI mapping
  updates before they can run successfully end-to-end.

## Operational guidance

- Normal development: push branches and use CI/test workflow feedback.
- Publishing: create a publish tag only when intentional (see AGENTS.md warning about accidental publish).
- For reproducibility, prefer documenting exact tag and workflow run URL in release notes.
