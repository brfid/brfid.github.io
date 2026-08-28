# brfid.github.io

This public repository retains the history and implementation of the former `brfid.github.io` site, including its Hugo resume and VAX/PDP-11 bio pipeline. The active source is [brfid/brfid.gitlab.io](https://gitlab.com/brfid/brfid.gitlab.io), and the active site is [brfid.gitlab.io](https://brfid.gitlab.io/).

GitHub Pages now publishes only a path-preserving redirect from `https://brfid.github.io/` to the GitLab site. It does not publish the retained site, resume PDF, feeds, or vintage provenance artifacts.

## Build and verify the redirect

Install Git, Python 3.11 or newer, and Hugo extended 0.163.3 or newer. Then create the local Python environment and verify a clean redirect build:

```bash
python3 -m venv .venv
make verify-redirect
```

The command builds `redirect/` into the ignored `site/` directory and runs `scripts/verify_redirect.py`. The verifier accepts only the intended HTML redirects and `robots.txt`; it rejects the former site artifacts and any unexpected output.

Preview the redirect locally when changing its presentation:

```bash
make redirect-preview
```

Open `http://localhost:1313/`. The JavaScript redirect will immediately send your browser to the GitLab site, so disable JavaScript temporarily if you need to inspect the fallback page.

## Redirect behavior

Hugo renders explicit redirects for `/`, `/resume/`, `/about/`, `/posts/`, and the two formerly published post routes. It also renders `404.html`, which lets an unknown GitHub Pages path carry its pathname, query, and fragment to the same path on `brfid.gitlab.io` in a browser.

GitHub Pages cannot return a server-side redirect from this repository. Known routes therefore use both JavaScript and a meta refresh. Unknown routes first receive GitHub Pages’ HTTP 404 response, then JavaScript performs the path-preserving transfer; without JavaScript, the 404 page’s fallback leads to the GitLab root.

Every rendered HTML page retains `noindex, nofollow, noarchive, nosnippet, noimageindex`. Hugo emits no feeds, sitemap, taxonomy, PDF, or provenance files. `robots.txt` leaves the HTML crawlable so crawlers can observe the page-level directive.

## Publish the redirect

A push to `main` runs `.github/workflows/deploy.yml`. The workflow checks out without submodules, builds only `redirect/`, verifies the exact artifact tree, and deploys it to GitHub Pages. It never invokes the retained full-site, PDF, or vintage build paths.

## Work with the retained implementation

The former implementation remains available for inspection and historical validation. It is not the production source for the current site.

To run its checks, initialize the PaperMod submodule and install the development and PDF dependencies:

```bash
git submodule update --init
.venv/bin/python -m pip install -e '.[dev,pdf]'
.venv/bin/python -m playwright install chromium
make check
make verify-site
```

For the VAX and PDP-11 implementation, see [the vintage pipeline operations guide](docs/integration/INDEX.md). The manual image-build and vintage-validation workflows remain available, but neither workflow publishes GitHub Pages.

## Source files

| Path | Function |
|---|---|
| `redirect/` | Hugo source for the GitHub Pages redirect |
| `scripts/verify_redirect.py` | Redirect artifact allowlist and contract verifier |
| `.github/workflows/deploy.yml` | Redirect-only GitHub Pages deployment |
| `hugo/` | Retained former site source |
| `resume_generator/` | Retained bio, provenance, and PDF tooling |
| `scripts/` | Redirect verifier plus retained site and SIMH orchestration |
| `vintage/` | Retained VAX and PDP-11 image definitions and guest inputs |
| `docs/integration/INDEX.md` | Vintage pipeline operations |
| `STATUS.md` | Current repository posture and queue |
