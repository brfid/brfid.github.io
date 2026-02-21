from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from host_logging import cli
from host_logging.core.models import BuildMetadata, LogEntry
from host_logging.core.storage import LogStorage


def test_cli_list_and_show_work_with_real_storage(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    storage = LogStorage(build_id="build-integration-1", base_path=str(tmp_path), local_fallback=False)
    metadata = BuildMetadata(
        build_id="build-integration-1",
        phase="phase2",
        start_time="2026-02-08T12:00:00Z",
        components=["vax"],
        git_commit="abc123",
        git_branch="main",
        environment={"runner": "pytest"},
    )

    storage.initialize(metadata)
    storage.write_raw("vax", "boot line")
    storage.write_event(
        LogEntry(
            build_id="build-integration-1",
            component="vax",
            timestamp="2026-02-08T12:00:01Z",
            phase="phase2",
            log_level="INFO",
            source="console",
            message="boot complete",
            parsed={"event": "boot"},
            tags=["boot"],
        )
    )
    metadata.end_time = "2026-02-08T12:00:02Z"
    metadata.status = "success"
    storage.finalize(metadata)

    cli.cmd_list(SimpleNamespace(path=str(tmp_path), limit=20))
    out_list = capsys.readouterr().out
    assert "build-integration-1" in out_list

    cli.cmd_show(SimpleNamespace(path=str(tmp_path), build_id="build-integration-1"))
    out_show = capsys.readouterr().out
    assert "Build: build-integration-1" in out_show
    assert "VAX:" in out_show
