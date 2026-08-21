# brfid.github.io

Source for [brfid.github.io](https://brfid.github.io/), a Hugo-based personal site, blog, and resume deployed to GitHub Pages.

The live site is built and deployed via a Hugo + vintage computing pipeline (VAX/PDP-11 via SIMH). The vintage pipeline generates rendered artifacts that Hugo includes in the final build.

## Hugo

Public landing content lives in `site.yaml`; Hugo templates and assets live under `hugo/`. The site builds with Hugo extended ≥ 0.156.0 (ARM64 binary available from Hugo releases).

Front-end assets are vendored, not fetched at build or view time: the Newsreader and IBM Plex Mono fonts ship as woff2 files in `hugo/static/fonts/` (self-hosted via `@font-face`, no CDN) and custom styles live in `hugo/assets/css/extended/`. Hugo bundles both — there is no separate asset build step.

Every HTML surface carries a site-wide `noindex, nofollow` robots directive, including blog posts, the resume, and the generated vintage build log, and Hugo does not publish a sitemap. `robots.txt` leaves HTML crawlable so search engines can observe `noindex`; it blocks the machine-readable pipeline status, public resume PDF, and RSS feeds. The deploy workflow fails if any published HTML omits the directive or a sitemap reappears.

### Local preview

```bash
make preview
```

Open `http://localhost:1313/`. The preview command syncs `site.yaml` and `resume.yaml`, builds the public resume HTML and phone-free `site/resume.pdf`, and runs Hugo from that output directory. It is production-equivalent by default, and neither output reads the private phone overlay. Files under `hugo/` live-reload. Restart `make preview` after changing `resume.yaml`, or after layout and CSS changes when the PDF itself also needs to be regenerated.

To generate the application PDF with a phone number, copy `resume.private.example.yaml` to the gitignored `resume.private.yaml`, edit the value, and run `make resume-pdf-application`. That explicit target writes `local/bradley-fidler-resume.pdf` outside the served and deployed `site/` tree. Run `make preview` again afterward because the application build refreshes `site/`. `make preview-public` remains as a compatibility alias for the same phone-free preview. Set `PREVIEW_PORT` to use a different port, for example `make preview PREVIEW_PORT=1314`.

### Build to `site/`

```bash
hugo --source hugo --destination ../site
```

Note: `--destination` is relative to the source directory, so `../site` writes to `site/` at the repo root.

**Publish:** pushing to `main` runs the vintage pipeline, builds the public resume HTML and phone-free PDF, verifies their navigation and privacy boundaries, and deploys the complete site to GitHub Pages. To skip a deploy, include `[nopublish]` anywhere in the commit message. `workflow_dispatch` is available for manual re-runs without a new commit.

### Blog posts

Published posts are Hugo page bundles under `hugo/content/posts/<slug>/`. Create a draft bundle with `make new-post POST_SLUG=<slug>`, put the post in its generated `index.md`, and place any referenced images beside it. The scaffold is a draft by default; `make preview-drafts` includes it locally, while production ignores it until its front matter sets `draft: false`.

Working essay sources stay in the private career repository. Only approved publish copy and its public assets cross into this public repository. The Blog index is `/posts/`; RSS is available at the historical `/index.xml` route and the section-specific `/posts/index.xml` route.

## Vintage pipeline (publish path)

The vintage pipeline's sole content artifact is the landing-page bio. The resume does not pass through the emulators; Hugo renders its HTML and Playwright prints the public PDF separately during the same production job:

- `build/vintage/brad.bio.txt` is the landing bio: `bradman.c` composes it as troff on the VAX, and the PDP-11 runs `nroff` to fill and justify it.
- `hugo/data/bio.yaml` is generated from `brad.bio.txt` and consumed by the landing template; it is not published as a file.
- `hugo/static/build.log.html` is the published machine-boundary build log with VAX and PDP-11 console sections, rendered by `resume_generator/build_log.py`.
- `hugo/static/pipeline-status.json` is the machine-readable result, build identity, commit, completion time, and per-stage artifact counts.

`site.yaml` owns the public identity (name, headline) and icon links; the landing bio text lives in `resume.yaml`'s `basics.summary`, shared with the resume Summary and PDF. The pipeline flattens the identity from `site.yaml` and that summary from `resume.yaml` into `build/vintage/bio.vintage.yaml`; the link list goes directly to Hugo. Only `basics.summary` enters this pipeline; the rest of the resume document (work, skills, etc.) does not.

The pipeline uses **pexpect** to drive SIMH emulators via stdin/stdout (no telnet ports, no sleep-based timing):

- **Stage B**: VAX (4.3BSD) compiles and runs `bradman.c` to generate `brad.bio.roff` (troff) from `bio.vintage.yaml`, then uuencodes it to `brad.bio.uu` (`scripts/vax_pexpect.py`)
- **Stage A**: PDP-11 (2.11BSD) uudecodes the spool and runs `nroff` (no macro package) to fill and justify `brad.bio.roff` → `brad.bio.txt` (`scripts/pdp11_pexpect.py`)
- **Stage A+B**: VAX generates, host couriers the spool, PDP-11 renders

Both stages are implemented and validated on `main`. See `git log` for validation history.

See `docs/integration/INDEX.md` for design details.

### Setup

Use Python 3.11 or newer.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m playwright install chromium
```

Run `make help` to list common commands for tests, the Hugo build, and resume generation.

### Quality checks

```bash
make check
```

`make check` is the shared local and CI quality gate: Ruff lint and format checks, mypy, all non-Docker/non-slow tests, Pylint, and Vulture. Use `make test` when only the fast test suite is needed.

### Publish path

`deploy.yml` runs the whole publish path on the `ubuntu-latest` runner itself: the vintage pipeline, Hugo build, phone-free resume PDF generation, privacy checks, and Pages deploy. There is no execution host to start or stop and no cloud account involved.

```bash
bash scripts/edcloud-vintage-runner.sh "build-$(date -u +%Y%m%d-%H%M%S)" > /tmp/stdout.txt
```

That single line is the whole pipeline invocation. The runner does `exec 3>&1` before redirecting its own stdout to a log file, so redirecting it to a file puts the base64 artifact markers on the parent's stdout while the verbose pipeline log stays in `$LOG_DIR`, which is how CI extracts artifacts with `awk`.

Single orchestration entrypoint: `scripts/edcloud-vintage-runner.sh` (the `edcloud` in the name is vestigial; it has no cloud coupling). Prebuilt GHCR images provide the emulators and disk images, while the runner bind-mounts the current checkout's pexpect scripts and shared session helper over the copies baked into those images. This keeps cached infrastructure from silently pinning older orchestration code. Set `KEEP_IMAGES=1` to preserve Docker images between runs (avoids rebuild on retry).

**Historically (until 2026-07-25):** CI authenticated to AWS, started an EC2 instance ("edcloud"), ran the same script there over SSM, and extracted the artifacts from the SSM output. That account was decommissioned; the `brfid/edcloud` repo is retained but no longer provisions anything for this site: [brfid/edcloud](https://github.com/brfid/edcloud).

### Testing the pipeline without publishing

`.github/workflows/vintage-validate.yml` (`workflow_dispatch` only) runs the pipeline on a hosted runner, publishes nothing, verifies that the rendered bio round-trips the public fields in `site.yaml` (name and headline verbatim) and `resume.yaml` (`basics.summary` word-for-word since nroff reflows it), and optionally compares `brad.bio.txt` against a known-good hash. SIMH emulates the guest CPU deterministically, so an unchanged render is evidence that a host or toolchain change was inert.

```bash
# Record the current hash, comparing against nothing
gh workflow run vintage-validate.yml --ref main

# Compare against a recorded baseline
gh workflow run vintage-validate.yml --ref main \
  -f expected_sha256=<recorded-hash>
```

The bio carries no date (`bradman` stamps the build date only in a troff comment, which `nroff` strips), so its raw SHA256 is stable across runs and directly comparable to a baseline. The baseline is tied to the current `site.yaml`; update it when the landing copy changes.

Artifacts and the full pipeline log are uploaded on success and failure alike.

### Vintage pipeline prerequisites

- `docker`, `git`, `python3` on the host. Nothing else — no AWS, no secrets.
- Pre-built images pulled from `ghcr.io/brfid/{vax,pdp11}-pexpect:latest`, with a local `docker build` fallback. **Both are amd64-only**, so they run natively on `ubuntu-latest` but require emulation (or a multi-arch rebuild) on an arm64 Mac.

## Source of truth

| Doc | Role |
|-----|------|
| `STATUS.md` | Operational state for site, pipeline, resume surfaces; procedure and active ops priorities |
| `~/src/career/STATUS.md` | Strategic arc (sequencing, posture, when/why phases run) that gates this site's reactivation |
| `docs/integration/INDEX.md` | Vintage pipeline design, stages, artifacts, constraints |

## Cold start order

1. This file
2. `STATUS.md`
3. `hugo/` (Hugo site root — theme, content, config)
4. `~/src/career/STATUS.md` (only if touching site reactivation, resume surfaces, or any phase-gated work)

Then apply `AGENTS.md` constraints.
