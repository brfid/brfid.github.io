"""Base collector class for DRY logging infrastructure."""

try:
    import docker
except ModuleNotFoundError:  # pragma: no cover - environment-dependent
    docker = None  # type: ignore[assignment]

from datetime import datetime, timezone
from typing import Optional, List
import threading

from arpanet_logging.core.models import LogEntry
from arpanet_logging.core.storage import LogStorage
from arpanet_logging.core.parser import BaseParser


class BaseCollector:
    """Base class for log collectors.

    Provides common functionality for streaming Docker logs and parsing them.
    Subclasses implement component-specific parsing logic.
    """

    @staticmethod
    def _utc_now_isoz() -> str:
        """Return a UTC ISO-8601 timestamp with trailing Z."""
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Component name (override in subclass)
    component_name: str = "unknown"

    # Default log source (override in subclass if needed)
    log_source: str = "docker"

    def __init__(
        self,
        build_id: str,
        container_name: str,
        storage: LogStorage,
        phase: str = "phase2",
        parser: Optional[BaseParser] = None
    ):
        """Initialize collector.

        Args:
            build_id: Unique build identifier
            container_name: Docker container name to collect from
            storage: Storage backend
            phase: Testing phase
            parser: Optional custom parser
        """
        self.build_id = build_id
        self.container_name = container_name
        self.storage = storage
        self.phase = phase
        self.parser = parser

        self.docker_client = docker.from_env() if docker is not None else None
        self.running = False
        self.thread: Optional[threading.Thread] = None

    def start(self):
        """Start collecting logs in background thread."""
        if self.running:
            print(f"⚠️  {self.component_name} collector already running")
            return

        self.running = True
        self.thread = threading.Thread(
            target=self._collect_loop,
            daemon=True,
            name=f"collector-{self.component_name}"
        )
        self.thread.start()
        print(f"🔄 {self.component_name.upper()} collector started")

    def stop(self):
        """Stop collecting logs and wait for thread to finish."""
        if not self.running:
            return

        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print(f"⏹️  {self.component_name.upper()} collector stopped")

    def _collect_loop(self):
        """Main collection loop (runs in background thread)."""
        if self.docker_client is None:
            print(f"❌ Docker SDK unavailable, cannot collect {self.component_name} logs")
            return

        try:
            container = self.docker_client.containers.get(self.container_name)

            # Stream logs in real-time
            for log_line in container.logs(
                stream=True,
                follow=True,
                timestamps=True
            ):
                if not self.running:
                    break

                try:
                    # Decode log line
                    line = log_line.decode('utf-8', errors='replace').rstrip()

                    # Process the line
                    self._process_line(line)

                except Exception as e:
                    print(f"Error processing log line from {self.component_name}: {e}")
                    continue

        except Exception as exc:
            if docker is not None and isinstance(exc, docker.errors.NotFound):
                print(f"❌ Container {self.container_name} not found")
                return
            print(f"❌ Error in {self.component_name} collector: {exc}")

    def _process_line(self, line: str):
        """Process a single log line.

        Args:
            line: Raw log line with timestamp prefix
        """
        # Parse Docker timestamp format: "2026-02-07T22:30:15.123456789Z message"
        try:
            if ' ' in line:
                timestamp_str, message = line.split(' ', 1)
            else:
                timestamp_str = self._utc_now_isoz()
                message = line
        except ValueError:
            timestamp_str = self._utc_now_isoz()
            message = line

        # Write raw message
        self.storage.write_raw(self.component_name, message)

        # Parse into structured entry
        entry = self.parse_line(timestamp_str, message)

        if entry:
            # Write structured event
            self.storage.write_event(entry)

    def parse_line(self, timestamp: str, message: str) -> Optional[LogEntry]:
        """Parse a log line into a structured entry.

        Default implementation uses the collector's parser if available.
        Subclasses can override for custom parsing logic.

        Args:
            timestamp: ISO 8601 timestamp
            message: Log message

        Returns:
            LogEntry if successfully parsed, None to skip
        """
        # Parse message using component parser
        parsed = self.parser.parse(message) if self.parser else {}
        tags = self.parser.extract_tags(message) if self.parser else []
        log_level = self.parser.detect_log_level(message) if self.parser else "INFO"

        # Create entry
        return self.create_entry(
            timestamp=timestamp,
            message=message,
            log_level=log_level,
            tags=tags,
            parsed=parsed
        )

    def create_entry(
        self,
        timestamp: str,
        message: str,
        log_level: str = "INFO",
        tags: Optional[List[str]] = None,
        parsed: Optional[dict] = None
    ) -> LogEntry:
        """Helper to create a LogEntry with common fields filled in.

        Args:
            timestamp: ISO 8601 timestamp
            message: Log message
            log_level: Log level
            tags: Optional tags
            parsed: Optional parsed data

        Returns:
            LogEntry instance
        """
        return LogEntry(
            build_id=self.build_id,
            component=self.component_name,
            timestamp=timestamp,
            phase=self.phase,
            log_level=log_level,
            source=self.log_source,
            message=message,
            parsed=parsed or {},
            tags=tags or []
        )
