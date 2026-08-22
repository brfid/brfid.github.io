"""Contracts for the containerized vintage runner."""

from pathlib import Path

RUNNER = Path(__file__).resolve().parents[1] / "scripts" / "edcloud-vintage-runner.sh"
WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"
PEXPECT_SCRIPTS = (
    RUNNER.parent / "vax_pexpect.py",
    RUNNER.parent / "pdp11_pexpect.py",
)


def test_runner_mounts_current_pexpect_sources_into_cached_images() -> None:
    """Cached emulator images must execute the scripts from the checkout."""
    runner = RUNNER.read_text(encoding="utf-8")

    expected_mounts = (
        "scripts/vax_pexpect.py:/opt/vax_pexpect.py:ro",
        "scripts/pdp11_pexpect.py:/opt/pdp11/pdp11_pexpect.py:ro",
        "scripts/simh_session.py:/opt/simh_session.py:ro",
        "scripts/simh_session.py:/opt/pdp11/simh_session.py:ro",
    )

    for mount in expected_mounts:
        assert mount in runner


def test_mounted_pexpect_scripts_defer_annotation_evaluation() -> None:
    """The VAX image runs Python 3.9, where ``X | None`` cannot evaluate."""
    for script in PEXPECT_SCRIPTS:
        source = script.read_text(encoding="utf-8")
        assert "from __future__ import annotations" in source


def test_production_images_are_immutable_and_fallback_is_disabled() -> None:
    """Production must fail closed instead of building a different checkout."""
    runner = RUNNER.read_text(encoding="utf-8")
    deploy = (WORKFLOWS / "deploy.yml").read_text(encoding="utf-8")
    validate = (WORKFLOWS / "vintage-validate.yml").read_text(encoding="utf-8")

    image_lines = [line for line in runner.splitlines() if line.startswith("GHCR_")]
    assert len(image_lines) == 2
    assert all("@sha256:" in line for line in image_lines)
    assert all(":latest" not in line for line in image_lines)
    assert 'ALLOW_LOCAL_IMAGE_BUILD: "0"' in deploy
    assert 'ALLOW_LOCAL_IMAGE_BUILD: "0"' in validate


def test_image_build_workflow_is_manual_and_reports_both_digests() -> None:
    """Image releases are explicit promotions, separate from site pushes."""
    workflow = (WORKFLOWS / "build-images.yml").read_text(encoding="utf-8")

    trigger = workflow.split("permissions:", maxsplit=1)[0]
    assert "workflow_dispatch:" in trigger
    assert "push:" not in trigger
    assert ":latest" not in workflow
    assert "steps.vax.outputs.digest" in workflow
    assert "steps.pdp11.outputs.digest" in workflow


def test_publish_paths_use_the_shared_semantic_validator() -> None:
    """Manual validation and deployment must enforce one output contract."""
    for name in ("deploy.yml", "vintage-validate.yml"):
        workflow = (WORKFLOWS / name).read_text(encoding="utf-8")
        assert ".venv/bin/python -m resume_generator.vintage_contract" in workflow


def test_runner_clears_owned_generated_outputs_before_each_run() -> None:
    """A failed retry must not reuse the prior run's successful artifacts."""
    runner = RUNNER.read_text(encoding="utf-8")

    for output in (
        "bio.vintage.yaml",
        "brad.bio.uu",
        "brad.bio.txt",
        "pipeline-status.json",
        "sections.jsonl",
    ):
        assert f"build/vintage/{output}" in runner
