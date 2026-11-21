# Agent instructions

Use this file for stable repository constraints, `README.md` for setup and operator commands, and `git log` for completed work. Do not maintain separate status files or task trackers.

## Repository scope

- Build and publish the Hugo site at `brfid.github.io`.
- Use Hugo for every published page, including the landing bio. Keep approved publication copies, their citations and required assets here. An explicitly author-authorized public draft may be stored with `draft: true`; it must remain absent from the site and feeds until website publication is separately approved. `draft: true` does not make a file in this public repository private.
- Host cited source documents and page images only when no equivalent complete copy is publicly accessible elsewhere. Keep only selected public sources and concise citation provenance, following [source hosting](README.md#host-cited-sources).
- Treat the repository, its history, commit messages, workflow logs, and generated site as public.
- Keep secrets, confidential material, and unapproved copy out of tracked files, examples, logs, and generated artifacts.
- Run the publish path on GitHub-hosted runners and verify it with the same local build command. Do not add an external execution host or cloud account.

## Read order

Read [README.md](README.md), then the source files relevant to the task. Follow the owner's current editorial brief for content changes. Keep planning and unpublished editorial discussions outside this public repository. The build and CI must depend only on the public checkout and documented tools.

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

- Use `resume.yaml` as the canonical source for the landing introduction, HTML résumé, and public PDF. The landing introduction uses its name, headline, and summary. Keep `site.yaml` name and headline in sync with `resume.yaml` fields `basics.name` and `basics.label`. Use `site.yaml` for landing-page social links. Keep selected samples and the bibliography in `hugo/content/work.md`; its URL supplies the CV’s Selected work link.
- Keep phone numbers out of `resume.yaml` and generated Hugo data; the public artifact must meet the [publication contracts](#preserve-publication-contracts).
- Use only the gitignored `resume.private.yaml` for `basics.phone`. Only `make resume-pdf-application` may read it, and that target must write outside the public `site/` tree.
- Edit the root YAML files. Leave the copies staged by Make in the build and preview directories alone.
- Keep alternate or rejected resume copy out of tracked examples and generated artifacts.
- Use literal blocks (`|-`) for the headline and prose descriptions, including short descriptions. Keep each paragraph on one source line. Leave short, unambiguous strings plain; quote date-like or otherwise ambiguous single-line strings. Use a literal block or double quotes for text containing a colon.
- Preserve the factual scope and attribution of approved copy. Editing or regenerating a document does not verify its claims.

## Work locally

- Run Python through `.venv/bin/python`. Do not install packages globally or modify system Python.
- Use the commands documented in `README.md` and `make help`.
- Use one public build path, `make verify-site`, for the complete HTML and PDF artifact in local checks and CI.
- Preview design and theme changes through Hugo. Do not create a separate HTML mockup.
- Extend PaperMod through `hugo/assets/css/extended/`, self-hosted fonts, and repository-owned partials. Do not edit the PaperMod submodule.
- Follow the [preview procedure](README.md#preview-the-site) and [resume inspection steps](README.md#edit-the-public-resume-or-profile). Inspect the application PDF when private-overlay behavior changes.

## Preserve publication contracts

- Keep all HTML, including the blog index, published posts, pagination, homepage, résumé, and aliases, on `noindex, nofollow, noarchive, nosnippet, noimageindex`. Apply this policy globally to current and future articles.
- Do not publish or advertise a sitemap while all HTML is excluded from indexing.
- Leave HTML crawlable for search engines in `robots.txt` so they can observe `noindex`. Block non-HTML artifacts and explicitly exclude archive crawlers (`archive.org_bot`, `ia_archiver`, and `CCBot`) from the entire site.
- Publish the introduction at `/`, the résumé at `/resume/`, selected work at `/work/`, the blog at `/posts/`, and both feeds at `/index.xml` and `/posts/index.xml`. Put a separate download link for the tagged PDF at `/resume.pdf` beside Resume in the header. Keep `/about/` redirecting to `/` and `/portfolio/` redirecting to `/work/`.
- Publish a post only when its front matter sets `draft: false`.
- Fail deployment if a required route, feed, navigation link, indexing directive, or public-PDF contract is missing.
- Keep the GitHub repository and Pages site public.
- Keep build jobs read-only. Grant Pages and identity-token permissions only to deployment from this repository's protected `main` branch.
- Pin Actions to full upstream commit IDs. Select the CI Python release and verify Hugo and Gitleaks downloads against committed checksums.
- Deploy the verified artifact from the same checked workflow run without rebuilding it, and skip publication when `main` has advanced.
- Require a tagged public resume PDF. Keep all telephone numbers out of public HTML and PDFs. Deployment rejects `tel:` links, plausible US telephone-number text, and any PDF other than `resume.pdf` under `site/`.

## Commit and publish

- Make coherent, scoped local commits for authorized edits at milestones, before major changes of direction, and on completion. Review the staged diff and use a terse imperative subject. Preserve unrelated work, attribution, and useful checkpoints. Use the [checks appropriate to the change](README.md#run-checks).
- Keep `main` linear. Do not commit generated directories such as `site/`, `build/`, `local/`, or `.venv/`.
- Get explicit authorization before pushing, publishing, or rewriting shared history. Proceed within the authorized scope unless permissions block the action. Branch settings that allow a force push do not authorize a rewrite.
- Before pushing, review all outgoing changes and commit messages for private material and [scan all outgoing commits for secrets](README.md#scan-before-pushing).
- For an authorized published-history rewrite, preserve one private recovery ref or bundle and use an exact lease, `--force-with-lease=refs/heads/main:<expected-remote-tip>`, with the reviewed remote commit ID. Keep recovery material outside publication.
- Every push to `main` starts deployment unless its head commit message contains `[nopublish]`.

## Report implementation work

Report changed paths and validation performed, including if none ran.
