# Operate the vintage pipeline

Use this page to run, validate, and promote the VAX and PDP-11 pipeline retained in this GitHub repository. For current production operations, use [the active GitLab repository’s guide](https://gitlab.com/brfid/brfid.gitlab.io/-/blob/main/docs/integration/INDEX.md). For console behavior and failure diagnosis, see [the pexpect implementation reference](operations/PEXPECT-PIPELINE-SPEC.md).

The pipeline’s former page-content output was the landing-page bio. Hugo and Playwright rendered the resume separately.

## Run the pipeline locally

Install Git and Python 3.11 or newer, then start Docker. Run the command from the repository root:

```bash
DOCKER_DEFAULT_PLATFORM=linux/amd64 \
  ALLOW_LOCAL_IMAGE_BUILD=0 \
  bash scripts/vintage-runner.sh \
  "local-$(date -u +%Y%m%d-%H%M%S)"
```

This command uses the immutable production image pair. Remove `ALLOW_LOCAL_IMAGE_BUILD=0` to let a failed pull build the checked-out Dockerfiles for local development.

The runner writes intermediate and final artifacts to `build/vintage/`, detailed logs to `/tmp/edcloud-vintage/`, and a concise completion message or failure tail to stdout. It creates `.venv/` and installs the package only when the existing environment cannot import the pipeline dependencies.

### Runner environment

| Variable | Default | Function |
|---|---|---|
| `ROOT_DIR` | Current directory | Repository root |
| `LOG_DIR` | `/tmp/edcloud-vintage` | Host log directory |
| `KEEP_IMAGES` | `0` | Keep local VAX and PDP-11 image tags after the run when set to `1` |
| `ALLOW_LOCAL_IMAGE_BUILD` | `1` | Build checked-out image recipes after a pinned-image pull fails |
| `GIT_SHA` | Current commit | Commit recorded in `pipeline-status.json` |

The hosted validation workflow sets `ALLOW_LOCAL_IMAGE_BUILD=0`.

## Data flow

`site.yaml` supplies `name` and `headline`. `resume.yaml` supplies `basics.summary`. `resume_generator/vintage_yaml.py` writes these values to `build/vintage/bio.vintage.yaml` as five ordered, quoted ASCII scalars: `schemaVersion`, `buildDate`, `bioName`, `bioHeadline`, and `bioProfile`.

| Stage | Machine | Operation | Output |
|---|---|---|---|
| B | VAX 4.3BSD | Compile and run `bradman.c`, then `uuencode` its troff output | `brad.bio.uu` |
| A | PDP-11 2.11BSD | `uudecode` the spool, then run `nroff -Tlp` | `brad.bio.txt` |
| Runner finalization | Local or GitHub runner | Record status and render the host and guest log | `pipeline-status.json`, `build.log.html` |
| Former deployment integration | Retained code | Validate a result and stage the three final artifacts for Hugo | `hugo/data/bio.yaml`, build log, and status |

The host transfers the spool between guests. The PDP-11 `unix` kernel has no working Ethernet.

`resume_generator/vintage_contract.py` requires nonempty, single-line, printable ASCII inputs. It compares the rendered name and headline exactly and compares the summary after whitespace normalization. `resume_generator/bio_yaml.py` removes the fixed-width fill and justification before Hugo renders the summary as flowing prose.

## Artifacts

| Path | Scope | Function |
|---|---|---|
| `build/vintage/bio.vintage.yaml` | Internal | Fixed guest input contract |
| `build/vintage/brad.bio.uu` | Internal | VAX-generated UUCP spool |
| `build/vintage/brad.bio.txt` | Final | PDP-11-rendered bio |
| `build/vintage/build.log.html` | Final | Host and guest build log |
| `build/vintage/sections.jsonl` | Internal | Named guest-console sections |
| `build/vintage/pipeline-status.json` | Final | Vintage pipeline result and stage counts |
| `hugo/data/bio.yaml` | Former deployment output | Flowing bio text and build provenance |
| `hugo/static/build.log.html` | Former deployment output | Copy of the final build log |
| `hugo/static/pipeline-status.json` | Former deployment output | Copy of the final status |

The runner removes the generated files it owns before every run. After environment setup, a failed stage writes `result: failure` with the current build ID and exit code, preventing a retry from reusing a prior success. The former deployment copied only a successful run’s final artifacts into Hugo.

## Production boundary

This GitHub repository no longer produces or reuses vintage results during Pages deployment. Its Pages workflow builds only the redirect under `redirect/`; the former standard and fast publication modes are retired here.

Use the active GitLab repository for current site publication and vintage-result reuse. The GitHub `vintage-validate.yml` workflow remains a manual, non-publishing way to exercise this retained implementation.

## Console contracts

- `pexpect` spawns SIMH directly through a pseudo-terminal. The pipeline opens no telnet port and uses no Compose service.
- State transitions wait for explicit console output. A 5 ms delay between heredoc lines throttles transport into the guest tty; it does not determine state.
- Artifact-producing guest commands use `run_checked()` and must return status `0` before the pipeline continues.
- The checkout's VAX and PDP-11 scripts and `simh_session.py` are bind-mounted over the copies in cached images.
- The VAX produces the UUCP spool. The host preserves it as text and injects it into the PDP-11 in short heredoc batches.
- The runner and workflows hand off the final files directly under `build/vintage/`; stdout is diagnostic only.

## Validate without publishing

Push the branch and authenticate the GitHub CLI with permission to run Actions workflows. Then run the manual validation workflow to exercise direct artifact collection, semantic comparison, status generation, and artifact upload:

```bash
BRANCH="$(git branch --show-current)"
gh workflow run vintage-validate.yml --ref "$BRANCH"
```

To compare the rendered bio with a prior run, add `-f expected_sha256=EXPECTED_SHA256` and replace `EXPECTED_SHA256` with the recorded digest. Change the baseline when the public name, headline, or summary changes. With the same public input, orchestration, and pinned image pair, the rendered bio is byte-stable because it contains no build date.

## Promote emulator images

Use this procedure after changing an emulator Dockerfile, configuration, base image, dependency, or disk image:

1. Push the branch and run the image workflow:

   ```bash
   BRANCH="$(git branch --show-current)"
   gh workflow run build-images.yml --ref "$BRANCH"
   ```

2. Copy both image digests from the workflow summary.
3. Update both `GHCR_VAX` and `GHCR_PDP11` in `scripts/vintage-runner.sh` so the release records an explicit pair.
4. Push the digest update and run `gh workflow run vintage-validate.yml --ref "$(git branch --show-current)"`.
5. Inspect `pipeline-status.json`, `brad.bio.txt`, `build.log.html`, and the console-section artifact.
6. Merge only after validation succeeds.

`build-images.yml` publishes source-commit tags for discovery. Hosted validation uses only the pinned digests and never waits for an image build. The Dockerfiles pin their base images by digest, and the PDP-11 recipe verifies the downloaded disk archive before extraction.

## References

- [`pexpect` implementation reference](operations/PEXPECT-PIPELINE-SPEC.md)
- [VAX stage and guest input contract](../vax/README.md)
- [Retained reuse fingerprint and bundle validator](../../resume_generator/vintage_reuse.py)
- [Pipeline runner](../../scripts/vintage-runner.sh)
- [Retired approaches](../archive/DEAD-ENDS.md)
