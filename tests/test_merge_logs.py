"""Tests for log merging script."""

import tempfile
from pathlib import Path
import subprocess


def test_merge_logs_chronological():
    """Test that logs are merged in chronological order."""
    with tempfile.TemporaryDirectory() as tmpdir:
        build_dir = Path(tmpdir) / "builds" / "test-build"
        build_dir.mkdir(parents=True)

        # Create test logs with different timestamps
        vax_log = build_dir / "VAX.log"
        vax_log.write_text(
            "[2026-02-13 10:00:00 VAX] Starting compilation\n"
            "[2026-02-13 10:00:05 VAX] Compilation complete\n"
        )

        github_log = build_dir / "GITHUB.log"
        github_log.write_text(
            "[2026-02-13 09:59:55 GITHUB] Transferring files\n"
            "[2026-02-13 10:00:10 GITHUB] Build complete\n"
        )

        pdp11_log = build_dir / "PDP11.log"
        pdp11_log.write_text(
            "[2026-02-13 10:00:02 PDP11] Processing data\n"
            "[2026-02-13 10:00:08 PDP11] Data processed\n"
        )

        # Run merge script with custom base path
        result = subprocess.run(
            ["python", "scripts/merge-logs.py", "test-build", tmpdir],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
        )

        # Check it succeeded
        assert result.returncode == 0, f"Merge failed: {result.stderr}"

        # Read merged output
        merged_log = build_dir / "merged.log"
        assert merged_log.exists(), "merged.log was not created"

        merged_lines = merged_log.read_text().splitlines()

        # Verify chronological order
        expected = [
            "[2026-02-13 09:59:55 GITHUB] Transferring files",
            "[2026-02-13 10:00:00 VAX] Starting compilation",
            "[2026-02-13 10:00:02 PDP11] Processing data",
            "[2026-02-13 10:00:05 VAX] Compilation complete",
            "[2026-02-13 10:00:08 PDP11] Data processed",
            "[2026-02-13 10:00:10 GITHUB] Build complete",
        ]

        assert merged_lines == expected, f"Expected:\n{expected}\n\nGot:\n{merged_lines}"


def test_merge_logs_empty_dir():
    """Test that merge script handles empty directory gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        build_dir = Path(tmpdir) / "builds" / "empty-build"
        build_dir.mkdir(parents=True)

        result = subprocess.run(
            ["python", "scripts/merge-logs.py", "empty-build", tmpdir],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
        )

        # Should fail gracefully with warning
        assert result.returncode == 1
        assert "No valid log entries" in result.stderr


def test_merge_logs_single_source():
    """Test merging with only one log source."""
    with tempfile.TemporaryDirectory() as tmpdir:
        build_dir = Path(tmpdir) / "builds" / "single-build"
        build_dir.mkdir(parents=True)

        vax_log = build_dir / "VAX.log"
        vax_log.write_text(
            "[2026-02-13 10:00:00 VAX] Line 1\n"
            "[2026-02-13 10:00:01 VAX] Line 2\n"
            "[2026-02-13 10:00:02 VAX] Line 3\n"
        )

        result = subprocess.run(
            ["python", "scripts/merge-logs.py", "single-build", tmpdir],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        merged_log = build_dir / "merged.log"
        merged_lines = merged_log.read_text().splitlines()
        assert len(merged_lines) == 3
