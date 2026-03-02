# Architecture

Companion docs:
- `README.md`
- `WORKFLOWS.md`
- `docs/integration/INDEX.md`

This repo is a Hugo-based personal site and technical writing portfolio.
The vintage pipeline is optional and produces Hugo input artifacts: `hugo/static/brad.man.txt`,
`hugo/static/brad.bio.txt`, `hugo/static/build.log.html`, and `hugo/data/bio.yaml`.

---

## System boundary

Control plane and execution plane are intentionally split.

- **Control plane** (GitHub Actions): tag handling, AWS start/stop, SSM invocation, artifact extraction, Hugo deploy.
- **Execution plane** (edcloud host): all VAX/PDP-11 orchestration in one script, `scripts/edcloud-vintage-runner.sh`.

Hugo remains the site generator in all modes.

---

## Publish mode

Triggered by `publish-*` tags. Single mode — no local/fast variant.

1. GitHub Actions authenticates to AWS via static credentials
2. Resolve + start edcloud instance
3. Run one SSM command on edcloud
4. edcloud runner executes the vintage pipeline and emits artifacts as base64 markers
5. GitHub Actions extracts artifacts to `hugo/static/`
6. Parses `brad.bio.txt` + reads `about` from `resume.yaml` → writes `hugo/data/bio.yaml`
7. Hugo build + GitHub Pages deploy
8. Stop edcloud if workflow started it

---

## Vintage pipeline (pexpect-based, validated)

The pipeline runs inside `scripts/edcloud-vintage-runner.sh` on edcloud.
Orchestration uses **pexpect** driving SIMH emulators via stdin/stdout — not telnet
ports or screen sessions.

### Stages

**Stage B — VAX (bradman.c compile + generate)**

- Input: `build/vintage/resume.vintage.yaml` (Python-flattened from `resume.yaml`)
- Process: pexpect boots 4.3BSD on SIMH VAX, injects `bradman.c` and `resume.vintage.yaml`
  via heredoc, compiles with `cc`, runs binary to produce `brad.1` and `brad.bio.txt`
- UUCP framing: VAX uuencodes `brad.1` itself (`uuencode brad.1 brad.1 > brad.1.uu`);
  host captures `brad.1.uu` from the pexpect session
- Bio mode: bradman also runs with `-mode bio` to emit `brad.bio.txt` (plain text);
  host captures `brad.bio.txt` separately
- Output: `build/vintage/brad.1.uu`, `build/vintage/brad.bio.txt`
- Status: Validated

**Stage A — PDP-11 (nroff render)**

- Input: `build/vintage/brad.1.uu` (UUE spool from VAX, delivered by host)
- Process: pexpect boots 2.11BSD on SIMH PDP-11, injects `brad.1.uu` via UUE batched
  heredoc, runs `uudecode` to recover `brad.1`, runs `nroff -man -Tlp brad.1 < /dev/null`
- Output: `brad.man.txt`
- Status: Validated

**Stage A+B — Connected (UUCP framing)**

- Transfer mechanism: host-mediated UUCP framing
  - VAX uuencodes `brad.1` → host captures `brad.1.uu` → host delivers to PDP-11 →
    PDP-11 `uudecode`s → `brad.1` → `nroff` → `brad.man.txt`
- FTP to PDP-11 is not viable: 2.11BSD `unix` kernel has no working Ethernet;
  `netnix` kernel crashes on `xq` init
- Status: Validated end-to-end

### Key constraints

- **PDP-11 pexpect startup**: the pexpect script spawns SIMH directly (stdin/stdout, no telnet);
  it must process output immediately from process start with no delays.
- PDP-11 requires `mount /usr` before `nroff` and `uudecode` are available.
- VAX console: login as root, no password on 4.3BSD guest.
- Both machines confirmed booting and tool-ready on 2026-02-28.

---

## Key artifacts

Input:
- `resume.yaml`

Generated (internal):
- `build/vintage/resume.vintage.yaml`
- `build/vintage/brad.1.uu` (UUCP spool from VAX)
- `build/vintage/brad.bio.txt`

Published input to Hugo:
- `hugo/static/brad.man.txt`
- `hugo/static/brad.bio.txt`
- `hugo/static/build.log.html`
- `hugo/data/bio.yaml` (parsed from `brad.bio.txt` + build log header; `about` read from `resume.yaml` top-level field)

Site output:
- `site/` (gitignored, generated fresh each CI run)

---

## Operational principles

- Single orchestration implementation for vintage stages (`scripts/edcloud-vintage-runner.sh`).
- Shared session utilities in `scripts/simh_session.py` (`make_logger`, `validate_uu_spool`,
  `inject_batched_heredoc`); imported by both pexpect scripts.
- CI contains bootstrap logic only; no embedded multi-stage console choreography.
- edcloud lifecycle can be automated end-to-end without manual pre-start.
- Runtime cleanup defaults are deterministic; opt out with `KEEP_IMAGES=1` for debugging.
