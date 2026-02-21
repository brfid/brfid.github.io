"""Host Logging System.

Modular, DRY logging infrastructure for host/network integration testing.
Provides real-time log collection, parsing, and persistent storage.
"""

__version__ = "0.1.0"

from host_logging.core.models import LogEntry, BuildMetadata
from host_logging.core.storage import LogStorage

# Optional collector imports depend on the docker SDK being installed.
try:
    from host_logging.core.collector import BaseCollector
    from host_logging.collectors.vax import VAXCollector
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
