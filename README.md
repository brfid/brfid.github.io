# brfid.github.io

Source and build tooling for [brfid.github.io](https://brfid.github.io/). Hugo renders the site, blog, and resume from public source files. Playwright prints the resume HTML as a tagged PDF.

The build has one path:

```text
site.yaml + resume.yaml + Hugo content and templates
    -> Hugo HTML -> Playwright PDF -> artifact verification -> GitHub Pages
```

## Set up a checkout

Install Git, Make, Python 3.11 or newer, Hugo extended 0.156.0 or newer, and Poppler (`pdfinfo` and `pdftotext`). GitHub CLI (`gh`) is needed only for manual workflow operations. Then run:

```bash
git submodule update --init
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements/build.lock
.venv/bin/python -m pip install --require-hashes -r requirements/dev.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
.venv/bin/python -m playwright install chromium
make check_env
make verify-site
```

On Linux, use `.venv/bin/python -m playwright install --with-deps chromium` for the browser installation so Chromium's system libraries are installed too.

The result is the complete public site under `site/`, including `site/resume.pdf`.

The repository vendors PaperMod as a pinned Git submodule and serves its [fonts locally](docs/fonts.md). There is no front-end package install or build step. Python dependencies install from hash locks. The [setup script](scripts/github/setup.sh) and [workflow](.github/workflows/publish.yml) select CI tools, verify downloads against committed checksums, and pin Actions to full commit IDs. Hosted runner updates and system PDF tools remain outside those pins; the build is not claimed to be byte-identical across machines.

## Preview the site

```bash
make preview
```

Open `http://localhost:1313/`. The command builds the public site and PDF before starting Hugo with live reload. Restart it after changing `resume.yaml`, the resume layout, or print CSS.

Use `make preview-drafts` to include draft posts. Set `PREVIEW_PORT` to use another port:

```bash
make preview PREVIEW_PORT=1314
```

## Run checks

Before running `make verify-site`, stop any Hugo preview in this checkout. Both commands use `site/`, and an active preview can overwrite production output with localhost URLs. Restart the preview after verification if needed.

```bash
make check
make verify-site
```

`make check` runs Ruff, formatting checks, mypy, pytest, Pylint, and Vulture. The browser tests render Hugo into a temporary directory and use the installed Chromium to check navigation, theme controls, article semantics, code copying, and print scoping without touching your preview.

`make verify-site` builds fresh HTML and a Chromium PDF, then validates the [publication contracts](AGENTS.md#preserve-publication-contracts). A verification failure exits unsuccessfully and prevents CI from uploading a Pages artifact. Pull requests and publications use this command too. Use `.venv/bin/python -m site_tools.verify site` to recheck an existing artifact without rebuilding it.

Use `make test` for unit, browser, and workflow tests alone, `make hugo-build` for HTML alone, and `make help` for the supported command list.

With Gitleaks installed, run the same history scan as CI:

```bash
gitleaks git --log-opts="--all --full-history -m" --redact --verbose --no-banner
```

This scans all fetched branches and tags, including merge results, and redacts matches in its diagnostics. It checks committed history; review uncommitted changes before committing them.

## Build an application PDF

1. Copy `resume.private.example.yaml` to the gitignored `resume.private.yaml`.
2. Replace the example `basics.phone` value.
3. Run `make resume-pdf-application`.

The command first builds and verifies the phone-free public artifact. It then writes the private PDF to `local/bradley-fidler-resume.pdf`. Only this target reads the private overlay. It rejects a missing or invalid overlay and any private PDF destination inside `site/`.

## Add a blog post

Create a draft page bundle:

```bash
make new-post POST_SLUG=maintenance-window
```

Edit `hugo/content/posts/maintenance-window/index.md` and place approved image assets beside it. Production publishes a post only when its front matter explicitly sets `draft: false`.

Maintain the complete article, citations, and supporting assets in its Hugo page bundle. The site publishes the full article as HTML and RSS. Working drafts stay outside this public repository; add only approved copy and public assets.

## Publish the site

A push to `main` runs the full-history secret scan, quality checks, and complete HTML/PDF build. After those pass, the workflow uploads the verified Pages artifact and deploys it from the same run without rebuilding it. Deployment runs only for this repository's protected `main` branch, and skips a build if the branch has advanced since it was checked.

A push whose head commit message contains `[nopublish]` runs the checks and retains the artifact without deploying.

To publish the current `main` manually, authenticate GitHub CLI and start the workflow:

```bash
gh auth status
gh workflow run publish.yml --ref main -f operation=publish
```

Use `-f operation=checks` to build and verify without publishing. Open the resulting run to inspect its `github-pages` artifact, kept for the [workflow's configured retention period](.github/workflows/publish.yml):

```bash
gh run list --workflow publish.yml --limit 5
gh run view --web
```

Pages deployment retries transient failures up to three times using the same artifact. Inspect the failed job and the live site if all deployment attempts fail.

All HTML, including the blog index, full articles, pagination, homepage, résumé, and aliases, requests exclusion from indexing. The policy applies globally to current and future articles. See the [publication contracts](AGENTS.md#preserve-publication-contracts) for the exact directives.

The site does not publish or advertise a sitemap. `robots.txt` leaves HTML crawlable so search engines can read its indexing directives, and blocks the public PDF and feeds. Article URLs, supporting assets, and both full-text feeds remain available to readers. The PDF block discourages crawling but [does not guarantee exclusion from search](https://developers.google.com/search/docs/crawling-indexing/robots/intro). These controls do not prevent public copies or archival retention; the repository's revision history is also public.

## Recover a publication

If deployment alone failed, the run still identifies the current `main` commit, and its checked artifact remains available, use GitHub Actions' **Re-run failed jobs**. The deployment job reuses that artifact. If it expired or `main` advanced, start a new manual publication of `main`.

If published source needs correction, start with a clean checkout on `main`. Inspect the offending commit, revert that change, verify the resulting source, and push the new commit. Replace the example SHA before running:

```bash
git status --short --branch
git log -5 --oneline
git show BAD_COMMIT_SHA
git revert BAD_COMMIT_SHA
make check
make verify-site
git push origin main
```

Revert a multi-commit change from newest to oldest, or prepare a focused corrective commit when other work depends on it. Recovery preserves shared history and passes through the same checks as an ordinary publication.

## Update dependencies

After changing `pyproject.toml` or `requirements/build.in`, regenerate the affected locks with uv:

```bash
uv pip compile requirements/build.in --python-version 3.11 --universal --generate-hashes -o requirements/build.lock
uv pip compile pyproject.toml --all-extras --python-version 3.11 --universal --generate-hashes --no-emit-package brfid-site -o requirements/dev.lock
```

Reinstall from the updated locks and, if Playwright changed, reinstall Chromium using the [checkout setup commands](#set-up-a-checkout). Run [the checks](#run-checks). After a Playwright update, inspect `/resume/` and `/resume.pdf`, since its Chromium version affects pagination.

Update the Python selection in [.github/workflows/publish.yml](.github/workflows/publish.yml); update Hugo's version in [scripts/github/setup.sh](scripts/github/setup.sh) together with its independently verified package checksum in `requirements/hugo.sha256`.

Update Gitleaks' version in `.github/workflows/publish.yml` together with `requirements/gitleaks.sha256`, checked against the upstream release's checksum file. Run the history scan after an update because detection rules may change.

For an Action update, resolve the intended release in its upstream repository to a commit, inspect its changes, and replace the full commit ID and version comment together. GitHub documents [why full commit IDs provide immutable Action references](https://docs.github.com/en/actions/reference/security/secure-use#using-third-party-actions). There is no dependency cache or automatic dependency-update workflow in this repository.

## Source files

| Path | Function |
|---|---|
| `site.yaml` | Public name, headline, and profile links |
| `resume.yaml` | Canonical public resume and shared landing summary |
| `resume.private.yaml` | Optional local phone overlay; gitignored |
| `hugo/` | Content, templates, configuration, styles, and fonts |
| `site_tools/pdf.py` | Public and private PDF rendering |
| `site_tools/verify.py` | Rendered HTML, feed, privacy, and PDF verification |
| `site_tools/environment.py` | Local prerequisite checks |
| `requirements/` | Hash-locked Python environment and Hugo/Gitleaks download checksums |
| [docs/multihoming-scans.json](docs/multihoming-scans.json) | Published archival scan paths, source provenance, and checksums |
| `.github/workflows/publish.yml` | Checks, artifact handoff, and Pages deployment |
| `scripts/github/setup.sh` | Hosted build environment setup |
