# brfid.github.io

This project generates and publishes a static resume site, with an optional VAX/ARPANET build stage as a technical signal.

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

## LLM / operator cold-start quickstart

If you are starting with little or no context, use this exact read order:

1. `README.md`
2. `docs/COLD-START.md`
3. `STATUS.md`
4. `docs/INDEX.md`
5. `docs/arpanet/INDEX.md` (for ARPANET tasks)

Then apply repository workflow constraints from `AGENTS.md`.

## Modes

- `--vax-mode local`: host-only VAX stage emulation path (fast iteration)
- `--vax-mode docker`: SIMH/VAX Docker path
- `--with-arpanet`: add ARPANET wrapper stage
- `--arpanet-execute`: run scaffold execution commands (instead of dry-run scaffold only)

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

### Build site (docker VAX mode)

```bash
.venv/bin/resume-gen --out site --with-vax --vax-mode docker
```

### Build site with ARPANET wrapper

```bash
# Scaffold mode
.venv/bin/resume-gen --out site --with-vax --with-arpanet --vax-mode docker

# Execute scaffold commands
.venv/bin/resume-gen --out site --with-vax --with-arpanet --arpanet-execute --vax-mode docker
```

## Useful Make targets

```bash
make test-phase2
make test-imp-logging
make docs
```

## Quality checks

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m mypy resume_generator arpanet_logging tests
.venv/bin/python -m ruff check .
```

## CI/CD overview

- `ci.yml`: quality gate on `main` and PRs
- `test.yml`: feature-branch + integration/docker smoke lanes
- `deploy.yml`: publish/tag deployment to GitHub Pages

Details: `WORKFLOWS.md`

## Documentation map

- `ARCHITECTURE.md` — end-to-end system flow
- `WORKFLOWS.md` — CI/test/publish behavior
- `docs/INDEX.md` — central documentation hub
- `docs/arpanet/INDEX.md` — ARPANET documentation map
- `docs/arpanet/overview/README.md` — ARPANET topology and operations
- `docs/arpanet/operations/TESTING-GUIDE.md` — ARPANET test commands/troubleshooting
- `docs/arpanet/operations/ARPANET-LOGGING-README.md` — logging subsystem usage
- `docs/arpanet/operations/TOPOLOGY-README.md` — topology generator and definitions
- `docs/vax/README.md` — VAX C tool contract

## Retained records and archives

Per project direction, historical and in-progress records are retained.

- Transport history: `docs/project/transport-archive.md`
- ARPANET implementation records (complete + in-progress):
  - `docs/arpanet/overview/PHASE1-SUMMARY.md`
  - `docs/arpanet/overview/PHASE2-PLAN.md`
  - `docs/arpanet/progress/PHASE2-VALIDATION.md`
  - `docs/arpanet/overview/PHASE3-PLAN.md`
  - `docs/arpanet/overview/PHASE3-IMPLEMENTATION-PLAN.md`
  - `docs/arpanet/progress/PHASE3-PROGRESS.md`
- Technical investigation records:
  - `docs/arpanet/research/CONSOLE-AUTOMATION-PROBLEM.md`
  - `docs/arpanet/research/CONSOLE-AUTOMATION-SOLUTION.md`
  - `docs/arpanet/operations/FTP-TESTING.md`
  - `docs/arpanet/research/PROTOCOL-ANALYSIS.md`

## Local preview

```bash
.venv/bin/python -m http.server --directory site 8000
```

Open `http://127.0.0.1:8000/`.
