# Project Status

**Last updated:** 2026-02-15

## Current Architecture

- **Platform**: `edcloud` single-host backend (AWS EC2 + Docker).
- **Workloads**: VAX + PDP-11 containers run on the same host.
- **Repo boundary**:
  - `brfid.github.io`: build/publish logic and minimal orchestration hooks.
  - `edcloud`: infrastructure lifecycle and platform operations.

## Lifecycle Model

- Legacy two-instance VAX/PDP-11 orchestration in this repo is retired.
- Root scripts `aws-start.sh`, `aws-stop.sh`, `aws-status.sh` now target one edcloud instance.
- Instance selection is:
  1. `EDCLOUD_INSTANCE_ID` env var, else
  2. tag lookup (`edcloud:managed=true`, `Name=edcloud`).

## Publish Workflow

- `.github/workflows/deploy.yml` distributed vintage lane now:
  1. activates one edcloud instance,
  2. prepares host checkout + starts `docker-compose.production.yml`,
  3. runs staged VAX/PDP-11 build logic against that single host,
  4. deactivates that same instance in `always()` cleanup.

## What Is Stable

- Local fast build path (`--vax-mode local`).
- Single-host lifecycle scripts from this repo.
- Documentation baseline shifted to integration paths (`docs/integration/*`) instead of removed `docs/arpanet/*`.

## Known Follow-Up

- Distributed vintage lane still carries historical log path conventions (`/mnt/arpanet-logs`) for compatibility.
- Additional cleanup is still possible in deep archive docs and legacy notes.
- Legacy multi-machine orchestration code has been removed from active repo paths; keep lifecycle changes in `edcloud`.
- edcloud next priority: define and enforce a reproducible core host-tools/settings baseline, with snapshot + restore drill standards (tracked in `https://github.com/brfid/edcloud/blob/main/SETUP.md` and `https://github.com/brfid/edcloud/blob/main/DESIGN.md`).

## Source Of Truth Pointers

- Overview: `README.md`
- Cold start: `docs/COLD-START.md`
- Workflow behavior: `WORKFLOWS.md`
- Documentation index: `docs/INDEX.md`
- Integration index: `docs/integration/INDEX.md`
- Historical transport archive: `docs/deprecated/transport-archive.md`
