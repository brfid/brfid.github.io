"""ARPANET 1822 protocol parser for IMP messages."""

import re
from typing import Optional, Dict, Any, List

from host_logging.core.parser import BaseParser


class ArpanetParser(BaseParser):
    """Parser for ARPANET 1822 protocol messages from IMP simulators."""

    # Patterns for ARPANET IMP log messages
    PATTERNS = {
        # Host Interface messages: "HI1: packet send/recv"
        "hi_packet": re.compile(r"(HI\d+):\s+(packet|message|send|recv|transmit)", re.I),

        # Modem Interface messages: "MI1: packet send/recv"
        "mi_packet": re.compile(r"(MI\d+):\s+(packet|message|send|recv|transmit)", re.I),

        # Message types: "type 002000" or "type=002000"
        "message_type": re.compile(r"(?:type|msg)[\s=]+(\d{6})"),

        # Host/IMP numbers: "host 1", "imp 2"
        "host_num": re.compile(r"host[\s#]+(\d+)", re.I),
        "imp_num": re.compile(r"imp[\s#]+(\d+)", re.I),

        # Link/connection: "link 1", "connection established"
        "link": re.compile(r"link[\s#]+(\d+)", re.I),
        "connection": re.compile(r"connection\s+(established|closed|failed|timeout)", re.I),

        # Routing: "route to", "forward to"
        "routing": re.compile(r"(route|forward|send)\s+to\s+(\w+)", re.I),

        # Interface attach: "attach -u hi1 2000:172.20.0.10:2000"
        "attach": re.compile(r"attach\s+.*?(hi\d+|mi\d+)\s+(\d+):([^:]+):(\d+)", re.I),

        # SIMH H316 simulator messages
        "h316_sim": re.compile(r"H316 simulator", re.I),
        "register_check": re.compile(r"(Good|Bad)\s+Registers", re.I),

        # UDP/networking
        "udp": re.compile(r"UDP.*?port\s+(\d+)", re.I),

        # Errors
        "error": re.compile(r"(error|fail|timeout|invalid)", re.I),
    }

    # ARPANET 1822 message type meanings (octal)
    MESSAGE_TYPES = {
        "000000": "Regular message",
        "002000": "Control message (IMP-to-host)",
        "004000": "Uncontrolled packet",
        "005000": "Control message",
        "010000": "Error in leader",
    }

    # Tag extraction patterns
    # Maps tag names to (pattern, flags) tuples for extract_tags()
    TAG_PATTERNS: Dict[str, re.Pattern[str]] = {
        "host-interface": re.compile(r'\bhi\d+\b', re.IGNORECASE),
        "modem-interface": re.compile(r'\bmi\d+\b', re.IGNORECASE),
        "send": re.compile(r'\b(send|transmit)\b', re.IGNORECASE),
        "receive": re.compile(r'\b(recv|receive)\b', re.IGNORECASE),
        "packet": re.compile(r'\b(packet|message)\b', re.IGNORECASE),
        "protocol": re.compile(r'\btype[\s=]+\d{6}\b', re.IGNORECASE),
        "arpanet-1822": re.compile(r'\b1822\b'),
        "routing": re.compile(r'\b(route|routing|forward)\b', re.IGNORECASE),
        "connection": re.compile(r'\bconnect', re.IGNORECASE),
        "attach": re.compile(r'\battach', re.IGNORECASE),
        "simh": re.compile(r'\bh316\b', re.IGNORECASE),
        "simulator": re.compile(r'\bsimulator\b', re.IGNORECASE),
        "error": re.compile(r'\b(error|fail)\b', re.IGNORECASE),
        "validation": re.compile(r'\bgood\s+registers\b', re.IGNORECASE),
        "udp": re.compile(r'\budp\b', re.IGNORECASE),
    }

    def parse(self, message: str) -> Optional[Dict[str, Any]]:
        """Parse ARPANET IMP log message.

        Args:
            message: Raw log message from IMP

        Returns:
            Dictionary of parsed data or None
        """
        parsed = {}

        # Check each pattern
        for pattern_name, pattern in self.PATTERNS.items():
            match = pattern.search(message)
            if match:
                if pattern_name == "hi_packet":
                    parsed["interface"] = match.group(1)
                    parsed["interface_type"] = "host"
                    parsed["action"] = match.group(2)
                    parsed["event_type"] = "host_interface"

                elif pattern_name == "mi_packet":
                    parsed["interface"] = match.group(1)
                    parsed["interface_type"] = "modem"
                    parsed["action"] = match.group(2)
                    parsed["event_type"] = "modem_interface"

                elif pattern_name == "message_type":
                    msg_type = match.group(1)
                    parsed["message_type"] = msg_type
                    parsed["message_type_name"] = self.MESSAGE_TYPES.get(msg_type, "Unknown")
                    parsed["event_type"] = "protocol_message"

                elif pattern_name == "host_num":
                    parsed["host_number"] = int(match.group(1))

                elif pattern_name == "imp_num":
                    parsed["imp_number"] = int(match.group(1))

                elif pattern_name == "link":
                    parsed["link_number"] = int(match.group(1))

                elif pattern_name == "connection":
                    parsed["connection_state"] = match.group(1)
                    parsed["event_type"] = "connection"

                elif pattern_name == "routing":
                    parsed["routing_action"] = match.group(1)
                    parsed["routing_target"] = match.group(2)
                    parsed["event_type"] = "routing"

                elif pattern_name == "attach":
                    parsed["interface"] = match.group(1).upper()
                    parsed["local_port"] = int(match.group(2))
                    parsed["remote_host"] = match.group(3)
                    parsed["remote_port"] = int(match.group(4))
                    parsed["event_type"] = "interface_attach"

                elif pattern_name == "register_check":
                    parsed["register_status"] = match.group(1)
                    parsed["event_type"] = "simulator_check"

                elif pattern_name == "udp":
                    parsed["udp_port"] = int(match.group(1))

        return parsed if parsed else None

    def extract_tags(self, message: str) -> List[str]:
        """Extract tags from ARPANET message.

        Uses TAG_PATTERNS dictionary for efficient, maintainable tag extraction.

        Args:
            message: Log message

        Returns:
            List of tags matching the message content
        """
        tags = []

        # Check each pattern in TAG_PATTERNS
        for tag_name, pattern in self.TAG_PATTERNS.items():
            if pattern.search(message):
                tags.append(tag_name)

        return tags

    def detect_log_level(self, message: str) -> str:
        """Detect log level from message content.

        Args:
            message: Log message

        Returns:
            Log level string (INFO, WARNING, ERROR, DEBUG)
        """
        message_lower = message.lower()

        if re.search(r'\b(error|fail|fatal|panic|bad registers)\b', message_lower):
            return "ERROR"
        elif re.search(r'\b(warn|warning|timeout)\b', message_lower):
            return "WARNING"
        elif re.search(r'\b(debug|trace|packet|send|recv)\b', message_lower):
            return "DEBUG"
        else:
            return "INFO"
