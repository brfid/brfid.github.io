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

Note:
- Legacy ARPANET phase docker jobs were removed from `test.yml` because they
  referenced archived/missing compose files and scripts.
- End-to-end distributed vintage verification runs in publish workflow lanes.

## Test marker taxonomy

Markers are auto-assigned in `tests/conftest.py`:

- `tests/integration/**` → `integration`
- `tests/system/**` → `docker` + `slow`
- everything else under `tests/` → `unit`

This keeps the default quality lane fast, while preserving higher-fidelity integration/docker
coverage in separate jobs.

## 3) Publish workflow (`deploy.yml`)

- Trigger:
  - tags:
    - Fast local: `publish`, `publish-fast`, `publish-fast-*`
    - Distributed vintage (canonical): `publish-vintage`, `publish-vintage-*`
    - Distributed vintage (legacy aliases): `publish-vax*`, `publish-docker*`
  - manual dispatch
- Runs quality checks, generates site artifacts, deploys to GitHub Pages.

### Important mode note (current behavior)

- `resume_generator` CLI supports `--vax-mode local` and `--vax-mode docker`.
- Workflow mode resolution uses `build_mode` output naming for clarity.

`deploy.yml` mode resolution:
- `publish-vintage*` tags (and legacy aliases `publish-vax*` / `publish-docker*`) → distributed vintage backend (`docker`)
- manual dispatch → selected input (`local` or `docker`)
- otherwise (`publish`, `publish-fast*`) → local mode

Operationally, that means:
- Local publish tags run fast local generation.
- Distributed vintage tags run the full edcloud-backed VAX/PDP-11 pipeline (single host, both containers).

### Infrastructure lifecycle behavior in `deploy.yml` (docker mode)

- A single **Activate edcloud infrastructure** step:
  - resolves one edcloud instance ID (secret `EDCLOUD_INSTANCE_ID` or tag lookup),
  - starts the instance and waits for `running`,
  - resolves host public IP and validates SSH connectivity.
- A **Prepare edcloud host** step:
  - ensures repo checkout exists on the host,
  - checks out the current workflow commit,
  - starts `docker-compose.production.yml`.
- A single **Deactivate edcloud infrastructure** step (with `always()`):
  - stops the same edcloud instance.
- Lifecycle log markers are written to `GITHUB.log`:
  - `EDCLOUD_ACTIVATE_BEGIN`
  - `EDCLOUD_ACTIVATE_READY`
  - `EDCLOUD_ACTIVATE_FAILED` (on failure paths)
  - `EDCLOUD_DEACTIVATE_BEGIN`
  - `EDCLOUD_DEACTIVATE_COMPLETE`

## Operational guidance

- Normal development: push branches and use CI/test workflow feedback.
- Publishing: create a publish tag only when intentional (see AGENTS.md warning about accidental publish).
- For reproducibility, prefer documenting exact tag and workflow run URL in release notes.
