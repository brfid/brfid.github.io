# Changelog

All notable changes to this project are documented in this file.

Format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
with date-based entries because this repository does not currently publish
semantic version tags.

## [Unreleased]

### Current State
- `CHANGELOG.md` `[Unreleased]` is the primary mutable LLM memory section.
- The legacy status file has been retired.

### Active Priorities
- None.

### In Progress
- None.

### Blocked
- None.

### Decisions Needed
- None.

### Recently Completed
- Initial changelog scaffold and historical backfill from commit history and
  retained status/session notes.
- Documentation model split introducing a dedicated current-state file and
  `CHANGELOG.md` as historical/cold-start record.
- Initial `[Unreleased]` memory sections (`Planned`, `Decisions Needed`) added
  before moving to the fixed custom schema.
- Defined and documented fixed `[Unreleased]` memory subcategories in `AGENTS.md`.
- Aligned `README.md` and `docs/INDEX.md` to use `CHANGELOG.md` `[Unreleased]`
  as the primary mutable state source.
- Converted the legacy status file into a compatibility pointer to the changelog
  memory schema, then removed it.
- Replaced active-doc references (`AGENTS.md`, `ARCHITECTURE.md`,
  `docs/pdp/INDEX.md`, `docs/integration/INDEX.md`) with `CHANGELOG.md`
  `[Unreleased]` guidance.
- Migrated legacy docs and retained history notes to `CHANGELOG.md` references
  where they describe current-state pointers.

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
