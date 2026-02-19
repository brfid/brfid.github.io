# Project Status

**Last updated:** 2026-02-15

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

- Historical log path conventions (`/mnt/arpanet-logs`) still appear in some integration paths for compatibility.
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
4. **PDP-11 image** — config and boot sequence fixed; still needs a live build on
   edcloud to confirm `unix` kernel boots and `uudecode`/`nroff` are present:
   - `vintage/configs/pdp11.ini`: xq (DEUNA networking) and ts (tape) blocks removed;
     neither is needed for console injection and xq requires `--privileged`.
   - `vintage/pdp11-boot.sh`: now sends `\r` at the `Boot:` prompt before waiting
     for multi-user (previous version skipped this step, leaving the system hung at `:`)
   - `vintage/Dockerfile.pdp11`: trimmed to headless-only deps (removed pcap/SDL2/vdeplug).
   - Remaining: `docker build` on edcloud, then interactive verify via `telnet localhost 2327`.

## Source-of-truth pointers

- `README.md`
- `docs/COLD-START.md`
- `WORKFLOWS.md`
- `docs/INDEX.md`
- `docs/integration/INDEX.md`
