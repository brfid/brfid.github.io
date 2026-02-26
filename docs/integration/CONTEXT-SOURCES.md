# Context Sources for Current VAX↔PDP-11 Transfer Work

Purpose: capture high-signal historical context that still informs the active
transfer path, while separating out dead ends.

Last reviewed: 2026-02-26

---

## Canonical Active Guidance

Use these first for current behavior:
- `docs/integration/operations/VAX-PDP11-COLD-START-DIAGNOSTICS.md`
- `docs/integration/INDEX.md`
- `README.md`, `CHANGELOG.md` (`[Unreleased]`)
- `scripts/edcloud-vintage-runner.sh`

---

## High-Signal Historical References (Still Useful)

1. `docs/archive/pipeline-planning/VAX-PDP11-VALIDATION-2026-02-14.md`
- Confirms practical Stage 1→3 shape and evidence expectations.
- Reiterates guest/container filesystem separation concerns when staging files.

2. `docs/archive/pipeline-planning/DEBUGGING-SUMMARY-2026-02-14.md`
- Captures why work must execute inside guest environments (not just host/container shell).
- Useful for diagnosing false-positive "success" where modern host tools run instead of vintage guest tools.

3. `docs/archive/vax/VAX-CONTAINER-BSD-FILE-SHARING.md`
- Captures guest/container filesystem and execution-boundary pitfalls from early runs.
- Useful for identifying false-positive success caused by running steps outside vintage guest environments.

4. `docs/archive/pipeline-planning/TAPE-TRANSFER-VALIDATION-2026-02-13.md`
- Demonstrates TS11 feasibility as historical evidence only.
- Not the selected current production path.

---

## Explicitly Not Current (Dead/Retired Paths)

Use `docs/archive/DEAD-ENDS.md` as the definitive registry for:
- ARPANET/PDP-10 expansion paths
- Chaosnet path
- FTP-based VAX↔PDP-11 transfer
- other retired transport experiments
