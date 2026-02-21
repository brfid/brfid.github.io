"""VAX/BSD log collector."""

from host_logging.core.collector import BaseCollector
from host_logging.parsers.bsd import BSDParser


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
