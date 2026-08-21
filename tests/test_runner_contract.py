"""Contracts for the containerized vintage runner."""

from pathlib import Path

RUNNER = Path(__file__).resolve().parents[1] / "scripts" / "edcloud-vintage-runner.sh"


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
