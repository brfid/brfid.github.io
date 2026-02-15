# brfid.github.io

This project generates and publishes a static resume site, with an optional distributed vintage build stage (VAX + PDP-11) as a technical signal.

## How it works

1. **Source input**: `resume.yaml`
2. **Host build (`resume_generator`)**:
   - renders resume HTML
   - renders resume PDF
   - prepares VAX-friendly YAML (`build/vax/resume.vax.yaml`)
3. **VAX stage** (`--with-vax`):
   - compiles/runs `vax/bradman.c`
   - generates roff manpage output (`build/vax/brad.1`)
   - host renders to `site/brad.man.txt`
4. **Optional ARPANET wrapper** (`--with-arpanet`):
   - orchestrates ARPANET scaffold path
   - writes transfer logs (`site/arpanet-transfer.log`)
   - in execute mode also writes `build/vax/arpanet-transfer-exec.log`
5. **Publish artifacts** land in `site/` for GitHub Pages.

For deeper component detail, see `ARCHITECTURE.md`.

## Production Infrastructure Management

`brfid.github.io` does minimal orchestration and plugs into the single-host `edcloud` platform.
Infrastructure lifecycle ownership is in the `edcloud` project:
`https://github.com/brfid/edcloud` (or your fork URL).

**Quick commands** (single-host backend):
```bash
./aws-status.sh  # Check edcloud instance status
./aws-stop.sh    # Stop edcloud instance
./aws-start.sh   # Start edcloud instance
```

**Backend**: Single t3a.medium instance running both VAX + PDP-11 containers via Docker Compose.
**Lifecycle lookup**: `EDCLOUD_INSTANCE_ID` env var or tag lookup (`edcloud:managed=true`, `Name=edcloud`).
**Operator footprint**: Intended to run from small ARM control nodes as well (for example, Pi Zero 2 class systems) as long as AWS CLI access is available.
**Cost**: ~$11/month at 4hrs/day or ~$6.40/month stopped (storage only). Auto-shutdown after 30min idle.
**Data safety**: All scripts preserve EBS volume - no data loss.

For host baseline tooling, rebuild policy, and backup/recovery standards, use edcloud docs:
- `https://github.com/brfid/edcloud/blob/main/SETUP.md`
- `https://github.com/brfid/edcloud/blob/main/DESIGN.md`

## LLM / operator cold-start quickstart

If you are starting with little or no context, use this exact read order:

1. `README.md`
2. `docs/COLD-START.md`
3. `STATUS.md`
4. `docs/INDEX.md`
5. `docs/integration/INDEX.md` (for integration/history tasks)

Then apply repository workflow constraints from `AGENTS.md`.

## Build modes (CLI)

- `--vax-mode local`: host-only VAX stage emulation (fast iteration)
- `--vax-mode docker`: authentic SIMH/VAX 11/780 build (4.3BSD, K&R C)

## Publish tags (GitHub Actions)

- Fast local (canonical): `publish`, `publish-fast`, `publish-fast-*`
- Distributed vintage (canonical): `publish-vintage`, `publish-vintage-*`
- Distributed vintage (legacy aliases): `publish-vax*`, `publish-docker*`

**Note**: ARPANET Phase 2 (IMPs) removed from CI as of 2026-02-13. Tape transfer functionality preserved for future integration.

## Quickstart (venv only)

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m playwright install chromium
```

### Build site (local VAX mode)

```bash
.venv/bin/resume-gen --out site --with-vax --vax-mode local
```

### Build site (distributed vintage backend)

```bash
.venv/bin/resume-gen --out site --with-vax --vax-mode docker
```

### Build site with distributed vintage backend

```bash
# Distributed vintage backend (authentic 4.3BSD + 2.11BSD pipeline)
.venv/bin/resume-gen --out site --with-vax --vax-mode docker

# Local mode (fast)
.venv/bin/resume-gen --out site --with-vax --vax-mode local
```

## Useful Make targets

```bash
make publish
make publish-vintage
make docs
```

## Quality checks

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m mypy resume_generator host_logging tests
.venv/bin/python -m ruff check resume_generator
```

## CI/CD overview

- `ci.yml`: quality gate on `main` and PRs
- `test.yml`: feature-branch quality + integration tests
- `deploy.yml`: publish/tag deployment to GitHub Pages

Details: `WORKFLOWS.md`

## Documentation map

- `ARCHITECTURE.md` — end-to-end system flow
- `WORKFLOWS.md` — CI/test/publish behavior
- `docs/INDEX.md` — central documentation hub
- `docs/integration/INDEX.md` — integration documentation map
- `docs/vax/README.md` — VAX C tool contract

## Retained records and archives

Per project direction, historical and in-progress records are retained.

- Transport history: `docs/deprecated/transport-archive.md`
- Integration and historical records: see `docs/integration/` and `docs/legacy/`

## Local preview

```bash
.venv/bin/python -m http.server --directory site 8000
```

Open `http://127.0.0.1:8000/`.
