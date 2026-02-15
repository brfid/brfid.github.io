# Cold Start Guide (LLM / New Operator)

Use this page when starting from zero context.

## 0) Current State

**Date**: 2026-02-15  
**Status**: Active path is single-host `edcloud` + containerized VAX/PDP-11.

- `brfid.github.io` owns resume generation, vintage build scripts, and site publish workflow.
- `edcloud` owns infrastructure lifecycle (provision/up/down/snapshot/destroy).
- Legacy two-instance VAX/PDP-11 + EFS orchestration is archived and not used.
- Orchestration is designed to run from small ARM controller systems too (for example, Pi Zero 2 class nodes).

## 1) Read Order

1. `README.md`
2. `docs/COLD-START.md` (this file)
3. `STATUS.md`
4. `docs/INDEX.md`
5. `docs/integration/INDEX.md` (if touching distributed vintage/integration work)

Then apply repository workflow constraints from `AGENTS.md`.

## 2) Source Of Truth

- Project status: `STATUS.md`
- Documentation hub: `docs/INDEX.md`
- Integration map (current + historical): `docs/integration/INDEX.md`
- Workflow behavior: `WORKFLOWS.md`

Infrastructure platform docs live in `edcloud`:
- `https://github.com/brfid/edcloud/blob/main/README.md`
- `https://github.com/brfid/edcloud/blob/main/SETUP.md`
- `https://github.com/brfid/edcloud/blob/main/MIGRATION.md`
- `https://github.com/brfid/edcloud/blob/main/DESIGN.md` (baseline tools/rebuild/backup rationale)

## 3) Lifecycle Boundary

- Do not reintroduce two-machine orchestration in this repo.
- Keep `brfid.github.io` orchestration minimal: start/stop/check the single edcloud host and run build stages.
- Prefer platform-level changes in `edcloud` instead of embedding infra logic here.

## 4) Quick Commands

```bash
# Check/start/stop the single edcloud host from this repo
./aws-status.sh
./aws-start.sh
./aws-stop.sh

# Build locally (fast)
.venv/bin/resume-gen --out site --with-vax --vax-mode local

# Build with distributed vintage mode
.venv/bin/resume-gen --out site --with-vax --vax-mode docker
```

## 5) Publish Tags

- Fast local: `publish`, `publish-fast`, `publish-fast-*`
- Distributed vintage: `publish-vintage`, `publish-vintage-*`
- Legacy aliases accepted: `publish-vax*`, `publish-docker*`

## 6) Archives And Historical Context

- Historical transport decisions: `docs/deprecated/transport-archive.md`
- Legacy ARPANET/IMP materials: `docs/legacy/`, `docs/integration/archive/`

Treat archive material as evidence/history, not active runbook.
