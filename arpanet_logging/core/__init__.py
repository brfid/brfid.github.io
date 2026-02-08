"""Core logging infrastructure."""

from arpanet_logging.core.models import LogEntry, BuildMetadata
from arpanet_logging.core.storage import LogStorage
from arpanet_logging.core.parser import BaseParser

try:
    from arpanet_logging.core.collector import BaseCollector
except ModuleNotFoundError:  # pragma: no cover - environment-dependent
    BaseCollector = None  # type: ignore[assignment]

__all__ = [
    "LogEntry",
    "BuildMetadata",
    "LogStorage",
    "BaseCollector",
    "BaseParser",
]
