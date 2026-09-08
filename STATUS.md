# Status

This file records current operations and queued work. Use `git log` for completed work and `~/src/career/STATUS.md` for career strategy.

## Current State

- `brfid/brfid.github.io` is the canonical public repository. The checkout lives at `~/src/brfid.github.io`; the former GitLab project has been deleted. Career strategy remains in `~/src/career/STATUS.md`.
- The live site builds the landing page, Blog, both RSS feeds, Resume, the `/about/` alias, and `resume.pdf` through Hugo and Playwright. Every HTML page retains the full `noindex` policy; sitemap output remains disabled.
- `site.yaml` supplies public identity and links. `resume.yaml` supplies the public resume and shared landing summary. Generated Hugo data remains gitignored.
- The public PDF is printed from the resume HTML and must be tagged and phone-free. Only `make resume-pdf-application` reads the private phone overlay, and it writes outside `site/`.
- `make verify-site` builds and validates the complete HTML and real PDF artifact. Pull requests and publications use that command. The Pages job deploys the artifact from the same checked run without rebuilding it, after full-history secret scanning and quality checks.
- The workflow selects an explicit Python release and Ubuntu runner release, verifies Hugo and Gitleaks against committed checksums, and pins Actions to immutable commits. Gitleaks scans the fetched Git history, including merge results. Only deployment has Pages write and identity-token permissions; it skips a run when a newer `main` commit exists. Hosted runner and system-package updates remain outside the dependency locks.
- Vintage execution, image promotion, reuse modes, and public vintage provenance are retired. `docs/vintage-pipeline.md` links to the original implementation in Git history. Existing hosted artifacts and container packages are unchanged.
- GitHub protects `main` against force pushes. Required status checks, required pull-request reviews, and administrator enforcement are not enabled.

## Posture

- None.

## Goals

1. Keep the public resume HTML, PDF, landing bio, and published posts aligned with their source files.
2. Keep publication independently buildable from public source files, with explicit dependencies and verification of the final artifact.

## Now

- None.

## Next

- Import the next approved essay with its public assets, then verify its route, feed entry, metadata, and responsive layout.

## Blocked

- None.

## Open decisions

- None.
