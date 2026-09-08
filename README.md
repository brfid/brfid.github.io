# brfid.github.io

Source and build tooling for [brfid.github.io](https://brfid.github.io/). Hugo renders the site, blog, and resume from public source files. Playwright prints the resume HTML as a tagged PDF.

The build has one path:

```text
site.yaml + resume.yaml + Hugo content and templates
    -> Hugo HTML -> Playwright PDF -> artifact verification -> GitHub Pages
```

Pull requests and publications run the same build and verification commands. Deployment receives the verified artifact from its own workflow run and does not rebuild it.

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

The result is the complete public site under `site/`, including `site/resume.pdf`. A verification failure exits unsuccessfully and prevents CI from uploading a Pages artifact.

The repository vendors PaperMod as a pinned Git submodule and serves its fonts locally. There is no front-end package install or build step. Python dependencies install from hash locks. CI selects Python 3.11.16 on `ubuntu-24.04`, verifies Hugo and Gitleaks downloads against committed checksums, and pins Actions to full commit IDs. The version selections live in `scripts/github/setup.sh` and `.github/workflows/publish.yml`. Hosted runner updates and system PDF tools remain outside those pins; the build is not claimed to be byte-identical across machines.

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

```bash
make check
make verify-site
```

`make check` runs Ruff, formatting checks, mypy, pytest, Pylint, and Vulture. The tests cover privacy failures, output policy, feeds, PDF rendering boundaries, and workflow gates. The stale-build guard is tested with successful, superseded, and failed API responses.

With Gitleaks installed, run the same history scan as CI:

```bash
gitleaks git --log-opts="--all --full-history -m" --redact --verbose --no-banner
```

This scans all fetched branches and tags, including merge results, and redacts matches in its diagnostics. It checks committed history; review uncommitted changes before committing them.

`make verify-site` builds fresh HTML and a real Chromium PDF, then checks required routes, feeds, navigation, structured data, the output allowlist, indexing directives, public email, PDF tagging, and phone and secret exclusion. This is also the CI build command. Use `.venv/bin/python -m site_tools.verify site` to recheck an existing artifact without rebuilding it.

Use `make test` for unit and workflow tests alone, `make hugo-build` for HTML alone, and `make help` for the supported command list.

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

Working drafts stay outside this public repository. Add only approved copy and public assets.

## Publish the site

A push to `main` runs the full-history secret scan, quality checks, and complete HTML/PDF build. After those pass, the workflow uploads the verified Pages artifact. Deployment runs only for this repository's protected `main` branch, and skips a build if the branch has advanced since it was checked. Only the deployment job has Pages write and identity-token permissions.

A commit message containing `[nopublish]` runs the checks and retains the artifact without deploying. Every publication uses the same build path; `[fast]` has no special meaning.

To publish the current `main` manually, authenticate GitHub CLI and start the workflow:

```bash
gh auth status
gh workflow run publish.yml --ref main -f operation=publish
```

Use `-f operation=checks` to build and verify without publishing. Open the resulting run to inspect its `github-pages` artifact, retained for 30 days:

```bash
gh run list --workflow publish.yml --limit 5
gh run view --web
```

Pages deployment retries transient failures up to three times using the same artifact. A failed build cannot reach deployment. Inspect the failed job and the live site if all deployment attempts fail.

Every rendered HTML page contains `noindex, nofollow, noarchive, nosnippet, noimageindex`. Hugo emits no sitemap. `robots.txt` leaves HTML crawlable and blocks the public PDF and feeds.

## Recover a publication

If deployment alone failed and the run still identifies the current `main` commit, use GitHub Actions' **Re-run failed jobs** within the artifact's 30-day retention window. The deployment job reuses that run's checked artifact. If the artifact expired, start a new manual publication of `main`.

If published source needs correction, inspect the offending commit, revert that change on `main`, verify the resulting source, and push the new commit. Replace the example SHA before running:

```bash
git status --short --branch
git log -5 --oneline
git show BAD_COMMIT_SHA
git revert BAD_COMMIT_SHA
make check
make verify-site
git push origin main
```

Start with a clean checkout on `main`. Revert a multi-commit change from newest to oldest, or prepare a focused corrective commit when other work depends on it. Recovery preserves shared history and passes through the same checks as an ordinary publication.

The current workflow checks the latest `main` commit before starting deployment. Runs from before the vintage pipeline retirement use the workflow at their original revision and lack that guard; use a new publication of `main` for recovery.

## Update dependencies

After changing `pyproject.toml` or `requirements/build.in`, regenerate the affected locks with uv:

```bash
uv pip compile requirements/build.in --python-version 3.11 --universal --generate-hashes -o requirements/build.lock
uv pip compile pyproject.toml --all-extras --python-version 3.11 --universal --generate-hashes --no-emit-package brfid-site -o requirements/dev.lock
```

Reinstall from the updated locks and run both checks above. Inspect `/resume/` and the PDF when updating Playwright, since its Chromium version affects pagination. Update the Python selection in `.github/workflows/publish.yml`; update Hugo's version in `scripts/github/setup.sh` together with its independently verified package checksum in `requirements/hugo.sha256`.

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
| `.github/workflows/publish.yml` | Checks, artifact handoff, and Pages deployment |
| `scripts/github/setup.sh` | Hosted build environment setup |
| `STATUS.md` | Current operational state and queue |

The former VAX/PDP-11 bio pipeline is [documented as a retired experiment](docs/vintage-pipeline.md); its implementation remains in Git history. [ARPANET Redux](https://github.com/brfid/arpanet-redux) continues the historical-computing work as an independent project.
