#!/usr/bin/env python3
"""Build and verify one standard or fail-closed fast GitLab Pages publication."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from resume_generator.bio_yaml import main as build_bio_yaml
from resume_generator.gitlab_artifacts import create_bundle, download_latest_matching
from resume_generator.gitlab_ci import (
    JOB_ERRORS,
    executable,
    required_environment,
    reset_directory,
    run,
)
from resume_generator.vintage_reuse import compute_fingerprint, validate_bundle

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = Path("/tmp/edcloud-vintage")  # noqa: S108 - fixed runner contract in an isolated CI job
FINGERPRINT = re.compile(r"[0-9a-f]{64}")
BUNDLE_DIR = ROOT / "build" / "vintage"
REUSABLE_ROOT = ROOT / "reusable-vintage"


@dataclass(frozen=True)
class GitLabContext:
    """Validated GitLab variables needed by one publication."""

    branch: str
    default_branch: str
    commit_sha: str
    pipeline_id: int
    pipeline_url: str
    project_id: int
    project_url: str

    @classmethod
    def from_environment(cls) -> GitLabContext:
        """Load required nonempty GitLab CI variables."""
        names = (
            "CI_COMMIT_BRANCH",
            "CI_DEFAULT_BRANCH",
            "CI_COMMIT_SHA",
            "CI_PIPELINE_ID",
            "CI_PIPELINE_URL",
            "CI_PROJECT_ID",
            "CI_PROJECT_URL",
        )
        values = required_environment(names)
        try:
            pipeline_id = int(values["CI_PIPELINE_ID"])
            project_id = int(values["CI_PROJECT_ID"])
        except ValueError as exc:
            raise ValueError("GitLab pipeline and project IDs must be integers") from exc
        if pipeline_id <= 0 or project_id <= 0:
            raise ValueError("GitLab pipeline and project IDs must be positive")
        return cls(
            branch=values["CI_COMMIT_BRANCH"],
            default_branch=values["CI_DEFAULT_BRANCH"],
            commit_sha=values["CI_COMMIT_SHA"],
            pipeline_id=pipeline_id,
            pipeline_url=values["CI_PIPELINE_URL"],
            project_id=project_id,
            project_url=values["CI_PROJECT_URL"],
        )


def _copy_if_regular(source: Path, destination: Path) -> None:
    if source.is_symlink() or not source.is_file():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def collect_failure_diagnostics() -> None:
    """Copy available runner diagnostics into the GitLab artifact tree."""
    diagnostics = ROOT / "diagnostics"
    diagnostics.mkdir(parents=True, exist_ok=True)
    if LOG_DIR.is_dir() and not LOG_DIR.is_symlink():
        for source in LOG_DIR.iterdir():
            _copy_if_regular(source, diagnostics / source.name)
    for name in ("pipeline-status.json", "sections.jsonl"):
        _copy_if_regular(BUNDLE_DIR / name, diagnostics / name)


def _run_standard(context: GitLabContext, bash: str) -> tuple[str, str]:
    reset_directory(BUNDLE_DIR, create=False)
    reset_directory(REUSABLE_ROOT, create=False)
    build_id = f"build-{datetime.now(UTC):%Y%m%d-%H%M%S}"
    runner_environment = os.environ.copy()
    runner_environment.update(
        {
            "GIT_SHA": context.commit_sha,
            "ALLOW_LOCAL_IMAGE_BUILD": "0",
            "LOG_DIR": str(LOG_DIR),
        }
    )
    run([bash, "scripts/vintage-runner.sh", build_id], cwd=ROOT, env=runner_environment)
    return context.commit_sha, context.pipeline_url


def _run_fast(context: GitLabContext, fingerprint: str) -> tuple[str, str]:
    reset_directory(BUNDLE_DIR, create=False)
    source = download_latest_matching(
        BUNDLE_DIR,
        fingerprint=fingerprint,
        project_id=context.project_id,
        project_url=context.project_url,
        ref=context.default_branch,
        max_age_days=90,
    )
    return source.source_sha, source.source_pipeline_url


def _stage_vintage_for_hugo(source_run_url: str) -> None:
    bio_path = BUNDLE_DIR / "brad.bio.txt"
    digest = hashlib.sha256(bio_path.read_bytes()).hexdigest()
    print(f"brad.bio.txt sha256: {digest}")

    hugo_static = ROOT / "hugo" / "static"
    hugo_static.mkdir(parents=True, exist_ok=True)
    (hugo_static / "brad.bio.txt").unlink(missing_ok=True)
    shutil.copyfile(BUNDLE_DIR / "build.log.html", hugo_static / "build.log.html")
    shutil.copyfile(BUNDLE_DIR / "pipeline-status.json", hugo_static / "pipeline-status.json")

    result = build_bio_yaml(
        [
            str(bio_path),
            str(ROOT / "hugo" / "data" / "bio.yaml"),
            "--build-log",
            str(hugo_static / "build.log.html"),
            "--pipeline-status",
            str(hugo_static / "pipeline-status.json"),
            "--build-run-url",
            source_run_url,
        ]
    )
    if result:
        raise RuntimeError("could not generate Hugo bio data")


def publish(mode: str, context: GitLabContext) -> None:
    """Run one complete publication and raise on any failed contract."""
    if context.branch != context.default_branch:
        raise ValueError(f"site publication is allowed only from {context.default_branch}")

    make = executable("make")
    bash = executable("bash")
    run([make, "check"], cwd=ROOT)

    fingerprint = compute_fingerprint(ROOT, ROOT / "site.yaml", ROOT / "resume.yaml")
    if FINGERPRINT.fullmatch(fingerprint) is None:
        raise RuntimeError("vintage fingerprint is not a SHA-256 digest")
    print(f"Vintage fingerprint: {fingerprint}")

    if mode == "standard":
        source_sha, source_run_url = _run_standard(context, bash)
    else:
        source_sha, source_run_url = _run_fast(context, fingerprint)

    validate_bundle(
        BUNDLE_DIR,
        ROOT / "site.yaml",
        ROOT / "resume.yaml",
        source_sha=source_sha,
        source_run_url=source_run_url,
        project_url=context.project_url,
    )
    _stage_vintage_for_hugo(source_run_url)

    run([make, "resume-pdf-public"], cwd=ROOT)
    run(
        [
            sys.executable,
            "scripts/verify_site.py",
            "site",
            "--production",
            "--resume-yaml",
            "resume.yaml",
            "--build-run-url",
            source_run_url,
        ],
        cwd=ROOT,
    )

    if mode == "standard":
        create_bundle(
            BUNDLE_DIR,
            REUSABLE_ROOT,
            fingerprint=fingerprint,
            project_id=context.project_id,
            project_url=context.project_url,
            ref=context.default_branch,
            source_sha=context.commit_sha,
            source_pipeline_id=context.pipeline_id,
            source_pipeline_url=context.pipeline_url,
        )

    print("GitLab Pages publication verified")
    print(f"Mode: {mode}")
    print(f"SHA: {context.commit_sha}")
    print(f"Vintage pipeline: {source_run_url}")


def main(argv: Sequence[str] | None = None) -> int:
    """Run a standard or fast GitLab publication."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("standard", "fast"))
    args = parser.parse_args(argv)

    success = False
    try:
        publish(args.mode, GitLabContext.from_environment())
        success = True
    except JOB_ERRORS as exc:
        print(f"GitLab publication: {exc}", file=sys.stderr)
        return 1
    finally:
        if not success:
            collect_failure_diagnostics()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
