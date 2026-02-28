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
- **Pexpect pipeline implemented (2026-02-28, branch feat/pexpect-pipeline):**
  - `scripts/pdp11_pexpect.py` — Stage A (PDP-11 nroff runner)
  - `scripts/vax_pexpect.py` — Stage B (VAX bradman.c compile+run)
  - `vintage/machines/pdp11/configs/pdp11-pexpect.ini` — pexpect-mode PDP-11 ini
  - `vintage/machines/pdp11/Dockerfile.pdp11-pexpect` — pexpect Docker image
  - `vintage/machines/vax/Dockerfile.vax-pexpect` — pexpect Docker image
  - `scripts/edcloud-vintage-runner.sh` — rewritten; no screen/telnet
  - **Not yet validated on edcloud** — requires docker build + test run on EC2.

### Active Priorities
1. **Validate on edcloud**: Run `edcloud-vintage-runner.sh <build-id>` on the
   EC2 instance to test the full pipeline end-to-end. Debug any boot-sequence
   or heredoc injection issues.
2. **CI integration**: Update `.github/workflows/deploy.yml` to invoke the
   new runner (currently calls the old screen/telnet runner).

### In Progress
- None.

### Blocked
- None. Implementation is done; next step is a live test on edcloud EC2.

### Decisions Needed
- None.

### Recently Completed
- **Pexpect pipeline implementation (2026-02-28):** Stage A (PDP-11), Stage B
  (VAX), Dockerfiles, and rewritten runner — all implemented on
  `feat/pexpect-pipeline`. Not yet validated on edcloud.
- **Documentation pass (2026-02-28):** Removed 21 dead MD files (screen/telnet
  runbooks, old archive docs, transport-archive.md, pdp-11 archive files);
  rewrote ARCHITECTURE.md, WORKFLOWS.md, docs/integration/INDEX.md,
  docs/vax/INDEX.md, docs/vax/README.md, docs/archive/DEAD-ENDS.md,
  docs/archive/README.md, docs/archive/arpanet/README.md,
  docs/archive/pdp-10/INDEX.md, docs/INDEX.md, AGENTS.md, README.md.
- Created `docs/integration/operations/PEXPECT-PIPELINE-SPEC.md` — primary
  cold-start implementation reference for the pexpect pipeline.
- **Diagnostic run (2026-02-28):** Confirmed both VAX and PDP-11 guest machines
  boot and reach root shells on edcloud; identified screen/telnet/sleep as
  fundamentally unreliable; chose pexpect as replacement.
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
