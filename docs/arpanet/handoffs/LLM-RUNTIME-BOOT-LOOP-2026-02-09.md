# ITS Docker Runtime Boot Failure - Problem Summary for a Problem-Solving LLM

## Goal

Stabilize the Phase 2 PDP-10/ITS container so it **boots successfully and stays up** in Docker Compose (`docker-compose.arpanet.phase2.yml`) as part of the ARPANET integration pipeline.

## Current Status

- ITS image build now completes (long-running `docker compose ... build pdp10` is successful).
- Phase 2 stack (`vax`, `imp1`, `imp2`, `pdp10`) can be recreated cleanly.
- Host ports `2326` and `10004` are bound and reachable.
- **But** `arpanet-pdp10` enters a restart loop and never reaches a stable runtime boot.

## Primary Failure Symptoms (from latest `docker logs arpanet-pdp10`)

Current startup reaches disk boot and then aborts:

- `./pdp10.ini-52> boot rpa0`
- `Internal error, PC: 000100`

Container behavior:

- `docker compose ... ps` shows `arpanet-pdp10   Restarting (0) ...`
- Restart count increases continuously.

## What Is Already Confirmed

1. Compose wiring is pointed at ITS artifacts:
   - `docker-compose.arpanet.phase2.yml` uses `Dockerfile.pdp10-its`.
   - PDP-10 config path mounted from `arpanet/configs/phase2/pdp10.ini`.
2. ITS build path is real (not stale TOPS-20), with valid long-running build stages and expected ITS build output.
3. Runtime restart issue occurs **after build completion**, during simulator boot from attached ITS disk.
4. SIMH capability interrogation in-container showed:
   - KS-10 simulator build in use
   - `RPA*` disk device family exists; `RP` does not
   - CPU memory option `2048K` is unsupported on this build
5. `pdp10.ini` and topology generator were updated accordingly:
   - disk commands switched to `rpa0`
   - `set cpu 2048k` disabled
   - parse-time RP/CPU errors are no longer the blocking failure class

## Most Likely Root Cause Class

Boot-time ITS disk/runtime incompatibility (or disk state issue) **after** command-level compatibility was fixed.

The container now gets through command parsing and reaches `boot rpa0`, then halts with an internal simulator/runtime error (`PC: 000100`).

## Relevant Files

- `arpanet/Dockerfile.pdp10-its`
- `arpanet/configs/phase2/pdp10.ini`
- `docker-compose.arpanet.phase2.yml`
- `arpanet/topology/definitions.py`
- `arpanet/topology/generators.py`

## Reproduction

```bash
docker compose -f docker-compose.arpanet.phase2.yml build pdp10
docker compose -f docker-compose.arpanet.phase2.yml up -d --force-recreate vax imp1 pdp10 imp2
docker compose -f docker-compose.arpanet.phase2.yml ps
docker logs arpanet-pdp10 --tail 260
```

## Desired End State

1. `arpanet-pdp10` status is `Up` (no restart loop).
2. Logs show successful ITS boot path past `boot rpa0` (no internal error at `PC: 000100`).
3. Port probes still pass (`2326`, `10004`).
4. Phase 2 stack remains routable (`vax` ↔ `imp1` ↔ `imp2` ↔ `pdp10`).

## Suggested Investigation Sequence for the Next LLM

1. Keep `RPA`/CPU syntax fixes in place (already validated) and avoid regressing to `RP`/`2048k`.
2. Re-test with a fully completed image build and clean recreate to rule out partial/stale disk artifacts.
3. Run `pdp10-ks` interactively (`do /machines/pdp10.ini`) and isolate the first failing boot transition after `boot rpa0`.
4. Validate disk provenance and format in runtime image (`/machines/data/its.dsk` source vs generated `rp0.dsk` pipeline).
5. Re-test cleanly and verify container stability.

## Constraints

- Keep ARPANET topology and ITS migration intent intact.
- Prefer minimal, targeted config fixes over broad architectural changes.
- Maintain reproducibility in Docker Compose workflow used by CI/pipeline.