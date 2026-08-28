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

This command uses the immutable production image pair. If a promoted-image pull fails and `ALLOW_LOCAL_IMAGE_BUILD` is `1`, the runner rebuilds both images from the checkout; it never mixes a pulled image with a local image. To test changed image-owned source before promotion, set both `BUILD_LOCAL_IMAGE_PAIR=1` and `ALLOW_LOCAL_IMAGE_BUILD=1`; that explicit mode skips the promoted manifest and builds the complete pair locally.

The runner writes each guest’s output to an isolated stage directory under `build/vintage/stages/`, validates regular nonempty files, and copies only expected handoff artifacts into `build/vintage/`. It writes detailed logs to `/tmp/edcloud-vintage/` and a concise completion message or failure tail to stdout. For a standalone local run, it creates `.venv/` from the committed hash locks only when the existing environment cannot import the pipeline dependencies.

### Runner environment

| Variable | Default | Function |
|---|---|---|
| `ROOT_DIR` | Current directory | Repository root |
| `LOG_DIR` | `/tmp/edcloud-vintage` | Host log directory |
| `KEEP_IMAGES` | `0` | Keep local VAX and PDP-11 image tags after the run when set to `1` |
| `ALLOW_LOCAL_IMAGE_BUILD` | `1` | Build checked-out image recipes after a pinned-image pull fails |
| `ALLOW_ENVIRONMENT_BOOTSTRAP` | `1` | Create `.venv/` from the committed build and runtime locks when the environment is incomplete |
| `BUILD_LOCAL_IMAGE_PAIR` | `0` | Build both images from changed checkout source without loading the promoted manifest when set to `1` |
| `GIT_SHA` | Current commit | Commit recorded in `pipeline-status.json` |

Production and the validation workflow set both allow flags and `BUILD_LOCAL_IMAGE_PAIR` to `0`; their setup job must prepare the environment before the runner starts.

## Data flow

`site.yaml` supplies `name` and `headline`. `resume.yaml` supplies `basics.summary`. `resume_generator/vintage_yaml.py` writes these values to `build/vintage/bio.vintage.yaml` as five ordered, quoted ASCII scalars: `schemaVersion`, `buildDate`, `bioName`, `bioHeadline`, and `bioProfile`.

| Stage | Machine | Operation | Output |
|---|---|---|---|
| B | VAX 4.3BSD | Read two mounted inputs, compile and run `bradman.c`, then `uuencode` its troff output | `stages/vax/brad.bio.uu` |
| Host handoff | Local or GitLab runner | Validate and copy the VAX spool into the PDP-11 read-only input mount | `brad.bio.uu` |
| A | PDP-11 2.11BSD | `uudecode` the spool, then run `nroff -Tlp` | `stages/pdp11/brad.bio.txt` |
| Runner finalization | Local or GitLab runner | Record status and render the host and guest log | `pipeline-status.json`, `build.log.html` |
| Deployment job | GitLab runner | Produce or retrieve a matching result, validate it, and stage the three final artifacts for Hugo | `hugo/data/bio.yaml`, published log and status |

The host transfers the spool between guests. The PDP-11 `unix` kernel has no working Ethernet.

`resume_generator/vintage_contract.py` requires nonempty, single-line, printable ASCII inputs. It compares the rendered name and headline exactly and compares the summary after whitespace normalization. `resume_generator/bio_yaml.py` removes the fixed-width fill and justification before Hugo renders the summary as flowing prose.

## Artifacts

| Path | Scope | Function |
|---|---|---|
| `build/vintage/bio.vintage.yaml` | Internal | Fixed guest input contract |
| `build/vintage/stages/vax/` | Internal | VAX-only output mount |
| `build/vintage/brad.bio.uu` | Internal | Host-validated VAX spool used as the PDP-11 input |
| `build/vintage/stages/pdp11/` | Internal | PDP-11-only output mount |
| `build/vintage/brad.bio.txt` | Final | Host-validated PDP-11-rendered bio |
| `build/vintage/build.log.html` | Final | Host and guest build log |
| `build/vintage/sections.jsonl` | Internal | Named guest-console sections |
| `build/vintage/pipeline-status.json` | Final | Vintage pipeline result and stage counts |
| `hugo/data/bio.yaml` | Deployment output | Flowing bio text and build provenance |
| `hugo/static/build.log.html` | Deployment output | Published copy of the final build log |
| `hugo/static/pipeline-status.json` | Deployment output | Published copy of the final status |

The runner removes the generated files it owns before every run. After environment setup, a failed stage writes `result: failure` with the current build ID and exit code, preventing a retry from reusing a prior success. Deployment copies only a successful run's final artifacts into Hugo.

## Reuse a successful production result

Standard mode uploads `brad.bio.txt`, `build.log.html`, and `pipeline-status.json` under `reusable-vintage/FINGERPRINT/` in the successful `publish-standard` job artifact. A manifest binds their checksums to the source commit, pipeline, ref, project, and reuse fingerprint. GitLab retains that artifact for 90 days, and the project disables indefinite retention of the latest successful artifact.

Fast mode, selected by `[fast]` in a pushed commit or the typed `publish_mode:fast` manual input, searches successful standard publications on `main` through GitLab's public API. The fingerprint recursively enumerates tracked and nonignored files in bounded implementation roots and excludes only named site/PDF-only modules. Before fingerprinting, validation requires `vintage/image-pair.json` to match the current image-owned source. Fast mode selects the newest artifact whose path matches that fingerprint, validates the manifest and all three checksums, then verifies that the status records the source commit, that the log and status name the same build, and that the rendered bio still matches the current public source strings.

The deployment preserves the result's log, status, and build ID, and keeps the GitLab pipeline link pointed at its source pipeline. Hugo and the public PDF are rebuilt from the current commit and deployed through the normal production verifier. The raw `brad.bio.txt` remains an internal Pages input; GitLab retains it only in the public CI artifact.

Fast mode fails closed when no valid matching artifact is available. Run a standard publication to produce and retain a fresh result; fast mode never invents new provenance or silently runs the vintage pipeline.

## Console contracts

- `pexpect` spawns SIMH directly through a pseudo-terminal. The pipeline opens no telnet port and uses no Compose service.
- State transitions wait for explicit console output. A 5 ms delay between heredoc lines throttles transport into the guest tty; it does not determine state.
- Artifact-producing guest commands use `run_checked()` and must return status `0` before the pipeline continues.
- The checkout's VAX and PDP-11 scripts and `simh_session.py` are mounted read-only over the inert copies in cached images. Those scripts belong to the runtime fingerprint rather than the image-input digest.
- Each guest runs alone on a build-specific internal bridge with no external route, receives only read-only inputs plus its own output directory, drops all Linux capabilities, and runs with no-new-privileges, process, and memory limits. The runner removes the bridge during cleanup.
- The VAX produces the UUCP spool in its output mount. The host rejects links and special or empty files, copies the spool into the PDP-11's read-only input mount, then combines the two validated console-section logs.
- The runner and workflows hand off only host-validated final files under `build/vintage/`; stdout is diagnostic only.

## Validate without publishing

Push the branch and authenticate `glab`, then start a manual vintage-validation pipeline to exercise direct artifact collection, semantic comparison, status generation, and artifact upload:

```bash
BRANCH="$(git branch --show-current)"
glab ci run --branch "$BRANCH" \
  --input operation:vintage-validation
```

To compare the rendered bio with a prior run, add `--input expected_vintage_sha256:EXPECTED_SHA256` and replace `EXPECTED_SHA256` with the recorded digest. Change the baseline when the public name, headline, or summary changes. With the same public input, orchestration, and promoted image pair, the rendered bio is byte-stable because it contains no build date.

## Promote emulator images

Use this procedure after changing an emulator Dockerfile, configuration, base image, dependency, or disk image:

1. Commit and push the image-owned source to protected `main` with `[nopublish]`, then run the image-build pipeline:

   ```bash
   glab ci run --branch main \
     --input operation:image-build
   ```

2. Download `out/image-pair.json` from the successful `image-build` job artifact. The report contains both immutable references, the source commit, and a deterministic digest of the image-owned files.
3. Replace `vintage/image-pair.json` with that complete report. Do not edit individual fields or copy references into the runner.
4. Push the manifest update and run the vintage-validation command above.
5. Inspect `pipeline-status.json`, `brad.bio.txt`, `build.log.html`, and the console-section artifact.
6. Merge only after validation succeeds.

The image-build job accepts only a typed manual pipeline on protected `main`. It uses a digest-pinned BuildKit backend, publishes source-commit tags under `registry.gitlab.com/brfid/brfid.gitlab.io/` for discovery, and labels both images with the source commit and image-input digest. Deployment pulls only manifest digests and requires both labels to match the promoted manifest. The Dockerfiles pin their base images by digest. The PDP-11 recipe downloads the versioned `211bsd-rpethset` package from this project's public GitLab Generic Package Registry and verifies checksum `74678c649338b10bfc470b4fec4bd75b649b4df1e3eb5a9f227ed7ac7d947b42` before extraction.

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
- [Promoted image manifest validator](../../resume_generator/image_manifest.py)
- [Reuse fingerprint and bundle validator](../../resume_generator/vintage_reuse.py)
- [Pipeline runner](../../scripts/vintage-runner.sh)
- [Retired approaches](../archive/DEAD-ENDS.md)
