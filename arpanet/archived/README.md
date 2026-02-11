# Archived: IMP Chain (Phase 2)

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

See `docs/arpanet/handoffs/LLM-KS10-IMP-MISMATCH-2026-02-10.md` for full analysis.

## Files moved here

### IMP Chain (original blocker)
- `docker-compose.arpanet.phase1.yml` — Single-IMP topology
- `docker-compose.arpanet.phase2.yml` — Multi-IMP topology

### Chaosnet Path A (ITS build blocker, 2026-02-11)
- `docker-compose.arpanet.chaosnet.yml` — Chaosnet shim topology
- `docker-compose.arpanet.phase2-chaosnet.yml` — IMP + Chaosnet hybrid

See `docs/arpanet/archive/chaosnet/README.md` for Chaosnet path details.

### KS10 Emulator (Boot failure, 2026-02-11)
- `Dockerfile.pdp10` — KS10 TOPS-20 (boot failure)
- `Dockerfile.pdp10-its` — KS10 ITS (boot failure)

Both fail with "Stop code 7, PC: 000100". See `docs/arpanet/archive/ks10/README.md`.

## To reactivate

1. Move compose files back to repo root
2. Restore Makefile targets (see `Makefile` archived section)
3. Address the HI1 framing mismatch (see blocker summary above)
4. Update `COLD-START.md` and `NEXT-STEPS.md`
