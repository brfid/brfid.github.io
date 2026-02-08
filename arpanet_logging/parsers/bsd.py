"""BSD 4.3 log message parser for VAX."""

import re
from typing import Optional, Dict, Any, List

from arpanet_logging.core.parser import BaseParser


class BSDParser(BaseParser):
    """Parser for BSD 4.3 system and console messages."""

    # Patterns for common BSD log formats
    PATTERNS = {
        # Network interface events: "de0 at uba0 csr 174510 vec 120, ipl 15"
        "interface_attach": re.compile(r"^(\w+)\s+at\s+(\w+)\s+csr\s+(\d+)\s+vec\s+(\d+)"),

        # Hardware address: "de0: hardware address 08:00:2b:92:49:19"
        "hw_address": re.compile(r"^(\w+):\s+hardware address\s+([\da-f:]+)", re.I),

        # Interface flags: "de0: flags=43<UP,BROADCAST,RUNNING>"
        "interface_flags": re.compile(r"^(\w+):\s+flags=(\d+)<([^>]+)>"),

        # IP configuration: "inet 172.20.0.10 netmask ffff0000 broadcast 172.20.255.255"
        "inet": re.compile(r"inet\s+([\d.]+)\s+netmask\s+(\w+)\s+broadcast\s+([\d.]+)"),

        # Boot messages: "4.3 BSD UNIX #2: Fri May 22 19:08:31 MET DST 2015"
        "bsd_version": re.compile(r"(\d+\.\d+)\s+BSD\s+UNIX"),

        # Daemon start: "starting network daemons: rwhod inetd printer"
        "daemons": re.compile(r"starting\s+network\s+daemons:\s+(.+)"),

        # Login: "login: root"
        "login": re.compile(r"login:\s+(\w+)"),

        # SIMH messages: "Connected to the VAX 11/780 simulator DZ device"
        "simh_connected": re.compile(r"Connected to the VAX.+simulator"),

        # Errors
        "error": re.compile(r"(error|fail|fatal|panic)", re.I),
    }

    def parse(self, message: str) -> Optional[Dict[str, Any]]:
        """Parse BSD log message.

        Args:
            message: Raw log message

        Returns:
            Dictionary of parsed data or None
        """
        parsed = {}

        # Try each pattern
        for event_type, pattern in self.PATTERNS.items():
            match = pattern.search(message)
            if match:
                parsed["event_type"] = event_type
                parsed["groups"] = match.groups()

                # Event-specific parsing
                if event_type == "interface_attach":
                    parsed["interface"] = match.group(1)
                    parsed["bus"] = match.group(2)
                    parsed["csr"] = match.group(3)

                elif event_type == "hw_address":
                    parsed["interface"] = match.group(1)
                    parsed["mac_address"] = match.group(2)

                elif event_type == "interface_flags":
                    parsed["interface"] = match.group(1)
                    parsed["flags_value"] = match.group(2)
                    parsed["flags"] = match.group(3).split(",")

                elif event_type == "inet":
                    parsed["ip_address"] = match.group(1)
                    parsed["netmask"] = match.group(2)
                    parsed["broadcast"] = match.group(3)

                elif event_type == "bsd_version":
                    parsed["version"] = match.group(1)

                elif event_type == "daemons":
                    parsed["daemons"] = match.group(1).split()

                elif event_type == "login":
                    parsed["username"] = match.group(1)

                break

        return parsed if parsed else None

    def extract_tags(self, message: str) -> List[str]:
        """Extract tags from BSD log message.

        Args:
            message: Raw log message

        Returns:
            List of tags
        """
        tags = []

        # Check for keywords
        message_lower = message.lower()

        if "boot" in message_lower or "bsd unix" in message_lower:
            tags.append("boot")

        if any(word in message_lower for word in ["de0", "interface", "inet", "netmask"]):
            tags.append("network")

        if "login" in message_lower or "logout" in message_lower:
            tags.append("auth")

        if "daemon" in message_lower:
            tags.append("daemon")

        if "error" in message_lower or "fail" in message_lower:
            tags.append("error")

        if "simh" in message_lower or "simulator" in message_lower:
            tags.append("simh")

        if any(addr in message for addr in ["172.20.0.", "172.17.0."]):
            tags.append("ip-config")

        # Add interface names as tags
        for iface in ["de0", "lo0", "eth0"]:
            if iface in message_lower:
                tags.append(f"interface-{iface}")

        return tags
