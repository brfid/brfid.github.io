# Integration: VAX ↔ PDP-11 vintage pipeline

Active pipeline reference. For implementation details, see `operations/PEXPECT-PIPELINE-SPEC.md`.

## System boundary

- **Control plane** (GitHub Actions): AWS start/stop, SSM invocation, artifact extraction, Hugo deploy.
- **Execution plane** (edcloud host): all VAX/PDP-11 orchestration in one script, `scripts/edcloud-vintage-runner.sh`.

Single-host edcloud instance. Runner uses `docker build`/`docker run` directly; no Compose orchestration.
Orchestration uses **pexpect** driving SIMH emulators via stdin/stdout — no telnet ports, no screen sessions, no sleep-based timing.

## Stages

| Stage | Machine | Input | Process | Output |
|-------|---------|-------|---------|--------|
| A | PDP-11 (2.11BSD) | `brad.1` (troff source) | `nroff -man` | `brad.man.txt` |
| B | VAX (4.3BSD) | `resume.vintage.yaml` | compile + run `bradman.c` (`roff` + `bio` modes) | `brad.1`, `brad.bio.txt` |
| A+B | VAX → host → PDP-11 | `resume.vintage.yaml` | B then A, host as courier | `brad.man.txt` |

Stage B bio mode: bradman runs with `-mode bio` to emit `brad.bio.txt` (plain text including
`principal_headline` and `impact_highlights`); captured separately by the host.

Homepage data flow (publish-critical path):

`resume.yaml` (`principal_headline`, `principal_impact`) → `resume.vintage.yaml`
(`principalHeadline`, `impactHighlights`) → VAX `brad.bio.txt` →
`resume_generator/bio_yaml.py` → `hugo/data/bio.yaml` → Hugo landing template.

## Key artifacts

Input:
- `resume.yaml`

Generated (internal, `build/vintage/`):
- `resume.vintage.yaml` — Python-flattened from `resume.yaml`
- `brad.1.uu` — UUE-encoded troff source (UUCP spool from VAX)
- `brad.bio.txt` — plain-text bio excerpt

Published to Hugo:
- `hugo/static/brad.man.txt`
- `hugo/static/brad.bio.txt`
- `hugo/static/build.log.html`
- `hugo/data/bio.yaml` (parsed from `brad.bio.txt`; `about` read from `resume.yaml` top-level field)

## Key constraints

- **PDP-11 networking**: the `unix` kernel (required — `netnix` crashes on `xq` init) has
  no working Ethernet. FTP from VAX to PDP-11 is not viable. Transfer is host-mediated:
  pexpect reads VAX output, injects into PDP-11.
- **PDP-11 pexpect startup**: pexpect spawns SIMH directly (stdin/stdout, no telnet port).
  The script must process SIMH output from process start with no delays.
- **PDP-11 `/usr` mount**: `mount /usr` required before `nroff` and `uudecode` are available.
- **VAX console**: root login, no password on 4.3BSD guest.
- Both machines confirmed booting and tool-ready (2026-02-28 diagnostic run).

## Operational notes

- Shared session utilities: `scripts/simh_session.py` (`make_logger`, `validate_uu_spool`,
  `inject_batched_heredoc`); imported by both pexpect scripts.
- CI contains bootstrap logic only; no embedded multi-stage console choreography.
- Set `KEEP_IMAGES=1` in the runner environment to preserve Docker images between runs (avoids rebuild on retry).

## Active runbooks

- [`operations/PEXPECT-PIPELINE-SPEC.md`](operations/PEXPECT-PIPELINE-SPEC.md) — implementation spec for the pexpect pipeline

## Related

- [`../../scripts/edcloud-vintage-runner.sh`](../../scripts/edcloud-vintage-runner.sh) — pipeline entrypoint
- [`../vax/README.md`](../vax/README.md) — VAX stage reference (bradman.c, YAML subset, output contract)
- [`../archive/DEAD-ENDS.md`](../archive/DEAD-ENDS.md) — retired paths (screen/telnet, FTP, ARPANET, PDP-10)
