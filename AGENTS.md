# Agent instructions

Use this file for stable repository constraints. Put setup and operator commands in `README.md`, current state in `STATUS.md`, and completed work in `git log`.

## Repository scope

- Build and publish the Hugo site at `brfid.gitlab.io`.
- Use Hugo for every published page. The VAX and PDP-11 pipeline generates the landing-page bio and provenance artifacts for Hugo; it does not generate the site.
- Treat the repository, its history, commit messages, workflow logs, and generated site as public.
- Keep private career strategy, draft positioning, salary data, confidential employer information, and rejected copy outside this repository.
- Run the publish path on GitLab-hosted runners or local Docker. Do not add an external execution host or cloud account.

## Read order

1. `README.md`
2. `STATUS.md`
3. `hugo/`
4. `docs/integration/INDEX.md`, only for vintage pipeline work
5. `~/src/career/STATUS.md`, only for resume surfaces, site reactivation, or phase-gated work

## Sources of truth

| Subject | Source |
|---|---|
| Current operations and queue | `STATUS.md` |
| Setup and supported commands | `README.md` |
| Vintage pipeline | `docs/integration/INDEX.md` |
| `pexpect` implementation | `docs/integration/operations/PEXPECT-PIPELINE-SPEC.md` |
| Retired approaches | `docs/archive/DEAD-ENDS.md` |
| Strategic career state | `~/src/career/STATUS.md` |
| Completed work | `git log` |

Do not copy mutable state between these files.

## Documentation

- Start with the reader's task, required inputs, command, and result.
- Use active voice and second person in procedures. Put conditions before instructions.
- Use sentence case for headings and workflow names, except for the fixed `STATUS.md` section names.
- Keep explanations only when they change an action, define a contract, or prevent a known failure.
- Keep code blocks runnable. Use current paths, target names, and options.
- Make comments describe non-obvious contracts or constraints. Remove comments that narrate the code.
- Link to the source of truth instead of restating it.
- Soft-wrap Markdown: one source line per paragraph or list item.

## Public resume data

- Use `resume.yaml` as the canonical public resume source. It drives the resume HTML, public PDF, and landing-page summary.
- Keep phone numbers out of `resume.yaml`, Hugo data, HTML, and `site/resume.pdf`.
- Use only the gitignored `resume.private.yaml` for `basics.phone`. Only `make resume-pdf-application` may read it, and that target must write outside the public `site/` tree.
- Treat `hugo/data/resume.yaml` as generated output. Never edit or commit it.
- Keep alternate or rejected resume copy out of tracked examples and generated artifacts.
- Double-quote human-authored YAML strings that contain a colon.
- Keep `resume.yaml` `basics.summary` shared by the landing page and resume until an explicit decision separates them. Keep public identity and links in `site.yaml`.
- Do not claim an intacs Automotive SPICE Provisional Assessor certification. The Romeo Power entry may state only that Brad passed the examination; the credential was not issued.

## Work locally

- Run Python through `.venv/bin/python`. Do not install packages globally or modify system Python.
- Use the commands documented in `README.md` and `make help`.
- Keep local and production provenance modes separate. `hugo-build`, `resume-pdf`, previews, and `verify-site` clear deployment-only bio, build-log, and status inputs; `resume-pdf-public` requires all three staged production inputs.
- Preview design and theme changes through Hugo. Do not create a separate HTML mockup.
- Extend PaperMod through `hugo/assets/css/extended/`, self-hosted fonts, and repository-owned partials. Do not edit the PaperMod submodule.
- Restart the preview after changing `resume.yaml`, or after changing layout or CSS that affects the PDF.
- Inspect both `/resume/` and `/resume.pdf` after resume changes. Inspect the application PDF when private-overlay behavior changes.

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

- Update `Now` when work starts or ends.
- Update `Goals` or `Next` for queued work.
- Update `Blocked` for external dependencies.
- Update `Open decisions` when operator input is required.
- Update `Current State` when architecture or runtime behavior changes.
- Do not record routine post editing or completed work.

## Preserve publication contracts

- Keep every rendered HTML page on `noindex, nofollow, noarchive, nosnippet, noimageindex` until the operator explicitly changes the policy.
- Keep sitemap output disabled.
- Leave HTML crawlable in `robots.txt` so crawlers can observe `noindex`. Use `robots.txt` only to block non-HTML artifacts.
- Publish `/posts/`, `/index.xml`, `/posts/index.xml`, `/resume/`, `/about/`, and `/resume.pdf`.
- Publish a post only when its front matter sets `draft: false`.
- Fail deployment if a required route, feed, navigation link, indexing directive, provenance artifact, or public-PDF contract is missing.
- Keep the GitLab project, Pages site, CI job logs, and reusable standard-publication artifacts publicly readable so fast mode needs no private API token.
- Keep GitLab's indefinite retention of the latest successful artifact disabled; the reusable vintage bundle expires after 90 days.
- Keep all telephone numbers out of public HTML and PDFs. Deployment rejects `tel:` links, plausible US telephone-number text, and any PDF other than `resume.pdf` under `site/`.

## Preserve vintage pipeline contracts

- Drive SIMH with pexpect over stdin and stdout. Do not restore screen, telnet, or fixed-delay state transitions. A short per-line transport throttle is permitted to protect the guest tty.
- Keep VAX and PDP-11 boot, shell, and shutdown state machines separate.
- Use the host to transfer the UUCP spool. The PDP-11 `unix` kernel has no working Ethernet.
- Keep `scripts/vintage-runner.sh` bind-mounting the checkout's pexpect scripts and `simh_session.py` over the cached image copies, and keep its final bio, build log, and status under `build/vintage/`.
- Pin production to an explicit pair of immutable container image digests and disable local image fallback in deployment and validation.
- Promote image changes through the manual image-build workflow and vintage validation procedure in `docs/integration/INDEX.md`.
- Keep standard mode as the default. Explicit fast mode may reuse only the exact retained bio, build log, and status from a matching successful run in standard mode.
- Include the three public bio strings and every implementation file that can affect vintage output or reuse validation in the reuse fingerprint. Keep unrelated site and resume fields eligible for fast mode.
- Preserve reused vintage provenance: the status SHA, build ID, log, and GitLab pipeline link must continue to identify the source run. Fail closed rather than synthesizing current-run provenance or silently running the vintage pipeline.

## Commit and publish

- Keep `main` linear. Use complete, intention-revealing commits and do not commit generated directories such as `site/`, `build/`, `local/`, or `.venv/`.
- Do not merge, rebase, tag, or push commits from the offline pre-rewrite backup.
- Do not rewrite shared `main` history unless the operator explicitly requests it.
- Do not push unless the operator explicitly requests a push.
- Before pushing, inspect changed files for private or secret material and run validation appropriate to the change.
- Every push to `main` starts deployment unless the commit message contains `[nopublish]`.
- A push whose commit message contains `[fast]` requests fail-closed fast mode. Use it only for changes that do not require a new landing-page bio result.

## Report implementation work

- Summarize changes by file path.
- List validation performed, or state that no validation ran.
- Update `docs/integration/INDEX.md` when pipeline documentation paths change.
