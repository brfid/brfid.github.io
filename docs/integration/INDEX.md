# Integration Documentation (VAX ↔ PDP-11)

Multi-machine connections and file transfer documentation.

## Current Architecture (2026-02-14)

**✅ OPERATIONAL**: Uuencode console transfer for discrete machine-to-machine communication

- **Method**: VAX encodes → Console I/O → PDP-11 decodes
- **Why**: Historically accurate (1970s-80s), no shared filesystem
- **Status**: Fully deployed and operational (publish-vax-uuencode-v3)
- **Docs**:
  - [UUENCODE-CONSOLE-TRANSFER.md](UUENCODE-CONSOLE-TRANSFER.md) - Architecture
  - [UUENCODE-IMPLEMENTATION-STATUS.md](UUENCODE-IMPLEMENTATION-STATUS.md) - Deployment status

## Key Documents

### Current (Operational)
- **[UUENCODE-CONSOLE-TRANSFER.md](UUENCODE-CONSOLE-TRANSFER.md)** - ✅ Console-based file transfer architecture
- **[UUENCODE-IMPLEMENTATION-STATUS.md](UUENCODE-IMPLEMENTATION-STATUS.md)** - ✅ Implementation and deployment status
- **[TAPE-TRANSFER-VALIDATION-2026-02-13.md](TAPE-TRANSFER-VALIDATION-2026-02-13.md)** - ✅ Tape transfer validation (proof of concept)

### Organization
- **[Progress](progress/)** - Timeline and progress logs
- **[Overview](overview/)** - Architecture overviews
- **[Operations](operations/)** - Operational guides
- **[Research](research/)** - Research and analysis
- **[Archive](archive/)** - Historical approaches (IMPs, etc.)
- **[Handoffs](handoffs/)** - LLM research handoffs

## Quick Links
- **[VAX Documentation](../vax/)** - 4.3BSD VAX 11/780
- **[PDP Documentation](../pdp/)** - 2.11BSD PDP-11/73
- **[AWS Infrastructure](../aws/)** - Cloud deployment
