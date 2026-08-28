# Operate the vintage pipeline

Use this page to run, validate, and promote the VAX and PDP-11 pipeline. For console behavior and failure diagnosis, see [the pexpect implementation reference](operations/PEXPECT-PIPELINE-SPEC.md).

The pipeline's only page-content output is the landing-page bio. Hugo and Playwright render the resume separately.

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

Production and the validation workflow set `ALLOW_LOCAL_IMAGE_BUILD=0`.

## Data flow

`site.yaml` supplies `name` and `headline`. `resume.yaml` supplies `basics.summary`. `resume_generator/vintage_yaml.py` writes these values to `build/vintage/bio.vintage.yaml` as five ordered, quoted ASCII scalars: `schemaVersion`, `buildDate`, `bioName`, `bioHeadline`, and `bioProfile`.

| Stage | Machine | Operation | Output |
|---|---|---|---|
| B | VAX 4.3BSD | Compile and run `bradman.c`, then `uuencode` its troff output | `brad.bio.uu` |
| A | PDP-11 2.11BSD | `uudecode` the spool, then run `nroff -Tlp` | `brad.bio.txt` |
| Runner finalization | Local or GitLab runner | Record status and render the host and guest log | `pipeline-status.json`, `build.log.html` |
| Deployment job | GitLab runner | Produce or retrieve a matching result, validate it, and stage the three final artifacts for Hugo | `hugo/data/bio.yaml`, published log and status |

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
| `hugo/data/bio.yaml` | Deployment output | Flowing bio text and build provenance |
| `hugo/static/build.log.html` | Deployment output | Published copy of the final build log |
| `hugo/static/pipeline-status.json` | Deployment output | Published copy of the final status |

The runner removes the generated files it owns before every run. After environment setup, a failed stage writes `result: failure` with the current build ID and exit code, preventing a retry from reusing a prior success. Deployment copies only a successful run's final artifacts into Hugo.

## Reuse a successful production result

Standard mode uploads `brad.bio.txt`, `build.log.html`, and `pipeline-status.json` under `reusable-vintage/FINGERPRINT/` in the successful `publish-standard` job artifact. A manifest binds their checksums to the source commit, pipeline, ref, project, and reuse fingerprint. GitLab retains that artifact for 90 days, and the project disables indefinite retention of the latest successful artifact.

Fast mode, selected by `[fast]` in a pushed commit or `PUBLISH_MODE=fast` in a manual pipeline, searches successful standard publications on `main` through GitLab's public API. It selects the newest artifact whose path matches the current fingerprint, validates the manifest and all three checksums, then verifies that the status records the source commit, that the log and status name the same build, and that the rendered bio still matches the current public source strings.

The deployment preserves the result's log, status, and build ID, and keeps the GitLab pipeline link pointed at its source pipeline. Hugo and the public PDF are rebuilt from the current commit and deployed through the normal production verifier. The raw `brad.bio.txt` remains an internal Pages input; GitLab retains it only in the public CI artifact.

Fast mode fails closed when no valid matching artifact is available. Run a standard publication to produce and retain a fresh result; fast mode never invents new provenance or silently runs the vintage pipeline.

## Console contracts

- `pexpect` spawns SIMH directly through a pseudo-terminal. The pipeline opens no telnet port and uses no Compose service.
- State transitions wait for explicit console output. A 5 ms delay between heredoc lines throttles transport into the guest tty; it does not determine state.
- Artifact-producing guest commands use `run_checked()` and must return status `0` before the pipeline continues.
- The checkout's VAX and PDP-11 scripts and `simh_session.py` are bind-mounted over the copies in cached images.
- The VAX produces the UUCP spool. The host preserves it as text and injects it into the PDP-11 in short heredoc batches.
- The runner and workflows hand off the final files directly under `build/vintage/`; stdout is diagnostic only.

## Validate without publishing

Push the branch and authenticate `glab`, then start a manual vintage-validation pipeline to exercise direct artifact collection, semantic comparison, status generation, and artifact upload:

```bash
BRANCH="$(git branch --show-current)"
glab ci run --branch "$BRANCH" \
  --variables-env OPERATION:vintage-validation
```

To compare the rendered bio with a prior run, add `--variables-env EXPECTED_VINTAGE_SHA256:EXPECTED_SHA256` and replace `EXPECTED_SHA256` with the recorded digest. Change the baseline when the public name, headline, or summary changes. With the same public input, orchestration, and pinned image pair, the rendered bio is byte-stable because it contains no build date.

## Promote emulator images

Use this procedure after changing an emulator Dockerfile, configuration, base image, dependency, or disk image:

1. Push the branch and run the image-build pipeline:

   ```bash
   BRANCH="$(git branch --show-current)"
   glab ci run --branch "$BRANCH" \
     --variables-env OPERATION:image-build
   ```

2. Copy both immutable references from `out/image-pair.json` in the successful `image-build` job artifact.
3. Update both `PINNED_VAX` and `PINNED_PDP11` in `scripts/vintage-runner.sh` so the release records an explicit pair.
4. Push the digest update and run the vintage-validation command above.
5. Inspect `pipeline-status.json`, `brad.bio.txt`, `build.log.html`, and the console-section artifact.
6. Merge only after validation succeeds.

The image-build job publishes source-commit tags under `registry.gitlab.com/brfid/brfid.gitlab.io/` for discovery. Deployment uses only the pinned digests and never waits for an image build. The Dockerfiles pin their base images by digest. The PDP-11 recipe downloads the versioned `211bsd-rpethset` package from this project's public GitLab Generic Package Registry and verifies checksum `74678c649338b10bfc470b4fec4bd75b649b4df1e3eb5a9f227ed7ac7d947b42` before extraction.

### Restore the PDP-11 disk package

If the `211bsd-rpethset` package is missing from GitLab, download the original archive, verify it, and upload the verified bytes:

```bash
curl --fail --location --show-error \
  --output 211bsd_rpethset.tgz \
  https://www.retro11.de/data/oc_w11/oskits/211bsd_rpethset.tgz
printf '%s  %s\n' \
  '74678c649338b10bfc470b4fec4bd75b649b4df1e3eb5a9f227ed7ac7d947b42' \
  '211bsd_rpethset.tgz' | shasum --algorithm 256 --check
glab api --method PUT \
  --header 'Content-Type: application/octet-stream' \
  --input 211bsd_rpethset.tgz \
  --silent \
  projects/85834009/packages/generic/211bsd-rpethset/2019-05-30/211bsd_rpethset.tgz
```

Delete the local archive after the upload. Confirm that the package remains anonymously downloadable before starting `image-build`; the Docker build does not use GitLab credentials to retrieve it.

## References

- [`pexpect` implementation reference](operations/PEXPECT-PIPELINE-SPEC.md)
- [VAX stage and guest input contract](../vax/README.md)
- [Reuse fingerprint and bundle validator](../../resume_generator/vintage_reuse.py)
- [Pipeline runner](../../scripts/vintage-runner.sh)
- [Retired approaches](../archive/DEAD-ENDS.md)
