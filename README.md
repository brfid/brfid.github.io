# brfid.github.io

Source and build tooling for [brfid.github.io](https://brfid.github.io/). Hugo renders the site, blog, and resume from public source files. Playwright prints the resume HTML as a tagged PDF.

The build has one path:

```text
site.yaml + resume.yaml + Hugo content and templates
    -> Hugo HTML -> Playwright PDF -> artifact verification -> GitHub Pages
```

## Set up a checkout

Install Git, Make, Python 3.11 or newer, Hugo extended 0.156.0 or newer, and Poppler (`pdfinfo` and `pdftotext`). GitHub CLI (`gh`) is needed only for manual workflow operations. Complete these steps from the repository root:

1. Initialize the theme and install the Python dependencies:

   ```bash
   git submodule update --init
   python3 -m venv .venv
   .venv/bin/python -m pip install --require-hashes -r requirements/build.lock
   .venv/bin/python -m pip install --require-hashes -r requirements/dev.lock
   .venv/bin/python -m pip install --no-deps --no-build-isolation -e .
   ```

2. Install Chromium. On Linux, include its system libraries:

   ```bash
   .venv/bin/python -m playwright install --with-deps chromium
   ```

   On macOS, install Chromium:

   ```bash
   .venv/bin/python -m playwright install chromium
   ```

3. Check prerequisites and build the complete public artifact:

   ```bash
   make verify-site
   ```

The result is the complete public site under `site/`, including `site/resume.pdf`. The homepage presents the introduction and CV; `/work/` contains selected samples and publications, and `/posts/` contains the blog. The PDF prints the homepage with a compact Selected work block and visible Work and LinkedIn addresses. Compatibility redirects retain `/resume/`, `/about/`, and `/portfolio/`.

The repository vendors PaperMod as a pinned Git submodule and serves its [fonts locally](docs/fonts.md). There is no front-end package install or build step.

## Preview the site

```bash
make preview
```

Open `http://localhost:1313/`. The command builds the public site and PDF before starting Hugo with live reload. Restart it after changing `site.yaml`, `resume.yaml`, or any layout or CSS that affects the PDF.

Preview writes to `local/preview/site/` and stages its Hugo data and cache under `local/preview/`. The verified publication artifact remains in `site/`, so you can run `make verify-site` while preview is running.

Set `PREVIEW_PORT` to use another port:

```bash
make preview PREVIEW_PORT=1314
```

## Run checks

```bash
make check
make verify-site
```

`make check` runs Ruff, formatting checks, mypy, pytest, Pylint, and Vulture. Its Hugo, browser, and PDF tests use temporary directories without touching your preview.

`make verify-site` builds fresh HTML and a Chromium PDF, then validates the [publication contracts](AGENTS.md#preserve-publication-contracts). CI uploads only a passing artifact. Use `.venv/bin/python -m site_tools.verify site` to recheck existing output without rebuilding it.

During development, choose checks for the changed behavior:

| Change | Local check |
|---|---|
| Python behavior without Hugo or Chromium | `make test-unit` |
| Hugo layout, script, browser, PDF, or workflow behavior | `make check` |
| Published routes, feeds, crawler policy, privacy, or complete site output | `make verify-site` after `make check` |

Use `make test` to run the same unit and integration tests without the other quality checks, `make hugo-build` for HTML alone, and `make help` for the supported command list.

With Gitleaks installed, run the same history scan as CI:

```bash
gitleaks git --log-opts="--all --full-history -m" --redact --verbose --no-banner
```

This scans all fetched branches and tags, including merge results, and redacts matches in its diagnostics. It checks committed history; review uncommitted changes before committing them.

## Edit the public resume or profile

Use the [public resume data rules](AGENTS.md#public-resume-data) when editing these sources:

1. Apply approved resume content to `resume.yaml`, including the name, headline, summary, experience, skills, and education rendered on the homepage and in the PDF. Edit `site.yaml` for social links and identity metadata. Edit `hugo/content/work.md` for selected samples and publications; its URL supplies the CV’s Selected work link.
2. Run `make verify-site` to build and validate the public HTML and PDF.
3. [Start or restart the preview](#preview-the-site), then inspect the homepage, `/work/`, and `/resume.pdf`.
4. Commit the approved changes locally. Follow [Publish the site](#publish-the-site) when publication is authorized.

To include a phone number in a private copy, [build an application PDF](#build-an-application-pdf).

## Build an application PDF

1. Copy `resume.private.example.yaml` to the gitignored `resume.private.yaml`.
2. Replace the example `basics.phone` value.
3. Run `make resume-pdf-application`.

The command first builds and verifies the phone-free public artifact. It then writes the private PDF to `local/brad-fidler-resume.pdf`. Only this target reads the private overlay. It rejects a missing or invalid overlay and any private PDF destination inside `site/`.

## Edit and import a blog post

Keep owner-approved publication copies and selected assets in `hugo/content/posts/<slug>/`. Compare with any existing copy and preserve divergent work before replacement.

For an [authorized public draft](AGENTS.md#repository-scope), set `draft: true` and verify that its route, assets and unique text are absent from the normal site build and both feeds. Use `[nopublish]` in the pushed head commit to run checks without deploying the site.

When website publication is authorized, set `draft: false`, use the bundle directory as the canonical slug, and give a date without a time. Optional aliases must be a list of `/posts/<slug>/` paths. The verifier rejects route overrides (`url`, a different `slug`, `type`, `layout`, `outputs`, `headless`, or `build`), future dates, `publishDate`, and `expiryDate`. Both feeds must carry complete article text: published posts cannot set `hiddenInRss`, and Hugo's RSS limit must remain unlimited.

After copying approved content, inspect the diff and run `make verify-site`. Follow [Publish the site](#publish-the-site) when publication is authorized.

## Host cited sources

Before adding an archival document or page image, check for a publicly accessible complete copy of the same edition. Retrieve the file, compare its identity and page coverage with the research original, and verify any page locator. Prefer an archive's direct file URL; a catalogue entry alone is insufficient. Retain research originals and detailed retrieval evidence outside the publication tree.

Keep necessary page photographs in the published post's `scans/` bundle. Keep necessary archival PDFs in `docs/<slug>-sources/`, outside the Pages artifact to preserve the [public PDF contract](AGENTS.md#preserve-publication-contracts). Cite a raw GitHub URL pinned to a full, already published commit ID and verify the remote bytes before using it. Preserve filenames and record checksums, original-source provenance, transformations and page mappings in the post's manifest under `docs/`. Remove entries for files no longer hosted; retain provenance for externally linked documents where it substantiates a citation.

A raw PDF URL may download the file instead of opening at a page fragment, so give printed and PDF page numbers in the citation. Correct an archival file under a new filename and update the citation deliberately; do not silently replace cited bytes.

## Publish the site

A push to `main` runs the full-history secret scan, `make check`, and `make verify-site`. The workflow uploads and deploys the verified artifact from that run without rebuilding, only from this repository's protected `main` and only while the checked commit is current.

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

Pages deployment makes up to three attempts using the same artifact. If all attempts fail, inspect the failed job and the live site.

The [indexing and crawler controls](AGENTS.md#preserve-publication-contracts) depend on crawler cooperation and do not remove existing copies.

## Recover a publication

If only deployment failed, `main` has not advanced, and the checked artifact remains available, use GitHub Actions' **Re-run failed jobs** to reuse it. If the artifact expired or `main` advanced, start a new manual publication of `main`.

If published source needs correction, start with a clean checkout on `main`:

1. Inspect the offending commit. Replace `BAD_COMMIT_SHA` with its commit ID:

   ```bash
   git status --short --branch
   git log -5 --oneline
   git show BAD_COMMIT_SHA
   ```

2. Revert the change:

   ```bash
   git revert BAD_COMMIT_SHA
   ```

3. Run the [complete checks](#run-checks).
4. Publish the correction:

   ```bash
   git push origin main
   ```

Revert a multi-commit change from newest to oldest, or prepare a focused corrective commit when other work depends on it. Recovery preserves shared history and passes through the same checks as an ordinary publication.

For Wayback Machine exclusion or removal, follow the [Internet Archive's request procedure](https://archivesupport.zendesk.com/hc/en-us/articles/360004651732-Using-The-Wayback-Machine).

## Update dependencies

After changing `pyproject.toml` or `requirements/build.in`, regenerate the affected locks with uv:

```bash
uv pip compile requirements/build.in --python-version 3.11 --universal --generate-hashes -o requirements/build.lock
uv pip compile pyproject.toml --all-extras --python-version 3.11 --universal --generate-hashes --no-emit-package brfid-site -o requirements/dev.lock
```

Reinstall from the updated locks and, if Playwright changed, reinstall Chromium using the [checkout setup commands](#set-up-a-checkout). Run [the checks](#run-checks). After a Playwright update, inspect the homepage and `/resume.pdf`, since its Chromium version affects pagination.

Update the Python selection in [.github/workflows/publish.yml](.github/workflows/publish.yml); update Hugo's version in [scripts/github/setup.sh](scripts/github/setup.sh) together with its independently verified package checksum in `requirements/hugo.sha256`.

Update Gitleaks' version in `.github/workflows/publish.yml` together with `requirements/gitleaks.sha256`, checked against the upstream release's checksum file. Run the history scan after an update because detection rules may change.

For an Action update, resolve the intended release in its upstream repository to a commit, inspect its changes, and replace the full commit ID and version comment together. GitHub documents [why full commit IDs provide immutable Action references](https://docs.github.com/en/actions/reference/security/secure-use#using-third-party-actions).

Hosted runner updates and system PDF tools remain unpinned; byte-identical builds across machines are not guaranteed.

## Contribute to the site

Read [the repository rules](AGENTS.md) before editing publication behavior. Use the [Google developer documentation style guide](https://developers.google.com/style/highlights) for procedures and the [Google Python docstring guidance](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) for Python APIs. Ruff enforces the configured docstring rules and 120-character Python format.

Choose validation from [Run checks](#run-checks).

`site_tools/publication.py` reads Hugo configuration and post front matter to define source-backed routes, aliases, and resources. `site_tools/verify.py` inspects the generated artifact against those expectations and independent publication and privacy rules. Add a route through approved source data; keep safety requirements independent of the output under test.

Repository-owned templates in `hugo/layouts/` extend the pinned PaperMod theme. Footer script partials are included conditionally, so check both the template and its browser behavior when changing them.

## Source files

| Path | Function |
|---|---|
| `site.yaml` | Public name, headline, and profile links |
| `resume.yaml` | Canonical landing-page CV and PDF content |
| `hugo/` | Content, templates, configuration, styles, and fonts |
| `site_tools/`, `tests/` | Python build, PDF, prerequisite, and verification tools and their tests |
| `requirements/` | Hash-locked Python environment and Hugo/Gitleaks download checksums |
| `docs/` | Citation manifests, hosted sources, and [font provenance and licenses](docs/fonts.md) |
| `.github/workflows/publish.yml`, `scripts/github/setup.sh` | Hosted environment, checks, and Pages deployment |
