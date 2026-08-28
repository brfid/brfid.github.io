# Status

This file records the current posture and queued work for the retained GitHub repository. Use `git log` for completed work and `~/src/brfid.gitlab.io/STATUS.md` for active-site operations.

## Current State

- This public repository retains the former Hugo site, resume tooling, VAX/PDP-11 pipeline, tests, and history. The active source and site are at `https://gitlab.com/brfid/brfid.gitlab.io` and `https://brfid.gitlab.io/`.
- GitHub Pages builds only `redirect/`. The published artifact contains seven Hugo-rendered HTML redirects and `robots.txt`; it contains no former site pages, feeds, PDFs, or vintage provenance.
- Known routes have fixed meta-refresh fallbacks. JavaScript preserves the browser pathname, query, and fragment for known and unknown routes while keeping `https://brfid.gitlab.io` as the fixed destination origin.
- Every redirect page carries the full `noindex` policy. `robots.txt` leaves the HTML crawlable so crawlers can observe it.
- The manual vintage image-build and validation workflows remain available for historical pipeline maintenance. They do not publish GitHub Pages.

## Posture

- Preserve this repository as a public historical implementation. Make current site and production-pipeline changes in `~/src/brfid.gitlab.io`.

## Goals

1. Keep GitHub Pages limited to a verified redirect to the active GitLab site.
2. Preserve the former site and vintage-pipeline source without treating them as the active publication path.

## Now

- None.

## Next

- None.

## Blocked

- None.

## Open decisions

- None.
