"""VAX/BSD log collector."""

from typing import Optional

from arpanet_logging.core.collector import BaseCollector
from arpanet_logging.core.models import LogEntry
from arpanet_logging.parsers.bsd import BSDParser


class VAXCollector(BaseCollector):
    """Collects logs from VAX/BSD SIMH container.

    Streams logs from Docker container running VAX/BSD 4.3, parses
    BSD system messages, and extracts network events, boot sequences,
    and authentication activities.
    """

    component_name = "vax"
    log_source = "console"

    def __init__(self, *args, **kwargs):
        """Initialize VAX collector with BSD parser."""
        super().__init__(*args, **kwargs)

        # Initialize parser if not provided
        if self.parser is None:
            self.parser = BSDParser()

    def parse_line(self, timestamp: str, message: str) -> Optional[LogEntry]:
        """Parse VAX/BSD log line.

        Args:
            timestamp: ISO 8601 timestamp
            message: Log message

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
