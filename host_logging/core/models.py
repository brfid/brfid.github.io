"""Data models for ARPANET logging."""

import json
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class LogEntry:
    """Structured log entry with normalized metadata.

    Attributes:
        build_id: Unique identifier for this test run (e.g., "build-20260207-221530")
        component: Component name ("vax", "imp1", "imp2", "pdp10")
        timestamp: ISO 8601 timestamp when log was generated
        phase: Testing phase ("phase1", "phase2", "validation")
        log_level: Log level ("DEBUG", "INFO", "WARN", "ERROR")
        source: Log source ("console", "syslog", "simh", "docker")
        message: Raw log message
        parsed: Component-specific parsed data
        tags: List of tags for categorization
    """

    build_id: str
    component: str
    timestamp: str  # ISO 8601 format
    phase: str
    log_level: str
    source: str
    message: str
    parsed: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LogEntry":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class BuildMetadata:
    """Metadata for a test build/run.

    Attributes:
        build_id: Unique build identifier
        phase: Testing phase
        start_time: When collection started
        end_time: When collection ended (None if ongoing)
        components: List of components being logged
        git_commit: Git commit hash
        git_branch: Git branch name
        environment: Environment info (AWS, local, etc.)
        status: Build status ("running", "success", "failed")
        notes: Additional notes or description
    """

    build_id: str
    phase: str
    start_time: str  # ISO 8601
    end_time: str | None = None  # ISO 8601
    components: list[str] = field(default_factory=list)
    git_commit: str | None = None
    git_branch: str | None = None
    environment: dict[str, Any] = field(default_factory=dict)
    status: str = "running"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convert to formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BuildMetadata":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ComponentStats:
    """Statistics for a component's logs.

    Attributes:
        component: Component name
        total_lines: Total log lines collected
        log_levels: Count by log level
        tags: Count by tag
        first_timestamp: First log entry timestamp
        last_timestamp: Last log entry timestamp
        errors: Number of error lines
        warnings: Number of warning lines
    """

    component: str
    total_lines: int = 0
    log_levels: dict[str, int] = field(default_factory=dict)
    tags: dict[str, int] = field(default_factory=dict)
    first_timestamp: str | None = None
    last_timestamp: str | None = None
    errors: int = 0
    warnings: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convert to formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
