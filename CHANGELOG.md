# Changelog

All notable changes to this project are documented in this file.

Format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
with date-based entries because this repository does not currently publish
semantic version tags.

## [Unreleased]

### Current State
- Hugo is the site generator; the vintage pipeline (VAX/PDP-11 via SIMH) is stable and produces four Hugo inputs: `hugo/static/brad.man.txt`, `hugo/static/brad.bio.txt`, `hugo/static/build.log.html`, and `hugo/data/bio.yaml`.
- Site live at www.jockeyholler.net. Pipeline last validated: `publish-vintage-20260302-151109`.
- Single build mode (vintage). `deploy.yml` triggers on `publish-*` tags only; no fast/local mode.
- `resume_generator` CLI is site-generation only (`--in`, `--out`, `--templates`, `--html-only`); vintage orchestration is owned by pexpect scripts + `scripts/edcloud-vintage-runner.sh`.
- Landing page hierarchy now supports vintage-pipeline-driven `principal_headline` and `impact_highlights` (emitted via `resume.vintage.yaml` -> `brad.bio.txt` -> `hugo/data/bio.yaml`), while `about` remains sourced from `resume.yaml` top-level `about`.
- Homepage hero presentation is now recruiter-first: single role line, concise summary, scoped CTA hierarchy, compact proof strip (first three impact highlights), and de-emphasized provenance footer while preserving pipeline-fed content fields.
- **PDP-11 networking (permanent constraint):** `unix` kernel has no Ethernet; inter-stage file transfer is host-mediated.
- Cold-start doc order: `README.md` → this file → `docs/integration/INDEX.md`.

### Active Priorities
- None.

### In Progress
- None.

### Blocked
- None.

### Decisions Needed
- None.

### Recently Completed
- **2026-03-02:** Simplified Hugo homepage information density for hiring-chain readability while retaining vintage/resume.yaml sourcing (`home_info.html` + homepage CSS updates).
- **2026-03-02:** Added principal homepage hierarchy path through vintage pipeline (`principalHeadline`/`impactHighlights` in vintage YAML, `brad.bio.txt` emission+parse, Hugo landing rendering, and tests).
- **2026-03-02:** Single vintage-only mode, `about` from `resume.yaml`, docs updated — see `[2026-03-02]` dated entry.
- **2026-03-02:** Removed legacy `resume_generator` vintage/ARPANET orchestration modules and flags; retained canonical pexpect + edcloud runner path.
- **2026-03-02:** Added/adjusted script docstrings for Google-style Ruff `D` conformance and fixed `host_logging` warning counter normalization (`WARN` + `WARNING`).
- **2026-03-02:** Ran scoped validation (`pytest`), Bandit, and Vulture; triaged findings for portfolio-readiness review.
- **2026-03-02:** Fixed CI gate failure on `d7f3c03` by narrowing `resume_generator/bio_yaml.py` exception handling (`except json.JSONDecodeError` instead of broad `except Exception`).

## [2026-03-02]

### Added
- `resume.yaml` top-level `about` field: single editorial source of truth for the landing page narrative paragraph.
- `hugo/data/bio.yaml` `about` field: pipeline-agnostic landing-page narrative paragraph.
- `home_info.html` renders `$bio.about` on landing page (`summary` retained for resume page and PDF).
- DomainTools role: sole-TW scope added as first highlight bullet.

### Changed
- Single vintage-only build mode: `deploy.yml` trigger is now `publish-*`; fast/local mode and mode detection removed. Every deploy runs the full vintage pipeline.
- `bio_yaml.py`: `about` is now sourced from `resume.yaml` top-level field (passed as 4th CLI arg) instead of being carried forward from the existing `hugo/data/bio.yaml`. Removes `_read_about_from_yaml`; adds `_read_about_from_resume_yaml`.
- `hugo/data/bio.yaml` in repo reduced to a minimal 4-key empty placeholder for local dev.
- `resume.yaml` tagline and `basics.label`: "Technical Writer" → "Principal Technical Writer" throughout.
- All prose strings in `resume.yaml` unwrapped to single lines (IDE word-wrap; YAML values unchanged).
- `portfolio.yaml` jockeyholler.net entry: `status: in-progress` → `live`; summary updated.
- `README.md`, `ARCHITECTURE.md`, `WORKFLOWS.md`: updated for single vintage mode, new `about` sourcing.
- `scripts/simh_session.py` (shared session utilities), `resume_generator/bio_yaml.py` (bio parser extracted), UUE validation, SIMH SHA pin, `.github/workflows/build-images.yml` (GHA image cache), HTML build log with `<details>` console sections. 156 tests.

## [2026-03-01]

### Added
- Bio mode: `bradman.c -mode bio` emits `brad.bio.txt` (name, label, summary, contact block); `bio_yaml.py` parses it into `hugo/data/bio.yaml` with `build_id` from `build.log.html`.
- Landing page bio: `home_info.html` renders name, label, summary, and pipeline provenance line from `site.Data.bio`; static fallback in repo for fast builds.
- Machine-boundary build log emitted by runner; extracted to `hugo/static/build.log.html` by CI.

### Changed
- UUCP framing: VAX uuencodes `brad.1` itself; host routes spool to PDP-11; PDP-11 `uudecode`s. ASCII conversion in `resume_generator/normalize.py`; `binascii.b2a_uu` replaces deprecated `uu` module.

## [2026-02-28]

### Added
- Pexpect pipeline: `scripts/vax_pexpect.py` (Stage B — VAX 4.3BSD compiles
  `bradman.c` → `brad.1`) and `scripts/pdp11_pexpect.py` (Stage A — PDP-11
  2.11BSD runs `nroff -man` → `brad.man.txt`). Both drive SIMH via stdin/stdout;
  no telnet ports, no screen sessions, no sleep-based timing.
- `scripts/edcloud-vintage-runner.sh` — single orchestration entrypoint for both
  stages on edcloud; emits artifact as base64 between hard markers for CI extraction.
- Docker configs: `vintage/machines/vax/Dockerfile.vax-pexpect`,
  `vintage/machines/pdp11/Dockerfile.pdp11-pexpect`, and matching `.ini` files.
- `docs/integration/operations/PEXPECT-PIPELINE-SPEC.md` — implementation spec.
- `docs/archive/DEAD-ENDS.md` — registry of retired approaches (screen/telnet,
  FTP between stages, ARPANET/PDP-10 pipeline paths).
- Site: portfolio page (`hugo/data/portfolio.yaml`, custom layout + CSS),
  Strachey's Principle post, Inter typography (`extend_head.html` + `typography.css`).
- Resume page: Certifications section, `tel:` link, `/about/` URL alias.

### Changed
- Screen/telnet/sleep orchestration retired; pexpect is the permanent replacement.
- AWS auth: OIDC → static credentials (`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`).
- Navigation: Portfolio replaces About; `/about/` aliases to `/resume/`.
- `secret-scan.yml`: switched to `GITLEAKS_LOG_OPTS: --all --no-merges` to scan
  full history; avoids git range error when force-push orphans the before SHA.
- 21 stale archive MD files removed; docs rewritten for pexpect model.
- Git history consolidated: iterative pipeline commits collapsed to 4 clean
  milestones (initial site, CI hardening, site content, pipeline + CI + docs).

### Fixed
- `export HOME=/root` in SSM commands — SSM shell has no `$HOME`;
  `git config --global` fails without it.
- `set -eu` not `set -euo pipefail` — dash in SSM Run Command doesn't support `pipefail`.
- `AmazonSSMManagedInstanceCore` IAM policy attached to edcloud instance role.
- `hugo --destination ../site` — `--destination` is source-relative;
  `--destination site` wrote to `hugo/site/` not `site/` at repo root.
- 12 pexpect-specific issues resolved during VAX + PDP-11 debugging (UUE
  injection, ERASE/KILL chars, csh vs sh, CANBSIZ overflow, nroff BEL hang,
  stty echo, boot prompt patterns — see `PEXPECT-PIPELINE-SPEC.md`).

## [2026-02-21]

### Added
- Hugo site (`hugo/`) with PaperMod theme, dark mode, `www.jockeyholler.net`
  canonical URL, and Blog / Portfolio / Resume navigation (`/about/` aliases to Resume).
- Hugo-native resume page rendered from `hugo/data/resume.yaml` data source; custom layout
  (`hugo/layouts/_default/resume.html`) and CSS; PDF download at `/resume.pdf`.
- Portfolio page drawn from `hugo/data/portfolio.yaml` structured data; custom layout
  and CSS; Inter typography loaded via `extend_head.html`.
- Blog posts: "How I Use Changelogs as LLM Memory", "Why Do We Call Them Packets?",
  and "Strachey's Principle" (with local image assets).
- CI/deploy: GitHub Actions Hugo build pipeline with tag-triggered publish
  (`publish-fast-*`, `publish-vintage-*`); Python/Playwright gated on vintage mode only.
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
