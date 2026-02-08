"""IMP (Interface Message Processor) log collector."""

from typing import Optional

from arpanet_logging.core.collector import BaseCollector
from arpanet_logging.core.models import LogEntry
from arpanet_logging.parsers.arpanet import ArpanetParser


class IMPCollector(BaseCollector):
    """Collects logs from IMP SIMH containers.

    Streams logs from Docker containers running H316 IMP simulator,
    parses ARPANET 1822 protocol messages, routing decisions, and
    host/modem interface events.
    """

    component_name = "imp"  # Will be overridden by imp1, imp2, etc.
    log_source = "console"

    def __init__(self, *args, **kwargs):
        """Initialize IMP collector with ARPANET parser."""
        super().__init__(*args, **kwargs)

        # Initialize parser if not provided
        if self.parser is None:
            self.parser = ArpanetParser()

    def parse_line(self, timestamp: str, message: str) -> Optional[LogEntry]:
        """Parse IMP log line.

        Args:
            timestamp: ISO 8601 timestamp
            message: Log message from IMP simulator

        Returns:
            LogEntry or None
        """
        # Parse message
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
