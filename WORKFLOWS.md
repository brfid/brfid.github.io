# Build and publish workflows

Current workflow map for `.github/workflows/`.

## `ci.yml`

- Trigger: push to `main`, pull requests
- Runs:
  - `ruff check resume_generator`
  - `mypy resume_generator host_logging tests`
  - `pytest -q -m "unit and not docker and not slow"`
  - `pylint resume_generator tests -sn`
  - `vulture --config pyproject.toml resume_generator`

## `test.yml`

- Trigger: push to non-`main` branches, pull requests
- Runs:
  - quality lane (same core checks)
  - integration lane: `pytest -q -m "integration and not docker and not slow"`

Legacy ARPANET docker jobs were removed from this workflow.

## Marker taxonomy

Defined in `tests/conftest.py`:

- `tests/integration/**` → `integration`
- `tests/system/**` → `docker`, `slow`
- all other tests under `tests/` → `unit`

## `deploy.yml`

- Trigger:
  - tags
    - fast/local: `publish`, `publish-fast`, `publish-fast-*`
    - distributed vintage: `publish-vintage`, `publish-vintage-*`
    - legacy aliases: `publish-vax*`, `publish-docker*` (deprecated naming)
  - manual dispatch

Mode resolution:

- `publish-vintage*` / legacy alias tags → `docker` mode
- manual dispatch → selected input mode
- other publish tags → `local` mode

Docker mode lifecycle in deploy workflow:

1. resolve + start one edcloud instance,
2. prepare host checkout,
3. start `docker-compose.production.yml`,
4. run build pipeline,
5. stop the same instance in `always()` cleanup.

Access model for docker mode:

- GitHub Actions joins the tailnet via `tailscale/github-action@v3`.
- Required secret: `TAILSCALE_AUTH_KEY`.
- All remote operations use `ssh/scp ubuntu@edcloud` (no public-IP SSH key flow).

Lifecycle markers written to `GITHUB.log`:

- `EDCLOUD_ACTIVATE_BEGIN`
- `EDCLOUD_ACTIVATE_READY`
- `EDCLOUD_ACTIVATE_FAILED`
- `EDCLOUD_DEACTIVATE_BEGIN`
- `EDCLOUD_DEACTIVATE_COMPLETE`
