"""Host Logging System.

Modular, DRY logging infrastructure for host/network integration testing.
Provides real-time log collection, parsing, and persistent storage.
"""

__version__ = "0.1.0"

from host_logging.core.models import BuildMetadata, LogEntry
from host_logging.core.storage import LogStorage

# Optional collector imports depend on the docker SDK being installed.
try:
    from host_logging.collectors.vax import VAXCollector
    from host_logging.core.collector import BaseCollector
except ModuleNotFoundError:  # pragma: no cover - environment-dependent
    BaseCollector = None  # type: ignore[assignment]  # pylint: disable=invalid-name
    VAXCollector = None  # type: ignore[assignment]  # pylint: disable=invalid-name

__all__ = [
    "LogEntry",
    "BuildMetadata",
    "LogStorage",
    "BaseCollector",
    "VAXCollector",
]
