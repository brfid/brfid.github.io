# Archived: KS10 Emulator Boot Failures

**Date Archived**: 2026-02-11
**Reason**: KS10 emulator incompatible with both ITS and TOPS-20
**Status**: dead end for this repository's current objectives

## What's Here

Documentation of KS10 boot failures for both ITS and TOPS-20. Both OSes failed with identical errors, confirming fundamental emulator incompatibility.

## Status Summary

| Component | Status | Error |
|-----------|--------|-------|
| **KS10 Emulator** | ❌ Incompatible | SIMH KS10 V4.0-0 |
| ITS Boot | ❌ Failed | "Internal error, PC: 000100" |
| TOPS-20 Boot | ❌ Failed | "Unknown stop code 7, PC: 000100" |
| **KL10 Emulator** | ✅ Solution | Community-proven for TOPS-20 |

## Root Cause

**Both ITS and TOPS-20 fail identically on SIMH KS10**:
- **Stop code 7**: Unknown halt condition
- **PC: 000100**: Halt at very low memory address (64 decimal)
- **Bootstrap failure**: Cannot reach MTBOOT prompt or ITS boot

**Community Research**:
- All working TOPS-20 setups use KL10 or KLH10
- Gunkies recipe (works): Uses KL10 emulator
- PiDP-10 (works): Uses KLH10 emulator
- Pre-built images: All use KL10/KLH10

**Conclusion**: KS10 lacks proper support for TOPS-20/ITS tape boot loaders

## What Was Tried

### ITS Path
1. ✅ ITS build from source (30-60+ minutes)
2. ✅ Docker build completed
3. ❌ Runtime boot failed with "PC: 000100"
4. ❌ Container restart loop

### TOPS-20 Path
1. ✅ TOPS-20 V4.1 tape obtained
2. ✅ Tape attached successfully to TUA0
3. ✅ Console configuration fixed (stdio mode)
4. ❌ `boot tua0` failed with "Stop code 7, PC: 000100"

## Time Investment

- ITS build attempts: 4-6 hours
- TOPS-20 tape boot debugging: 8 hours
- Console/telnet configuration: 6 hours
- **Total**: ~20 hours on KS10 approach

## Why Archived

**Unrecoverable blockers**:
- Emulator-level incompatibility (not fixable via config)
- No community examples of KS10 + TOPS-20/ITS working
- Stop code 7 appears to be unhandled condition in SIMH KS10

**Solution exists**:
- Switch to KL10 emulator (proven to work)
- Gunkies recipe provides exact working configuration
- Pre-built TOPS-20 images available for KL10

## Could This Be Revived?

Only if:
- SIMH KS10 receives boot loader fix
- Alternative KS10 tape images found
- Someone debugs and patches SIMH KS10 bootstrap code

**Not recommended**: KL10 is proven solution, KS10 is dead end

## Current Path

No current path in this repo depends on PDP-10 runtime.
See `../../DEAD-ENDS.md` for canonical retirement status.
