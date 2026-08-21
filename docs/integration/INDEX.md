# Integration: VAX ↔ PDP-11 vintage pipeline

Active pipeline reference. For implementation details and the as-built gotchas, see `operations/PEXPECT-PIPELINE-SPEC.md`.

The pipeline's sole artifact is the landing-page bio. The resume does not pass through it; it is rendered separately by Hugo + Playwright.

## System boundary

> **Status (2026-07-25): the pipeline runs on GitHub-hosted `ubuntu-latest` runners.** The edcloud execution host was decommissioned along with its AWS account, and the pipeline was ported the same day — control and execution planes are now the same machine. Do not reintroduce a cloud dependency for the publish path.

- **Control plane** (GitHub Actions): artifact extraction, Hugo deploy.
- **Execution plane**: all VAX/PDP-11 orchestration in one script, `scripts/edcloud-vintage-runner.sh`, invoked directly on the same runner. The name is historical — the script has no AWS coupling and needs only `docker`, `git`, and `python3`, so any Linux (or arm64 macOS) host with Docker can execute it unchanged.

Runner uses `docker build`/`docker run` directly; no Compose. Orchestration uses **pexpect** driving SIMH emulators via stdin/stdout — no telnet ports, no screen sessions, no sleep-based timing.

## Stages

| Stage | Machine | Input | Process | Output |
|-------|---------|-------|---------|--------|
| B | VAX (4.3BSD) | `bio.vintage.yaml` | compile + run `bradman.c` → troff, then `uuencode` | `brad.bio.uu` (UUCP spool) |
| A | PDP-11 (2.11BSD) | `brad.bio.uu` | `uudecode`, then `nroff` (no macro package) fills and justifies | `brad.bio.txt` |
| A+B | VAX → host → PDP-11 | `bio.vintage.yaml` | B then A, host as courier | `brad.bio.txt` |

`bradman.c` has a single job: read the flat bio YAML and emit a small troff document (name and headline verbatim, blurb filled and justified to a 60-column measure). The PDP-11 runs `nroff` **without** `-man` — the bio is prose, not a man page.

## Homepage data flow (the publish-critical path)

`site.yaml` (`name`, `headline`) + `resume.yaml` (`blurb`) → `build/vintage/bio.vintage.yaml` (`bioName`, `bioHeadline`, `bioProfile`) → VAX composes troff → PDP-11 `nroff` → `brad.bio.txt` → `resume_generator/bio_yaml.py` (plus the enclosing GitHub Actions run URL) → `hugo/data/bio.yaml` → Hugo landing template. Icon links are read directly from `site.yaml` after it is copied to Hugo data. Only `resume.yaml`'s `blurb` enters the pipeline — the resume document itself does not.

The blurb reaches the page as prose: `bio_yaml.py` collapses nroff's fixed-width fill and justification back to flowing single-spaced sentences (blank lines stay as paragraph breaks), and the landing template sets `about` in the humanist serif. The vintage typesetting still runs on the machines; only its column geometry is dropped from the final type.

## Key artifacts

Input: `site.yaml`.

Generated (internal, `build/vintage/`):
- `bio.vintage.yaml` — flat ASCII YAML from `site.yaml`, emitted by `resume_generator/vintage_yaml.py`
- `brad.bio.uu` — UUE-encoded troff bio (UUCP spool from VAX)
- `brad.bio.txt` — the nroff-rendered bio (internal; parsed into `bio.yaml`, not served as a file)

Consumed by Hugo:
- `hugo/data/site.yaml` (generated copy of the public landing source)
- `hugo/data/bio.yaml` (generated from `brad.bio.txt`)
- `hugo/static/build.log.html` (rendered by `resume_generator/build_log.py` from the host log and named guest-console sections)
- `hugo/static/pipeline-status.json` (machine-readable build identity, result, and per-stage line counts)

## Key constraints

- **PDP-11 networking**: the `unix` kernel (required — `netnix` crashes on `xq` init) has no working Ethernet. FTP from VAX to PDP-11 is not viable. Transfer is host-mediated: pexpect reads VAX output, injects into PDP-11.
- **PDP-11 pexpect startup**: pexpect spawns SIMH directly (stdin/stdout, no telnet port). The script must process SIMH output from process start with no delays.
- **PDP-11 `/usr` mount**: `mount /usr` required before `nroff` and `uudecode` are available.
- **VAX console**: root login, no password on the 4.3BSD guest.

## Operational notes

- Shared session utilities: `scripts/simh_session.py` (`make_logger`, `validate_uu_spool`, `inject_batched_heredoc`); imported by both pexpect scripts.
- Published build-log rendering: `resume_generator/build_log.py`; the shell runner owns orchestration and marker transport only.
- Marker base64 uses `base64 | tr -d '\n'` (portable across GNU and BSD/macOS), not the GNU-only `base64 -w 0`.
- Set `KEEP_IMAGES=1` in the runner environment to preserve Docker images between runs (avoids rebuild on retry).

## Related

- [`operations/PEXPECT-PIPELINE-SPEC.md`](operations/PEXPECT-PIPELINE-SPEC.md) — as-built implementation spec and gotchas
- [`../../scripts/edcloud-vintage-runner.sh`](../../scripts/edcloud-vintage-runner.sh) — pipeline entrypoint
- [`../vax/README.md`](../vax/README.md) — VAX stage reference (bradman.c, YAML subset)
- [`../archive/DEAD-ENDS.md`](../archive/DEAD-ENDS.md) — retired paths (screen/telnet, FTP, ARPANET, PDP-10)
