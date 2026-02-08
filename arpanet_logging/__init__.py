"""ARPANET Logging System.

Modular, DRY logging infrastructure for ARPANET integration testing.
Provides real-time log collection, parsing, and persistent storage.
"""

__version__ = "0.1.0"

from arpanet_logging.core.models import LogEntry, BuildMetadata
from arpanet_logging.core.storage import LogStorage

# Optional collector imports depend on the docker SDK being installed.
try:
    from arpanet_logging.core.collector import BaseCollector
    from arpanet_logging.collectors.vax import VAXCollector
except ModuleNotFoundError:  # pragma: no cover - environment-dependent
    BaseCollector = None  # type: ignore[assignment]
    VAXCollector = None  # type: ignore[assignment]

__all__ = [
    "LogEntry",
    "BuildMetadata",
    "LogStorage",
    "BaseCollector",
    "VAXCollector",
]
