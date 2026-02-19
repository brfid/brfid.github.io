# Cold Start Guide

Use when starting with no local context.

## Current state

- Active architecture: single-host `edcloud` backend running containerized VAX/PDP-11 workloads.
- Repo boundary:
  - `brfid.github.io`: build/publish pipeline
  - `edcloud`: infrastructure lifecycle
- Legacy multi-instance + EFS deployment is archived.
- **Active work**: restoring the uuencode console transfer pipeline (Option B) to the
  single-host edcloud model. Items 1–3 of 4 blocking issues resolved (2026-02-18).
  The one remaining step before triggering a live end-to-end run is building and
  boot-verifying the revised PDP-11 Docker image on edcloud. See `STATUS.md` → "Next work".

## Read order

1. `README.md`
2. `docs/COLD-START.md`
3. `STATUS.md`
4. `docs/INDEX.md`
5. `docs/integration/INDEX.md` (integration/history work)

Then apply `AGENTS.md` constraints.

## Source of truth

- Project status: `STATUS.md`
- Workflow behavior: `WORKFLOWS.md`
- Documentation hub: `docs/INDEX.md`
- Integration map: `docs/integration/INDEX.md`

`edcloud` platform docs:
- `https://github.com/brfid/edcloud/blob/main/README.md`
- `https://github.com/brfid/edcloud/blob/main/SETUP.md`
- `https://github.com/brfid/edcloud/blob/main/DESIGN.md`

## Lifecycle boundary

- Do not add multi-host orchestration back into this repo.
- Keep local lifecycle hooks minimal (`aws-*.sh`).
- Put platform/lifecycle changes in `edcloud`.

## Quick commands

```bash
./aws-status.sh
./aws-start.sh
./aws-stop.sh

.venv/bin/resume-gen --out site --with-vax --vax-mode local
.venv/bin/resume-gen --out site --with-vax --vax-mode docker
```

## Publish tags

- Fast/local: `publish`, `publish-fast`, `publish-fast-*`
- Distributed vintage: `publish-vintage`, `publish-vintage-*`
- Legacy aliases accepted: `publish-vax*`, `publish-docker*`

## Historical context

- `docs/deprecated/transport-archive.md`
- `docs/legacy/`
- `docs/integration/archive/`

Treat these as historical evidence, not active runbooks.
