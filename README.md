# brfid.github.io

Static resume site generator with an optional vintage build stage (VAX/PDP-11) used as a technical signal.

## Pipeline summary

1. Source: `resume.yaml`
2. Host build (`resume_generator`): HTML, PDF, VAX-stage inputs
3. Optional vintage stage (`--with-vintage`): produces `build/vintage/brad.1`
4. Host render: `brad.1` → `site/brad.man.txt`
5. Output: deployable static artifacts in `site/`

Architecture detail: `ARCHITECTURE.md`.

## Infrastructure boundary

This repo owns build/publish logic and minimal lifecycle hooks.
Infrastructure lifecycle is owned by `edcloud`: `https://github.com/brfid/edcloud`

- Do not add multi-host orchestration back into this repo.
- Keep local lifecycle hooks minimal (`aws-*.sh`).
- Put platform/lifecycle changes in `edcloud`.

Local helper scripts call into that lifecycle model:

```bash
./aws-status.sh
./aws-start.sh
./aws-stop.sh
```

Instance resolution order:
1. `EDCLOUD_INSTANCE_ID` when set
2. tag lookup: `edcloud:managed=true`, `Name=edcloud`

`edcloud` platform docs:
- `https://github.com/brfid/edcloud/blob/main/README.md`
- `https://github.com/brfid/edcloud/blob/main/SETUP.md`
- `https://github.com/brfid/edcloud/blob/main/DESIGN.md`

## Source of truth

| Doc | Role |
|-----|------|
| `CHANGELOG.md` (`[Unreleased]`) | Current project state, active priorities, blockers, and decisions |
| `CHANGELOG.md` (dated entries) | Chronological change history and milestone evidence |
| `WORKFLOWS.md` | CI/test/publish behavior |
| `ARCHITECTURE.md` | System design |
| `docs/INDEX.md` | Documentation hub |
| `docs/integration/INDEX.md` | Integration/ARPANET history map |
| `docs/deprecated/`, `docs/legacy/` | Historical evidence (not active runbooks) |

## Cold start order

1. This file (`README.md`)
2. `CHANGELOG.md` (`[Unreleased]` first, then latest dated entries)
3. `docs/INDEX.md`
4. `docs/integration/INDEX.md` (when working integration/history topics)

Then apply `AGENTS.md` constraints.

## Build modes

- `--vintage-mode local` — host-only fast iteration
- `--vintage-mode docker` — SIMH historical host mode (4.3BSD/K&R C on VAX machine target)

## Publish tags

- Fast/local: `publish`, `publish-fast`, `publish-fast-*`
- Distributed vintage: `publish-vintage`, `publish-vintage-*`
- Legacy alias tags still accepted: `publish-vax*`, `publish-docker*`

## Quickstart (venv only)

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m playwright install chromium
```

Build (local mode):

```bash
.venv/bin/resume-gen --out site --with-vintage --vintage-mode local
```

Build (distributed vintage mode):

```bash
.venv/bin/resume-gen --out site --with-vintage --vintage-mode docker
```

## Quality checks

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m mypy resume_generator host_logging tests
.venv/bin/python -m ruff check resume_generator
```

Workflow behavior: `WORKFLOWS.md`

## Documentation map

- `ARCHITECTURE.md`
- `WORKFLOWS.md`
- `CHANGELOG.md`
- `docs/INDEX.md`
- `docs/integration/INDEX.md`
- `docs/vax/README.md`

## Local preview

```bash
.venv/bin/python -m http.server --directory site 8000
```

Open `http://127.0.0.1:8000/`.
