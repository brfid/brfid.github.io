# Changelog

All notable changes to this project are documented in this file.

Format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
with date-based entries because this repository does not currently publish
semantic version tags.

## [Unreleased]

### Current State
- Hugo site at `hugo/`. PaperMod, dark mode, canonical URL `www.jockeyholler.net`.
  Content: `about.md`, `portfolio.md` (Work page), `resume.md` (Resume page),
  first post (`posts/changelog-as-llm-memory.md`). Builds clean locally.
- `hugo/data/resume.yaml` remains a copy of `resume.yaml` (symlink not followed by
  this Hugo data loader), but sync is now automated in CI (`deploy.yml` step) and
  available locally via `make sync-resume-data` / `make hugo-build`.
- `site/` is gitignored — Hugo (and vintage pipeline mkdir calls) generate it
  fresh in CI. Do not commit anything to `site/`.
- `deploy.yml` restructured: mode detected first; Python/quality checks/Playwright
  run only in `docker` (vintage) mode. Local publish path is Hugo-only.
- Vintage pipeline: Stage 4 now copies `brad.man.txt` to `hugo/static/brad.man.txt`
  (not `site/`), so Hugo owns that path in the build.
- edcloud lifecycle entrypoints (`aws-start.sh`, `aws-stop.sh`, `aws-status.sh`)
  now delegate to a shared Python CLI (`scripts/edcloud_lifecycle.py`) to reduce
  duplicated AWS instance-resolution logic while keeping shell wrappers for operators.
- DNS: jockeyholler.net apex A/AAAA → GitHub Pages IPs; www CNAME → brfid.github.io.
  Route 53 change C037890339C8W3JAICBDC (2026-02-21). CloudFront aliases removed.
- GitHub Pages custom domain (`www.jockeyholler.net`) is now set in repo UI settings.
- First Hugo-era publish is still pending to replace pre-Hugo content currently served.

### Active Priorities
- Commit `hugo/static/resume.pdf` (generated locally) so `/resume.pdf` is present on
  next deploy.
- Run first intentional Hugo-era deploy after custom-domain UI step is complete.

### In Progress
- None.

### Blocked
- None.

### Decisions Needed
- None. Key decisions already made:
  - Hugo + PaperMod, dark mode, `hugo/` subdir in repo root.
  - `www.jockeyholler.net` as canonical URL; apex redirects to www.
  - GitHub Actions + GitHub Pages for deployment (unchanged pattern).
  - Vintage pipeline stays as on-demand job (`publish-vintage` tag), not part
    of every Hugo content push.
  - brad@jockeyholler.net email deferred (SES DKIM records already in Route 53).

### Recently Completed
- Consolidated duplicated AWS lifecycle logic into `scripts/edcloud_lifecycle.py`
  and converted `aws-start.sh`, `aws-stop.sh`, and `aws-status.sh` into thin
  wrappers that call the shared Python implementation.
- Updated `scripts/publish-local.sh` tag format to `publish-fast-<timestamp>` so
  local helper-generated tags match `.github/workflows/deploy.yml` trigger patterns.
- Added automated resume data sync before Hugo build in CI:
  `cp resume.yaml hugo/data/resume.yaml` in `.github/workflows/deploy.yml`.
- Added local parity targets in `Makefile`: `sync-resume-data`, `hugo-build`,
  and `resume-pdf`.
- Generated `hugo/static/resume.pdf` locally via `make resume-pdf` without
  introducing extra static artifacts.
- Resume page (`hugo/content/resume.md`): Hugo-native resume from `resume.yaml` data.
  PaperMod chrome (dark mode, nav, fonts). Sections: Summary, Experience, Skills,
  Projects, Education, Publications. PDF download link at `/resume.pdf`.
  Layout: `hugo/layouts/_default/resume.html`. CSS: `hugo/assets/css/extended/resume.css`.
  Data: `hugo/data/resume.yaml` (copy of `resume.yaml`). Nav: Blog · Work · Resume · About.
  Builds clean; all sections verified in generated HTML.
- Portfolio page: added `docs.domaintools.com/llm/` link to LLM and AI Documentation section.
- Nav: renamed "Writing" → "Blog" in `hugo.toml`.
- README, WORKFLOWS, ARCHITECTURE updated for Hugo-first model.
- deploy.yml restructured: mode detected before Python setup; Python/quality
  checks/Playwright gated on `docker` mode only. Local publish skips all Python.
- `site/` gitignored; all tracked files removed from repo. Hugo (and vintage pipeline
  mkdir calls) generate `site/` fresh in CI. Repo is now clean of build artifacts.
- Portfolio page (`hugo/content/portfolio.md`) created from `portfolio.yaml` data;
  added "Work" nav item to `hugo.toml` menu (weight 15, between Writing and About).
- `deploy.yml` Stage 4: changed `brad.man.txt` destination from `site/` to
  `hugo/static/` so Hugo owns that path in the build.
- `deploy.yml`: added Hugo build step (runs for all modes before Pages upload);
  added submodule checkout and Hugo setup via `peaceiris/actions-hugo@v3 0.156.0`.
  Removed Python site generator step for local mode (Hugo replaces it).
- First post published: `hugo/content/posts/changelog-as-llm-memory.md`.
- Added thin `CLAUDE.md` at repo root (`@AGENTS.md` import).
- Hugo scaffold: `hugo/` at repo root, PaperMod theme (git submodule), dark
  mode default, `hugo.toml` configured, `about.md` and `posts/_index.md`
  created, `static/CNAME` set to `www.jockeyholler.net`. Hugo v0.156.0
  extended installed at `/usr/local/bin/hugo` (ARM64).
- Build command: `hugo --source hugo --destination ../site` (outputs into
  existing `site/` alongside pipeline artifacts).
- DNS migration: jockeyholler.net apex (A + AAAA) and www (CNAME) switched from
  CloudFront aliases to GitHub Pages. Orphaned `loopback.api` alias removed.
- Architectural decision: Hugo absorbs site templating/generation; vintage
  pipeline shrinks to build-artifact role only.
- AGENTS.md updated: mission, start-here order, commit cadence reflect Hugo.
- Initial changelog scaffold and historical backfill from commit history.

## [2026-02-21]

### Changed
- Migrated distributed deploy access from public-IP/key SSH to Tailscale SSH in
  `.github/workflows/deploy.yml` (`812ef8b`).
- Added `tailscale/github-action@v3` flow and switched remote operations to
  `ssh/scp ubuntu@edcloud` (`812ef8b`).
- Converted Stage 1 VAX build ambiguity from warn-and-continue to hard-fail
  behavior in deploy workflow (`812ef8b`).
- Updated VAX-side build script to consume `resume.vintage.yaml` end-to-end,
  matching uploaded artifact naming (`812ef8b`).
- Rationalized agent/doc guidance and cold-start docs (`812ef8b`).

### Fixed
- Restored `resume_generator` quality gates after refactor drift:
  - `mypy` typing issue in `resume_generator/normalize.py`.
  - `ruff`/`pylint` issues in `resume_generator/landing.py` and
    `resume_generator/vintage_stage.py` (`812ef8b`).

## [2026-02-18]

### Changed
- Refactored deploy pipeline to run console orchestration from edcloud repo
  checkout rather than SCPing scripts per step (`e25637c`).
- Updated project handoff/status docs for continuity across sessions (`36e18e7`).

### Fixed
- Restored uuencode console transfer path for edcloud single-host model,
  including deploy orchestration and logging path alignment (`23a81a3`).
- Fixed PDP-11 boot/image issues:
  - removed xq/ts dependencies where unnecessary,
  - corrected Boot prompt handling,
  - trimmed PDP-11 image deps for headless use (`242beb9`).

## [2026-02-15]

### Changed
- Migrated production lifecycle boundary from AWS multi-instance assumptions to
  edcloud single-host operations (`5c9037e`, `d92ba6f`).
- Renamed publish lane semantics from VAX-centric naming to distributed vintage
  naming while retaining legacy tag aliases (`d218871`).

## [2026-02-14]

### Added
- Enterprise logs viewer page and richer published log artifacts (`ec5b2b3`,
  `31a3048`).

### Changed
- Stabilized deploy lifecycle and aligned logs/docs for production publish
  behavior (`1a1f76a`, `5a58852`).
- Continued docs IA reorganization and retained historical evidence mapping
  (`6066061` and associated docs updates).

### Fixed
- Corrected module/workflow references after logging namespace shifts
  (`ab4c2ab`, `86138b4`, `2762cc1`).
- Resolved deploy YAML/script integration issues and heredoc/script extraction
  errors (`6835a49`, `fb6989a`).

## [2026-02-13]

### Added
- Uuencode console transfer path for VAX -> PDP-11 artifact relay (`6f481df`).
- Build-info/logging system enhancements and build metadata widget (`f8da60a`,
  `bb61d96`).
- Helper lifecycle scripts (`aws-start.sh`, `aws-stop.sh`, `aws-status.sh`)
  for operator convenience (`11502a3`).

### Changed
- Deployment quality gates and publish workflow behavior tuned for reliability
  (`37824c1`, `61b8601`).

### Fixed
- Multiple pipeline stability issues around instance handling, build/log
  directories, and console-transfer addressing (`d437c8b`, `6075ccf`,
  `d1c2d0d`, `f1f5482`, `112261c`).

## [2026-02-11]

### Added
- ARPANET-era research/prototyping components for KL10/PDP-10 and serial/FTP
  exploration (`ff09618`, `babac5b`).

### Changed
- Documentation and handoff updates to reflect evolving AWS + emulation status
  and blockers (`d9b2bf0`, `64a09e8`, related docs commits).

## [2026-02-08 to 2026-02-10]

### Added
- HI1/framing evidence collection, gating automation, and packet-capture-driven
  diagnostics for ARPANET authenticity workflows (`08b5870`, `874ec74`, and
  related series).

### Changed
- Documentation IA and cold-start guidance consolidation across repo/docs
  (`7ad890f`, `2500d34`, `a4d7ce3`).

## [2026-01-24 to 2026-01-29]

### Added
- Core static resume generation pipeline and GitHub Pages deployment model
  (`ef627da`, `6949ece`).
- Landing page, local vintage stage, manifest support, and CI/test structure
  (`2d0a40e`).
- Transcript replay support and test helpers (`efc45c2`).

### Changed
- Transfer strategy moved toward tape-first and image digest pinning for better
  reproducibility (`e6e549d`, `cb624f7`, `5ff2d1e`).

## [2025-09-05]

### Added
- Initial public release (`d729be3`).
