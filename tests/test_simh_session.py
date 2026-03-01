"""Tests for scripts/simh_session.py shared SIMH session utilities."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# scripts/ is not a package; add it to the path so we can import simh_session.
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from simh_session import UUE_CHUNK_SIZE, inject_batched_heredoc, make_logger, validate_uu_spool

VALID_UUE = (
    "begin 644 brad.1\n"
    r"M+2UM86X,`0(#!`4&!P@)"  + r"`@L,#0X/$!$2$Q05%A<8&1H;&QT='h" + "\n"
    "`\n"
    "end"
)


# ---------------------------------------------------------------------------
# validate_uu_spool
# ---------------------------------------------------------------------------


def test_validate_valid_spool() -> None:
    validate_uu_spool(VALID_UUE)  # must not raise


def test_validate_empty_spool() -> None:
    with pytest.raises(ValueError, match="empty"):
        validate_uu_spool("")


def test_validate_empty_whitespace_only() -> None:
    with pytest.raises(ValueError, match="empty"):
        validate_uu_spool("   \n   \n")


def test_validate_missing_begin() -> None:
    with pytest.raises(ValueError, match="begin"):
        validate_uu_spool("data line\nend")


def test_validate_missing_end() -> None:
    with pytest.raises(ValueError, match="end"):
        validate_uu_spool("begin 644 foo\ndata line")


def test_validate_no_data_lines() -> None:
    with pytest.raises(ValueError, match="no data lines"):
        validate_uu_spool("begin 644 foo\nend")


def test_validate_custom_label_in_error() -> None:
    with pytest.raises(ValueError, match="myfile.uu"):
        validate_uu_spool("", label="myfile.uu")


# ---------------------------------------------------------------------------
# make_logger
# ---------------------------------------------------------------------------


def test_make_logger_writes_to_stderr(capsys) -> None:
    log = make_logger("test_prefix")
    log("hello world")
    captured = capsys.readouterr()
    assert "[test_prefix]" in captured.err
    assert "hello world" in captured.err


def test_make_logger_includes_timestamp(capsys) -> None:
    log = make_logger("ts_test")
    log("msg")
    captured = capsys.readouterr()
    # Timestamp is in YYYY-MM-DD HH:MM:SS format
    import re
    assert re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", captured.err)


def test_make_logger_different_prefixes(capsys) -> None:
    log_a = make_logger("vax_pexpect")
    log_b = make_logger("pdp11_pexpect")
    log_a("from vax")
    log_b("from pdp11")
    captured = capsys.readouterr()
    assert "[vax_pexpect]" in captured.err
    assert "[pdp11_pexpect]" in captured.err


# ---------------------------------------------------------------------------
# inject_batched_heredoc
# ---------------------------------------------------------------------------


def _make_mock_child(prompt: str = "PDPsh> ") -> MagicMock:
    child = MagicMock()
    child.expect.return_value = 0
    return child


def test_inject_single_batch() -> None:
    """Lines that fit in one chunk are injected as a single heredoc."""
    child = _make_mock_child()
    lines = ["begin 644 foo", "MDATA", "`", "end"]
    inject_batched_heredoc(child, "/tmp/foo.uu", lines, "PDPsh> ", 60)

    # Single batch: first sendline is the cat redirect
    first_call = child.sendline.call_args_list[0]
    assert "cat > /tmp/foo.uu" in first_call[0][0]
    # Final sendline before expect is HEREDOC_EOF
    heredoc_eof_calls = [c for c in child.sendline.call_args_list if c[0][0] == "HEREDOC_EOF"]
    assert len(heredoc_eof_calls) == 1
    # expect called once
    assert child.expect.call_count == 1


def test_inject_multiple_batches() -> None:
    """Lines exceeding UUE_CHUNK_SIZE are split into multiple heredocs."""
    child = _make_mock_child()
    # 25 lines → ceil(25 / UUE_CHUNK_SIZE) batches
    lines = [f"line{i}" for i in range(25)]
    inject_batched_heredoc(child, "/tmp/bar.uu", lines, "PDPsh> ", 60)

    expected_batches = -(-25 // UUE_CHUNK_SIZE)  # ceil division
    assert child.expect.call_count == expected_batches


def test_inject_first_batch_uses_create_redirect() -> None:
    """First batch uses '>' (create); subsequent batches use '>>'."""
    child = _make_mock_child()
    lines = [f"line{i}" for i in range(UUE_CHUNK_SIZE + 1)]
    inject_batched_heredoc(child, "/tmp/x.uu", lines, "PDPsh> ", 60)

    cat_calls = [
        c[0][0] for c in child.sendline.call_args_list
        if c[0][0].startswith("cat ")
    ]
    assert "cat > /tmp/x.uu" in cat_calls[0]
    assert "cat >> /tmp/x.uu" in cat_calls[1]


def test_inject_empty_lines() -> None:
    """Empty line list produces no heredoc batches."""
    child = _make_mock_child()
    inject_batched_heredoc(child, "/tmp/empty.uu", [], "PDPsh> ", 60)
    child.sendline.assert_not_called()
    child.expect.assert_not_called()
