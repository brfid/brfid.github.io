# Integration Documentation (VAX ↔ PDP-11)

Integration records for cross-system transfer experiments and validation.

## Scope

- Active production path is single-host `edcloud` + `docker-compose.production.yml`.
- This section is primarily retained integration evidence from earlier multi-machine phases.
- Source of truth for current behavior:
  - `../README.md`
  - `../CHANGELOG.md` (`[Unreleased]`)
  - `../WORKFLOWS.md`

## Active path (in progress)

Uuencode console transfer (Option B) on single-host edcloud is the current target:

- VAX encodes artifact → GH Actions SSHes into edcloud → `screen`/telnet injects data
  into PDP-11 console at `localhost:2327` → PDP-11 decodes with `uudecode`/`nroff`
- Last confirmed working end-to-end: `publish-vax-uuencode-v3` (2026-02-14, two-instance/EFS setup)
- Pipeline broken by single-host migration; restored 2026-02-18 (commits `23a81a3`, `242beb9`, `e25637c`)

### Known-good evidence
- `uudecode` confirmed present in 2.11BSD rpethset: `docs/deprecated/PDP11-DEBUG-FINDINGS.md`
- `nroff` confirmed operational in `publish-vax-uuencode-v3`: `docs/integration/progress/NEXT-STEPS.md`
- `unix` kernel (default) boots cleanly; `netnix` crashes on xq init (xq disabled in `configs/pdp11.ini`)

### One remaining gap before a live end-to-end run
- The revised `Dockerfile.pdp11` (xq/ts removed, Bookworm rebuild) has not been built
  and boot-verified on edcloud. Verification steps:
  `docker compose -f docker-compose.production.yml up -d --build pdp11`
  then validate `telnet localhost 2327`.

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
