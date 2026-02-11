# ITS Build Tools — Two-Phase Approach

## Problem

ITS (Incompatible Timesharing System) for the PDP-10 must be built using the
[ITS project](https://github.com/PDP-10/its) build system, which:

1. Compiles KLH10 (PDP-10 emulator) for the host
2. Boots a temporary ITS inside KLH10 using `expect` scripts
3. Assembles the full ITS system from source inside the emulator
4. Produces a bootable RP06 disk image

This process requires an x86_64 host. Running it on the Pi via Docker/QEMU
double-emulation is prohibitively slow (hours or hangs).

## Solution: Split Build and Run

### Phase 1 — Build on Mac M2 (one-time)

```bash
cd tools/its-build
./build-its-image.sh
```

This runs the ITS build system inside an x86_64 Docker container.
Rosetta 2 on macOS handles the x86 emulation efficiently (much faster
than QEMU user-mode on the Pi).

Output: `artifacts/` containing the RP06 disk image and KLH10 config.

### Phase 2 — Run on Pi

```bash
# Copy artifacts to Pi
scp -r artifacts/ pi@raspberrypi:~/its/

# On the Pi
cd ~/its
# Copy run-its-on-pi.sh there too, then:
./run-its-on-pi.sh
```

This builds KLH10 *natively* on the Pi (ARM64 — just the emulator binary,
not the full ITS assembly process) and boots from the pre-built disk image.

## Why This Works

| Step | Where | What | Time |
|------|-------|------|------|
| ITS assembly | Mac (x86_64 Docker) | Full build system + expect scripts | ~15 min |
| KLH10 compile | Pi (native ARM64) | Just the C emulator | ~2 min |
| ITS boot | Pi (native ARM64) | KLH10 + pre-built disk | seconds |

The expensive step (assembling ITS inside the emulator) runs on x86_64
where KLH10 is well-tested. The Pi only needs to compile and run KLH10
itself, which is a straightforward C program.

## KLH10 ARM64 Notes

The PDP-10/klh10 fork has been built on ARM64 by others. Known issues:

- **36-bit word packing**: KLH10 stores PDP-10 36-bit words in 64-bit host
  words. This works on both x86_64 and ARM64 (both LP64, little-endian).
- **No x86 assembly**: KLH10 is pure C (no SSE/inline asm dependencies).
- **Alignment**: ARM64 is more strict but KLH10 uses standard aligned access.

If the PDP-10/klh10 build fails on the Pi, check:
1. `uint64_t` availability (should be fine on modern Pi OS)
2. Any `#ifdef __x86_64__` guards that exclude ARM — patch to include `__aarch64__`

## Relationship to ARPANET Work

Once ITS boots on the Pi, the next step is CHAOSNET/ARPANET networking
between the ITS (PDP-10) and VAX (4.3BSD) instances. See:
- `docs/arpanet/INDEX.md`
- `docs/arpanet/progress/NEXT-STEPS.md`
