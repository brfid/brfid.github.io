"""Core logging infrastructure."""

from host_logging.core.models import BuildMetadata, LogEntry
from host_logging.core.parser import BaseParser
from host_logging.core.storage import LogStorage

try:
    from host_logging.core.collector import BaseCollector
except ModuleNotFoundError:  # pragma: no cover - environment-dependent
    BaseCollector = None  # type: ignore[assignment]  # pylint: disable=invalid-name

__all__ = [
    "LogEntry",
    "BuildMetadata",
    "LogStorage",
    "BaseCollector",
    "BaseParser",
]
