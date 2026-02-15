# Integration Documentation (VAX ↔ PDP-11)

Integration records for VAX/PDP-11 transfer and IMP experiments.

## Status And Scope

- **Current active production path**: single-host `edcloud` lifecycle + `docker-compose.production.yml` in this repo.
- **This section**: mixed operational notes and historical records from prior multi-machine/EFS phases.
- **Source of truth for "current" behavior**:
  - `../README.md`
  - `../STATUS.md`
  - `../WORKFLOWS.md`

## Current Architecture (2026-02-15)

**Historical milestone (retained):** Uuencode console transfer for discrete machine-to-machine communication.
The active deployment path is now single-host `edcloud`; this section is retained primarily as integration evidence.

- **Method**: VAX encodes → Console I/O → PDP-11 decodes
- **Why**: Historically accurate (1970s-80s), no shared filesystem
- **Status at time of write**: Fully deployed and operational (`publish-vax-uuencode-v3`)
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
