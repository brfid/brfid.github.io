"""IMP (Interface Message Processor) log collector."""

from host_logging.core.collector import BaseCollector
from host_logging.parsers.arpanet import ArpanetParser


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
