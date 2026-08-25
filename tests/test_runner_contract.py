"""Contracts for the containerized vintage runner."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "vintage-runner.sh"
WORKFLOWS = ROOT / ".github" / "workflows"
PEXPECT_SCRIPTS = (
    RUNNER.parent / "vax_pexpect.py",
    RUNNER.parent / "pdp11_pexpect.py",
    RUNNER.parent / "simh_session.py",
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
    deploy = (WORKFLOWS / "deploy.yml").read_text(encoding="utf-8")
    validate = (WORKFLOWS / "vintage-validate.yml").read_text(encoding="utf-8")
    reuse = (ROOT / "resume_generator" / "vintage_reuse.py").read_text(encoding="utf-8")

    assert ".venv/bin/python -m resume_generator.vintage_reuse validate" in deploy
    assert ".venv/bin/python -m resume_generator.vintage_contract" in validate
    assert "validate_rendered_bio(rendered_bio, expected)" in reuse


def test_workflows_consume_direct_runner_artifacts() -> None:
    """Deployment and validation must consume the runner's files without stdout transport."""
    runner = RUNNER.read_text(encoding="utf-8")
    deploy = (WORKFLOWS / "deploy.yml").read_text(encoding="utf-8")
    validate = (WORKFLOWS / "vintage-validate.yml").read_text(encoding="utf-8")
    reuse = (ROOT / "resume_generator" / "vintage_reuse.py").read_text(encoding="utf-8")

    assert "_BASE64_BEGIN" not in runner
    assert "base64 <" not in runner
    for workflow in (deploy, validate):
        assert "bash scripts/vintage-runner.sh" in workflow
        assert "/tmp/vintage-stdout.txt" not in workflow
        assert "_BASE64_BEGIN" not in workflow
    assert "for artifact in brad.bio.txt build.log.html pipeline-status.json; do" in validate
    assert '"build/vintage/${artifact}"' in validate
    for artifact in ("brad.bio.txt", "build.log.html", "pipeline-status.json"):
        assert f'"{artifact}"' in reuse
        assert f"build/vintage/{artifact}" in deploy


def test_runner_preserves_public_status_and_log_identifiers() -> None:
    """Renaming the executable must not rename published provenance or documented logs."""
    runner = RUNNER.read_text(encoding="utf-8")

    assert 'LOG_DIR="${LOG_DIR:-/tmp/edcloud-vintage}"' in runner
    assert '"pipeline": "edcloud-vintage"' in runner


def test_workflows_export_the_log_directory_consumed_by_the_runner() -> None:
    """Diagnostic artifact paths must use the directory inherited by the runner."""
    deploy = (WORKFLOWS / "deploy.yml").read_text(encoding="utf-8")
    validate = (WORKFLOWS / "vintage-validate.yml").read_text(encoding="utf-8")

    for workflow in (deploy, validate):
        runner_step = workflow.split("name: Run vintage pipeline", maxsplit=1)[1]
        assert "LOG_DIR: /tmp/edcloud-vintage" in runner_step
        assert 'echo "log_file=${LOG_DIR}/${BUILD_ID}.log"' in runner_step
        assert "LOG_DIR=/tmp/edcloud-vintage" not in runner_step


def test_validation_workflow_keeps_the_digest_local_to_its_summary() -> None:
    """The digest has no downstream consumer and must not expose a dead step output."""
    validate = (WORKFLOWS / "vintage-validate.yml").read_text(encoding="utf-8")

    assert "id: compare" not in validate
    assert 'echo "sha256=${sha}" >> "$GITHUB_OUTPUT"' not in validate
    assert r'echo "| SHA256 | \`${sha}\` |"' in validate


def test_standalone_vintage_bootstrap_excludes_pdf_dependencies() -> None:
    """A vintage-only run must not install Playwright or its browser runtime."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    runner = RUNNER.read_text(encoding="utf-8")

    dependencies = project["project"]["dependencies"]
    pdf_dependencies = project["project"]["optional-dependencies"]["pdf"]
    assert not any(dependency.lower().startswith("playwright") for dependency in dependencies)
    assert sum(dependency.lower().startswith("playwright==") for dependency in pdf_dependencies) == 1
    assert ".venv/bin/python -m pip install --quiet -e ." in runner
    assert ".[pdf]" not in runner


def test_runner_clears_owned_generated_outputs_before_each_run() -> None:
    """A failed retry must not reuse the prior run's successful artifacts."""
    runner = RUNNER.read_text(encoding="utf-8")

    for output in (
        "bio.vintage.yaml",
        "build.log.html",
        "brad.bio.uu",
        "brad.bio.txt",
        "pipeline-status.json",
        "sections.jsonl",
    ):
        assert f"build/vintage/{output}" in runner


def test_image_recipes_pin_external_inputs() -> None:
    """Image rebuilds must use immutable base references and verify the guest archive."""
    pdp11 = (ROOT / "vintage" / "machines" / "pdp11" / "Dockerfile.pdp11-pexpect").read_text(encoding="utf-8")
    vax = (ROOT / "vintage" / "machines" / "vax" / "Dockerfile.vax-pexpect").read_text(encoding="utf-8")

    pdp11_from = [line for line in pdp11.splitlines() if line.startswith("FROM ")]
    vax_from = next(line for line in vax.splitlines() if line.startswith("FROM "))
    pdp11_base = "FROM debian:bookworm-slim@sha256:abd67ffcfa541b485a3dff59865ab629aa048a6c613e639d36e7456b0b229241"
    assert pdp11_from == [f"{pdp11_base} AS simh-builder", f"{pdp11_base} AS runtime"]
    assert vax_from.startswith("FROM jguillaumes/simh-vaxbsd:latest@sha256:")
    assert "74678c649338b10bfc470b4fec4bd75b649b4df1e3eb5a9f227ed7ac7d947b42" in pdp11
    assert "sha256sum -c -" in pdp11


def test_pdp11_runtime_image_excludes_build_dependencies() -> None:
    """The final PDP-11 stage must contain runtime dependencies, not its toolchain."""
    dockerfile = (ROOT / "vintage" / "machines" / "pdp11" / "Dockerfile.pdp11-pexpect").read_text(encoding="utf-8")
    builder, runtime = dockerfile.split(" AS runtime\n", maxsplit=1)
    runtime_install = runtime.split("RUN apt-get update && apt-get install -y --no-install-recommends", maxsplit=1)[
        1
    ].split("    && rm -rf /var/lib/apt/lists/*", maxsplit=1)[0]

    for package in ("build-essential", "libedit-dev", "libpcre3-dev", "wget", "ca-certificates", "git"):
        assert package in builder
        assert package not in runtime_install
    for package in ("libedit2", "libpcre3", "python3", "python3-pexpect"):
        assert package in runtime_install
    assert "apt-get install -y --no-install-recommends" in runtime
    assert "COPY --from=simh-builder /usr/local/bin/pdp11 /usr/local/bin/pdp11" in runtime
    assert "COPY --from=simh-builder /opt/pdp11/211bsd_rpeth.dsk /opt/pdp11/211bsd_rpeth.dsk" in runtime
    assert "pdp11 RegisterSanityCheck" in runtime
    assert "python3 -c 'import pexpect'" in runtime
    for command in ("cc", "git", "make", "wget"):
        assert f"! command -v {command}" in runtime


def test_vax_image_disables_unused_devices() -> None:
    """The VAX image must not expose retired or unattached hardware."""
    dockerfile = (ROOT / "vintage" / "machines" / "vax" / "Dockerfile.vax-pexpect").read_text(encoding="utf-8")
    config = (ROOT / "vintage" / "machines" / "vax" / "configs" / "vax780-pexpect.ini").read_text(encoding="utf-8")
    directives = {line.strip() for line in config.splitlines() if line.strip() and not line.lstrip().startswith(";")}

    assert {
        "set lpt disabled",
        "set rp disabled",
        "set rl disabled",
        "set rq2 disabled",
        "set rq3 disabled",
        "set ts disabled",
    } <= directives
    assert "att rq0 RA81.000" in directives
    assert "att rq1 RA81VHD.001" in directives
    assert {line for line in directives if line.endswith(" enabled")} == {"set rq enabled"}
    for prefix in ("attach lpt ", "set rp0 ", "set rp1 ", "set rp2 ", "set rp3 ", "set rl0 ", "set rl1 "):
        assert not any(line.startswith(prefix) for line in directives)
    assert "/opt/vax-ini-path.txt" not in dockerfile


def test_docker_context_is_a_strict_allowlist() -> None:
    """Local image builds must not expose unrelated or private checkout files."""
    dockerignore = ROOT / ".dockerignore"
    rules = {
        line for line in dockerignore.read_text(encoding="utf-8").splitlines() if line and not line.startswith("#")
    }

    assert "**" in rules
    assert rules == {
        "**",
        "!.dockerignore",
        "!scripts/",
        "!scripts/pdp11_pexpect.py",
        "!scripts/simh_session.py",
        "!scripts/vax_pexpect.py",
        "!vintage/",
        "!vintage/machines/",
        "!vintage/machines/pdp11/",
        "!vintage/machines/pdp11/Dockerfile.pdp11-pexpect",
        "!vintage/machines/pdp11/configs/",
        "!vintage/machines/pdp11/configs/pdp11-pexpect.ini",
        "!vintage/machines/vax/",
        "!vintage/machines/vax/Dockerfile.vax-pexpect",
        "!vintage/machines/vax/configs/",
        "!vintage/machines/vax/configs/vax780-pexpect.ini",
    }
