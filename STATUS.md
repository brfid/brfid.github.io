# Status

Mutable operational state for the site, pipeline, and resume surfaces. **Strategic arc (sequencing, posture, when/why phases run) lives upstream in `~/src/career/STATUS.md`;** this file owns the *how* and points back there at the seam. Section headers are shared so the shape is recognizable across the boundary. Release history lives in `git log`; long-lived workflow constraints live in `AGENTS.md`.

## Current State

- The public build publishes the landing page, Blog navigation, `/posts/`, `/index.xml`, `/posts/index.xml`, Resume navigation, `/resume/`, its `/about/` alias, and the phone-free `/resume.pdf`; JSON, taxonomy, and sitemap outputs remain absent. The global header contains only Blog and Resume, identity and profile links stay on the landing page, RSS appears on the Blog index, the PDF download appears on the Resume page, and source/build provenance lives in the footer. The Blog section publishes two posts, `/posts/stracheys-principle/` and `/posts/doc-rot-maintenance-gap/`. The repository is public, GitHub Pages uses the Actions deployment mode with HTTPS enforced, and `site.yaml` is the source for the public name, headline, and labeled profile links (`resume.yaml`'s `basics.summary` supplies both the landing bio and resume Summary). Every HTML surface carries a site-wide `noindex` directive, `robots.txt` blocks non-HTML artifacts including the PDF and feeds, and the production build emits no sitemap.
- The remaining former Hugo posts and the packet-history image assets still live as drafts under the private `~/src/career/essays/` tree. Public branches and tags have been rewritten so their histories contain neither the former post sources and assets nor tracked generated-site copies. The public `hugo/content/posts/` tree contains the Blog section index and the published `stracheys-principle/` and `doc-rot-maintenance-gap/` bundles; further approved post copy returns as page bundles, and the draft bundle archetype keeps work out of production until explicitly published.
- **The resume uses one Hugo render for local and public surfaces.** `resume.yaml` syncs to the gitignored `hugo/data/resume.yaml`; Hugo renders `/resume/` and Playwright prints it to `site/resume.pdf`. The PDF is tagged for accessibility and carries a heading outline. `make resume-pdf`, `make resume-pdf-public`, `make preview`, `make preview-public`, and production all build the phone-free public PDF. Only `make resume-pdf-application` reads the separate gitignored `resume.private.yaml`, and it writes the phone-bearing application PDF to `local/bradley-fidler-resume.pdf` outside the web root; HTML never carries it. The resume no longer touches the vintage pipeline, and the retired PDP-11 man-page renderer is absent. Dormant portfolio data containing obsolete resume copy has been removed while the portfolio page remains suppressed. The approved application resume renders as a three-page PDF.
- **The vintage pipeline runs on GitHub-hosted `ubuntu-latest` runners** (ported 2026-07-25, same day the AWS/edcloud host was decommissioned). `deploy.yml` invokes `scripts/edcloud-vintage-runner.sh` directly on the runner; control plane and execution plane are now the same machine and the publish path touches no external infrastructure. Cached GHCR images provide the emulators and disk images, but the runner bind-mounts the checked-out pexpect scripts and shared session helper over their baked copies so CI cannot execute stale orchestration. Per `AGENTS.md`, do not reintroduce a cloud dependency here.
- The vintage pipeline is bio-only: `site.yaml` identity plus `resume.yaml` `basics.summary` → `build/vintage/bio.vintage.yaml` → the VAX composes the bio as troff (`bradman.c`) → the PDP-11 fills and justifies it with `nroff` → `brad.bio.txt` → `hugo/data/bio.yaml`. The raw bio stays inside `build/vintage/`; only the rendered homepage and build log publish. Missing or mismatched bio output fails validation. The summary reaches the page as humanist prose: the VAX composes it and the PDP-11 fills and justifies it, then `bio_yaml.py` collapses that fixed-width justification back to flowing single-spaced sentences, which the landing template (`home_info.html`, `.bio-summary`) sets in the Newsreader serif. The machine provenance shows in the footer's VAX/PDP-11 build-log link, not in the letterforms.
- The publish path requires and exposes a curated, responsive VAX/PDP-11 build log with Home and source routes, links the landing page to the exact enclosing GitHub Actions run, and emits a non-empty `pipeline-status.json` with build and stage metadata. Unknown Hugo routes render a themed recovery page with Home, Blog, and Resume links.
- Pipeline runtime on a hosted runner is **~3m20s** (4 vCPU / 15 GiB / amd64), measured across two runs. `deploy.yml`'s 70-minute job timeout is therefore very generous; it is left as-is because the failure it bounds is a SIMH console hang, not slow arithmetic.
- Single build mode (vintage). `deploy.yml` triggers on push to `main` (skip with `[nopublish]` in commit message); `workflow_dispatch` is available for re-runs.
- `resume_generator.pdf.build_pdf()` serves the built site while writing a PDF to an explicit output path, which keeps the private application PDF outside the served tree. Production calls the phone-free `make resume-pdf-public` target and verifies the HTML, alias, navigation, public PDF, absence of telephone data, and absence of the private application PDF before uploading the Pages artifact. `resume_generator/normalize.py` is now just `to_ascii` for the vintage bio. Vintage orchestration is owned by pexpect scripts and `scripts/edcloud-vintage-runner.sh`.
- **PDP-11 networking (permanent constraint):** the `unix` kernel has no Ethernet; inter-stage file transfer is host-mediated.
- Cold-start doc order: `README.md` -> this file -> `hugo/` -> `~/src/career/STATUS.md` when work touches the dormant essays or resume surfaces -> `docs/integration/INDEX.md` only for vintage pipeline work.

## Posture

- None.

## Goals

1. Publish a selected essay only after its copy is ready in the private career repo; leave the portfolio suppressed until its material receives the same review.
2. Optional: publish multi-arch vintage images and add a `make vintage` target so the full pipeline has a tested native path on the arm64 Mac. The GitHub-hosted amd64 path remains the production path.
3. Optionally rename the historical `edcloud-vintage-runner.sh` and its marker/JSON labels in a separate contract change.

## Now

- The site-wide clarity and accessibility pass is implemented and locally verified. Keep the approved resume, public HTML, tagged phone-free production PDF, and the two published Blog posts aligned. The verified pre-rewrite backup at `/Users/brf/src/brfid.github.io-pre-history-rewrite-20260821` must never be pushed.

## Next

- Import further approved essays as page bundles when selected, validating public routes and assets; never restore superseded copy from the offline backup.

## Blocked

- None.

## Open decisions

- None.
