# Integration Documentation (VAX ↔ PDP-11)

Active pipeline integration reference.

## Architecture

Single-host edcloud instance running VAX and PDP-11 containers via `docker-compose.production.yml`.

Orchestration uses **pexpect** driving SIMH emulators via stdin/stdout.
No telnet console ports, no screen sessions, no sleep-based timing.

Pipeline stages (built and validated incrementally):

| Stage | Machine | Input | Process | Output |
|-------|---------|-------|---------|--------|
| A | PDP-11 (2.11BSD) | `brad.1` (troff source) | `nroff -man` | `brad.man.txt` |
| B | VAX (4.3BSD) | `resume.vintage.yaml` | compile + run `bradman.c` | `brad.1` |
| A+B | VAX → host → PDP-11 | `resume.vintage.yaml` | B then A, host as courier | `brad.man.txt` |

## Key constraints

- **PDP-11 networking**: the `unix` kernel (required — `netnix` crashes on `xq` init) has
  no working Ethernet. FTP from VAX to PDP-11 is not viable. Transfer is host-mediated:
  pexpect reads VAX output, injects into PDP-11.
- **PDP-11 console timeout**: SIMH exits if no client connects within ~60 seconds of boot.
  The pexpect script must connect immediately on startup.
- **PDP-11 `/usr` mount**: `mount /usr` required before `nroff` and `uudecode` are available.
- **VAX console**: root login, no password on 4.3BSD guest.
- Both machines confirmed booting and tool-ready (2026-02-28 diagnostic run).

## Active runbooks

- [`operations/PEXPECT-PIPELINE-SPEC.md`](operations/PEXPECT-PIPELINE-SPEC.md) — implementation spec for the pexpect pipeline

## Related

- [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md) — system design and stage descriptions
- [`../../scripts/edcloud-vintage-runner.sh`](../../scripts/edcloud-vintage-runner.sh) — pipeline entrypoint
- [`../archive/DEAD-ENDS.md`](../archive/DEAD-ENDS.md) — retired paths (screen/telnet approach, FTP, ARPANET, PDP-10)
