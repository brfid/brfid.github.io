from __future__ import annotations

import json
from pathlib import Path

from arpanet_logging.core.models import BuildMetadata, LogEntry
from arpanet_logging.core.storage import LogStorage


def _metadata(build_id: str) -> BuildMetadata:
    return BuildMetadata(
        build_id=build_id,
        phase="phase2",
        start_time="2026-02-08T10:00:00Z",
        components=["vax", "imp1"],
        git_commit="abc123",
        git_branch="main",
        environment={"host": "test"},
    )


def _entry(build_id: str, component: str, level: str, message: str, tags: list[str]) -> LogEntry:
    return LogEntry(
        build_id=build_id,
        component=component,
        timestamp="2026-02-08T10:01:00Z",
        phase="phase2",
        log_level=level,
        source="console",
        message=message,
        parsed={"k": "v"},
        tags=tags,
    )


def test_storage_initialize_and_finalize_write_expected_artifacts(tmp_path: Path) -> None:
    storage = LogStorage(build_id="build-1", base_path=str(tmp_path), local_fallback=False)
    metadata = _metadata("build-1")

    storage.initialize(metadata)
    storage.write_raw("vax", "boot line")
    storage.write_event(_entry("build-1", "vax", "ERROR", "fatal error", ["error", "boot"]))
    storage.write_event(_entry("build-1", "vax", "WARN", "warning line", ["boot"]))

    metadata.end_time = "2026-02-08T10:02:00Z"
    metadata.status = "success"
    storage.finalize(metadata)

    build_path = tmp_path / "builds" / "build-1"
    assert (build_path / "metadata.json").exists()
    assert (build_path / "vax" / "vax.log").exists()
    assert (build_path / "vax" / "events.jsonl").exists()
    assert (build_path / "vax" / "summary.json").exists()

    summary = json.loads((build_path / "vax" / "summary.json").read_text(encoding="utf-8"))
    assert summary["total_lines"] == 2
    assert summary["errors"] == 1
    assert summary["warnings"] == 1
    assert summary["tags"]["boot"] == 2


def test_storage_index_is_updated_and_sorted_most_recent_first(tmp_path: Path) -> None:
    first = LogStorage(build_id="build-old", base_path=str(tmp_path), local_fallback=False)
    first_meta = _metadata("build-old")
    first.initialize(first_meta)
    first_meta.end_time = "2026-02-08T10:01:00Z"
    first_meta.start_time = "2026-02-08T10:00:00Z"
    first.finalize(first_meta)

    second = LogStorage(build_id="build-new", base_path=str(tmp_path), local_fallback=False)
    second_meta = _metadata("build-new")
    second_meta.start_time = "2026-02-08T11:00:00Z"
    second.initialize(second_meta)
    second_meta.end_time = "2026-02-08T11:01:00Z"
    second.finalize(second_meta)

    index_path = tmp_path / "index.json"
    data = json.loads(index_path.read_text(encoding="utf-8"))
    assert [item["build_id"] for item in data[:2]] == ["build-new", "build-old"]
