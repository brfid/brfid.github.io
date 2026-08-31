# Status

This file records current operations and queued work. Use `git log` for completed work and `~/src/career/STATUS.md` for career strategy.

## Current State

- The repository moved from GitLab CI to GitHub Actions. `brfid/brfid.github.io` is canonical; the former `gitlab.com/brfid/brfid.gitlab.io` project has been deleted. The local checkout lives at `~/src/brfid.github.io`. The pre-migration GitHub history (when this repo published only a redirect to GitLab) is preserved under the `archive/redirect-era` tag.
- GitHub Pages publishes the Hugo landing page, Blog, both RSS feeds, Resume, the `/about/` alias, `resume.pdf`, a build log, and `pipeline-status.json` at `https://brfid.github.io`. It emits no sitemap, taxonomy pages, or Hugo JSON indexes.
- Every HTML page carries the full site-wide `noindex` policy. `robots.txt` leaves HTML crawlable and blocks the PDF, feeds, and pipeline status.
- `site.yaml` supplies public identity and links. `resume.yaml` supplies the public resume and the shared landing-page summary. Generated Hugo data remains gitignored.
- Hugo renders one public resume page, and Playwright prints it as a tagged, phone-free PDF. Local Hugo, PDF, preview, and verification builds clear deployment-only provenance. Only `make resume-pdf-application` reads `resume.private.yaml`; it writes the private PDF outside `site/`.
- The vintage pipeline converts the public name, headline, and summary to a fixed ASCII contract, composes troff on VAX 4.3BSD, renders it with `nroff` on PDP-11 2.11BSD, validates the round trip, and writes the final bio, build log, and status under `build/vintage/` for deployment to stage into Hugo.
- GitHub-hosted amd64 runners execute the publish path. Standard mode validates the source-bound immutable VAX and PDP-11 pair in `vintage/image-pair.json`, disables local image fallback and environment bootstrap, isolates each guest to read-only inputs and a stage-only output mount, and retains a public fingerprinted, checksummed bio, build log, and status artifact for 90 days.
- The PDP-11 image recipe retrieves its checksum-pinned 2.11BSD disk archive from a GitHub Release asset on `brfid/brfid.github.io`. A manually dispatched image-build workflow runs only on protected `main` with a digest-pinned BuildKit backend, publishes source-commit tags to `ghcr.io/brfid/`, and emits one manifest binding both immutable digests to the source commit and image-input digest. The runner requires both provenance labels after pull.
- Explicit fast mode searches successful standard publications through GitHub's Actions API, authenticated with the workflow's own `GITHUB_TOKEN`, and reuses the newest retained result with the same bio inputs, promoted image manifest, and recursively enumerated vintage implementation. It preserves that result's build ID, status SHA, log, and GitHub Actions run link while rebuilding and verifying the current Hugo site and public PDF; missing or invalid reuse artifacts stop publication.
- Both publication modes require successful quality and full-history gitleaks jobs. Deployment then enforces an explicit Pages path allowlist, exact-origin contained feed links, indexing and provenance contracts, PDF tagging, `tel:` exclusion, international telephone-number checks, and redacted secret-pattern scans before a success-only Pages artifact can upload.
- The image-build workflow's BuildKit backend uses an immutable digest. Python environments install from committed hash locks, Hugo installation uses a repository-owned package checksum, and dependency caches key from the applicable lock without caching the browser executable.
- The public post bundles are `hugo/content/posts/stracheys-principle/` and `hugo/content/posts/doc-rot-maintenance-gap/`. Additional drafts remain outside this repository until approved for publication.

## Posture

- None.

## Goals

1. Keep the public resume HTML, PDF, landing bio, and published posts aligned with their source files.
2. Keep the publish path reproducible from public source files and pinned runtime dependencies.

## Now

- None.

## Next

- Import the next approved essay with its public assets, then verify its route, feed entry, metadata, and responsive layout.

## Blocked

- None.

## Open decisions

- None.
