# Changelog

All notable technical changes to this project are documented in this file.

This changelog tracks project architecture, tooling, infrastructure, build/deploy behavior,
runtime constraints, generated data paths, and repo workflow. It intentionally excludes routine
blog, portfolio, and resume content edits.

Format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), with date-based
entries because this repository does not currently publish semantic version tags.

## [Unreleased]

### Current State

- Hugo is the site generator; the vintage pipeline (VAX/PDP-11 via SIMH) normally produces four Hugo inputs: `hugo/static/brad.man.txt`, `hugo/static/brad.bio.txt`, `hugo/static/build.log.html`, and `hugo/data/bio.yaml`.
- **Deploy pipeline currently broken:** every `Publish Site` run since 2026-07-01 fails in `stage_b_vax`. Root cause identified; see Blocked.
- Site live at brfid.github.io. Pipeline last validated: `publish-vintage-20260302-151109`.
- Single build mode (vintage). `deploy.yml` triggers on push to `main` (skip with `[nopublish]` in commit message); `workflow_dispatch` is available for re-runs.
- `resume_generator.cli.build_html()` renders only the resume page (used by `make resume-pdf`); vintage orchestration is owned by pexpect scripts and `scripts/edcloud-vintage-runner.sh`.
- Landing page data hierarchy supports vintage-pipeline-driven `principal_headline` and `impact_highlights` (`resume.vintage.yaml` -> `brad.bio.txt` -> `hugo/data/bio.yaml`); `about` remains sourced from root `resume.yaml` during CI.
- **PDP-11 networking (permanent constraint):** the `unix` kernel has no Ethernet; inter-stage file transfer is host-mediated.
- Cold-start doc order: `README.md` -> this file -> `hugo/` (then `docs/integration/INDEX.md` only for vintage pipeline work).

### Active Priorities

- `scripts/vax_pexpect.py`'s `pexpect.EOF` handler (around line 413) discards `child.before` on exit, unlike the `TIMEOUT` handler which logs the last 500 bytes. This is why the CI logs for the current Stage B failures show only "SIMH process exited unexpectedly" with no console context — fix by logging `child.before` in the EOF branch too, so future crashes are diagnosable from CI logs alone without a manual SSM reproduction.

### In Progress

- None.

### Blocked

- **`deploy.yml` Stage B (`stage_b_vax`) fails on every run since 2026-07-01** (3 consecutive `Publish Site` failures as of `c13789b`). Confirmed unrelated to repo changes: diffed every pexpect-critical file (`Dockerfile.vax-pexpect`, `configs/vax780-pexpect.ini`, `scripts/vax_pexpect.py`, `scripts/simh_session.py`, `scripts/edcloud-vintage-runner.sh`) against the last known-good deploy (`17fc3ff`, 2026-05-31) — no changes. `build-images.yml` (which builds `ghcr.io/brfid/vax-pexpect`) hasn't run since 2026-05-19, so the image is byte-identical between the working and failing runs. Reproduced directly on the edcloud instance (`i-01884060fea188bcd`) via SSM, running the container manually with `--verbose`: host resources are clean (2 vCPU/1.9GB RAM, load average 0.00, 18GB disk free, no OOM/segfault in `dmesg`), but the guest 4.3BSD kernel itself panics during boot:

  ```text
  WARNING: clock lost 165 days -- CHECK AND RESET THE DATE!
  Automatic reboot in progress...
  /dev/ra0a: SUMMARY INFORMATION BAD (SALVAGED)
  Reboot request failed, PC: 8002A90C (MOVL 8003E628,R0)
  Goodbye
  ```

  The RA81 disk image's internal clock has drifted far enough from real time to trigger 4.3BSD's auto-fsck-and-reboot path, which crashes in-kernel before reaching the `login:` prompt. This is a guest-OS/disk-image issue, not host or CI infrastructure.

### Decisions Needed

- **How to fix the VAX guest clock/reboot crash blocking Stage B:** candidates are (a) rebuild/patch `Dockerfile.vax-pexpect` or the RA81 disk image to pin or advance the guest clock before the auto-reboot check fires, (b) have `vax_pexpect.py`'s `_boot()` detect and answer the clock-reset prompt interactively instead of hitting the crashing auto-reboot path, (c) check whether upstream `jguillaumes/simh-vaxbsd` has a fix. Needs a decision before Stage B can run reliably again.

## [2026-07-01]

### Changed
- Migrated site from jockeyholler.net custom domain to brfid.github.io. Removed CNAME, updated hugo.toml baseURL and label, updated portfolio/README/AGENTS references.

### Removed
- Removed the pre-Hugo static site generator left over from before Hugo took over the landing/portfolio pages: `resume_generator/{landing,portfolio,manifest,manpage}.py`, `cli.py`'s `build_site()`/`main()` and the `resume-gen` console script, and the orphaned `templates/{index,portfolio}.html.j2` and `build-info-widget.html`. `resume_generator.cli.build_html()` (resume page + PDF, used by `make resume-pdf`) and the vintage-pipeline parsers (`bio_yaml.py`, `vintage_yaml.py`) are unaffected.
- Removed dead vintage-pipeline files from the retired telnet/FTP/IMP era (superseded by the pexpect pipeline; see `docs/archive/DEAD-ENDS.md`): `vintage/machines/pdp11/{Dockerfile.pdp11,pdp11-boot.sh,pdp11_autoboot.exp}`, the IMP/ARPANET config tree under `vintage/machines/pdp11/configs/`, `vintage/machines/vax/{Dockerfile.ftp-server,Dockerfile.simh-ftp,vsftpd*.conf,vax-boot.sh}`, and `vintage/tools/extract_simh_tap.py`.
- Removed dead infrastructure: `infra/`, `test_infra/`, tag-based publish scripts, legacy Makefile targets (`publish`, `publish-vintage`, `publish_arpanet`, `test_docker`). Cleaned `.gitignore` and `conftest.py`.
- Removed the dead ARPANET archive binary (`docs/archive/arpanet/imp/h316ov`, a 1.1MB compiled ELF with no traceability value) and stale `vintage/machines/vax/examples/` scratch notes predating the current `bradman.c` YAML-subset parser.

## [2026-04-01]

### Changed
- Simplified repository documentation structure: `README.md` remains the cold-start entry point, `AGENTS.md` holds stable workflow constraints, `CHANGELOG.md` holds mutable technical state, and `docs/integration/INDEX.md` owns vintage-pipeline integration details.
- Removed stale top-level architecture/workflow documents after their current technical guidance moved into the source-of-truth docs.

## [2026-03-04]

### Added
- Added `principal_headline`/profile data support to the vintage resume pipeline so the VAX-generated bio artifact can carry landing-page hierarchy fields.
- Added tests for vintage YAML emission and bio parsing of the new profile fields.

### Changed
- Ignored generated `hugo/data/resume.yaml`; CI now copies root `resume.yaml` into Hugo data during deploy instead of tracking the generated copy.
- Updated landing-page data fallback order to prefer pipeline-generated bio data, then root resume data for fast/local builds.

## [2026-03-02]

### Added
- Added `resume.yaml` top-level `about` as the single source of truth for the landing-page narrative paragraph.
- Added `hugo/data/bio.yaml` `about` output for pipeline-agnostic local rendering.

### Changed
- Migrated deploy behavior to a single vintage-only build mode: pushes to `main` deploy by default; commit messages containing `[nopublish]` skip deploy; `workflow_dispatch` remains available for manual re-runs.
- Updated `bio_yaml.py` so `about` is read from root `resume.yaml` instead of being carried forward from existing `hugo/data/bio.yaml`.
- Reduced tracked `hugo/data/bio.yaml` to a minimal placeholder for local development.
- Updated README and integration docs for single vintage mode and generated bio data flow.
- Relaxed lint line-length policy from 100 to 120 chars for Ruff and pylint.
- Added `instance-status-ok` wait to `edcloud_lifecycle.py cmd_start` for parity with deploy workflow behavior.
- Scoped `ci.yml` to `main`; `test.yml` owns PR and feature-branch quality checks.
- Aligned pylint scope to `resume_generator tests` in workflows.

### Removed
- Removed unused `host_logging` package and associated tests.
- Removed unused `resume_generator/contact_json.py`.
- Removed unused `docker>=7.0` dependency.
- Removed legacy `resume_generator` vintage/ARPANET orchestration modules and flags.

### Fixed
- Narrowed `resume_generator/bio_yaml.py` exception handling to `json.JSONDecodeError`.

## [2026-03-01]

### Added
- Added VAX bio mode: `bradman.c -mode bio` emits `brad.bio.txt` with name, label, summary, and contact data.
- Added `resume_generator/bio_yaml.py` to parse `brad.bio.txt` into `hugo/data/bio.yaml` with build provenance from `build.log.html`.
- Added landing-page rendering for pipeline-generated bio data and provenance.
- Added machine-boundary HTML build log extraction from edcloud runner output.
- Added shared SIMH session utilities, UUE spool validation, SIMH SHA pinning, and GitHub Actions image-cache workflow.

### Changed
- Moved VAX -> PDP-11 transfer to UUCP framing: VAX uuencodes `brad.1`, host routes spool, PDP-11 decodes it before `nroff`.
- Added ASCII normalization in `resume_generator/normalize.py`; replaced deprecated `uu` module usage with `binascii.b2a_uu`.
- Refactored pexpect scripts to use shared session helpers.

## [2026-02-28]

### Added
- Added pexpect-based vintage pipeline: `scripts/vax_pexpect.py` drives VAX 4.3BSD to compile/run `bradman.c`; `scripts/pdp11_pexpect.py` drives PDP-11 2.11BSD to run `nroff -man`.
- Added `scripts/edcloud-vintage-runner.sh` as the single orchestration entry point for edcloud pipeline execution and artifact extraction.
- Added pexpect Docker configs for VAX and PDP-11 under `vintage/machines/`.
- Added `docs/integration/operations/PEXPECT-PIPELINE-SPEC.md` as the active implementation spec.
- Added `docs/archive/DEAD-ENDS.md` as the registry of retired pipeline approaches.
- Added Hugo portfolio and resume page layouts, CSS, and structured data files.

### Changed
- Retired screen/telnet/sleep console orchestration in favor of pexpect over stdin/stdout.
- Moved AWS auth from OIDC to static GitHub repo secrets for the deploy workflow.
- Updated navigation so `/portfolio/` is a first-class site section and `/about/` aliases to `/resume/`.
- Updated `secret-scan.yml` to scan full history with `GITLEAKS_LOG_OPTS: --all --no-merges`.
- Removed stale archive documents and rewrote integration docs around the pexpect model.
- Consolidated git history into clean public milestones.

### Fixed
- Exported `HOME=/root` in SSM commands so `git config --global` works under SSM shell.
- Used `set -eu` instead of `set -euo pipefail` for SSM shell compatibility.
- Attached `AmazonSSMManagedInstanceCore` permissions to the edcloud instance role.
- Corrected Hugo destination handling to `--destination ../site` because destination paths are source-relative.
- Documented and resolved VAX/PDP-11 pexpect failure modes including UUE injection, terminal erase/kill chars, csh vs sh behavior, CANBSIZ overflow, nroff BEL hang, stty echo, and boot prompt matching.

## [2026-02-21]

### Added
- Added Hugo site foundation under `hugo/` with PaperMod, dark mode, `www.jockeyholler.net` canonical URL, and GitHub Pages CNAME.
- Added Hugo-native resume and portfolio rendering from YAML data sources.
- Added GitHub Actions Hugo build/deploy workflow with publish-tag triggers.
- Added initial vintage artifact pipeline integration: VAX compiles and encodes resume data, PDP-11 typesets output with `nroff`, and Hugo serves the generated artifact.
- Added edcloud lifecycle helper scripts and Python CLI.
- Added initial research archive structure for exploratory emulation notes.

### Changed
- Established Hugo as the full-site generator and scoped vintage computing to artifact generation.
- Centralized edcloud lifecycle management in `scripts/edcloud_lifecycle.py` with thin shell wrappers.
- Refactored deploy workflow to run console orchestration from an edcloud checkout.
- Updated PDP-11 readiness checks from one-shot TCP probes to log-signal gating to avoid TTI disconnect/reboot loops.

## [2026-02-14]

### Added
- Added VAX <-> PDP-11 uuencode console-transfer prototype and validated end-to-end artifact flow on single-host edcloud with Docker Compose.
- Added cold-start diagnostics runbook for serialized console sessions and log-based readiness gating.
- Added edcloud single-host deployment model with VAX and PDP-11 containers co-located on one EC2 instance.

### Changed
- Evaluated ARPANET IMP, KL10/KS10 TOPS-20, and Chaosnet emulation paths as candidate pipeline stages; documented findings and convergence decision in the archive.
