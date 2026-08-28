#!/usr/bin/env python3
"""Run the pinned vintage pipeline without publishing and retain diagnostics."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from resume_generator.gitlab_ci import JOB_ERRORS, GitLabJobIdentity, executable, reset_directory, run
from resume_generator.image_manifest import load_image_pair
from resume_generator.vintage_contract import main as validate_vintage_contract
from resume_generator.vintage_reuse import BUNDLE_FILES

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = Path("/tmp/edcloud-vintage")  # noqa: S108 - fixed runner contract in an isolated CI job
OUTPUT_DIR = ROOT / "out"
SHA256 = re.compile(r"[0-9a-f]{64}")


def _copy_if_regular(source: Path, destination: Path) -> None:
    if source.is_symlink() or not source.is_file():
        return
    shutil.copyfile(source, destination)


def _collect(build_id: str) -> None:
    _copy_if_regular(LOG_DIR / f"{build_id}.log", OUTPUT_DIR / "pipeline.log")
    _copy_if_regular(ROOT / "build" / "vintage" / "sections.jsonl", OUTPUT_DIR / "sections.jsonl")
    for name in BUNDLE_FILES:
        _copy_if_regular(ROOT / "build" / "vintage" / name, OUTPUT_DIR / name)


def _require_artifacts() -> None:
    for name in BUNDLE_FILES:
        path = OUTPUT_DIR / name
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"final vintage artifact is missing: {path}")
        if path.stat().st_size == 0:
            raise RuntimeError(f"final vintage artifact is empty: {path}")


def validate(expected_sha256: str, *, commit_sha: str) -> None:
    """Run and validate one pinned vintage pipeline result."""
    if expected_sha256 and SHA256.fullmatch(expected_sha256) is None:
        raise ValueError("expected vintage SHA-256 must be blank or a lowercase digest")

    load_image_pair(ROOT)
    reset_directory(OUTPUT_DIR, create=True)
    build_id = f"validate-{datetime.now(UTC):%Y%m%d-%H%M%S}"
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_SHA": commit_sha,
            "ALLOW_LOCAL_IMAGE_BUILD": "0",
            "ALLOW_ENVIRONMENT_BOOTSTRAP": "0",
            "BUILD_LOCAL_IMAGE_PAIR": "0",
            "LOG_DIR": str(LOG_DIR),
            "ROOT_DIR": str(ROOT),
        }
    )
    start = time.monotonic()
    result = run(
        [executable("bash"), "scripts/vintage-runner.sh", build_id],
        check=False,
        cwd=ROOT,
        env=environment,
    )
    elapsed = int(time.monotonic() - start)
    print(f"Pipeline wall clock: {elapsed // 60}m{elapsed % 60:02d}s (exit {result.returncode})")
    _collect(build_id)
    if result.returncode:
        raise RuntimeError(f"vintage pipeline failed after {elapsed}s with exit {result.returncode}")

    _require_artifacts()
    json.loads((OUTPUT_DIR / "pipeline-status.json").read_text(encoding="utf-8"))
    contract_result = validate_vintage_contract(
        [str(OUTPUT_DIR / "brad.bio.txt"), str(ROOT / "site.yaml"), str(ROOT / "resume.yaml")]
    )
    if contract_result:
        raise RuntimeError("vintage bio did not satisfy the public source contract")

    bio = (OUTPUT_DIR / "brad.bio.txt").read_bytes()
    digest = hashlib.sha256(bio).hexdigest()
    line_count = bio.count(b"\n")
    print(f"brad.bio.txt: {line_count} lines, {len(bio)} bytes")
    print(f"sha256: {digest}")
    if not expected_sha256:
        print("Baseline not compared; no expected digest was supplied")
    elif digest == expected_sha256:
        print("brad.bio.txt matches the supplied baseline")
    else:
        raise RuntimeError(f"brad.bio.txt digest {digest} does not match baseline {expected_sha256}")


def main(argv: Sequence[str] | None = None) -> int:
    """Run vintage validation from a typed GitLab pipeline input."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-sha256", default="", help="optional expected brad.bio.txt digest")
    args = parser.parse_args(argv)
    try:
        identity = GitLabJobIdentity.from_environment(
            ROOT,
            expected_jobs=("vintage-validation",),
            expected_sources=("web", "api"),
        )
        validate(args.expected_sha256, commit_sha=identity.commit_sha)
    except JOB_ERRORS as exc:
        print(f"GitLab vintage validation: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
