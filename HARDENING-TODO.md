# Finish the repository hardening

This temporary handoff covers the remaining hosted validation and publication for the architecture and security hardening on `main`. `STATUS.md` remains the source of truth for the queue. Delete this file and its links after the work below is complete.

## Completed controls

- Commit `f19f93ab57639cf2f168a33d8888f5e32c703040` published the typed-input CI contract without deploying; its `checks-nopublish` pipeline passed both quality and full-history secret gates.
- GitLab now disables pipeline-variable overrides, uses fast-forward merges, requires a successful merge pipeline, protects `main` and the `production` environment, limits production deployment to Maintainers, and does not retain the latest successful artifact indefinitely.
- Image-build pipeline `2800537896` used the digest-pinned BuildKit backend on protected `main` and emitted a canonical, source-bound VAX/PDP-11 manifest. The current change promotes that complete manifest and removes the temporary unlabeled-image exception.
- Local quality, rendered-site, shell-syntax, CI-lint, clean dependency-bootstrap, image-manifest, and redacted secret checks pass.
- The first hosted validation accepted both images and completed the VAX stage, then a progressing PDP-11 boot reached the old 180-second safety bound. The current change raises that output-driven boot bound to five minutes before retrying.

## 1. Validate the promoted vintage pair

After the manifest commit's non-publishing checks pass, run the typed vintage validation from the same protected `main` commit:

```bash
glab ci run --branch main \
  --input operation:vintage-validation
```

Inspect `pipeline-status.json`, `brad.bio.txt`, `build.log.html`, `sections.jsonl`, and the job log. Confirm the status records success, the bio still matches the public source contract, both guest stages completed, both image labels passed, and no local image fallback or environment bootstrap occurred.

If byte comparison is useful, pass the previously recorded public bio digest through `--input expected_vintage_sha256:EXPECTED_SHA256`.

## 2. Run one standard publication

The promoted manifest invalidates the fast-reuse fingerprint. Run one standard publication to exercise the full path, seed a new 90-day reusable bundle, and deploy the current site:

```bash
glab ci run --branch main \
  --input operation:publish \
  --input publish_mode:standard
```

Require `checks`, `secret-scan`, and `publish-standard` to succeed. Confirm the Pages artifact contains only the verifier allowlist, the production environment records the deployment, the public site still carries the complete `noindex` policy, and the reusable vintage artifact expires after 90 days.

## 3. Close the handoff

After the standard publication succeeds, remove the completed item from `STATUS.md`, delete this file and its integration-index link, run the normal validation again, and commit and push the cleanup. Keep pipeline-variable overrides disabled and leave the latest-successful-artifact retention setting off.
