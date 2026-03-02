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
  - tags
    - fast/local: `publish-fast-*`
    - vintage: `publish-vintage-*`
  - manual dispatch (`build_mode`: `local` or `vintage`)

Mode resolution:

- `publish-vintage-*` tags → vintage mode
- manual dispatch `build_mode=vintage` → vintage mode
- otherwise → local mode

Local mode:

1. Checkout with submodules (PaperMod theme)
2. Setup Hugo 0.156.0 extended
3. Sync `resume.yaml` → `hugo/data/resume.yaml`
4. `hugo --source hugo --destination ../site`
5. Upload and deploy to GitHub Pages

Vintage mode control plane (GitHub Actions):

1. Authenticate to AWS via static credentials (`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`)
2. Resolve + start edcloud instance
3. Invoke a single SSM command on edcloud
4. Extract artifacts from SSM output markers:
   - `brad.man.txt` → `hugo/static/brad.man.txt`
   - `brad.bio.txt` → `hugo/static/brad.bio.txt` (best-effort)
   - `build.log.html` → `hugo/static/build.log.html` (best-effort)
5. Generate bio data for Hugo: parse `brad.bio.txt` + build log header → `hugo/data/bio.yaml`
6. Best-effort stop edcloud if this workflow started it
7. Build/deploy Hugo as normal

Vintage mode execution plane (edcloud host):

- Single entrypoint: `scripts/edcloud-vintage-runner.sh`
- Script orchestrates the pexpect-based VAX/PDP-11 pipeline (see `ARCHITECTURE.md`)
- Emits artifact as base64 between hard markers on stdout for CI extraction
- Debug override: set `KEEP_IMAGES=1` to keep containers running after a run

Required secrets for vintage mode:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- optional `EDCLOUD_INSTANCE_ID` (if unset, workflow resolves by tags)
