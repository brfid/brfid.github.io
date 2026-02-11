#!/usr/bin/env python3
"""
Chaosnet Shim: Protocol bridge between ARPANET and Chaosnet for ITS compatibility.

This shim enables communication between the ARPANET IMP infrastructure
and PDP-10/ITS nodes using Chaosnet protocol (NCP).

Usage:
    python chaosnet_shim.py --config config.yaml
    python chaosnet_shim.py --pdp10-host 0x7700 --pdp10-subnet 0x01 --listen-port 173
"""

import argparse
import logging
import socket
import struct
import sys
from dataclasses import dataclass
from typing import Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger('chaosnet-shim')

# Chaosnet protocol constants
CHAOSNET_PORT = 173  # Octal 0255 = 173 decimal
# Header format: >HHHHHH (type, length, src_host, src_subnet, dst_host, dst_subnet)
# 2+2+2+2+2+2 = 12 bytes total (all unsigned shorts)
CHAOSNET_HEADER_SIZE = 12

# Chaosnet packet types
PKT_RFC = 0x01  # Request for Connection
PKT_OPN = 0x02  # Open Connection  
PKT_CLS = 0x03  # Close Connection
PKT_DAT = 0x04  # Data
PKT_ACK = 0x05  # Acknowledgment
PKT_FWD = 0x06  # Forward (routing)
PKT_RND = 0x0C  # Random (used for testing)


@dataclass
class ChaosnetPacket:
    """Parsed Chaosnet packet structure.
    
    Header format (12 bytes): >HHHHHH
    - pkt_type: unsigned short (2 bytes)
    - length: unsigned short (2 bytes)
    - src_host: unsigned short (2 bytes)
    - src_subnet: unsigned short (2 bytes)
    - dst_host: unsigned short (2 bytes)
    - dst_subnet: unsigned short (2 bytes)
    """
    pkt_type: int
    length: int
    src_host: int
    src_subnet: int
    dst_host: int
    dst_subnet: int
    data: bytes
    
    def to_bytes(self) -> bytes:
        """Serialize packet to bytes for transmission."""
        header = struct.pack('>HHHHHH',
            self.pkt_type,
            self.length,
            self.src_host,
            self.src_subnet,
            self.dst_host,
            self.dst_subnet
        )
        return header + self.data


class ChaosnetShim:
    """
    Chaosnet-to-ARPANET protocol adapter.
    
    Bridges between UDP-based ARPANET IMP communication and
    Chaosnet protocol for ITS compatibility.
    """
    
    def __init__(
        self,
        pdp10_host: int = 0x7700,
        pdp10_subnet: int = 0x01,
        listen_port: int = CHAOSNET_PORT,
        arpanet_gateway: str = "172.20.0.30",
        debug: bool = False
    ):
        """
        Initialize Chaosnet shim.
        
        Args:
            pdp10_host: PDP-10 Chaosnet host number (e.g., 0x7700 for BBN#7700)
            pdp10_subnet: PDP-10 Chaosnet subnet number
            listen_port: Local UDP port to listen on
            arpanet_gateway: IP address of ARPANET gateway (IMP2)
            debug: Enable debug logging
        """
        self.pdp10_host = pdp10_host
        self.pdp10_subnet = pdp10_subnet
        self.listen_port = listen_port
        self.arpanet_gateway = arpanet_gateway
        self.debug = debug
        
        if debug:
            logger.setLevel(logging.DEBUG)
        
        # Statistics
        self.stats = {
            'rfc_received': 0,
            'opn_received': 0,
            'dat_received': 0,
            'cls_received': 0,
            'packets_sent': 0,
            'bytes_received': 0,
            'bytes_sent': 0,
            'parse_errors': 0,
        }
        
        self._socket: Optional[socket.socket] = None
        self._running = False
        
    def start(self) -> None:
        """Start the Chaosnet shim service."""
        logger.info(f"Starting Chaosnet shim on port {self.listen_port}")
        logger.info(f"PDP-10 target: host=0x{self.pdp10_host:04X}, subnet=0x{self.pdp10_subnet:02X}")
        logger.info(f"ARPANET gateway: {self.arpanet_gateway}")
        
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self._socket.bind(('0.0.0.0', self.listen_port))
            self._socket.settimeout(1.0)  # Allow periodic checks
            self._running = True
            logger.info(f"Chaosnet shim listening on port {self.listen_port}")
            self._main_loop()
        except OSError as e:
            logger.error(f"Failed to bind to port {self.listen_port}: {e}")
            raise
        finally:
            if self._socket:
                self._socket.close()
                
    def stop(self) -> None:
        """Stop the Chaosnet shim service."""
        logger.info("Stopping Chaosnet shim...")
        self._running = False
        
    def _main_loop(self) -> None:
        """Main event loop for processing packets."""
        logger.info("Entering main event loop")
        
        while self._running:
            try:
                data, addr = self._socket.recvfrom(4096)
                self.stats['bytes_received'] += len(data)
                self._handle_packet(data, addr)
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Error processing packet: {e}")
                self.stats['parse_errors'] += 1
                
        logger.info("Main event loop ended")
        
    def _handle_packet(self, data: bytes, addr: Tuple[str, int]) -> None:
        """
        Handle incoming UDP packet.
        
        Args:
            data: Raw packet data
            addr: Source address (IP, port)
        """
        if len(data) < CHAOSNET_HEADER_SIZE:
            logger.warning(f"Packet too short: {len(data)} bytes")
            self.stats['parse_errors'] += 1
            return
            
        # Parse header (format: >HHHHHH = 12 bytes total)
        try:
            pkt_type, length, src_host, src_subnet, dst_host, dst_subnet = \
                struct.unpack('>HHHHHH', data[:CHAOSNET_HEADER_SIZE])
            pkt_data = data[CHAOSNET_HEADER_SIZE:]
        except struct.error as e:
            logger.error(f"Failed to parse packet header: {e}")
            self.stats['parse_errors'] += 1
            return
            
        packet = ChaosnetPacket(
            pkt_type=pkt_type,
            length=length,
            src_host=src_host,
            src_subnet=src_subnet,
            dst_host=dst_host,
            dst_subnet=dst_subnet,
            data=pkt_data
        )
        
        if self.debug:
            logger.debug(f"Received: type=0x{pkt_type:02X}, "
                        f"src=({src_host:04X},{src_subnet:02X}), "
                        f"dst=({dst_host:04X},{dst_subnet:02X}), "
                        f"len={length}")
            
        # Route packet based on type
        response = self._route_packet(packet)
        
        if response:
            sent = self._socket.sendto(response, addr)
            self.stats['packets_sent'] += 1
            self.stats['bytes_sent'] += sent
            
    def _route_packet(self, packet: ChaosnetPacket) -> Optional[bytes]:
        """
        Route incoming packet to appropriate handler.
        
        Args:
            packet: Parsed Chaosnet packet
            
        Returns:
            Response packet bytes, or None if no response
        """
        # Check if this packet is for our PDP-10
        if packet.dst_host == self.pdp10_host and packet.dst_subnet == self.pdp10_subnet:
            return self._handle_pdp10_packet(packet)
        else:
            # Forward to ARPANET gateway
            return self._forward_to_arpanet(packet)
            
    def _handle_pdp10_packet(self, packet: ChaosnetPacket) -> Optional[bytes]:
        """
        Handle packet destined for PDP-10.
        
        Args:
            packet: Parsed Chaosnet packet
            
        Returns:
            Response packet bytes, or None if no response
        """
        if packet.pkt_type == PKT_RFC:
            self.stats['rfc_received'] += 1
            logger.info(f"RFC from host=0x{packet.src_host:04X}")
            return self._handle_rfc(packet)
        elif packet.pkt_type == PKT_DAT:
            self.stats['dat_received'] += 1
            logger.info(f"DATA packet, {len(packet.data)} bytes")
            return self._handle_dat(packet)
        elif packet.pkt_type == PKT_CLS:
            self.stats['cls_received'] += 1
            logger.info("CLS (close connection)")
            return self._handle_cls(packet)
        else:
            logger.debug(f"Unhandled packet type: 0x{packet.pkt_type:02X}")
            return None
            
    def _handle_rfc(self, packet: ChaosnetPacket) -> bytes:
        """
        Handle RFC (Request for Connection) packet.
        
        Returns OPN (Open) response to establish connection.
        
        Args:
            packet: RFC packet
            
        Returns:
            OPN response packet
        """
        logger.info(f"Opening connection to host=0x{packet.src_host:04X}")
        self.stats['opn_received'] += 1
        
        # Respond with OPN
        response = ChaosnetPacket(
            pkt_type=PKT_OPN,
            length=CHAOSNET_HEADER_SIZE,
            src_host=self.pdp10_host,
            src_subnet=self.pdp10_subnet,
            dst_host=packet.src_host,
            dst_subnet=packet.src_subnet,
            data=b''
        )
        return response.to_bytes()
        
    def _handle_dat(self, packet: ChaosnetPacket) -> bytes:
        """
        Handle DAT (Data) packet.
        
        Returns ACK acknowledgment.
        
        Args:
            packet: DAT packet
            
        Returns:
            ACK response packet
        """
        # Send acknowledgment
        response = ChaosnetPacket(
            pkt_type=PKT_ACK,
            length=CHAOSNET_HEADER_SIZE,
            src_host=self.pdp10_host,
            src_subnet=self.pdp10_subnet,
            dst_host=packet.src_host,
            dst_subnet=packet.src_subnet,
            data=b''
        )
        return response.to_bytes()
        
    def _handle_cls(self, packet: ChaosnetPacket) -> Optional[bytes]:
        """
        Handle CLS (Close Connection) packet.
        
        Args:
            packet: CLS packet
            
        Returns:
            CLS response packet
        """
        logger.info(f"Closing connection from host=0x{packet.src_host:04X}")
        # Echo CLS back
        return packet.to_bytes()
        
    def _forward_to_arpanet(self, packet: ChaosnetPacket) -> Optional[bytes]:
        """
        Forward packet to ARPANET gateway.
        
        Args:
            packet: Packet to forward
            
        Returns:
            Response from gateway, or None
        """
        # In a full implementation, this would forward to IMP2
        # For now, log and return None
        if self.debug:
            logger.debug(f"Forwarding to ARPANET: host=0x{packet.dst_host:04X}")
        return None
        
    def get_stats(self) -> dict:
        """Return shim statistics."""
        return self.stats.copy()
        
    def print_stats(self) -> None:
        """Print statistics to stdout."""
        print("\n=== Chaosnet Shim Statistics ===")
        for key, value in self.stats.items():
            print(f"  {key}: {value}")
        print("================================\n")


def wrap_chaosnet_packet(data: bytes, dest_host: int, dest_subnet: int) -> bytes:
    """
    Wrap data in Chaosnet NCP packet format.
    
    Args:
        data: Raw data to wrap
        dest_host: Destination host number
        dest_subnet: Destination subnet number
        
    Returns:
        Wrapped packet bytes
    """
    packet = ChaosnetPacket(
        pkt_type=PKT_DAT,
        length=CHAOSNET_HEADER_SIZE + len(data),
        src_host=0,  # Will be set by shim
        src_subnet=0,
        dst_host=dest_host,
        dst_subnet=dest_subnet,
        data=data
    )
    return packet.to_bytes()


def unwrap_chaosnet_packet(data: bytes) -> Tuple[bytes, int, int]:
    """
    Extract data and addressing from Chaosnet packet.
    
    Args:
        data: Raw packet bytes
        
    Returns:
        Tuple of (data, src_host, src_subnet)
        
    Raises:
        ValueError: If packet is malformed
    """
    if len(data) < CHAOSNET_HEADER_SIZE:
        raise ValueError(f"Packet too short: {len(data)} bytes")
        
    pkt_type, length, src_host, src_subnet, dst_host, dst_subnet = \
        struct.unpack('>HHHHHH', data[:CHAOSNET_HEADER_SIZE])
    pkt_data = data[CHAOSNET_HEADER_SIZE:]
    
    return pkt_data, src_host, src_subnet


def handle_rfc(src_host: int, src_subnet: int, data: bytes) -> bytes:
    """
    Generate RFC (Request for Connection) packet.
    
    Args:
        src_host: Source host number
        src_subnet: Source subnet number
        data: Optional data (user info)
        
    Returns:
        RFC packet bytes
    """
    packet = ChaosnetPacket(
        pkt_type=PKT_RFC,
        length=CHAOSNET_HEADER_SIZE + len(data),
        src_host=src_host,
        src_subnet=src_subnet,
        dst_host=0,  # Will be set by caller
        dst_subnet=0,
        data=data
    )
    return packet.to_bytes()


def handle_dat(data: bytes) -> bytes:
    """
    Generate DAT (Data) packet.
    
    Args:
        data: Data payload
        
    Returns:
        DAT packet bytes
    """
    packet = ChaosnetPacket(
        pkt_type=PKT_DAT,
        length=CHAOSNET_HEADER_SIZE + len(data),
        src_host=0,
        src_subnet=0,
        dst_host=0,
        dst_subnet=0,
        data=data
    )
    return packet.to_bytes()


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Chaosnet Shim - Protocol bridge for ITS compatibility'
    )
    parser.add_argument(
        '--pdp10-host',
        type=lambda x: int(x, 0),  # Allow hex (0x7700) or decimal
        default=0x7700,
        help='PDP-10 Chaosnet host number (default: 0x7700)'
    )
    parser.add_argument(
        '--pdp10-subnet',
        type=lambda x: int(x, 0),
        default=0x01,
        help='PDP-10 Chaosnet subnet number (default: 0x01)'
    )
    parser.add_argument(
        '--listen-port',
        type=int,
        default=CHAOSNET_PORT,
        help=f'UDP port to listen on (default: {CHAOSNET_PORT})'
    )
    parser.add_argument(
        '--arpanet-gateway',
        type=str,
        default='172.20.0.30',
        help='ARPANET gateway IP (default: 172.20.0.30)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()
    
    shim = ChaosnetShim(
        pdp10_host=args.pdp10_host,
        pdp10_subnet=args.pdp10_subnet,
        listen_port=args.listen_port,
        arpanet_gateway=args.arpanet_gateway,
        debug=args.debug
    )
    
    try:
        shim.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt, shutting down...")
        shim.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1
    
    shim.print_stats()
    return 0


if __name__ == '__main__':
    sys.exit(main())
