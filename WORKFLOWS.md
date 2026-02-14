# Build and publish workflows

This file documents the workflows that currently exist in `.github/workflows/`.

## 1) CI checks (`ci.yml`)

- Trigger: push to `main`, pull requests
- Runs:
  - `ruff` on primary portfolio module: `resume_generator`
  - `mypy resume_generator host_logging tests`
  - `pytest -q -m "unit and not docker and not slow"`
  - `pylint resume_generator tests -sn`
  - `vulture --config pyproject.toml resume_generator`

Early-development note:
- CI intentionally does **not** enforce full-repo Ruff yet.
- Legacy/experimental areas are handled incrementally.

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
  - tags: `publish`, `publish-fast`, `publish-vax`, `publish-vax-*`, `publish-docker`, `publish-docker-*`
  - manual dispatch
- Runs quality checks, generates site artifacts, deploys to GitHub Pages.

### Important mode note (current behavior)

- `resume_generator` CLI supports `--vax-mode local` and `--vax-mode docker`.

`deploy.yml` mode resolution:
- `publish-vax*` / `publish-docker*` tags → docker mode
- manual dispatch → selected input (`local` or `docker`)
- otherwise (`publish`, `publish-fast`) → local mode

Operationally, that means:
- Local publish tags run fast local generation.
- Docker publish tags run the full AWS-backed VAX/PDP-11 pipeline.

### AWS lifecycle behavior in `deploy.yml` (docker mode)

- A single **Activate AWS infrastructure** step:
  - starts both EC2 instances,
  - waits for both to be `running`,
  - resolves and validates both public IPs,
  - waits for SSH readiness with timeout + hard failure.
- A single **Deactivate AWS infrastructure** step (with `always()`):
  - stops both EC2 instances,
  - waits for both to be `stopped`.
- Lifecycle log markers are written to `GITHUB.log`:
  - `AWS_ACTIVATE_BEGIN`
  - `AWS_ACTIVATE_READY`
  - `AWS_ACTIVATE_FAILED` (on failure paths)
  - `AWS_DEACTIVATE_BEGIN`
  - `AWS_DEACTIVATE_COMPLETE`

## Operational guidance

- Normal development: push branches and use CI/test workflow feedback.
- Publishing: create a publish tag only when intentional (see AGENTS.md warning about accidental publish).
- For reproducibility, prefer documenting exact tag and workflow run URL in release notes.
