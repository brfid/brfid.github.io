# brfid.github.io

Hugo-based personal site and technical writing portfolio at [jockeyholler.net](https://www.jockeyholler.net/).
Optional vintage build stage (VAX/PDP-11 via SIMH) generates artifact resume as a technical signal.

## Pipeline summary

**Local publish (Hugo):**
1. Author content in `hugo/content/`
2. `hugo --source hugo --destination site` → generates `site/`
3. Push `publish` tag → GitHub Actions builds and deploys to GitHub Pages

**Vintage publish (on-demand):**
1. `resume_generator` produces inputs for VAX build
2. VAX/PDP-11 pipeline (on edcloud) generates `brad.man.txt`
3. Artifact drops into `hugo/static/` before Hugo build
4. Push `publish-vintage` tag → full pipeline runs in CI

Architecture detail: `ARCHITECTURE.md`.

## Infrastructure boundary

This repo owns build/publish logic and minimal lifecycle commands.
Infrastructure lifecycle is owned by `edcloud`: `https://github.com/brfid/edcloud`

- Do not add multi-host orchestration back into this repo.
- Keep local lifecycle commands minimal (`scripts/edcloud_lifecycle.py`).
- Put platform/lifecycle changes in `edcloud`.

Local helper commands call into that lifecycle model:

```bash
.venv/bin/python scripts/edcloud_lifecycle.py status
.venv/bin/python scripts/edcloud_lifecycle.py start
.venv/bin/python scripts/edcloud_lifecycle.py stop

# or via make targets
make aws-status
make aws-start
make aws-stop
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
3. `hugo/` (Hugo site root — theme, content, config)
4. `docs/INDEX.md`
5. `docs/integration/INDEX.md` (when working integration/history topics)

Then apply `AGENTS.md` constraints.

## Publish tags

- Hugo local: `publish`, `publish-fast`, `publish-fast-*`
- Distributed vintage: `publish-vintage`, `publish-vintage-*`
- Legacy alias tags still accepted: `publish-vax*`, `publish-docker*`

## Quickstart (Hugo)

Requires Hugo extended ≥ 0.156.0. ARM64 binary available from Hugo releases.

```bash
# Local preview with live reload
hugo server --source hugo

# Build to site/
hugo --source hugo --destination site
```

## Quickstart (vintage pipeline, optional)

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

Quality checks (vintage mode only):

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
hugo server --source hugo
```

Open `http://localhost:1313/`.
