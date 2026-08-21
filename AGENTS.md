# Agent notes (repo workflow)

Purpose: this file defines agent workflow constraints only. Setup/quickstart belongs in `README.md`; mutable project memory belongs in `STATUS.md`; release history lives in `git log`.

## Mission (stable constraints)

- Build and publish a Hugo-based personal site at brfid.github.io.
- Hugo owns the published site surface. The vintage pipeline (VAX/PDP-11 via SIMH) remains an artifact generator feeding Hugo inputs, not a site generator.
- The vintage pipeline is a technical signal, not the product. Richer content surfaces may return when their private source copy is ready.
- Prefer clear, evidence-backed updates over broad speculative changes.
- Keep infrastructure orchestration minimal in this repo. As of 2026-07-25 there is no external execution host: the AWS/edcloud account was decommissioned, and the vintage pipeline is to run on GitHub-hosted `ubuntu-latest` runners and/or local Docker. Do not reintroduce a cloud dependency for the publish path.

## Start-here order (for new LLM sessions)

`README.md` is the cold-start entry point (infrastructure boundary, source-of-truth map, quickstart).

1. `README.md`
2. `STATUS.md`
3. `hugo/` (Hugo site root — theme, content, config)
4. `docs/integration/INDEX.md` (only if touching vintage pipeline internals)
5. `~/src/career/STATUS.md` (only if touching site reactivation, resume surfaces, or any phase-gated work)

## Source-of-truth map

- Current mutable state / active queue: `STATUS.md`
- Strategic arc / sequencing / posture (in the private `~/src/career` repo): `~/src/career/STATUS.md`. This repo's `STATUS.md` is operationally downstream of it; do not duplicate strategic state here.
- Change history / milestone evidence: `git log` (clean, intention-revealing commits)
- Integration active path + spec: `docs/integration/INDEX.md`
- Implementation spec (pexpect pipeline): `docs/integration/operations/PEXPECT-PIPELINE-SPEC.md`
- Explicit retired/blocked path registry: `docs/archive/DEAD-ENDS.md`

Do not duplicate mutable status in this file; update `STATUS.md` instead.

## Resume source

- `resume.yaml` is the canonical, single bio source file. This repository is public, so treat every value in it as published information. It drives the resume HTML page and its PDF, and `basics.summary` also drives the landing bio.
- Public resume data never contains Brad's phone number. A local, gitignored `resume.private.yaml` may supply `basics.phone`; only the explicit `make resume-pdf-application` target may read it, and that target writes `local/bradley-fidler-resume.pdf` outside the web root. `make resume-pdf`, `make resume-pdf-public`, `make preview`, and the production deploy must never read the overlay. The Hugo resume HTML and `site/resume.pdf` must always remain phone-free. Copy `resume.private.example.yaml` when setting up a fresh checkout.
- `hugo/data/resume.yaml` is a generated, gitignored copy made by `make sync-resume-data`. Never edit it directly.
- Do not keep alternate or dormant resume copy in tracked examples, portfolio data, or generated artifacts. Rejected wording belongs only in the offline pre-rewrite backup and must never be merged or copied back into the public repository.
- Double-quote human-authored string values that contain a colon, especially `label`, `summary`, and `highlights` values. An unquoted colon can make PyYAML interpret prose as a mapping instead of a string without producing a useful failure at the point of edit.
- `basics.summary` is deliberately shared by the landing page, resume Summary, and PDF until those surfaces need different copy. Do not add a parallel top-level blurb without an explicit decision to split them again. `site.yaml` owns only the public identity (name, headline) and links.
- Do not add a certifications entry for the intacs Automotive SPICE Provisional Assessor examination. Brad passed the examination at Romeo Power, but the employer did not file the fee and the credential was never issued. Claim only the examination passed, as the Romeo Power highlight does.

## Memory model

`STATUS.md` holds project memory in this repo. Strategic arc (sequencing, posture, when/why phases run) lives upstream in `~/src/career/STATUS.md`; this repo's `STATUS.md` carries operational state and points back there at the seam.

- `STATUS.md` holds mutable operational state for the site and pipeline, plus active operational priorities, using fixed subcategories in this exact order:
  1. `Current State`
  2. `Posture`
  3. `Goals`
  4. `Now`
  5. `Next`
  6. `Blocked`
  7. `Open decisions`

  Keep every subcategory present; if empty, use `- None.`. Section headers mirror the upstream `~/src/career` repo's `STATUS.md` so the shape is recognizable across the boundary; content scope differs (this file is operational, career's is strategic).

`STATUS.md` holds forward-looking/current state only — not a running log of finished work. Completed work is discoverable from `git log` (this repo keeps clean, intention-revealing commits; see Git discipline) and doesn't need restating except where it changes `Current State`.

Update rules:

1. On start/end of a task, update `Now`.
2. On new queued work, update `Goals` or `Next`.
3. On external dependency or waiting condition, update `Blocked`.
4. On user choice needed, update `Open decisions`.
5. On architecture/runtime truth changes, update `Current State`.
6. Do not record routine blog content authoring/editing/import work in `STATUS.md`; reserve updates for repo workflow, infrastructure, tooling, and runtime-status changes.

## Local dev

Run `make preview` from the repo root to preview locally. It syncs the site and resume data, builds the production-equivalent public resume HTML and phone-free `site/resume.pdf`, then runs Hugo with that output directory so both `/resume/` and `/resume.pdf` work at `http://localhost:1313/`. `make preview-public` is a compatibility alias with the same privacy boundary. Files under `hugo/` live-reload. Restart either command after changing `resume.yaml`, or after layout and CSS changes when the PDF itself also needs to be regenerated. Set `PREVIEW_PORT` to use a port other than 1313. The operator node is an arm64 Mac with Hugo and Docker installed. No staging environment or remote preview URL is needed.

During resume work, keep `make preview` running; regenerate and inspect both `/resume/` and `/resume.pdf` after meaningful source or print-layout changes. When the application PDF also needs verification, run `make resume-pdf-application` and inspect the generated file under `local/`, then restart the preview because the application build cleans `site/`. Create local milestone commits, and never push without Brad's explicit approval.

Local landing-page builds need two things that CI does for itself: `cp site.yaml hugo/data/site.yaml` (`make sync-site-data`) and an initialized `hugo/themes/PaperMod` submodule. `make preview` also syncs `resume.yaml` because it serves the resume and its generated PDF.

Prototype design and theme changes in the Hugo site, never as a free-standing HTML mockup (which drifts from PaperMod's real markup and cascade and tempts theme-fighting hacks). Work only through standard PaperMod mechanisms: its CSS variables, `hugo/assets/css/extended/*.css`, self-hosted fonts in `hugo/static/fonts/`, and repo-owned partials (`home_info.html`, `extend_head.html`); review the local build. To preview the build-provenance line without running the vintage pipeline, add a throwaway gitignored `hugo/data/bio.yaml` with `build_log`, `build_id`, and `build_run_url`.

Keep the entire site out of search indexes until Brad explicitly reverses that decision. Every Hugo-rendered page and the generated vintage build log must carry the shared `noindex, nofollow, noarchive, nosnippet, noimageindex` directive, Hugo must not emit a sitemap, and the production verifier must enforce both. Do not use `Disallow: /` in `robots.txt`: crawlers need to fetch HTML to observe `noindex`. Use robots rules only for non-HTML artifacts that cannot carry a meta tag.

## Virtualenv-only

- Use the repo-local venv at `.venv/` for all Python commands.
- Do not install anything globally or modify system Python.

## Commit cadence

Commit at significant milestones so the history stays readable and bisectable. Examples:

- Hugo scaffold complete (theme, config, first content)
- Landing page / design milestone complete
- New post published or portfolio entry added
- Deploy workflow changes (Hugo build step, Pages config)
- Vintage pipeline changes (SIMH stages, artifact format)

Pre-commit checks are optional by default in this repo workflow.

- Run `make check` when a task or reviewer explicitly requests validation.

## Git discipline (public-repo baseline)

- Keep `main` linear and readable: small, intention-revealing commits; no WIP commits.
- Prefer additive fixes over history rewrites; rewrite shared `main` history only when explicitly requested by the operator.
- The resume-reactivation release intentionally replaces the old public history with a clean root so rejected resume copy is no longer reachable through repository refs. Never merge, rebase, tag, or push from the offline pre-rewrite backup or any pre-rewrite commit.
- Do not push to GitHub unless the operator explicitly requests a push.
- Before pushing, check for accidental secret material in changed files and avoid committing generated artifacts (`site/`, `build/`, `hugo/public/`, `.venv/`).

## No accidental publishing

- GitHub Pages deploy triggers on every push to `main`. To skip a deploy, include `[nopublish]` anywhere in the commit message. `workflow_dispatch` is available for manual re-runs.
- Production publishes `/resume/`, its `/about/` alias, and `/resume.pdf`. Deployment must fail if any is absent, if the navigation links are missing, if the HTML or PDF contains a telephone number, or if the private application PDF appears anywhere under the web root.

## Do-not-break constraints

- Keep Python execution in `.venv/` only.
- Avoid global/system package installs.
- Do not reintroduce screen/telnet/sleep-based console orchestration; the pexpect approach supersedes it.
- Keep `scripts/edcloud-vintage-runner.sh` bind-mounting the checkout's VAX/PDP-11 pexpect scripts and `simh_session.py` over the copies baked into the cached GHCR images. The images provide emulator infrastructure; the checked-out repository owns the orchestration code executed by CI.

## Expected output shape for implementation work

- Summarize changes by file path.
- Include validation performed (or explicitly state none performed).
- If docs paths changed, update relevant indexes (`docs/integration/INDEX.md` for pipeline docs).

## Runtime-status boundary

- Keep long-lived constraints here; record changing implementation status in `STATUS.md`.
- Prefer referencing current paths in code/docs (for example `vintage/machines/vax/bradman.c`).
