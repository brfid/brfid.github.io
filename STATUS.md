# Status

This file records current operations and queued work. Use `git log` for completed work and `~/src/career/STATUS.md` for career strategy.

## Current State

- Hugo publishes the landing page, Blog, both RSS feeds, Resume, the `/about/` alias, `resume.pdf`, a build log, and `pipeline-status.json`. It emits no sitemap, taxonomy pages, or Hugo JSON indexes.
- Every HTML page carries the full site-wide `noindex` policy. `robots.txt` leaves HTML crawlable and blocks the PDF, feeds, and pipeline status.
- `site.yaml` supplies public identity and links. `resume.yaml` supplies the public resume and the shared landing-page summary. Generated Hugo data remains gitignored.
- Hugo renders one public resume page, and Playwright prints it as a tagged, phone-free PDF. Only `make resume-pdf-application` reads `resume.private.yaml`; it writes the private PDF outside `site/`.
- The vintage pipeline converts the public name, headline, and summary to a fixed ASCII contract, composes troff on VAX 4.3BSD, renders it with `nroff` on PDP-11 2.11BSD, validates the round trip, and passes the result to Hugo.
- GitHub-hosted `ubuntu-latest` runners execute the publish path. Production uses the immutable VAX and PDP-11 image pair pinned in `scripts/edcloud-vintage-runner.sh` and disables local image fallback.
- Deployment verifies routes, feeds, navigation state, indexing policy, provenance, PDF tagging and privacy, `tel:` links, and plausible US telephone-number text before uploading the Pages artifact.
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
