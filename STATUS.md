# Project Status

**Last updated:** 2026-02-18

## Current architecture

- Platform: `edcloud` single-host backend (AWS EC2 + Docker)
- Workloads: VAX and PDP-11 containers on the same host
- Ownership boundary:
  - `brfid.github.io`: build/publish pipeline and minimal lifecycle hooks
  - `edcloud`: infrastructure lifecycle and platform operations

## Lifecycle model

- Multi-instance orchestration in this repo is retired.
- `aws-start.sh`, `aws-stop.sh`, and `aws-status.sh` target one edcloud instance.
- Instance resolution order:
  1. `EDCLOUD_INSTANCE_ID`
  2. tag lookup (`edcloud:managed=true`, `Name=edcloud`)

## Publish behavior (distributed vintage lane)

`deploy.yml` in docker mode:

1. starts one edcloud instance,
2. prepares host checkout and starts `docker-compose.production.yml`,
3. runs VAX/PDP-11 build stages,
4. stops that same instance in `always()` cleanup.

## Stable now

- Local build path (`--vax-mode local`)
- Single-host lifecycle hooks in this repo
- Active docs rooted in `docs/INDEX.md` and `docs/integration/INDEX.md`

## Follow-up

- Archive docs can be trimmed further, but remain intentionally retained.
- Lifecycle/platform changes should continue in `edcloud`, not in this repo.

## Next work (in progress)

Restoring the uuencode console transfer pipeline (Option B) on edcloud:

1. **CI gate** ✅ — pylint scope restored to `resume_generator` only (commit 23a81a3).
2. **deploy.yml stages 1–3** ✅ — all `screen`/telnet console commands now run on edcloud
   via `ssh ubuntu@$EDCLOUD_IP "bash -se" <<EOF` heredoc (ports 2323/2327 are
   localhost-only on edcloud).
3. **Log paths** ✅ — `/mnt/arpanet-logs` replaced with `~/arpanet-logs` throughout
   deploy.yml, including the `merge-logs.py` base-path argument.
4. **PDP-11 image** — config and boot sequence fixed (commits `242beb9`, `e25637c`);
   still needs a `docker build` + boot on edcloud with the new image:
   - `vintage/configs/pdp11.ini`: xq (DEUNA networking) and ts (tape) blocks removed;
     neither is needed for console injection; xq also requires `--privileged`.
   - `vintage/pdp11-boot.sh`: now sends `\r` at the `Boot:` prompt before waiting
     for multi-user (previous version skipped this, leaving the system hung at `:`).
   - `vintage/Dockerfile.pdp11`: trimmed to headless-only deps (removed pcap/SDL2/vdeplug).
   - `uudecode` and `nroff` presence in 2.11BSD rpethset: **confirmed** — `uudecode`
     confirmed interactively (`docs/deprecated/PDP11-DEBUG-FINDINGS.md`, 2026-02-14);
     `nroff` confirmed operational in `publish-vax-uuencode-v3` run (2026-02-14,
     `docs/integration/progress/NEXT-STEPS.md`).
   - Remaining gap: the revised `Dockerfile.pdp11` has not yet been built and
     boot-verified on edcloud. Run `docker compose -f docker-compose.production.yml
     up -d --build pdp11` on edcloud and confirm `telnet localhost 2327` reaches a
     shell prompt.

## Session log (2026-02-18)

- Fixed pylint CI gate, SSH-wrapped deploy.yml console ops, migrated log paths
  (see commit `23a81a3`).
- Fixed `pdp11.ini` (removed xq/ts), `pdp11-boot.sh` (Boot: prompt), `Dockerfile.pdp11`
  (trimmed deps) (commit `242beb9`).
- Removed SCP step from deploy.yml; all scripts now run from `~/brfid.github.io/scripts/`
  on edcloud (Option A); added PDP-11 port 2327 readiness poll before Stage 2 injection
  (commit `e25637c`).

## Source-of-truth pointers

- `README.md`
- `docs/COLD-START.md`
- `WORKFLOWS.md`
- `docs/INDEX.md`
- `docs/integration/INDEX.md`
