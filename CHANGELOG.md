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
- `deploy.yml` now uses a minimal control-plane model:
  - local mode builds Hugo only,
  - vintage mode uses AWS OIDC + EC2 start/stop + single SSM invocation.
- Deploy triggers are now limited to `publish-fast-*` and `publish-vintage-*`.
- Vintage pipeline: Stage 4 now copies `brad.man.txt` to `hugo/static/brad.man.txt`
  (not `site/`), so Hugo owns that path in the build.
- Vintage orchestration is centralized in `scripts/edcloud-vintage-runner.sh`;
  GitHub Actions no longer embeds multi-stage console choreography.
- `scripts/edcloud-vintage-runner.sh` now applies standard runtime cleanup on exit
  (screen session cleanup, `docker compose down --remove-orphans --volumes`,
  run-scoped temp file removal) with `KEEP_RUNTIME=1` debug override.
- Vintage post-deploy EC2 stop is now best-effort/non-blocking so publish result is
  not coupled to teardown transient failures.
- edcloud lifecycle entrypoints (`aws-start.sh`, `aws-stop.sh`, `aws-status.sh`)
  now delegate to a shared Python CLI (`scripts/edcloud_lifecycle.py`) to reduce
  duplicated AWS instance-resolution logic while keeping shell wrappers for operators.
- DNS: jockeyholler.net apex A/AAAA → GitHub Pages IPs; www CNAME → brfid.github.io.
  Route 53 change C037890339C8W3JAICBDC (2026-02-21). CloudFront aliases removed.
- GitHub Pages custom domain (`www.jockeyholler.net`) is now set in repo UI settings.
- First Hugo-era publish is still pending to replace pre-Hugo content currently served.
- PDP-11 console instability root cause identified in current single-host edcloud runtime:
  one-shot readiness probes (`echo > /dev/tcp/...:2327`) can trigger SIMH TTI
  disconnect/reboot behavior during early boot. Console handling now avoids probe-driven
  connect/disconnect for PDP-11 startup checks.
- Cold-start diagnostics runbook added at
  `docs/integration/operations/VAX-PDP11-COLD-START-DIAGNOSTICS.md` to standardize
  serialized console handling, log-based PDP-11 readiness gating, and minimum evidence
  bundle capture for Stage 1→3 rehearsals.
- Git history for `hugo/content/posts/why-do-we-call-them-packets/index.md` was rewritten
  so the current wording is now embedded in the original post-introducing commit on `main`
  (no compatibility chain retained).

### Active Priorities
- Commit `hugo/static/resume.pdf` (generated locally) so `/resume.pdf` is present on
  next deploy.
- Run first intentional Hugo-era deploy after custom-domain UI step is complete.
- Validate end-to-end `publish-vintage-*` run under the new OIDC + SSM bootstrap path.

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
- Added standard/simple teardown behavior for vintage runs:
  - runner-level exit trap cleanup in `scripts/edcloud-vintage-runner.sh`,
  - post-deploy best-effort EC2 stop semantics in `.github/workflows/deploy.yml`.
- Refactored vintage deploy architecture to a clean control-plane/execution-plane split:
  GitHub Actions now performs AWS bootstrap only (OIDC + start/stop + SSM), and
  edcloud-side orchestration is centralized in `scripts/edcloud-vintage-runner.sh`.
- Replaced SSH/Tailscale-driven deploy choreography in `.github/workflows/deploy.yml`
  with single-command SSM invocation and marker-based artifact extraction into
  `hugo/static/brad.man.txt`.
- Updated active docs (`README.md`, `WORKFLOWS.md`, `ARCHITECTURE.md`,
  `docs/integration/INDEX.md`, `docs/vax/README.md`) to match the new boundary and
  remove stale `resume.vax.yaml`/`site/brad.man.txt` terminology.
- Added concise repository contribution/hygiene guidance for public-readiness:
  `CONTRIBUTING.md`.
- Added automated secret scanning workflow `.github/workflows/secret-scan.yml`
  using `gitleaks/gitleaks-action@v2` with full history checkout.
- Updated `WORKFLOWS.md` to document the new secret-scan lane and its purpose.
- Restored Hugo PaperMod theme tracking as a git submodule (`hugo/themes/PaperMod`)
  after it was present locally but missing from the index, which caused CI local-mode
  publish runs to fail at `hugo --source hugo --destination ../site` with
  `module "PaperMod" not found`.
- Hardened publish trigger safety by removing bare fixed tags from
  `.github/workflows/deploy.yml` (`publish`, `publish-fast`, `publish-vintage`,
  `publish-vax`, `publish-docker`) and keeping wildcard-only publish patterns.
- Updated publish docs in `README.md`, `WORKFLOWS.md`, and `ARCHITECTURE.md` to
  use unique tag patterns (`publish-fast-*`, `publish-vintage-*`) only.
- Fixed PDP-11 container boot wrapper readiness behavior (`vintage/machines/pdp11/pdp11-boot.sh`)
  to avoid localhost console probe connections that caused SIMH TTI disconnect/reboot loops.
- Updated distributed deploy Stage 2 readiness in `.github/workflows/deploy.yml` to avoid
  one-shot `/dev/tcp/127.0.0.1/2327` probes; readiness now uses container-up + SIMH
  listener log signal checks.
- Revalidated PDP-11 smoke boot and console persistence locally after fixes:
  boot reaches `2.11 BSD UNIX` prompt, interactive session remains attached, `/usr` mounts,
  and `/usr/bin/uudecode` + `/usr/bin/nroff` are present.
- Added VAX↔PDP-11 cold-start diagnostics runbook
  (`docs/integration/operations/VAX-PDP11-COLD-START-DIAGNOSTICS.md`) and wired it into
  docs indexes for faster, more productive diagnostic resumes.
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
