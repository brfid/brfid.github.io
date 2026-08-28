# Agent instructions

Use this file for stable repository constraints. Put setup and operator commands in `README.md`, current state in `STATUS.md`, and completed work in `git log`.

## Repository scope

- Treat this repository as the public historical source for the former `brfid.github.io` site and vintage pipeline.
- Publish only the Hugo redirect under `redirect/` to GitHub Pages. Never restore the retained full site, resume PDF, feeds, or provenance artifacts to GitHub Pages unless the operator explicitly requests it.
- Treat [brfid/brfid.gitlab.io](https://gitlab.com/brfid/brfid.gitlab.io) and `~/src/brfid.gitlab.io` as the active site source. Make current site, resume, post, and production-pipeline changes there.
- Preserve the retained `hugo/`, `resume_generator/`, `vintage/`, integration documentation, tests, and history unless the operator explicitly requests historical maintenance or removal.
- Treat the repository, its history, commit messages, workflow logs, and generated redirect as public. Keep private career strategy, salary data, confidential employer information, secrets, and rejected copy outside it.
- Run GitHub Pages on GitHub-hosted runners. Do not add an external execution host or cloud account.

## Read order

1. `README.md`
2. `STATUS.md`
3. `redirect/` and `scripts/verify_redirect.py` for GitHub Pages work
4. `docs/integration/INDEX.md` only for retained vintage-pipeline work
5. `~/src/brfid.gitlab.io/README.md` and `~/src/brfid.gitlab.io/STATUS.md` for active-site work

## Sources of truth

| Subject | Source |
|---|---|
| Current repository posture and queue | `STATUS.md` |
| Setup and supported commands | `README.md` |
| GitHub Pages redirect | `redirect/`, `scripts/verify_redirect.py`, and `.github/workflows/deploy.yml` |
| Retained vintage pipeline | `docs/integration/INDEX.md` |
| Active site and deployment | `~/src/brfid.gitlab.io` |
| Completed work | `git log` |

Do not copy mutable state between these files or repositories.

## Documentation

- Start with the reader’s task, required inputs, command, and result.
- Use active voice and second person in procedures. Put conditions before instructions.
- Use sentence case for headings and workflow names, except for the fixed `STATUS.md` section names.
- Keep explanations only when they change an action, define a contract, or prevent a known failure.
- Keep code blocks runnable. Use current paths, target names, and options.
- Make comments describe non-obvious contracts or constraints. Remove comments that narrate the code.
- Soft-wrap Markdown: one source line per paragraph or list item.

## Preserve the redirect contract

- Use Hugo for every published page.
- Keep `https://brfid.gitlab.io` as a fixed destination origin. Preserve the browser pathname, query, and fragment without allowing visitor-controlled input to replace the destination host.
- Keep explicit routes for `/`, `/resume/`, `/about/`, `/posts/`, `/posts/stracheys-principle/`, and `/posts/doc-rot-maintenance-gap/`. Keep `404.html` as the fallback for all other paths.
- Keep every rendered HTML page on `noindex, nofollow, noarchive, nosnippet, noimageindex` until the operator explicitly changes the policy.
- Leave HTML crawlable in `robots.txt` so crawlers can observe `noindex`.
- Disable feeds, sitemap, taxonomy output, PDF generation, and vintage provenance in the redirect build.
- Fail deployment when the output contains any file beyond the redirect allowlist.
- Keep `.github/workflows/deploy.yml` independent of submodules, Python packages, Playwright, Docker, and the vintage pipeline.

## Work locally

- Run Python through `.venv/bin/python`. Do not install packages globally or modify system Python.
- Use `make verify-redirect` for a clean redirect build and contract check.
- Preview redirect presentation through Hugo with `make redirect-preview`; do not create a separate HTML mockup.
- Treat `make verify-site`, the PDF targets, and the full-site preview targets as retained historical tooling, not publication paths.
- Do not edit the PaperMod submodule.

## Public data

- Keep telephone numbers and private overlays out of tracked files and all GitHub Pages output.
- Keep `resume.private.yaml` gitignored. Only the retained `make resume-pdf-application` target may read it, and it must write outside `site/`.
- Do not claim an intacs Automotive SPICE Provisional Assessor certification. The retained Romeo Power entry may state only that Brad passed the examination; the credential was not issued.

## Maintain retained pipeline boundaries

- Do not reconnect the VAX/PDP-11 pipeline to GitHub Pages.
- Keep image building and vintage validation manual.
- Drive SIMH with pexpect over stdin and stdout. Do not restore screen, telnet, or fixed-delay state transitions.
- Keep VAX and PDP-11 boot, shell, and shutdown state machines separate, and use the host to transfer the UUCP spool.
- Keep immutable image digests and disable local image fallback in hosted validation.
- Update `docs/integration/INDEX.md` when retained pipeline documentation paths change.

## Maintain status

Keep these `STATUS.md` sections in this order:

1. `Current State`
2. `Posture`
3. `Goals`
4. `Now`
5. `Next`
6. `Blocked`
7. `Open decisions`

Use `- None.` for an empty section. Record only current or forward-looking operational state.

## Commit and publish

- Keep `main` linear. Use complete, intention-revealing commits and do not commit generated directories such as `site/`, `build/`, `local/`, or `.venv/`.
- Do not rewrite shared history, commit, or push unless the operator explicitly requests it.
- Before pushing, inspect changed files for private or secret material and run redirect validation plus checks appropriate to the change.
- Every push to `main` deploys the redirect. The retired `[nopublish]` and `[fast]` commit-message modes no longer apply.

## Report implementation work

- Summarize changes by file path.
- List validation performed, or state that no validation ran.
