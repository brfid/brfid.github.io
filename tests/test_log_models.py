from __future__ import annotations

from arpanet_logging.core.models import BuildMetadata, ComponentStats, LogEntry


def test_log_entry_roundtrip_dict_and_json() -> None:
    entry = LogEntry(
        build_id="build-123",
        component="vax",
        timestamp="2026-02-08T10:00:00Z",
        phase="phase2",
        log_level="INFO",
        source="console",
        message="boot complete",
        parsed={"event": "boot"},
        tags=["boot"],
    )

    as_dict = entry.to_dict()
    assert as_dict["component"] == "vax"
    assert as_dict["parsed"]["event"] == "boot"

    rebuilt = LogEntry.from_dict(as_dict)
    assert rebuilt == entry
    assert '"build_id": "build-123"' in entry.to_json()


def test_build_metadata_roundtrip_dict_and_json() -> None:
    metadata = BuildMetadata(
        build_id="build-456",
        phase="phase3",
        start_time="2026-02-08T11:00:00Z",
        end_time="2026-02-08T11:05:00Z",
        components=["vax", "imp1"],
        git_commit="deadbeef",
        git_branch="main",
        environment={"platform": "Linux"},
        status="success",
        notes="ok",
    )

    payload = metadata.to_dict()
    assert payload["phase"] == "phase3"
    assert payload["components"] == ["vax", "imp1"]

    rebuilt = BuildMetadata.from_dict(payload)
    assert rebuilt == metadata
    assert '"status": "success"' in metadata.to_json()


def test_component_stats_json_contains_expected_fields() -> None:
    stats = ComponentStats(
        component="imp1",
        total_lines=10,
        log_levels={"INFO": 8, "ERROR": 2},
        tags={"routing": 4},
        first_timestamp="2026-02-08T10:00:00Z",
        last_timestamp="2026-02-08T10:10:00Z",
        errors=2,
        warnings=1,
    )

    rendered = stats.to_json()
    assert '"component": "imp1"' in rendered
    assert '"errors": 2' in rendered
