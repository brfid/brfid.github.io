# Integration Documentation (VAX ↔ PDP-11)

Integration records for cross-system transfer experiments and validation.

## Scope

- Active production path is single-host `edcloud` + `docker-compose.production.yml`.
- This section is primarily retained integration evidence from earlier multi-machine phases.
- Source of truth for current behavior:
  - `../README.md`
  - `../STATUS.md`
  - `../WORKFLOWS.md`

## Active path (in progress)

Uuencode console transfer (Option B) on single-host edcloud is the current target:

- VAX encodes artifact → GH Actions SSHes into edcloud → `screen`/telnet injects data into PDP-11 console at `localhost:2327` → PDP-11 decodes with `uudecode`/`nroff`
- Last confirmed working: `publish-vax-uuencode-v3` (2026-02-14, prior to single-host migration)
- Blocking items tracked in `../STATUS.md` under "Next work"

## Key records

- [TAPE-TRANSFER-VALIDATION-2026-02-13.md](TAPE-TRANSFER-VALIDATION-2026-02-13.md) — tape transfer validation record
- [UUENCODE-CONSOLE-TRANSFER.md](UUENCODE-CONSOLE-TRANSFER.md) — console transfer design
- [UUENCODE-IMPLEMENTATION-STATUS.md](UUENCODE-IMPLEMENTATION-STATUS.md) — deployment status at time of implementation

## Subsections

- [progress/](progress/) — timeline/progress logs
- [overview/](overview/) — architecture overviews
- [operations/](operations/) — retained runbooks and notes
- [research/](research/) — research artifacts
- [archive/](archive/) — archived approaches
- [handoffs/](handoffs/) — handoff notes

## Related indexes

- [../vax/INDEX.md](../vax/INDEX.md)
- [../pdp/INDEX.md](../pdp/INDEX.md)
- [../aws/INDEX.md](../aws/INDEX.md)
