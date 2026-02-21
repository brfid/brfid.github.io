# Integration Documentation (VAX ↔ PDP-11)

Active pipeline integration reference for the VAX/PDP-11 vintage computing artifact pipeline.

## Current architecture

Single-host `edcloud` instance running VAX and PDP-11 containers via `docker-compose.production.yml`.

- VAX (VMS/BSD) compiles the resume artifact and encodes it via uuencode
- GitHub Actions SSHes into edcloud, injects encoded data into PDP-11 console via screen/telnet
- PDP-11 (2.11BSD) decodes with `uudecode` and typesets with `nroff`
- Output: `brad.man.txt` → committed to `hugo/static/` → served by Hugo

Source of truth for current behavior: `../../README.md`, `../../CHANGELOG.md` (`[Unreleased]`), `../../WORKFLOWS.md`.

## Active runbooks

- [`operations/VAX-PDP11-COLD-START-DIAGNOSTICS.md`](operations/VAX-PDP11-COLD-START-DIAGNOSTICS.md) — serialized cold-start diagnostic path for Stage 1→3 rehearsal on edcloud

## Related

- [`../vax/INDEX.md`](../vax/INDEX.md) — VAX operational reference
- [`../archive/pipeline-planning/`](../archive/pipeline-planning/) — historical build records and validation logs
