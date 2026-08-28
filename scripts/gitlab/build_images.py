#!/usr/bin/env python3
"""Build and publish one explicit amd64 VAX/PDP-11 image pair to GitLab Registry."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from resume_generator.gitlab_ci import (
    JOB_ERRORS,
    PUBLICATION_BRANCH,
    GitLabJobIdentity,
    executable,
    required_environment,
    reset_directory,
    run,
)
from resume_generator.image_manifest import (
    IMAGE_INPUTS_LABEL,
    IMAGE_REGISTRY_PREFIX,
    compute_image_inputs_sha256,
    render_image_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "out"
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
EXPECTED_REGISTRY = "registry.gitlab.com"
EXPECTED_REGISTRY_USER = "gitlab-ci-token"
BUILDKIT_IMAGE = "docker.io/moby/buildkit@sha256:040d34121c27906c4ff9ac152a30d52bf2c5d328d3bb748916bb3d2743c02528"


@dataclass(frozen=True)
class RegistryContext:
    """Validated GitLab identity and registry credentials used by the image builder."""

    commit_sha: str
    pipeline_id: int
    registry: str
    image_prefix: str
    username: str
    password: str

    @classmethod
    def from_environment(cls) -> RegistryContext:
        """Reject identity overrides before sending credentials to the fixed registry."""
        identity = GitLabJobIdentity.from_environment(
            ROOT,
            expected_branch=PUBLICATION_BRANCH,
            expected_jobs=("image-build",),
            expected_sources=("web", "api"),
            require_protected=True,
        )
        values = required_environment(("CI_REGISTRY", "CI_REGISTRY_IMAGE", "CI_REGISTRY_USER", "CI_REGISTRY_PASSWORD"))
        expected = {
            "CI_REGISTRY": EXPECTED_REGISTRY,
            "CI_REGISTRY_IMAGE": IMAGE_REGISTRY_PREFIX,
            "CI_REGISTRY_USER": EXPECTED_REGISTRY_USER,
        }
        for name, expected_value in expected.items():
            if values[name] != expected_value:
                raise ValueError(f"{name} must be {expected_value!r}, got {values[name]!r}")
        return cls(
            commit_sha=identity.commit_sha,
            pipeline_id=identity.pipeline_id,
            registry=values["CI_REGISTRY"],
            image_prefix=values["CI_REGISTRY_IMAGE"],
            username=values["CI_REGISTRY_USER"],
            password=values["CI_REGISTRY_PASSWORD"],
        )


def _read_digest(metadata_path: Path) -> str:
    if metadata_path.is_symlink() or not metadata_path.is_file():
        raise RuntimeError(f"Buildx metadata is missing or is not a regular file: {metadata_path}")
    value: Any = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Buildx metadata must be a JSON object: {metadata_path}")
    digest = value.get("containerimage.digest")
    if not isinstance(digest, str) or DIGEST.fullmatch(digest) is None:
        raise RuntimeError(f"Buildx did not report an immutable digest in {metadata_path}")
    return digest


def _build_image(  # pylint: disable=too-many-arguments
    docker: str,
    *,
    tag: str,
    commit_sha: str,
    image_inputs_sha256: str,
    dockerfile: str,
    metadata_path: Path,
) -> str:
    run(
        [
            docker,
            "buildx",
            "build",
            "--platform",
            "linux/amd64",
            "--push",
            "--tag",
            tag,
            "--label",
            f"org.opencontainers.image.revision={commit_sha}",
            "--label",
            f"{IMAGE_INPUTS_LABEL}={image_inputs_sha256}",
            "--metadata-file",
            str(metadata_path),
            "--file",
            dockerfile,
            ".",
        ],
        cwd=ROOT,
    )
    return _read_digest(metadata_path)


def build_images(context: RegistryContext) -> None:
    """Build both images, publish them, and emit the manifest used for promotion."""
    reset_directory(OUTPUT_DIR, create=True)
    image_inputs_sha256 = compute_image_inputs_sha256(ROOT)
    docker = executable("docker")
    logged_in = False
    run(
        [docker, "login", context.registry, "--username", context.username, "--password-stdin"],
        cwd=ROOT,
        input_text=context.password,
    )
    logged_in = True

    builder = f"vintage-{context.pipeline_id}"
    created = False
    try:
        run(
            [
                docker,
                "buildx",
                "create",
                "--name",
                builder,
                "--driver",
                "docker-container",
                "--driver-opt",
                f"image={BUILDKIT_IMAGE}",
                "--use",
            ],
            cwd=ROOT,
        )
        created = True
        run([docker, "buildx", "inspect", "--bootstrap"], cwd=ROOT)

        vax_path = f"{context.image_prefix}/vax-pexpect"
        pdp11_path = f"{context.image_prefix}/pdp11-pexpect"
        vax_digest = _build_image(
            docker,
            tag=f"{vax_path}:{context.commit_sha}",
            commit_sha=context.commit_sha,
            image_inputs_sha256=image_inputs_sha256,
            dockerfile="vintage/machines/vax/Dockerfile.vax-pexpect",
            metadata_path=OUTPUT_DIR / "vax-metadata.json",
        )
        pdp11_digest = _build_image(
            docker,
            tag=f"{pdp11_path}:{context.commit_sha}",
            commit_sha=context.commit_sha,
            image_inputs_sha256=image_inputs_sha256,
            dockerfile="vintage/machines/pdp11/Dockerfile.pdp11-pexpect",
            metadata_path=OUTPUT_DIR / "pdp11-metadata.json",
        )
    finally:
        if created:
            run(
                [docker, "buildx", "rm", "--force", builder],
                check=False,
                cwd=ROOT,
                quiet=True,
            )
        if logged_in:
            run([docker, "logout", context.registry], check=False, cwd=ROOT, quiet=True)

    rendered = render_image_manifest(
        source_sha=context.commit_sha,
        image_inputs_sha256=image_inputs_sha256,
        vax=f"{vax_path}@{vax_digest}",
        pdp11=f"{pdp11_path}@{pdp11_digest}",
    )
    (OUTPUT_DIR / "image-pair.json").write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    print("Promote out/image-pair.json to vintage/image-pair.json, then run vintage validation.")


def main(argv: Sequence[str] | None = None) -> int:
    """Build the GitLab vintage image pair."""
    if argv:
        print("build_images.py takes no positional arguments", file=sys.stderr)
        return 2
    try:
        build_images(RegistryContext.from_environment())
    except JOB_ERRORS as exc:
        print(f"GitLab image build: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
