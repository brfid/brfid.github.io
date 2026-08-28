# Finish the repository hardening

This temporary handoff records the incomplete hosted vintage transition. `STATUS.md` remains the source of truth for the queue. Delete this file and its links only after a successful standard publication.

## Safe current state

- Remote `main` contains the hardening contract in `f19f93ab57639cf2f168a33d8888f5e32c703040`, the fully labeled image manifest in `578fa9263feb201688f14c67529b91ed448df2d3`, and the five-minute PDP-11 boot safety bound in `9718ebf0fb3ffae009eacfa5a6d80daf045813d7`. Every push used `[nopublish]`, and each `checks-nopublish` pipeline passed quality and full-history secret gates.
- GitLab disables pipeline-variable overrides, uses fast-forward merges, requires a successful merge pipeline, protects `main` and the `production` environment, limits production deployment to Maintainers, and does not retain the latest successful artifact indefinitely.
- Image-build pipeline `2800537896` succeeded on protected `main` with the digest-pinned BuildKit backend. `vintage/image-pair.json` contains its complete canonical manifest, and the runtime requires both image provenance labels.
- No new Pages deployment ran. The public site still uses the last successful standard publication and was not replaced by either failed validation.
- Local quality checks pass 214 tests. Rendered-site verification, shell syntax, CI lint and dry-run simulation, clean hash-locked environment bootstrap, image-manifest validation, whitespace checks, and redacted current-tree and full-history secret scans passed during this work.

## Blocking defect

Do not start a standard publication yet. The promoted PDP-11 image does not reach the root prompt under the hardened hosted runner, so publication would fail closed before deployment.

- Vintage-validation pipeline `2800550279`, job `16175784287`, accepted both image labels and completed the VAX stage, then timed out after 180 seconds while the PDP-11 was still at `init: configure system` and device probes.
- Commit `9718ebf0fb3ffae009eacfa5a6d80daf045813d7` raised only the output-driven root-prompt safety bound to five minutes. Its non-publishing checks passed.
- Vintage-validation pipeline `2800572117`, job `16175951146`, reached the identical PDP-11 device-probe point and timed out after the full 300 seconds. This proves the problem is not ordinary runner contention; do not increase the timeout again without new evidence.
- The retry used expected public bio SHA-256 `a929edcd7fcf3e245f968291438328687dff9ddc1ee74d3f73464ca5083936b5`, derived from successful standard-publication job `16160800424`. No new bio was produced for comparison.

## Evidence collected

- The old and new PDP-11 images contain byte-identical `211bsd_rpeth.dsk` files and INI configuration, and their installed runtime package versions match.
- Both SIMH binaries report source commit `627e6a6b135261f9dcb46dc1a8665c7fe67d3f7c` and GCC 12.2. Their ELF files differ, but the only unique printable strings are build times. This does not establish the rebuilt executable as the cause.
- The last successful standard publication, pipeline `2798436161`, job `16160800424`, used the old image and the pre-hardening Docker invocation on the same `saas-linux-small-amd64` runner class.
- The hardening changed the guest invocation to stage-only mounts plus `--network none`, `--cap-drop ALL`, `--security-opt no-new-privileges`, `--pids-limit 256`, and `--memory 2g`. The failure occurs before the output mount is used.
- Local Docker Desktop tests are inconclusive because nested amd64-on-arm64 emulation does not boot even the known-good old image within 15 minutes, with or without the restrictions. Do not treat that result as evidence against a particular hosted restriction.
- The old and new PDP-11 images were pulled into local Docker only for read-only comparison. Remove them later if desired; they do not affect the Git working tree.

## Next safe investigation

1. Keep publication stopped and preserve the current fail-closed manifest.
2. Isolate the Docker invocation change on a native amd64 runner. Test `--network none` first because it is the restriction most likely to alter runtime behavior. A per-run Docker bridge created with `docker network create --internal` is the preferred next experiment because it supplies a network namespace interface without an external route. Give each job a build-ID-derived network name, attach only one guest at a time, and remove it in `cleanup()`.
3. Do not permanently weaken the other restrictions or restore the shared `/build` mount without evidence. If the internal network does not fix the boot, test one remaining restriction at a time in a non-publishing diagnostic path.
4. After a repository correction, run `make check`, `make verify-site`, image-manifest validation, `git diff --check`, and a redacted secret scan. Push the correction with `[nopublish]` and require both gates to pass.
5. Retry typed vintage validation with `glab ci run --branch main --input operation:vintage-validation --input expected_vintage_sha256:a929edcd7fcf3e245f968291438328687dff9ddc1ee74d3f73464ca5083936b5`.
6. Require successful `pipeline-status.json`, `brad.bio.txt`, `build.log.html`, and `sections.jsonl`; confirm both guest stages completed, both labels passed, no local fallback or environment bootstrap occurred, and the bio digest matched.
7. Only then run `glab ci run --branch main --input operation:publish --input publish_mode:standard`. Require `checks`, `secret-scan`, and `publish-standard` to succeed, then verify the Pages allowlist, production deployment, complete `noindex` policy, and 90-day reusable artifact.
8. Remove the completed item from `STATUS.md`, delete this file and its integration-index link, rerun normal validation, and commit and push the cleanup.
