"""Core logging infrastructure."""

from host_logging.core.models import LogEntry, BuildMetadata
from host_logging.core.storage import LogStorage
from host_logging.core.parser import BaseParser

try:
    from host_logging.core.collector import BaseCollector
except ModuleNotFoundError:  # pragma: no cover - environment-dependent
    BaseCollector = None  # type: ignore[assignment]

__all__ = [
    "LogEntry",
    "BuildMetadata",
    "LogStorage",
    "BaseCollector",
    "BaseParser",
]
