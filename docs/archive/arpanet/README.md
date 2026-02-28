# Archived: IMP Chain (Phase 2)

> Archived historical document. Not active implementation guidance for the current
> VAX↔PDP-11 pipeline.

## What's here

The multi-hop IMP routing topology (VAX → IMP1 → IMP2 → PDP-10) is preserved
here for future work. It was deactivated because of a fundamental HI1 framing
mismatch between the SIMH KS10 IMP device and the H316 IMP simulator.

## Blocker summary

The KS10 SIMH `IMP` device emits raw Ethernet/ARP-style frames over UDP.
The H316 IMP simulator expects BBN 1822 protocol leaders (96-bit format).
These are incompatible at the byte level — not a configuration issue but an
architectural mismatch between two emulators that were never designed to
interoperate.

Evidence: `bad magic number` errors on IMP2 HI1 with values like `feffffff`,
`00000219`, `ffffffff`.

See `handoffs/LLM-KS10-IMP-MISMATCH-2026-02-10.md` for full analysis.

## Files moved here

### IMP Chain (original blocker)
- `docker-compose.arpanet.phase1.yml` — Single-IMP topology
- `docker-compose.arpanet.phase2.yml` — Multi-IMP topology

### Chaosnet Path A (ITS build blocker, 2026-02-11)
- `docker-compose.arpanet.chaosnet.yml` — Chaosnet shim topology
- `docker-compose.arpanet.phase2-chaosnet.yml` — IMP + Chaosnet hybrid

Chaosnet detail and KS10/PDP-10 records removed (low-value dead ends).
