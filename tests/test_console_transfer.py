"""Tests for uuencode console transfer system."""

import tempfile
from pathlib import Path
import subprocess
import shutil
import pytest


@pytest.mark.skipif(not shutil.which('uuencode'), reason="uuencode not installed")
def test_uuencode_decode_roundtrip():
    """Test that uuencode/uudecode roundtrip preserves data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create test file
        original = tmpdir_path / "test.txt"
        original.write_text("Hello from VAX!\nLine 2\nLine 3\n")

        # Encode
        encoded = tmpdir_path / "test.txt.uu"
        result = subprocess.run(
            ["uuencode", str(original), "test.txt"],
            stdout=open(encoded, 'w'),
            check=True
        )

        assert encoded.exists()
        assert encoded.stat().st_size > 0

        # Verify encoded format
        encoded_text = encoded.read_text()
        assert encoded_text.startswith("begin ")
        assert "test.txt" in encoded_text
        assert encoded_text.strip().endswith("end")

        # Decode
        decoded = tmpdir_path / "test.txt"
        decoded.unlink()  # Remove original

        subprocess.run(
            ["uudecode", str(encoded)],
            cwd=tmpdir,
            check=True
        )

        # Verify decoded matches original
        assert decoded.exists()
        assert decoded.read_text() == original.read_text()


@pytest.mark.skipif(not shutil.which('uuencode'), reason="uuencode not installed")
def test_multiline_uuencode():
    """Test uuencode with multiline content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create multiline file
        original = tmpdir_path / "multiline.txt"
        content = "\n".join([f"Line {i}" for i in range(100)])
        original.write_text(content)

        # Encode
        encoded = tmpdir_path / "multiline.txt.uu"
        subprocess.run(
            ["uuencode", str(original), "multiline.txt"],
            stdout=open(encoded, 'w'),
            check=True
        )

        # Count lines in encoded file
        encoded_lines = encoded.read_text().splitlines()
        assert len(encoded_lines) > 10  # Should be many lines

        # Decode
        original.unlink()
        subprocess.run(
            ["uudecode", str(encoded)],
            cwd=tmpdir,
            check=True
        )

        # Verify
        assert original.read_text() == content


def test_console_transfer_script_exists():
    """Verify console transfer script exists and is executable."""
    script = Path("scripts/console-transfer.py")
    assert script.exists()
    assert script.stat().st_mode & 0o111  # Executable


def test_vax_build_script_exists():
    """Verify VAX build script exists and is executable."""
    script = Path("scripts/vax-build-and-encode.sh")
    assert script.exists()
    assert script.stat().st_mode & 0o111  # Executable


def test_pdp11_validate_script_exists():
    """Verify PDP-11 validation script exists and is executable."""
    script = Path("scripts/pdp11-validate.sh")
    assert script.exists()
    assert script.stat().st_mode & 0o111  # Executable
