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
    executable,
    required_environment,
    reset_directory,
    run,
)

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "out"
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")


@dataclass(frozen=True)
class RegistryContext:
    """Validated GitLab registry variables used by the image builder."""

    commit_sha: str
    pipeline_id: str
    registry: str
    image_prefix: str
    username: str
    password: str

    @classmethod
    def from_environment(cls) -> RegistryContext:
        """Load required nonempty registry credentials and image identity."""
        names = (
            "CI_COMMIT_SHA",
            "CI_PIPELINE_ID",
            "CI_REGISTRY",
            "CI_REGISTRY_IMAGE",
            "CI_REGISTRY_USER",
            "CI_REGISTRY_PASSWORD",
        )
        values = required_environment(names)
        return cls(
            commit_sha=values["CI_COMMIT_SHA"],
            pipeline_id=values["CI_PIPELINE_ID"],
            registry=values["CI_REGISTRY"],
            image_prefix=values["CI_REGISTRY_IMAGE"],
            username=values["CI_REGISTRY_USER"],
            password=values["CI_REGISTRY_PASSWORD"],
        )


def _read_digest(metadata_path: Path) -> str:
    value: Any = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Buildx metadata must be a JSON object: {metadata_path}")
    digest = value.get("containerimage.digest")
    if not isinstance(digest, str) or DIGEST.fullmatch(digest) is None:
        raise RuntimeError(f"Buildx did not report an immutable digest in {metadata_path}")
    return digest


def _build_image(
    docker: str,
    *,
    tag: str,
    commit_sha: str,
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
    """Build both images, publish them, and record their immutable references."""
    reset_directory(OUTPUT_DIR, create=True)
    docker = executable("docker")
    run(
        [docker, "login", context.registry, "--username", context.username, "--password-stdin"],
        cwd=ROOT,
        input_text=context.password,
    )

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
            dockerfile="vintage/machines/vax/Dockerfile.vax-pexpect",
            metadata_path=OUTPUT_DIR / "vax-metadata.json",
        )
        pdp11_digest = _build_image(
            docker,
            tag=f"{pdp11_path}:{context.commit_sha}",
            commit_sha=context.commit_sha,
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

    report = {
        "source_sha": context.commit_sha,
        "vax": f"{vax_path}@{vax_digest}",
        "pdp11": f"{pdp11_path}@{pdp11_digest}",
    }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    (OUTPUT_DIR / "image-pair.json").write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    print("Pin both references in scripts/vintage-runner.sh, then run a vintage-validation pipeline.")


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
