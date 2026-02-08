# Build and publish workflows

This file documents the workflows that currently exist in `.github/workflows/`.

## 1) CI checks (`ci.yml`)

- Trigger: push to `main`, pull requests
- Runs:
  - `ruff` on primary portfolio module: `resume_generator`
  - `mypy resume_generator arpanet_logging tests`
  - `pytest -q -m "unit and not docker and not slow"`
  - `pylint resume_generator tests -sn`
  - `vulture --config pyproject.toml resume_generator`

Early-development note:
- CI intentionally does **not** enforce full-repo Ruff yet.
- `arpanet_logging` and legacy/experimental areas (for example parts of `arpanet/`) are handled incrementally.

## 2) Feature-branch test workflow (`test.yml`)

- Trigger: push to non-`main` branches, pull requests
- Jobs:
  - quality checks (same toolchain as CI)
  - integration lane:
    - `pytest -q -m "integration and not docker and not slow"`
  - ARPANET Phase 1 docker bring-up test (`docker-compose.arpanet.phase1.yml`)
  - ARPANET Phase 2 docker smoke test (`docker-compose.arpanet.phase2.yml` + `arpanet/scripts/test-phase2-imp-link.sh`)
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

- `resume_generator` CLI supports `--vax-mode local` and `--vax-mode docker`.
- ARPANET Phase 3 scaffold is toggled by:
  - `--with-arpanet` (dry-run scaffold; safe default)
  - `--arpanet-execute` (explicitly enables scaffold command execution)
- `deploy.yml` now maps ARPANET publish modes to CLI-compatible arguments:
  - workflow/tag mode `arpanet` → `--vax-mode docker --with-arpanet --arpanet-execute`
  - workflow/tag mode `local` → `--vax-mode local`

Operationally, that means:
- `publish` / `publish-*` tags run local mode.
- `publish-arpanet*` / `publish-full*` tags run docker VAX mode with ARPANET scaffold execution enabled.
- ARPANET publish path uses the Phase 2 compose topology (`docker-compose.arpanet.phase2.yml`) and captures logs
  from `vax`, `imp1`, `imp2`, and `pdp10`.

## Operational guidance

- Normal development: push branches and use CI/test workflow feedback.
- Publishing: create a publish tag only when intentional (see AGENTS.md warning about accidental publish).
- For reproducibility, prefer documenting exact tag and workflow run URL in release notes.
