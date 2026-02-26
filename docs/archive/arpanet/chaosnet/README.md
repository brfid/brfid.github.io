# Archived: Path A (Chaosnet-First Approach)

**Date Archived**: 2026-02-11
**Reason**: Blocked on PDP-10 ITS disk build

## What's here

Path A attempted to implement Chaosnet-over-ARPANET for VAX ↔ PDP-10 file transfer. The Chaosnet protocol implementation was completed and verified, but the approach was blocked at the infrastructure layer.

## Status Summary

| Component | Status | Notes |
|-----------|--------|-------|
| Chaosnet shim | ✅ Complete | Protocol verified with 12-byte header format |
| Test framework | ✅ Complete | Unit tests passing |
| IMP routing | ✅ Complete | VAX → IMP1 → IMP2 routing operational |
| **PDP-10 ITS** | ❌ Blocked | Docker build timed out, no `its.dsk` created |
| File transfer | ⏸️ Blocked | Cannot test without ITS endpoint |

## Why Archived

1. **ITS Build Timeout**: PDP-10 ITS Docker build failed to complete after ~1800 seconds
2. **Simpler Alternative**: Serial Tunnel approach provides direct VAX-PDP10 connection without IMP complexity
3. **TOPS-20 Available**: Container is running TOPS-20, which doesn't support Chaosnet
4. **AWS Cost**: No justification for running test instance while blocked

## Could This Be Revived?

Yes, if:
- ITS disk build succeeds (longer timeout, faster hardware, or pre-built disk)
- Alternative PDP-10 emulator with Chaosnet support found
- Someone wants the historically-authentic ITS/Chaosnet experience

## Retention note

Detailed Path A artifacts were removed during archive cleanup because they were
low-value dead-end records. This summary is retained as the canonical marker.

See `../../DEAD-ENDS.md` for active retirement status.
