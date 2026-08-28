# Finish the repository hardening

This temporary handoff covers the uncommitted architecture and security hardening in the current `main` working tree. `STATUS.md` remains the source of truth for the queue. Delete this file and its links after the work below is complete.

## Current state

- The working tree is intentionally uncommitted and unpushed. Remote `main` does not yet contain the typed-input CI configuration.
- The local repository is in a working state: `make check` passes 213 tests, `make verify-site` passes, GitLab CI lint and dry-run simulation pass, shell syntax and `git diff --check` pass, and redacted gitleaks scans pass for the current tree and all 33 commits.
- GitLab already uses fast-forward merges, requires a successful merge pipeline, protects `main` and the `production` environment, limits production deployment to Maintainers, limits pipeline-variable overrides to the Owner, and does not retain the latest successful artifact indefinitely.
- The current immutable VAX/PDP-11 pair remains usable. Its revision labels and source commit are verified, and only those exact two digests may omit the new image-input label.
- No vintage pipeline, image build, deployment pipeline, commit, or push ran during this implementation.

## 1. Publish the CI contract without deploying

Inspect the complete diff and public-data boundary, then commit the current work with `[nopublish]` and push it to `main`. The first push should run checks and gitleaks without starting the vintage pipeline or replacing the Pages deployment.

```bash
git status --short --branch
git diff --check
make check
make verify-site
gitleaks git --redact --no-banner --log-opts="--all -m" .
```

After the push, require the `checks-nopublish` pipeline to pass before continuing.

## 2. Disable legacy pipeline-variable overrides

After the typed-input configuration is present on remote `main`, disable pipeline-variable overrides completely. Do not make this change before the first push because the old remote configuration still uses pipeline variables for manual operations.

```bash
glab api --method PUT   projects/85834009   -f ci_pipeline_variables_minimum_override_role=no_one_allowed   --silent
```

Read the project through the API and confirm `ci_pipeline_variables_minimum_override_role` is `no_one_allowed` without printing the full credential-bearing project response.

## 3. Build and promote a fully labeled image pair

Start the typed image-build operation on the checked `main` commit:

```bash
glab ci run --branch main   --input operation:image-build
```

Download `out/image-pair.json` from the successful `image-build` job. Replace `vintage/image-pair.json` with that complete file; do not copy individual fields. The new report must contain both immutable references, the source commit, and the image-input digest.

Remove the exact legacy unlabeled-pair exception from `resume_generator/image_manifest.py`, update `tests/test_image_manifest.py`, and remove the legacy-exception wording from `STATUS.md` and `docs/integration/INDEX.md`. Keep the revision and image-input label checks mandatory for every pair.

Commit and push the manifest and exception removal with `[nopublish]`, then require the checks pipeline to pass.

## 4. Validate the promoted vintage pair

Run the manual vintage validation from the commit that contains the promoted manifest:

```bash
glab ci run --branch main   --input operation:vintage-validation
```

Inspect `pipeline-status.json`, `brad.bio.txt`, `build.log.html`, `sections.jsonl`, and the job log. Confirm the status records success, the bio still matches the public source contract, both guest stages completed, and no local image fallback or environment bootstrap occurred.

If byte comparison is useful, pass the previously recorded public bio digest through `--input expected_vintage_sha256:EXPECTED_SHA256`.

## 5. Run one standard publication

A manifest or legacy-exception change invalidates the fast-reuse fingerprint. Run one standard publication to exercise the full path, seed a new 90-day reusable bundle, and deploy the current site:

```bash
glab ci run --branch main   --input operation:publish   --input publish_mode:standard
```

Require `checks`, `secret-scan`, and `publish-standard` to succeed. Confirm the Pages artifact contains only the verifier allowlist, the production environment records the deployment, the public site still carries the complete `noindex` policy, and the reusable vintage artifact expires after 90 days.

## 6. Close the handoff

After the standard publication succeeds, remove the completed items from `STATUS.md`, delete this file and its integration-index link, run the normal validation again, and commit the cleanup. Keep pipeline-variable overrides disabled and leave the latest-successful-artifact retention setting off.
