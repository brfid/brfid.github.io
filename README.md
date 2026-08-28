# brfid.gitlab.io

Source and build tooling for [brfid.gitlab.io](https://brfid.gitlab.io/). Hugo renders the site, blog, and resume. A VAX and PDP-11 pipeline renders the landing-page bio published by the site.

## Set up a checkout

Install these prerequisites:

- Git
- GitLab CLI (`glab`), only for starting manual pipelines
- Python 3.11 or newer
- Hugo extended 0.156.0 or newer
- Docker, only for the vintage pipeline

Initialize the checkout and its local Python environment:

```bash
git submodule update --init
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,pdf]'
.venv/bin/python -m playwright install chromium
make check_env
```

The repository vendors PaperMod as a Git submodule and serves self-hosted Newsreader and IBM Plex Mono fonts. It has no front-end package install or build step.

## Preview the site

```bash
make preview
```

Open `http://localhost:1313/`. The command clears deployment-only provenance inputs, builds the public resume page and phone-free `site/resume.pdf`, then starts Hugo with live reload. Restart it after changing `resume.yaml`, or after changing resume layout or print CSS.

Use `make preview-drafts` to include draft posts. Set `PREVIEW_PORT` to change the port:

```bash
make preview PREVIEW_PORT=1314
```

## Build an application PDF

1. Copy `resume.private.example.yaml` to the gitignored `resume.private.yaml`.
2. Replace the example `basics.phone` value.
3. Run `make resume-pdf-application`.

The command leaves a complete phone-free public build under `site/` and writes the private PDF to `local/bradley-fidler-resume.pdf`. It rejects a missing or invalid private overlay and any private PDF destination inside the public site tree.

## Run checks

```bash
make check
make verify-site
```

`make check` runs Ruff, formatting checks, mypy, pytest, Pylint, and Vulture. `make verify-site` clears deployment-only provenance inputs, builds Hugo in a clean directory, and checks routes, feeds, linked artifacts, structured data, navigation state, and the site-wide indexing policy. CI runs both commands.

Use `make test` to run pytest without the other checks. Use `make help` to list all supported targets.

## Build the public site

```bash
make hugo-build
```

The command clears deployment-only provenance inputs, syncs the public YAML inputs, and writes a clean build to `site/`. Use `make resume-pdf` to add the public PDF. Deployment uses the separate `resume-pdf-public` target, which fails unless the vintage bio, build log, and pipeline status have all been staged.

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

Before starting a manual pipeline, authenticate `glab` with `glab auth login --hostname gitlab.com` and verify it with `glab auth status`.

A push to `main` uses standard mode: GitLab CI runs the checks and secret scan, executes the vintage pipeline, builds Hugo and the public PDF, verifies the published contracts, and deploys to GitLab Pages. Add `[nopublish]` to the commit message to run checks without publishing.

For any change that does not affect the landing-page bio, such as a post, layout, or resume field other than `basics.summary`, add `[fast]` to the commit message to select fast mode:

```bash
git commit -m "Publish site-only change [fast]"
git push origin main
```

You can request the same path manually:

```bash
glab ci run --branch main \
  --variables-env OPERATION:publish \
  --variables-env PUBLISH_MODE:fast
```

Fast mode reuses the exact bio, build log, and pipeline status from the newest matching successful standard publication, and keeps the GitLab pipeline link pointed at that source. GitLab retains the fingerprinted bundle for 90 days. Fast mode still rebuilds the public PDF and Hugo site, runs the production verifier, and deploys a new Pages artifact. It fails without deploying if the retained result has expired, its manifest or provenance is invalid, or a bio input or vintage implementation file has changed.

Run standard mode to produce a fresh retained result:

```bash
glab ci run --branch main \
  --variables-env OPERATION:publish \
  --variables-env PUBLISH_MODE:standard
```

In standard mode, the vintage pipeline uses only the immutable VAX and PDP-11 image digests pinned in `scripts/vintage-runner.sh`. It does not build fallback images.

## Source files

| Path | Function |
|---|---|
| `site.yaml` | Public name, headline, and profile links |
| `resume.yaml` | Public resume data and shared bio summary |
| `resume.private.yaml` | Optional local phone overlay; gitignored |
| `hugo/` | Site content, templates, configuration, styles, and fonts |
| `resume_generator/` | Bio, vintage validation and reuse, build-log, and PDF generators |
| `.gitlab-ci.yml` | GitLab checks, publication, validation, and image-build jobs |
| `scripts/` | Site verifier, GitLab job scripts, and SIMH orchestration |
| `STATUS.md` | Current operational state and queue |
| `docs/integration/INDEX.md` | Vintage pipeline operations |
| `docs/archive/` | Retired-path registry; not operating guidance |
