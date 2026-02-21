#!/usr/bin/env python3
"""Simplified Chaosnet SHIM for ARPANET integration.

This is a minimal implementation to test Chaosnet connectivity between
the ARPANET IMP network and a PDP-10/ITS host. It provides basic packet
wrapping/unwrapping for the Chaosnet NCP protocol.

Protocol Reference:
- Chaosnet uses octal addressing (e.g., 0o7700 for host)
- Standard listen port: 173 decimal (0o255 octal)
- Packet types: RFC (request), OPN (open), DAT (data), CLS (close)
"""

import logging
import socket
import struct

# Chaosnet constants
CHAOSNET_PORT = 173  # Standard Chaosnet port (octal 0o255)
CHAOSNET_HEADER_SIZE = 16  # Bytes

# Packet types (simplified subset)
PKT_RFC = 1  # Request for Connection
PKT_OPN = 2  # Open Connection
PKT_CLS = 3  # Close Connection
PKT_FWD = 4  # Forward (routing)
PKT_DAT = 8  # Data
PKT_ACK = 9  # Acknowledgment

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class ChaosnetPacket:
    """Represents a simplified Chaosnet packet."""

    def __init__(
        self,
        pkt_type: int,
        dest_host: int,
        dest_subnet: int,
        src_host: int,
        src_subnet: int,
        data: bytes = b"",
    ):
        self.pkt_type = pkt_type
        self.dest_host = dest_host
        self.dest_subnet = dest_subnet
        self.src_host = src_host
        self.src_subnet = src_subnet
        self.data = data

    def to_bytes(self) -> bytes:
        """Serialize packet to bytes (simplified format)."""
        # Simplified 16-byte header + data
        header = struct.pack(
            "!BBBBBBH8s",
            self.pkt_type,
            self.dest_host,
            self.dest_subnet,
            self.src_host,
            self.src_subnet,
            0,  # Reserved
            len(self.data),
            b"\x00" * 8,  # Padding
        )
        return header + self.data

    @classmethod
    def from_bytes(cls, data: bytes) -> "ChaosnetPacket":
        """Deserialize packet from bytes (simplified format)."""
        if len(data) < CHAOSNET_HEADER_SIZE:
            raise ValueError(f"Packet too short: {len(data)} bytes")

        header = struct.unpack("!BBBBBBH8s", data[:CHAOSNET_HEADER_SIZE])
        pkt_type = header[0]
        dest_host = header[1]
        dest_subnet = header[2]
        src_host = header[3]
        src_subnet = header[4]
        data_len = header[6]

        payload = data[CHAOSNET_HEADER_SIZE : CHAOSNET_HEADER_SIZE + data_len]

        return cls(pkt_type, dest_host, dest_subnet, src_host, src_subnet, payload)


class ChaosnetShim:
    """Simplified Chaosnet-to-ARPANET protocol adapter.

    This shim sits between the ARPANET IMP network and a PDP-10/ITS host,
    translating between IMP host-interface protocol and Chaosnet NCP.
    """

    def __init__(
        self,
        listen_addr: str = "0.0.0.0",
        listen_port: int = CHAOSNET_PORT,
        pdp10_host: int = 0o7700,
        pdp10_subnet: int = 0o01,
    ):
        """Initialize the Chaosnet shim.

        Args:
            listen_addr: Address to listen on
            listen_port: Port to listen on (default: 173)
            pdp10_host: PDP-10 Chaosnet host number (octal)
            pdp10_subnet: PDP-10 Chaosnet subnet number (octal)
        """
        self.listen_addr = listen_addr
        self.listen_port = listen_port
        self.pdp10_host = pdp10_host
        self.pdp10_subnet = pdp10_subnet
        self.socket: socket.socket | None = None
        self.running = False

    def start(self) -> None:
        """Start the shim service."""
        logger.info(f"Starting Chaosnet shim on {self.listen_addr}:{self.listen_port}")
        logger.info(f"PDP-10 target: host={oct(self.pdp10_host)} subnet={oct(self.pdp10_subnet)}")

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.listen_addr, self.listen_port))
        self.socket.settimeout(1.0)  # 1 second timeout for graceful shutdown

        self.running = True
        logger.info("✅ Chaosnet shim started successfully")

        try:
            self._run_loop()
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the shim service."""
        logger.info("Stopping Chaosnet shim")
        self.running = False
        if self.socket:
            self.socket.close()
            self.socket = None
        logger.info("✅ Chaosnet shim stopped")

    def _run_loop(self) -> None:
        """Main processing loop."""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(4096)
                logger.debug(f"Received {len(data)} bytes from {addr}")

                # Process packet
                response = self._process_packet(data, addr)

                # Send response if any
                if response:
                    self.socket.sendto(response, addr)
                    logger.debug(f"Sent {len(response)} bytes to {addr}")

            except TimeoutError:
                continue  # Normal timeout, check running flag and continue
            except Exception as e:
                logger.error(f"Error processing packet: {e}")

    def _process_packet(self, data: bytes, addr: tuple[str, int]) -> bytes | None:
        """Process incoming packet and return response.

        Args:
            data: Raw packet data
            addr: Source address (ip, port)

        Returns:
            Response packet bytes or None
        """
        try:
            packet = ChaosnetPacket.from_bytes(data)

            logger.info(
                f"Received {self._packet_type_name(packet.pkt_type)} from "
                f"host={oct(packet.src_host)} subnet={oct(packet.src_subnet)}"
            )

            # Handle packet based on type
            if packet.pkt_type == PKT_RFC:
                return self._handle_rfc(packet, addr)
            elif packet.pkt_type == PKT_OPN:
                return self._handle_opn(packet, addr)
            elif packet.pkt_type == PKT_DAT:
                return self._handle_dat(packet, addr)
            elif packet.pkt_type == PKT_CLS:
                return self._handle_cls(packet, addr)
            else:
                logger.warning(f"Unknown packet type: {packet.pkt_type}")
                return None

        except Exception as e:
            logger.error(f"Error parsing packet: {e}")
            return None

    def _handle_rfc(self, packet: ChaosnetPacket, addr: tuple[str, int]) -> bytes:
        """Handle RFC (Request for Connection) packet.

        Args:
            packet: Chaosnet packet
            addr: Source address

        Returns:
            OPN (Open) response packet
        """
        logger.info(f"📨 RFC from {oct(packet.src_host)}: requesting connection")

        # Respond with OPN (connection accepted)
        response = ChaosnetPacket(
            pkt_type=PKT_OPN,
            dest_host=packet.src_host,
            dest_subnet=packet.src_subnet,
            src_host=self.pdp10_host,
            src_subnet=self.pdp10_subnet,
            data=b"Connection accepted",
        )

        logger.info(f"✅ Sending OPN to {oct(packet.src_host)}")
        return response.to_bytes()

    def _handle_opn(self, packet: ChaosnetPacket, addr: tuple[str, int]) -> bytes | None:
        """Handle OPN (Open Connection) packet."""
        logger.info(f"✅ Connection opened with {oct(packet.src_host)}")
        return None  # No response needed

    def _handle_dat(self, packet: ChaosnetPacket, addr: tuple[str, int]) -> bytes:
        """Handle DAT (Data) packet.

        Args:
            packet: Chaosnet packet
            addr: Source address

        Returns:
            ACK response packet
        """
        logger.info(f"📦 Data received from {oct(packet.src_host)}: {len(packet.data)} bytes")

        # Log data content (first 100 chars)
        if packet.data:
            preview = packet.data[:100].decode("utf-8", errors="replace")
            logger.debug(f"Data preview: {preview}")

        # Respond with ACK
        response = ChaosnetPacket(
            pkt_type=PKT_ACK,
            dest_host=packet.src_host,
            dest_subnet=packet.src_subnet,
            src_host=self.pdp10_host,
            src_subnet=self.pdp10_subnet,
        )

        logger.info(f"✅ Sending ACK to {oct(packet.src_host)}")
        return response.to_bytes()

    def _handle_cls(self, packet: ChaosnetPacket, addr: tuple[str, int]) -> bytes | None:
        """Handle CLS (Close Connection) packet."""
        logger.info(f"🔌 Connection closed by {oct(packet.src_host)}")
        return None  # No response needed

    @staticmethod
    def _packet_type_name(pkt_type: int) -> str:
        """Get human-readable packet type name."""
        names = {
            PKT_RFC: "RFC",
            PKT_OPN: "OPN",
            PKT_CLS: "CLS",
            PKT_FWD: "FWD",
            PKT_DAT: "DAT",
            PKT_ACK: "ACK",
        }
        return names.get(pkt_type, f"UNKNOWN({pkt_type})")


def main():
    """Entry point for running shim as standalone service."""
    import sys

    # Parse command-line arguments
    listen_addr = "0.0.0.0"
    listen_port = CHAOSNET_PORT
    pdp10_host = 0o7700  # Default BBN host number
    pdp10_subnet = 0o01

    if len(sys.argv) > 1:
        listen_port = int(sys.argv[1])
    if len(sys.argv) > 2:
        pdp10_host = int(sys.argv[2], 8)  # Octal
    if len(sys.argv) > 3:
        pdp10_subnet = int(sys.argv[3], 8)  # Octal

    # Create and start shim
    shim = ChaosnetShim(
        listen_addr=listen_addr,
        listen_port=listen_port,
        pdp10_host=pdp10_host,
        pdp10_subnet=pdp10_subnet,
    )

    try:
        shim.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
