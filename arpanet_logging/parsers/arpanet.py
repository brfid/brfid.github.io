"""ARPANET 1822 protocol parser for IMP messages."""

import re
from typing import Optional, Dict, Any, List

from arpanet_logging.core.parser import BaseParser


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

        Args:
            message: Log message

        Returns:
            List of tags
        """
        tags = []
        message_lower = message.lower()

        # Interface tags
        if re.search(r'\bhi\d+\b', message_lower):
            tags.append("host-interface")
        if re.search(r'\bmi\d+\b', message_lower):
            tags.append("modem-interface")

        # Action tags
        if re.search(r'\b(send|transmit)\b', message_lower):
            tags.append("send")
        if re.search(r'\b(recv|receive)\b', message_lower):
            tags.append("receive")
        if re.search(r'\b(packet|message)\b', message_lower):
            tags.append("packet")

        # Protocol tags
        if re.search(r'\btype[\s=]+\d{6}\b', message_lower):
            tags.append("protocol")
        if re.search(r'\b1822\b', message):
            tags.append("arpanet-1822")

        # Routing tags
        if re.search(r'\b(route|routing|forward)\b', message_lower):
            tags.append("routing")

        # Connection tags
        if re.search(r'\bconnect', message_lower):
            tags.append("connection")
        if re.search(r'\battach', message_lower):
            tags.append("attach")

        # SIMH simulator tags
        if re.search(r'\bh316\b', message_lower):
            tags.append("simh")
        if re.search(r'\bsimulator\b', message_lower):
            tags.append("simulator")

        # Error/status tags
        if re.search(r'\b(error|fail)\b', message_lower):
            tags.append("error")
        if re.search(r'\bgood\s+registers\b', message_lower):
            tags.append("validation")

        # UDP networking tags
        if re.search(r'\budp\b', message_lower):
            tags.append("udp")

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
