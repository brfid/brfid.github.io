# ITS Docker Runtime Boot Failure - Problem Summary for a Problem-Solving LLM

## Goal

Stabilize the Phase 2 PDP-10/ITS container so it **boots successfully and stays up** in Docker Compose (`docker-compose.arpanet.phase2.yml`) as part of the ARPANET integration pipeline.

## Current Status

- ITS image build now completes (long-running `docker compose ... build pdp10` is successful).
- Phase 2 stack (`vax`, `imp1`, `imp2`, `pdp10`) can be recreated cleanly.
- Host ports `2326` and `10004` are bound and reachable.
- **But** `arpanet-pdp10` enters a restart loop and never reaches a stable runtime boot.

## Primary Failure Symptoms (from `docker logs arpanet-pdp10`)

Repeated errors on startup:

- `%SIM-ERROR: No such Unit: RP0`
- `%SIM-ERROR: Non-existent device: RP0`
- `%SIM-ERROR: CPU device: Non-existent parameter - 2048K`

Container behavior:

- `docker compose ... ps` shows `arpanet-pdp10   Restarting (0) ...`
- Restart count increases continuously.

## What Is Already Confirmed

1. Compose wiring is pointed at ITS artifacts:
   - `docker-compose.arpanet.phase2.yml` uses `Dockerfile.pdp10-its`.
   - PDP-10 config path mounted from `arpanet/configs/phase2/pdp10.ini`.
2. ITS build path is real (not stale TOPS-20), with valid long-running build stages and expected ITS build output.
3. Runtime restart issue occurs **after build completion**, during simulator startup/config application.

## Most Likely Root Cause Class

`pdp10.ini` commands appear incompatible with the simulator binary/configuration actually running in container runtime.

Specifically, the ini assumes:

- an `RP0` device exists and is attachable as `rp06`
- `set cpu 2048k` is valid for this sim build

but runtime says those options/devices do not exist.

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
2. Logs show successful ITS boot path (or at minimum no `RP0`/CPU parameter hard errors).
3. Port probes still pass (`2326`, `10004`).
4. Phase 2 stack remains routable (`vax` ↔ `imp1` ↔ `imp2` ↔ `pdp10`).

## Suggested Investigation Sequence for the Next LLM

1. Interrogate simulator capabilities inside built runtime image:
   - list available devices/units
   - verify valid CPU/memory syntax
2. Reconcile `arpanet/configs/phase2/pdp10.ini` with actual supported commands.
3. If needed, adjust how disk image is attached/booted (device naming mismatch likely).
4. Re-test with clean stack restart and verify container stability.

## Constraints

- Keep ARPANET topology and ITS migration intent intact.
- Prefer minimal, targeted config fixes over broad architectural changes.
- Maintain reproducibility in Docker Compose workflow used by CI/pipeline.