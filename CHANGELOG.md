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
- Deploy triggers are hardened to unique publish tag patterns only (`publish-fast-*`,
  `publish-vintage-*`, plus legacy wildcard aliases) so stale fixed tags cannot
  accidentally republish old commits.
- Vintage pipeline: Stage 4 now copies `brad.man.txt` to `hugo/static/brad.man.txt`
  (not `site/`), so Hugo owns that path in the build.
- edcloud lifecycle entrypoints (`aws-start.sh`, `aws-stop.sh`, `aws-status.sh`)
  now delegate to a shared Python CLI (`scripts/edcloud_lifecycle.py`) to reduce
  duplicated AWS instance-resolution logic while keeping shell wrappers for operators.
- DNS: jockeyholler.net apex A/AAAA → GitHub Pages IPs; www CNAME → brfid.github.io.
  Route 53 change C037890339C8W3JAICBDC (2026-02-21). CloudFront aliases removed.
- GitHub Pages custom domain (`www.jockeyholler.net`) is now set in repo UI settings.
- Hugo site is live at `www.jockeyholler.net`; multiple `publish-fast-*` tags have been pushed (latest: `publish-fast-20260222-2309`). Pre-Hugo content replaced.
- PDP-11 container has a **second root cause** beyond the probe issue: SIMH's
  `set console telnet=2327` blocks the simulation until a client connects. Without
  a client within ~30 seconds, SIMH times out (`Console Telnet connection timed out`)
  and the container exits. This was happening on every cold start. The `BUFFERED`
  SIMH option is not supported in the build used (v4.0-0 commit 627e6a6b).
- Auto-boot handler introduced: `vintage/machines/pdp11/auto-boot.exp` (expect
  script), `expect` and `telnet` packages added to `Dockerfile.pdp11`, and
  `pdp11-boot.sh` updated to start the handler in background. Handler connects to
  the console, answers the `Boot:` prompt, detects single-user shell (`erase, kill
  ^U`), sends `exit` to proceed to multi-user mode. Boot reaches multi-user `/etc/rc`
  phase successfully. **Remaining issue**: the 180-second expect timeout fires while
  `/etc/rc` + fsck complete (slow on emulated PDP-11), causing auto-boot to
  disconnect mid-boot, triggering the SIMH TTI error and container exit. Fix is to
  increase post-exit timeout to ≥600s and verify SIMH handles disconnect gracefully
  once 2.11BSD is fully in multi-user mode. Changes are committed; container is
  on `main` but PDP-11 does not yet reach a stable running state.
- Cold-start diagnostics runbook added at
  `docs/integration/operations/VAX-PDP11-COLD-START-DIAGNOSTICS.md` to standardize
  serialized console handling, log-based PDP-11 readiness gating, and minimum evidence
  bundle capture for Stage 1→3 rehearsals.
- Git history for `hugo/content/posts/why-do-we-call-them-packets/index.md` was rewritten
  so the current wording is now embedded in the original post-introducing commit on `main`
  (no compatibility chain retained).

### Active Priorities
- Rehearse full distributed vintage Stage 1-3 flow on edcloud with updated non-probing
  PDP-11 readiness checks to confirm end-to-end stability.
- Migrate blog posts: author and publish additional posts to build out the blog
  as a portfolio and thought-leadership signal for senior IC technical writing roles.

### In Progress
- PDP-11 auto-boot: fix `auto-boot.exp` post-exit timeout (increase from 180s to
  ≥600s), then verify container reaches stable multi-user login: and SIMH handles
  disconnect cleanly. Once verified, confirm Stage 2/3 CI flow can connect.
  Key files: `vintage/machines/pdp11/auto-boot.exp`, `pdp11-boot.sh`,
  `Dockerfile.pdp11`. Docker root on edcloud is `/opt/edcloud/state/docker`.

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
- First Hugo-era deploy: `publish-fast-20260221-1950` through `publish-fast-20260222-2309`
  pushed; Hugo site now live at `www.jockeyholler.net` replacing pre-Hugo content.
  `hugo/static/resume.pdf` committed and served at `/resume.pdf`.
- Resume and site positioning pass: removed "Principal" level claim from label and
  about page; rewrote summary to lead with strategy ownership; added greenfield/from-scratch
  framing to DomainTools strategy bullet; added SME interviewing highlight to UCLA role;
  strengthened MCP bullet and DDT project description; added `certifications` section
  to `resume.yaml` and `resume.html`; added UCLA PhD graduation year (2011); wrapped
  phone in `tel:` link; strengthened hugo.toml meta description.
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
