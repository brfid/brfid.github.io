# Agent instructions

Use this file for stable repository constraints, `README.md` for setup and operator commands, and `git log` for completed work. Do not maintain separate status files or task trackers.

## Repository scope

- Build and publish the Hugo site at `brfid.github.io`.
- Use Hugo for every published page, including the landing bio. Keep complete approved publication copies, citations, supporting assets, and full-text RSS here. Nonfiction editorial masters belong in the private `~/src/posts` workspace.
- Treat the repository, its history, commit messages, workflow logs, and generated site as public.
- Keep private career strategy, draft positioning, salary data, confidential employer information, and rejected copy outside this repository.
- Run the publish path on GitHub-hosted runners and verify it with the same local build command. Do not add an external execution host or cloud account.

## Read order

1. `README.md`
2. `hugo/`

For nonfiction editorial work on the owner's Mac, use `~/src/posts`: read its `AGENTS.md` and the essay's `notes.md`, and revise its `article/` master. Follow that workspace's instructions to compare and copy approved publication content, preserving divergent site work and source provenance. Keep private guidance, research, and working examples there. The site builds independently; its checks and CI must not require the private repository. The procedural documentation rules below govern site setup and operation instructions.

## Documentation

- Start with the reader's task, required inputs, command, and result.
- Use active voice and second person in procedures. Put conditions before instructions.
- Use sentence case for headings and workflow names.
- Keep explanations only when they change an action, define a contract, or prevent a known failure.
- Keep code blocks runnable. Use current paths, target names, and options.
- Make comments describe non-obvious contracts or constraints. Remove comments that narrate the code.
- Link to the source of truth instead of restating it.
- Soft-wrap Markdown: one source line per paragraph or list item.

## Public resume data

- Use `resume.yaml` as the canonical public resume source for the resume HTML and public PDF. Keep its `basics.summary` shared by the landing page and resume until an explicit decision separates them. Keep public identity and links in `site.yaml`.
- Keep phone numbers out of `resume.yaml` and generated Hugo data; the public artifact must meet the [publication contracts](#preserve-publication-contracts).
- Use only the gitignored `resume.private.yaml` for `basics.phone`. Only `make resume-pdf-application` may read it, and that target must write outside the public `site/` tree.
- Treat `hugo/data/resume.yaml` as generated output. Never edit or commit it.
- Keep alternate or rejected resume copy out of tracked examples and generated artifacts.
- Double-quote human-authored YAML strings that contain a colon.
- Do not claim an intacs Automotive SPICE Provisional Assessor certification. The Romeo Power entry may state only that Brad passed the examination; the credential was not issued.

## Work locally

- Run Python through `.venv/bin/python`. Do not install packages globally or modify system Python.
- Use the commands documented in `README.md` and `make help`.
- Use one public build path, `make verify-site`, for the complete HTML and PDF artifact in local checks and CI.
- Preview design and theme changes through Hugo. Do not create a separate HTML mockup.
- Extend PaperMod through `hugo/assets/css/extended/`, self-hosted fonts, and repository-owned partials. Do not edit the PaperMod submodule.
- Restart the preview after changing `resume.yaml`, or after changing layout or CSS that affects the PDF.
- Inspect both `/resume/` and `/resume.pdf` after resume changes. Inspect the application PDF when private-overlay behavior changes.

## Preserve publication contracts

- Keep all HTML, including the blog index, published posts, pagination, homepage, résumé, and aliases, on `noindex, nofollow, noarchive, nosnippet, noimageindex`. Apply this policy globally to current and future articles.
- Do not publish or advertise a sitemap while all HTML is excluded from indexing.
- Leave HTML crawlable in `robots.txt` so crawlers can observe `noindex`. Use `robots.txt` only to block non-HTML artifacts.
- Publish `/posts/`, `/index.xml`, `/posts/index.xml`, `/resume/`, `/about/`, and `/resume.pdf`.
- Publish a post only when its front matter sets `draft: false`.
- Fail deployment if a required route, feed, navigation link, indexing directive, or public-PDF contract is missing.
- Keep the GitHub repository and Pages site public.
- Keep build jobs read-only. Grant Pages and identity-token permissions only to deployment from this repository's protected `main` branch.
- Pin Actions to full upstream commit IDs. Select the CI Python release and verify Hugo and Gitleaks downloads against committed checksums.
- Deploy the verified artifact from the same checked workflow run without rebuilding it, and skip publication when `main` has advanced.
- Require a tagged public resume PDF. Keep all telephone numbers out of public HTML and PDFs. Deployment rejects `tel:` links, plausible US telephone-number text, and any PDF other than `resume.pdf` under `site/`.

## Commit and publish

- For authorized edits, make coherent local checkpoint commits at meaningful milestones, before major changes of direction, and when finishing the task. Keep messages clear enough to identify and revert each stage; describe any unfinished checkpoint. Preserve unrelated work unless the operator asks to include it. Retain useful checkpoints; do not amend, squash, or otherwise rewrite them unless requested.
- Keep `main` linear. Validate as appropriate to the change and do not commit generated directories such as `site/`, `build/`, `local/`, or `.venv/`.
- Do not merge, rebase, tag, or push commits from the offline pre-rewrite backup.
- Do not rewrite shared `main` history unless the operator explicitly requests it.
- Do not push unless the operator explicitly requests a push.
- Before pushing, inspect changed files for private or secret material and run validation appropriate to the change.
- Every push to `main` starts deployment unless its head commit message contains `[nopublish]`.

## Report implementation work

- Summarize changes by file path.
- List validation performed, or state that no validation ran.
