"""Contracts for the containerized vintage runner."""

import json
import shutil
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "vintage-runner.sh"
BUILD_IMAGES_WORKFLOW = ROOT / ".github" / "workflows" / "build-images.yml"
VALIDATE_WORKFLOW = ROOT / ".github" / "workflows" / "vintage-validate.yml"
GITHUB_SCRIPTS = ROOT / "scripts" / "github"
PUBLISH = GITHUB_SCRIPTS / "publish.py"
VALIDATE = GITHUB_SCRIPTS / "validate_vintage.py"
BUILD_IMAGES = GITHUB_SCRIPTS / "build_images.py"
IMAGE_MANIFEST = ROOT / "vintage" / "image-pair.json"
PEXPECT_SCRIPTS = (
    RUNNER.parent / "vax_pexpect.py",
    RUNNER.parent / "pdp11_pexpect.py",
    RUNNER.parent / "simh_session.py",
)


def test_runner_rejects_unsafe_build_id_before_host_setup(tmp_path: Path) -> None:
    """A caller-controlled build ID must not escape the fixed log and output paths."""
    bash = shutil.which("bash")
    if bash is None:
        raise RuntimeError("bash is required for the runner contract")

    result = subprocess.run(  # noqa: S603 - bash is resolved and the malicious value is a fixed test input
        [bash, str(RUNNER), "../escape"],
        check=False,
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "<safe-build-id>" in result.stderr
    assert list(tmp_path.iterdir()) == []


def test_runner_mounts_current_pexpect_sources_into_cached_images() -> None:
    """Cached emulator images must execute read-only scripts from the checkout."""
    runner = RUNNER.read_text(encoding="utf-8")

    expected_mounts = (
        "src=${ROOT_DIR}/scripts/vax_pexpect.py,dst=/opt/vax_pexpect.py,readonly",
        "src=${ROOT_DIR}/scripts/pdp11_pexpect.py,dst=/opt/pdp11/pdp11_pexpect.py,readonly",
        "src=${ROOT_DIR}/scripts/simh_session.py,dst=/opt/simh_session.py,readonly",
        "src=${ROOT_DIR}/scripts/simh_session.py,dst=/opt/pdp11/simh_session.py,readonly",
    )

    for mount in expected_mounts:
        assert mount in runner


def test_mounted_pexpect_scripts_defer_annotation_evaluation() -> None:
    """The VAX image runs Python 3.9, where ``X | None`` cannot evaluate."""
    for script in PEXPECT_SCRIPTS:
        source = script.read_text(encoding="utf-8")
        assert "from __future__ import annotations" in source


def test_pdp11_boot_timeout_allows_for_hosted_runner_contention() -> None:
    """A progressing 2.11BSD boot must not fail at the old three-minute boundary."""
    source = (ROOT / "scripts" / "pdp11_pexpect.py").read_text(encoding="utf-8")

    assert "_BOOT_TIMEOUT = 300" in source
    assert "timeout=_BOOT_TIMEOUT" in source


def test_production_images_are_immutable_and_fallback_is_disabled() -> None:
    """Production must consume one source-bound image manifest and disable fallback."""
    runner = RUNNER.read_text(encoding="utf-8")
    publish = PUBLISH.read_text(encoding="utf-8")
    validate = VALIDATE.read_text(encoding="utf-8")
    manifest = json.loads(IMAGE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["schema_version"] == 1
    assert len(manifest["image_inputs_sha256"]) == 64
    for machine in ("vax", "pdp11"):
        reference = manifest[machine]
        assert reference.startswith(f"ghcr.io/brfid/{machine}-pexpect@sha256:")
        assert ":latest" not in reference
    assert "resume_generator.image_manifest" in runner
    assert '"ALLOW_LOCAL_IMAGE_BUILD": "0"' in publish
    assert '"ALLOW_LOCAL_IMAGE_BUILD": "0"' in validate
    assert '"ALLOW_ENVIRONMENT_BOOTSTRAP": "0"' in publish
    assert '"ALLOW_ENVIRONMENT_BOOTSTRAP": "0"' in validate
    assert '"BUILD_LOCAL_IMAGE_PAIR": "0"' in publish
    assert '"BUILD_LOCAL_IMAGE_PAIR": "0"' in validate
    assert "validate-labels" in runner
    assert "org.opencontainers.image.revision" in runner
    assert "io.brfid.vintage.image-inputs-sha256" in runner


def test_vintage_validation_checks_out_full_history() -> None:
    """A shallow checkout cannot resolve the promoted manifest's source commit."""
    pipeline = VALIDATE_WORKFLOW.read_text(encoding="utf-8")

    assert "fetch-depth: 0" in pipeline


def test_image_build_job_is_manual_and_reports_both_digests() -> None:
    """Image releases are typed manual operations that emit one promotable manifest."""
    pipeline = BUILD_IMAGES_WORKFLOW.read_text(encoding="utf-8")
    build = BUILD_IMAGES.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in pipeline
    assert "GITHUB_REF_PROTECTED: ${{ github.ref_protected }}" in pipeline
    assert ".venv/bin/python -m scripts.github.build_images" in pipeline
    assert "expected_branch=PUBLICATION_BRANCH" in build
    assert "require_protected=True" in build
    assert ":latest" not in build
    assert '"containerimage.digest"' in build
    assert "compute_image_inputs_sha256(ROOT)" in build
    assert "IMAGE_INPUTS_LABEL" in build
    assert "render_image_manifest(" in build
    assert "docker.io/moby/buildkit@sha256:" in build
    assert 'f"image={BUILDKIT_IMAGE}"' in build
    assert "buildx-stable-1" not in build


def test_local_image_fallback_builds_an_explicit_complete_pair() -> None:
    """A pull failure or development override must build both images, never mix sources."""
    runner = RUNNER.read_text(encoding="utf-8")

    assert 'BUILD_LOCAL_IMAGE_PAIR="${BUILD_LOCAL_IMAGE_PAIR:-0}"' in runner
    assert 'if [[ "$BUILD_LOCAL_IMAGE_PAIR" == "1" ]]' in runner
    assert 'elif docker pull "$PINNED_PDP11" && docker pull "$PINNED_VAX"; then' in runner
    assert 'elif [[ "$ALLOW_LOCAL_IMAGE_BUILD" == "1" ]]; then' in runner
    assert "A promoted image pull failed; rebuilding both images" in runner
    local_builder = runner.split("build_local_images() {", maxsplit=1)[1].split("\n}\n", maxsplit=1)[0]
    assert local_builder.count("docker build") == 2
    assert "Dockerfile.pdp11-pexpect" in local_builder
    assert "Dockerfile.vax-pexpect" in local_builder


def test_publish_paths_use_the_shared_semantic_validator() -> None:
    """Manual validation and deployment must enforce one output contract."""
    pipeline = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    publish = PUBLISH.read_text(encoding="utf-8")
    validate = VALIDATE.read_text(encoding="utf-8")
    reuse = (ROOT / "resume_generator" / "vintage_reuse.py").read_text(encoding="utf-8")

    assert ".venv/bin/python -m scripts.github.validate_vintage" in pipeline
    assert "validate_bundle(" in publish
    assert "validate_vintage_contract(" in validate
    assert "validate_rendered_bio(rendered_bio, expected)" in reuse


def test_github_jobs_consume_direct_runner_artifacts() -> None:
    """Deployment and validation must consume the runner's files without stdout transport."""
    runner = RUNNER.read_text(encoding="utf-8")
    publish = PUBLISH.read_text(encoding="utf-8")
    validate = VALIDATE.read_text(encoding="utf-8")
    reuse = (ROOT / "resume_generator" / "vintage_reuse.py").read_text(encoding="utf-8")

    assert "_BASE64_BEGIN" not in runner
    assert "base64 <" not in runner
    for job_script in (publish, validate):
        assert "scripts/vintage-runner.sh" in job_script
        assert "/tmp/vintage-stdout.txt" not in job_script
        assert "_BASE64_BEGIN" not in job_script
    assert "for name in BUNDLE_FILES:" in validate
    assert 'ROOT / "build" / "vintage" / name' in validate
    for artifact in ("brad.bio.txt", "build.log.html", "pipeline-status.json"):
        assert f'"{artifact}"' in reuse
        assert f'"{artifact}"' in publish


def test_runner_preserves_public_status_and_log_identifiers() -> None:
    """Renaming the executable must not rename published provenance or documented logs."""
    runner = RUNNER.read_text(encoding="utf-8")

    assert 'LOG_DIR="${LOG_DIR:-/tmp/edcloud-vintage}"' in runner
    assert '"pipeline": "edcloud-vintage"' in runner


def test_github_jobs_export_the_log_directory_consumed_by_the_runner() -> None:
    """Diagnostic artifact paths must use the directory inherited by the runner."""
    publish = PUBLISH.read_text(encoding="utf-8")
    validate = VALIDATE.read_text(encoding="utf-8")

    for job_script in (publish, validate):
        assert 'LOG_DIR = Path("/tmp/edcloud-vintage")' in job_script
        assert '"LOG_DIR": str(LOG_DIR)' in job_script


def test_validation_job_keeps_the_digest_local_to_its_log() -> None:
    """The digest has no downstream consumer and must not create dead metadata."""
    validate = VALIDATE.read_text(encoding="utf-8")

    assert "GITHUB_OUTPUT" not in validate
    assert 'print(f"sha256: {digest}")' in validate


def test_standalone_vintage_bootstrap_excludes_pdf_dependencies() -> None:
    """A local vintage bootstrap uses only the hash-locked runtime environment."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    runner = RUNNER.read_text(encoding="utf-8")

    dependencies = project["project"]["dependencies"]
    pdf_dependencies = project["project"]["optional-dependencies"]["pdf"]
    assert not any(dependency.lower().startswith("playwright") for dependency in dependencies)
    assert sum(dependency.lower().startswith("playwright==") for dependency in pdf_dependencies) == 1
    assert "--require-hashes -r requirements/runtime.lock" in runner
    assert "--no-deps --no-build-isolation -e ." in runner
    assert "Prepared Python environment is required; hosted bootstrap is disabled" in runner
    assert ".[pdf]" not in runner


def test_runner_isolates_each_guest_and_validates_host_handoffs() -> None:
    """Guests run alone without external access or ambient capabilities."""
    runner = RUNNER.read_text(encoding="utf-8")

    assert "--network none" not in runner
    for option in (
        "--cap-drop ALL",
        "--security-opt no-new-privileges",
        "--pids-limit 256",
        "--memory 2g",
    ):
        assert option in runner
    for network_contract in (
        'CONTAINER_NETWORK_NAME="vintage-${BUILD_ID}"',
        "docker network create",
        "--internal",
        'docker network rm "$CONTAINER_NETWORK_ID"',
    ):
        assert network_contract in runner
    assert runner.count('--network "$CONTAINER_NETWORK_ID"') == 2
    main = runner.split("main() {", maxsplit=1)[1].split("\n}", maxsplit=1)[0]
    assert main.index("create_container_network") < main.index("stage_b_vax")
    assert "build/vintage:/build" not in runner
    assert "dst=/inputs/bradman.c,readonly" in runner
    assert "dst=/inputs/bio.vintage.yaml,readonly" in runner
    assert "dst=/inputs/brad.bio.uu,readonly" in runner
    assert "build/vintage/stages/vax" in runner
    assert "build/vintage/stages/pdp11" in runner
    assert '[[ -L "$output" || ! -f "$output" || ! -s "$output" ]]' in runner
    assert "cat -- build/vintage/stages/vax/sections.jsonl build/vintage/stages/pdp11/sections.jsonl" in runner


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

    for package in (
        "build-essential",
        "libedit-dev",
        "libpcre3-dev",
        "wget",
        "ca-certificates",
        "git",
    ):
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
    for prefix in (
        "attach lpt ",
        "set rp0 ",
        "set rp1 ",
        "set rp2 ",
        "set rp3 ",
        "set rl0 ",
        "set rl1 ",
    ):
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
