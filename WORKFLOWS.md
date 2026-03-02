# Build and publish workflows

Current workflow map for `.github/workflows/`.

## `ci.yml`

- Trigger: push to `main`, pull requests
- Runs:
  - `ruff check resume_generator`
  - `mypy resume_generator host_logging tests`
  - `pytest -q -m "unit and not docker and not slow"`
  - `pylint resume_generator -sn`
  - `vulture --config pyproject.toml resume_generator`

## `test.yml`

- Trigger: push to non-`main` branches, pull requests
- Runs:
  - quality lane (same core checks)
  - integration lane: `pytest -q -m "integration and not docker and not slow"`

## `secret-scan.yml`

- Trigger: push to `main`, pull requests, manual dispatch
- Runs:
  - `gitleaks/gitleaks-action@v2` with full history checkout (`fetch-depth: 0`)
  - `GITLEAKS_LOG_OPTS: --all --no-merges` — scans full history rather than a
    push-delta range; avoids git error when force-push orphans the before SHA

## Marker taxonomy

Defined in `tests/conftest.py`:

- `tests/integration/**` → `integration`
- `tests/system/**` → `docker`, `slow`
- all other tests under `tests/` → `unit`

## `build-images.yml`

- Trigger: push to `main` when `vintage/machines/**/Dockerfile*` or `scripts/*.py` change;
  manual dispatch
- Builds Docker images for both pexpect stages (VAX and PDP-11)
- Pushes to `ghcr.io/brfid/brfid.github.io/` with `latest` tag
- Uses GitHub Actions cache (`type=gha`) for layer caching to speed incremental rebuilds
- Images consumed by `deploy.yml` vintage mode (pull from ghcr.io rather than rebuilding)

## `deploy.yml`

- Trigger:
  - tags: `publish-*`
  - manual dispatch (no inputs; useful for re-runs without tagging)

Single mode (vintage). No local/fast variant.

Control plane steps (GitHub Actions):

1. Checkout with submodules (PaperMod theme)
2. Setup Hugo 0.156.0 extended
3. Authenticate to AWS via static credentials (`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`)
4. Resolve + start edcloud instance
5. Invoke a single SSM command on edcloud
6. Extract artifacts from SSM output markers:
   - `brad.man.txt` → `hugo/static/brad.man.txt`
   - `brad.bio.txt` → `hugo/static/brad.bio.txt` (best-effort)
   - `build.log.html` → `hugo/static/build.log.html` (best-effort)
7. Sync `resume.yaml` → `hugo/data/resume.yaml`
8. Generate bio data: parse `brad.bio.txt` + read `about` from `resume.yaml` → `hugo/data/bio.yaml`
   (`label`, `principal_headline`, `impact_highlights`, `summary` from vintage output)
9. `hugo --source hugo --destination ../site`
10. Upload and deploy to GitHub Pages
11. Best-effort stop edcloud if this workflow started it

Execution plane (edcloud host):

- Single entrypoint: `scripts/edcloud-vintage-runner.sh`
- Script orchestrates the pexpect-based VAX/PDP-11 pipeline (see `ARCHITECTURE.md`)
- Emits artifacts as base64 between hard markers on stdout for CI extraction
- Debug override: set `KEEP_IMAGES=1` to keep containers running after a run

Required secrets:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- optional `EDCLOUD_INSTANCE_ID` (if unset, workflow resolves by tags)
