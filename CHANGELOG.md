# Changelog

All notable changes to this project are documented in this file.

Format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
with date-based entries because this repository does not currently publish
semantic version tags.

## [Unreleased]

### Current State
- Hugo is the site generator (`hugo/`); the vintage pipeline (VAX/PDP-11 via SIMH)
  is an on-demand artifact generator — it feeds `hugo/static/brad.man.txt`,
  `hugo/static/brad.bio.txt`, `hugo/static/build.log.txt`, and `hugo/data/bio.yaml`.
- **Pexpect pipeline CI-VALIDATED end-to-end (2026-02-28, tag `publish-vintage-20260228-203550`).**
  Stage B (VAX) → Stage A (PDP-11) → `brad.man.txt` → Hugo build → GitHub Pages deploy.
  All steps green; site live at www.jockeyholler.net.
- **Architecture decision (2026-02-28):** screen/telnet/sleep orchestration retired;
  pexpect is the permanent replacement.
- **PDP-11 networking constraint (permanent):** The `unix` kernel has no working
  Ethernet. File transfer between stages is host-mediated.
- Cold-start doc order: `README.md` → this file → `docs/integration/INDEX.md`
  → `docs/integration/operations/PEXPECT-PIPELINE-SPEC.md`.
- **GitHub Pages source set to GitHub Actions (2026-02-28).** Pages previously
  reverted to legacy (Jekyll) mode when repo was made private; corrected by
  switching source to GitHub Actions in repo Settings → Pages UI.

### Active Priorities
- None.

### In Progress
- None.

### Blocked
- None.

### Decisions Needed
- None.

### Recently Completed
- **2026-03-01:** UUCP framing (VAX uuencodes `brad.1` itself; host routes spool;
  PDP-11 decodes), ASCII conversion moved to `resume_generator/normalize.py`,
  deprecated `uu` module replaced with `binascii.b2a_uu`. CI-validated
  (`publish-vintage-20260301-192822`).
- **2026-03-01:** Bio mode (`-mode bio` in `bradman.c`), UTC timestamps on all
  pexpect `_log()` calls, machine-boundary build log, bio/log artifact extraction
  in `deploy.yml`. CI-validated (`publish-vintage-20260301-194153`).
- **2026-03-01:** Bio wired into Hugo landing page via `hugo/data/bio.yaml`.
  Pipeline parses `brad.bio.txt` → `bio.yaml` in "Generate bio data for Hugo" step
  (deploy.yml, vintage mode only). Static fallback in repo for local dev / fast
  builds. `hugo/layouts/partials/home_info.html` override renders name, label,
  summary, and optional build log link from `site.Data.bio`.

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
