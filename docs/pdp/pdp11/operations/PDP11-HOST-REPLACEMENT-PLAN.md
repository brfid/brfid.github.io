# PDP-11 (2.11BSD) Host Replacement Plan

**Date**: 2026-02-12  
**Status**: Planned (not executed yet)  
**Intent**: Stand up a lower-risk second vintage host candidate and, if successful, promote it to replace the current VAX host role in active transfer demos.

---

## Why this plan exists

Recent PDP-10/KLH10 work is blocked at BOOT handoff proof (`@` prompt not yet proven under strict automation). The current VAX host is stable, but the team requested a practical alternative host path to reduce dependency on one fragile bring-up sequence.

Among discussed options, **PDP-11 + 2.11BSD** is the best balance of:
- turnkey availability (known bootable images),
- UNIX/BSD compatibility,
- realistic path to service-level testing (FTP/telnet/r-commands depending on image),
- lower setup risk than full PDP-10 installation loops.

---

## Option ranking (implementation-oriented)

### 1) PDP-11 + 2.11BSD (**recommended**)
- **Risk**: Low/Medium
- **Time-to-first-proof**: Fast
- **Why**: prebuilt images + BSD-like userland + strong historical fit.

### 2) PDP-11 + RSTS/E
- **Risk**: Medium
- **Time-to-first-proof**: Medium
- **Why**: DECnet-rich path, but more operator/config overhead.

### 3) PDP-8 / Altair / PDP-9/15 / pure V7 nostalgia paths
- **Risk**: Medium/High for networked transfer goals
- **Time-to-first-proof**: Variable
- **Why not first**: weaker fit for immediate host-replacement and transfer-validation needs.

---

## Phased rollout (with hard gates)

## Phase 0 — Image + runtime baseline
**Goal**: lock one reproducible PDP-11/2.11BSD image candidate and boot profile.

Deliverables:
1. Image source/provenance recorded (URL, checksum, license notes).
2. Candidate runtime config documented (CPU model, memory, disk attach, console attach).
3. Initial compose/topology notes drafted.

**Gate to proceed**: boot candidate chosen and documented.

## Phase 1 — Standalone PDP-11 bring-up
**Goal**: boot PDP-11 reliably to login in an isolated container.

Deliverables:
1. PDP-11 container recipe committed (Dockerfile or pinned image reference).
2. Minimal startup config committed (console + disk).
3. Transcript proving clean boot + interactive login.

**Gate to proceed**: repeatable boot/login in bounded retries.

## Phase 2 — Network and service validation
**Goal**: verify host-level connectivity and at least one file-transfer or remote-session workflow.

Deliverables:
1. Static IP on Docker bridge validated.
2. Service reachability transcript (ftp/telnet/other viable service).
3. One successful host-level operation (file put/get or remote command path).

**Gate to proceed**: deterministic network/service proof.

## Phase 3 — Side-by-side mode with current VAX path
**Goal**: keep VAX stable while validating PDP-11 in parallel to avoid regressions.

Deliverables:
1. Compose/topology supports both old and candidate host paths (no forced cutover yet).
2. Existing critical docs still point to current active path until PDP-11 gate passes.
3. Comparative notes: boot stability, operational cost, automation reliability.

**Gate to proceed**: PDP-11 demonstrates equal or better operational stability.

## Phase 4 — Promote replacement
**Goal**: switch default host role from VAX to PDP-11 for the relevant demo path.

Deliverables:
1. Default compose/topology target updated.
2. Scripts/tests re-targeted.
3. Status/docs indexes updated to reflect new default.

**Gate to close**: one end-to-end transfer proof with new default host.

---

## Repo integration points (for implementation)

Likely touchpoints when executing this plan:

- Topology model and generation:
  - `arpanet/topology/definitions.py`
  - `arpanet/topology/generators.py`
  - `docs/arpanet/operations/TOPOLOGY-README.md`
- Compose/runtime:
  - `docker-compose.*.yml` (new or updated target file)
  - `arpanet/configs/` (new host config)
- Test orchestration:
  - `arpanet/scripts/test_*.py` and related shell tests
- Canonical docs/status:
  - `STATUS.md`
  - `docs/arpanet/progress/NEXT-STEPS.md`
  - `docs/arpanet/INDEX.md`
  - `docs/INDEX.md`

---

## Acceptance criteria (summary)

1. PDP-11 boots and logs in reliably.
2. Networking is deterministic on project Docker bridge.
3. At least one transfer/session workflow succeeds with evidence transcript.
4. Side-by-side validation shows no regression risk.
5. Cutover docs and scripts are aligned after promotion.

---

## Rollback policy

If any gate fails, keep current VAX path as default and preserve PDP-11 as an experimental branch. No active-path docs should be flipped to PDP-11 until Phase 4 gate is met.
