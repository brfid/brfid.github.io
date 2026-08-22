"""Tests for shared SIMH session utilities."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# scripts/ is not a package; add it to the path so we can import simh_session.
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from pdp11_pexpect import _CAPTURE_BEGIN as PDP_CAPTURE_BEGIN
from pdp11_pexpect import _CAPTURE_END as PDP_CAPTURE_END
from simh_session import (
    UUE_CHUNK_SIZE,
    GuestCommandError,
    inject_batched_heredoc,
    make_logger,
    run_checked,
    validate_uu_spool,
)
from vax_pexpect import _CAPTURE_BEGIN as VAX_CAPTURE_BEGIN
from vax_pexpect import _CAPTURE_END as VAX_CAPTURE_END

VALID_UUE = (
    "begin 644 brad.bio.roff\n"
    r"M+2UM86X,`0(#!`4&!P@)" + r"`@L,#0X/$!$2$Q05%A<8&1H;&QT='h" + "\n"
    "`\n"
    "end"
)


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


def test_make_logger_writes_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    log = make_logger("test_prefix")
    log("hello world")
    captured = capsys.readouterr()
    assert "[test_prefix]" in captured.err
    assert "hello world" in captured.err


def test_make_logger_includes_timestamp(capsys: pytest.CaptureFixture[str]) -> None:
    log = make_logger("ts_test")
    log("msg")
    captured = capsys.readouterr()
    assert re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", captured.err)


def test_make_logger_different_prefixes(capsys: pytest.CaptureFixture[str]) -> None:
    log_a = make_logger("vax_pexpect")
    log_b = make_logger("pdp11_pexpect")
    log_a("from vax")
    log_b("from pdp11")
    captured = capsys.readouterr()
    assert "[vax_pexpect]" in captured.err
    assert "[pdp11_pexpect]" in captured.err


def _make_mock_child(prompt: str = "PDPsh> ") -> MagicMock:
    child = MagicMock()
    child.expect.return_value = 0
    child.match.group.return_value = b"0"
    return child


def test_inject_single_batch() -> None:
    child = _make_mock_child()
    lines = ["begin 644 foo", "MDATA", "`", "end"]
    inject_batched_heredoc(child, "/tmp/foo.uu", lines, "PDPsh> ", 60)

    first_call = child.sendline.call_args_list[0]
    assert "cat > /tmp/foo.uu" in first_call[0][0]
    heredoc_eof_calls = [c for c in child.sendline.call_args_list if c[0][0] == "HEREDOC_EOF"]
    assert len(heredoc_eof_calls) == 1
    assert child.expect.call_count == 3


def test_inject_multiple_batches() -> None:
    child = _make_mock_child()
    lines = [f"line{i}" for i in range(25)]
    inject_batched_heredoc(child, "/tmp/bar.uu", lines, "PDPsh> ", 60)

    expected_batches = -(-25 // UUE_CHUNK_SIZE)  # ceil division
    assert child.expect.call_count == expected_batches + 2


def test_inject_first_batch_uses_create_redirect() -> None:
    child = _make_mock_child()
    lines = [f"line{i}" for i in range(UUE_CHUNK_SIZE + 1)]
    inject_batched_heredoc(child, "/tmp/x.uu", lines, "PDPsh> ", 60)

    cat_calls = [c[0][0] for c in child.sendline.call_args_list if c[0][0].startswith("cat ")]
    assert "cat > /tmp/x.uu" in cat_calls[0]
    assert "cat >> /tmp/x.uu" in cat_calls[1]


def test_inject_empty_lines() -> None:
    child = _make_mock_child()
    inject_batched_heredoc(child, "/tmp/empty.uu", [], "PDPsh> ", 60)
    child.sendline.assert_not_called()
    child.expect.assert_not_called()


@pytest.mark.parametrize(
    ("pattern", "marker"),
    [
        (VAX_CAPTURE_BEGIN, b"__BRADBIOUU_BEGIN__"),
        (VAX_CAPTURE_END, b"__BRADBIOUU_END__"),
        (PDP_CAPTURE_BEGIN, b"__BRAD_BIO_TXT_BEGIN__"),
        (PDP_CAPTURE_END, b"__BRAD_BIO_TXT_END__"),
    ],
)
def test_capture_markers_match_only_complete_lines(pattern: re.Pattern[bytes], marker: bytes) -> None:
    assert pattern.search(marker + b"\r\n")
    assert pattern.search(b"prefix\r\n" + marker + b"\n")
    assert not pattern.search(b"prefix" + marker + b"\r\n")
    assert not pattern.search(marker + b"suffix\r\n")


def test_run_checked_returns_command_output() -> None:
    child = _make_mock_child()
    child.before = b"command output\r\n"

    output = run_checked(child, "do-work", "PDPsh> ", 60, label="work")

    assert output == b"command output\r\n"
    sent = child.sendline.call_args.args[0]
    assert 'echo __VINTAGE_RC_"${vintage_rc}__"' in sent
    assert "__VINTAGE_RC_0__" not in sent
    assert child.expect.call_count == 2


def test_run_checked_raises_for_nonzero_guest_status() -> None:
    child = _make_mock_child()
    child.before = b"guest error\r\n"
    child.match.group.return_value = b"7"

    with pytest.raises(GuestCommandError, match="guest exit status 7"):
        run_checked(child, "false", "PDPsh> ", 60, label="expected failure")
