# brfid.github.io

Source and build tooling for [brfid.github.io](https://brfid.github.io/). Hugo renders the site, blog, and resume. A VAX and PDP-11 pipeline renders the landing-page bio before deployment.

## Set up a checkout

Install these prerequisites:

- Git
- Python 3.11 or newer
- Hugo extended 0.156.0 or newer
- Docker, only for the vintage pipeline

Initialize the checkout and its local Python environment:

```bash
git submodule update --init
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m playwright install chromium
make check_env
```

The repository vendors PaperMod as a Git submodule and serves self-hosted Newsreader and IBM Plex Mono fonts. It has no front-end package install or build step.

## Preview the site

```bash
make preview
```

Open `http://localhost:1313/`. The command builds the public resume page and phone-free `site/resume.pdf`, then starts Hugo with live reload. Restart it after changing `resume.yaml`, or after changing resume layout or print CSS.

Use `make preview-drafts` to include draft posts. Set `PREVIEW_PORT` to change the port:

```bash
make preview PREVIEW_PORT=1314
```

## Build an application PDF

1. Copy `resume.private.example.yaml` to the gitignored `resume.private.yaml`.
2. Replace the example `basics.phone` value.
3. Run `make resume-pdf-application`.

The command writes `local/bradley-fidler-resume.pdf`. It rejects a missing or invalid private overlay and any private PDF destination inside the public site tree. Run `make preview` afterward to restore `site/resume.pdf`.

## Run checks

```bash
make check
make verify-site
```

`make check` runs Ruff, formatting checks, mypy, pytest, Pylint, and Vulture. `make verify-site` builds Hugo in a clean directory and checks routes, feeds, structured data, navigation state, and the site-wide indexing policy. CI runs both commands.

Use `make test` to run pytest without the other checks. Use `make help` to list all supported targets.

## Build the public site

```bash
make hugo-build
```

The command syncs the public YAML inputs and writes a clean build to `site/`. Use `make resume-pdf` to add the public PDF.

Every rendered HTML page contains `noindex, nofollow, noarchive, nosnippet, noimageindex`. Hugo emits no sitemap. `robots.txt` leaves HTML crawlable so crawlers can read the page-level directive and blocks the PDF, feeds, and pipeline status.

## Add a blog post

Create a draft page bundle:

```bash
make new-post POST_SLUG=maintenance-window
```

Edit `hugo/content/posts/maintenance-window/index.md` and place referenced assets beside it. Production publishes the post only after its front matter sets `draft: false`.

Working drafts stay outside this public repository. Add only approved copy and public assets.

## Vintage pipeline

The pipeline transforms three public strings into the landing bio:

`site.yaml` name and headline plus `resume.yaml` `basics.summary` -> VAX troff -> PDP-11 `nroff` -> `brad.bio.txt` -> Hugo data

For local execution, validation, implementation, and image promotion, see [the vintage pipeline operations guide](docs/integration/INDEX.md).

## Publish the site

A push to `main` runs the vintage pipeline, builds Hugo and the public PDF, verifies the published contracts, and deploys to GitHub Pages. Add `[nopublish]` to the commit message to skip deployment. Run the Publish site workflow manually to repeat a deployment without a new commit.

Production accepts only the immutable VAX and PDP-11 image digests pinned in `scripts/edcloud-vintage-runner.sh`. It does not build fallback images.

## Source files

| Path | Function |
|---|---|
| `site.yaml` | Public name, headline, and profile links |
| `resume.yaml` | Public resume data and shared bio summary |
| `resume.private.yaml` | Optional local phone overlay; gitignored |
| `hugo/` | Site content, templates, configuration, styles, and fonts |
| `resume_generator/` | Bio, build-log, vintage-contract, and PDF generators |
| `scripts/` | Site verifier and SIMH orchestration |
| `STATUS.md` | Current operational state and queue |
| `docs/integration/INDEX.md` | Vintage pipeline operations |
| `docs/archive/` | Retired-path registry; not operating guidance |
