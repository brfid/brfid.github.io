# Changelog

All notable changes to this project are documented in this file.

Format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
with date-based entries because this repository does not currently publish
semantic version tags.

## [Unreleased]

### Current State
- Hugo is the site generator (`hugo/`); the vintage pipeline (VAX/PDP-11 via SIMH)
  is an on-demand artifact generator only — it feeds `hugo/static/brad.man.txt`.
- **Architecture decision (2026-02-28):** The screen/telnet/sleep orchestration
  approach is retired. The replacement is **pexpect** — Python prompt-detection
  driving SIMH via stdin/stdout (no telnet port). This eliminates all timing races.
- **Both machines confirmed working on edcloud (2026-02-28 diagnostic run):**
  - VAX 4.3BSD: boots to login, root login works, `cc` present.
  - PDP-11 2.11BSD: boots to `#` prompt after Enter at `Boot:`, `mount /usr`
    works, `/usr/bin/nroff` and `/usr/bin/uudecode` present.
- **PDP-11 networking constraint (permanent):** The `unix` kernel has no working
  Ethernet (`netnix` crashes on `xq` init). FTP to PDP-11 is not viable. File
  transfer between stages must be host-mediated (pexpect captures VAX output,
  host writes to temp file, pexpect injects into PDP-11 session).
- Cold-start doc order: `README.md` → this file → `docs/integration/INDEX.md`
  → `docs/integration/operations/PEXPECT-PIPELINE-SPEC.md`.
- **Pexpect pipeline implemented + first fix (2026-02-28, branch
  `feat/pexpect-pipeline`):**
  - `scripts/pdp11_pexpect.py` — Stage A (PDP-11 nroff runner)
  - `scripts/vax_pexpect.py` — Stage B (VAX bradman.c compile+run); fixed to
    read `resume.vintage.yaml` as UTF-8 and transliterate typographic Unicode
    (em-dashes, curly quotes) to ASCII before VAX injection.
  - `vintage/machines/pdp11/configs/pdp11-pexpect.ini` — pexpect-mode PDP-11 ini
  - `vintage/machines/pdp11/Dockerfile.pdp11-pexpect` — pexpect Docker image
  - `vintage/machines/vax/Dockerfile.vax-pexpect` — pexpect Docker image
  - `scripts/edcloud-vintage-runner.sh` — rewritten; no screen/telnet
  - `.github/workflows/deploy.yml` — timeout bumped (job 70 min, SSM 50 min)
  - **Validation in progress** — multiple debug runs. Current fix on edcloud:
  chunked UUE injection (10 lines/batch) + stty -ixon -ixoff.

### Active Priorities
1. **Confirm edcloud validation**: Second pipeline run in progress
   (`BUILD_ID=manual-20260228-173226`). If it passes, merge
   `feat/pexpect-pipeline` → `main` and update CHANGELOG.
2. **CI smoke test** (after merge): Trigger a `publish-vintage-*` tag and
   confirm the GitHub Actions workflow produces `hugo/static/brad.man.txt`.

### In Progress
- Edcloud validation run `manual-20260228-173226` — waiting for exit code.

### Blocked
- None.

### Decisions Needed
- None.

### Recently Completed
- **Iterative VAX injection debugging (2026-02-28):** Five debug runs. Issues
  found and fixed in sequence:
  1. UnicodeDecodeError — resume.vintage.yaml not ASCII; fixed with UTF-8 read +
     NFKD transliteration.
  2. SIMH instant exit — disk images gzipped (RA81.000.gz); added gunzip in
     Dockerfile. Created static vax780-pexpect.ini (no network/DZ terminals).
  3. False prompt match — "# " needed (not "#"); kernel banner contains "#10".
  4. YAML tty overflow — lines up to 571 chars exceed 256-byte tty CANBSIZ;
     switched to uuencode injection.
  5. UUE stall — single 94-line heredoc stalls PTY echo after ~180s; fixed with
     10-line chunks + stty -ixon -ixoff to disable flow control.
- **Docker images built on edcloud (2026-02-28):** Both `pdp11-pexpect` and
  `vax-pexpect` images built successfully. Images cached with `KEEP_IMAGES=1`.
- **Pexpect pipeline implementation (2026-02-28):** Stage A (PDP-11), Stage B
  (VAX), Dockerfiles, and rewritten runner — all on `feat/pexpect-pipeline`.
- **Docker images built on edcloud (2026-02-28):** Both `pdp11-pexpect` and
  `vax-pexpect` images built successfully. Images cached with `KEEP_IMAGES=1`.
- **CI timeout extended (2026-02-28):** `deploy.yml` job timeout 40→70 min,
  SSM polling 30→50 min to accommodate first-run docker builds.
- **Documentation pass (2026-02-28):** Removed 21 dead MD files; rewrote key
  docs; created `docs/integration/operations/PEXPECT-PIPELINE-SPEC.md`.
- **Diagnostic run (2026-02-28):** Confirmed both VAX and PDP-11 guest machines
  boot and reach root shells on edcloud; chose pexpect as replacement.
- **Architecture decision:** Retired screen/telnet/sleep orchestration entirely.
  Added to `docs/archive/DEAD-ENDS.md`.

## [2026-02-21]

### Added
- Hugo site (`hugo/`) with PaperMod theme, dark mode, `www.jockeyholler.net`
  canonical URL, and Blog / Work / Resume / About navigation.
- Hugo-native resume page rendered from `resume.yaml` data source; custom layout
  (`hugo/layouts/_default/resume.html`) and CSS; PDF download at `/resume.pdf`.
- Portfolio page (Work nav) drawn from `portfolio.yaml` structured data.
- Blog posts: "How I Use Changelogs as LLM Memory" and "Why Do We Call Them
  Packets?" (with local image assets).
- CI/deploy: GitHub Actions Hugo build pipeline with tag-triggered publish
  (`publish`, `publish-vintage`); Python/Playwright gated on vintage mode only.
- Vintage artifact pipeline integrated as an optional CI stage: VAX compiles and
  encodes resume → PDP-11 typesets with `nroff` → output committed to
  `hugo/static/brad.man.txt` for Hugo to serve.
- Research archive (`docs/archive/`): exploratory emulation notes organized by
  host type (VAX, PDP-11, PDP-10, ARPANET); see `docs/archive/README.md`.

### Changed
- Architectural decision: Hugo as site generator for all content; vintage
  pipeline scoped to artifact-only role.
- DNS: apex A/AAAA and www CNAME switched from CloudFront aliases to GitHub
  Pages; orphaned alias records removed.
- edcloud lifecycle management centralized into shared Python CLI
  (`scripts/edcloud_lifecycle.py`) with thin shell wrappers for operator use.
- Deploy workflow refactored to run console orchestration from edcloud repo
  checkout; Tailscale SSH replaces public-IP key-based access.
- PDP-11 readiness checks updated to avoid one-shot TCP probes that triggered
  SIMH TTI disconnect/reboot loops; log-signal–based gating used instead.

## [2026-02-14]

### Added
- VAX ↔ PDP-11 uuencode console transfer pipeline; end-to-end artifact flow
  validated on single-host edcloud with Docker Compose.
- Cold-start diagnostics runbook (`docs/integration/operations/VAX-PDP11-COLD-START-DIAGNOSTICS.md`)
  standardizing serialized console session discipline and log-based readiness gating.
- edcloud single-host deployment model: VAX and PDP-11 containers co-located on
  one EC2 instance, reducing operational surface area and Tailscale SSH dependency.

### Changed
- Evaluated ARPANET IMP, KL10/KS10 (TOPS-20), and Chaosnet emulation paths as
  potential pipeline stages; documented findings and convergence decision in
  `docs/archive/arpanet/` and `docs/archive/pdp-10/`.
