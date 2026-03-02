"""Base parser interface for log parsing."""

from abc import ABC, abstractmethod
from typing import Any


class BaseParser(ABC):
    """Base class for log parsers.

    Parsers extract structured information from raw log messages.
    """

    @abstractmethod
    def parse(self, message: str) -> dict[str, Any] | None:
        """Parse a log message.

        Args:
            message: Raw log message

        Returns:
            Dictionary of parsed data, or None if not parseable
        """

    @abstractmethod
    def extract_tags(self, message: str) -> list[str]:
        """Extract tags/categories from a log message.

        Args:
            message: Raw log message

        Returns:
            List of tags
        """

    def detect_log_level(self, message: str) -> str:
        """Detect log level from message.

        Args:
            message: Raw log message

        Returns:
            Log level string ("DEBUG", "INFO", "WARN", "ERROR")
        """
        message_lower = message.lower()

        if any(word in message_lower for word in ["error", "fail", "fatal", "panic"]):
            return "ERROR"
        if any(word in message_lower for word in ["warn", "warning"]):
            return "WARN"
        if any(word in message_lower for word in ["debug", "trace"]):
            return "DEBUG"
        return "INFO"
