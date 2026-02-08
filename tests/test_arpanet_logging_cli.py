from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from arpanet_logging import cli


def test_generate_build_id_has_expected_format() -> None:
    build_id = cli.generate_build_id()
    assert re.fullmatch(r"build-\d{8}-\d{6}", build_id) is not None


def test_cmd_collect_constructs_orchestrator_and_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    called = SimpleNamespace(run_duration=None)

    class _FakeOrchestrator:
        def __init__(self, *, build_id: str, components: list[str], phase: str, base_path: str) -> None:
            assert build_id == "build-fixed"
            assert components == ["vax", "imp1"]
            assert phase == "phase2"
            assert base_path == "/tmp/logs"

        def run(self, duration: int | None = None) -> None:
            called.run_duration = duration

    monkeypatch.setattr(cli, "LogOrchestrator", _FakeOrchestrator)

    args = SimpleNamespace(
        build_id="build-fixed",
        components=["vax", "imp1"],
        phase="phase2",
        path="/tmp/logs",
        duration=30,
    )
    cli.cmd_collect(args)
    assert called.run_duration == 30


def test_cmd_list_prints_when_index_missing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    args = SimpleNamespace(path=str(tmp_path), limit=20)
    cli.cmd_list(args)
    out = capsys.readouterr().out
    assert "No builds found" in out


def test_cmd_show_prints_component_summary(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    build_id = "build-1"
    build_path = tmp_path / "builds" / build_id
    (build_path / "vax").mkdir(parents=True)

    metadata = {
        "build_id": build_id,
        "phase": "phase2",
        "start_time": "2026-02-08T10:00:00Z",
        "end_time": "2026-02-08T10:05:00Z",
        "status": "success",
        "git_commit": "abc123",
        "git_branch": "main",
        "components": ["vax"],
    }
    (build_path / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    summary = {
        "total_lines": 12,
        "errors": 1,
        "warnings": 2,
        "first_timestamp": "2026-02-08T10:00:01Z",
        "last_timestamp": "2026-02-08T10:04:59Z",
        "tags": {"boot": 3, "network": 2},
    }
    (build_path / "vax" / "summary.json").write_text(json.dumps(summary), encoding="utf-8")

    args = SimpleNamespace(path=str(tmp_path), build_id=build_id)
    cli.cmd_show(args)
    out = capsys.readouterr().out
    assert "Build: build-1" in out
    assert "Total lines: 12" in out
    assert "Top tags: boot(3), network(2)" in out


def test_cmd_cleanup_removes_older_builds(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    builds_path = tmp_path / "builds"
    builds_path.mkdir(parents=True)

    for name in ["build-1", "build-2", "build-3"]:
        (builds_path / name).mkdir()

    args = SimpleNamespace(path=str(tmp_path), keep=1)
    cli.cmd_cleanup(args)

    remaining = sorted(p.name for p in builds_path.iterdir())
    assert remaining == ["build-3"]

    out = capsys.readouterr().out
    assert "Cleanup complete" in out


def test_cmd_cleanup_handles_missing_builds_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = SimpleNamespace(path=str(tmp_path), keep=3)
    cli.cmd_cleanup(args)
    out = capsys.readouterr().out
    assert "No builds directory" in out


def test_cmd_cleanup_noop_when_build_count_within_keep(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    builds_path = tmp_path / "builds"
    builds_path.mkdir(parents=True)
    (builds_path / "build-1").mkdir()
    (builds_path / "build-2").mkdir()

    args = SimpleNamespace(path=str(tmp_path), keep=5)
    cli.cmd_cleanup(args)

    out = capsys.readouterr().out
    assert "nothing to clean up" in out
