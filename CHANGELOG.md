# Changelog

All notable changes to this project are documented in this file.

Format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
with date-based entries because this repository does not currently publish
semantic version tags.

## [Unreleased]

### Current State
- Hugo remains the site generator (`hugo/`); the VAX↔PDP-11 path is an on-demand
  artifact pipeline only.
- Canonical active pipeline docs for cold starts are:
  `README.md` → `CHANGELOG.md` (`[Unreleased]`) → `docs/integration/INDEX.md` →
  `docs/integration/operations/VAX-PDP11-COLD-START-DIAGNOSTICS.md`.
- Historical context is now intentionally reduced:
  `docs/archive/DEAD-ENDS.md` is the retired-path registry and
  `docs/integration/CONTEXT-SOURCES.md` points to the retained high-signal evidence.
- Current runtime blocker: on clean edcloud rehearsals, Stage 1 can reach VAX
  console port `2323` after upload but may fail to reach a usable shell prompt,
  preventing `/tmp/vax-build-and-encode.sh` and blocking Stage 2/3.
- `hugo/static/brad.man.txt` is currently not present from a verified recent run;
  treat artifact regeneration as pending.

### Active Priorities
- Run the cold-start diagnostics runbook on edcloud and capture the full evidence
  bundle for the next Stage 1→3 attempt.
- Stabilize Stage 1 VAX shell-ready behavior in `scripts/edcloud-vintage-runner.sh`
  so build execution runs inside the guest consistently.
- After Stage 1 is stable, execute Stage 2/3 transfer (`uudecode` + `nroff`) and
  confirm artifact output into `hugo/static/brad.man.txt`.

### In Progress
- None.

### Blocked
- End-to-end VAX→PDP-11 transfer remains blocked until Stage 1 consistently reaches
  a shell prompt after the upload session.

### Decisions Needed
- None.

### Recently Completed
- Pruned low-value archive markdown from early false-positive/dead-end phases,
  retaining only a reduced evidence core for current debugging.
- Added `docs/archive/DEAD-ENDS.md` and `docs/integration/CONTEXT-SOURCES.md`
  to separate retired paths from still-useful historical context.
- Updated archive/integration indexes and cross-links so cold-start navigation
  routes directly to active runbooks first.
- Tightened `scripts/edcloud-vintage-runner.sh` readiness behavior so Stage 1
  explicitly fails with evidence when shell login is not established.
- Streamlined this `[Unreleased]` section to keep fresh-session handoff concise.

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
