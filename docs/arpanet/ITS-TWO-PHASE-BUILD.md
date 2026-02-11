# ITS Two-Phase Build Strategy

**Status**: Proposed solution to ITS install blocker
**Blocker**: ITS build system requires x86_64; Pi (ARM64) cannot run it natively;
Docker/QEMU double-emulation on Pi is too slow.

## Approach

Split the build into two phases:

1. **Build phase** (Mac M2 or any x86_64): Run ITS project build system in
   `--platform linux/amd64` Docker container. Rosetta 2 on Mac M2 gives
   near-native x86 performance. Produces RP06 disk image artifact.

2. **Run phase** (Pi): Compile KLH10 natively on ARM64 (just the emulator,
   ~2 min). Boot from pre-built disk image.

## Implementation

See `tools/its-build/` for scripts:
- `build-its-image.sh` — Phase 1 (run on Mac)
- `run-its-on-pi.sh` — Phase 2 (run on Pi)
- `Dockerfile` — x86_64 build container

## Alternatives Considered

| Approach | Outcome |
|----------|---------|
| Native KLH10 + full ITS build on Pi | Build failures, too slow |
| Docker x86 on Pi (QEMU) | Double emulation, hangs |
| SIMH KS10 on Pi | ITS support immature in SIMH |
| Cross-compile entire ITS on Mac for ARM | ITS build runs *inside* emulator, can't cross-compile |
| **Two-phase: build on Mac, run on Pi** | **Proposed — separates the hard part** |

## Risk

- KLH10 may need minor patches to compile on ARM64. The PDP-10/klh10 fork
  has community ARM64 patches; worst case is a few `#ifdef` additions.
- The disk image built on x86_64 KLH10 should be byte-compatible since
  both platforms are little-endian LP64.
