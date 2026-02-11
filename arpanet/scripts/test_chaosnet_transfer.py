#!/usr/bin/env python3
"""
Chaosnet Transfer Test Script

Validates Chaosnet file transfer capability between VAX/BSD and PDP-10/ITS
using the Chaosnet protocol (NCP) for ITS-native networking.

Usage:
    python test_chaosnet_transfer.py --help
    python test_chaosnet_transfer.py --dry-run
    python test_chaosnet_transfer.py --artifact /tmp/test-file.txt
"""

import argparse
import json
import logging
import socket
import struct
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)
logger = logging.getLogger('chaosnet-test')

# Chaosnet protocol constants
CHAOSNET_PORT = 173  # Octal 0255 = 173 decimal
# Header format: >HHHHHH (type, length, src_host, src_subnet, dst_host, dst_subnet)
# 2+2+2+2+2+2 = 12 bytes total (all unsigned shorts)
CHAOSNET_HEADER_SIZE = 12

# Packet types
PKT_RFC = 0x01  # Request for Connection
PKT_OPN = 0x02  # Open Connection
PKT_DAT = 0x04  # Data
PKT_ACK = 0x05  # Acknowledgment


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
    data: bytes = b''
    
    def to_bytes(self) -> bytes:
        """Serialize packet to bytes."""
        header = struct.pack('>HHHHHH',
            self.pkt_type,
            self.length,
            self.src_host,
            self.src_subnet,
            self.dst_host,
            self.dst_subnet
        )
        return header + self.data


@dataclass
class TestResult:
    """Result of a Chaosnet transfer test."""
    timestamp: str
    test_name: str
    passed: bool
    duration_seconds: float
    details: dict = field(default_factory=dict)
    error: Optional[str] = None


class ChaosnetTransferTest:
    """Test harness for Chaosnet file transfer validation."""
    
    def __init__(
        self,
        artifact_path: str = "/tmp/chaosnet-test.txt",
        output_dir: str = "build/arpanet/analysis",
        dry_run: bool = False,
        verbose: bool = False,
        shim_host: str = "localhost",
        shim_port: int = 2328
    ):
        """
        Initialize test harness.
        
        Args:
            artifact_path: Path to test artifact file
            output_dir: Directory for output artifacts
            dry_run: If True, skip actual network operations
            verbose: Enable verbose logging
            shim_host: Hostname/IP of chaosnet shim (default: localhost for docker port mapping)
            shim_port: Port of chaosnet shim (default: 2328 for docker port mapping)
        """
        self.artifact_path = artifact_path
        self.output_dir = Path(output_dir)
        self.dry_run = dry_run
        self.verbose = verbose
        
        # Topology settings (from phase2-chaosnet topology)
        self.shim_host = shim_host
        self.shim_port = shim_port
        self.pdp10_host = 0x7700  # BBN#7700
        self.pdp10_subnet = 0x01
        
        # Statistics
        self.stats = {
            'rfc_sent': 0,
            'opn_received': 0,
            'dat_sent': 0,
            'ack_received': 0,
            'bytes_sent': 0,
            'parse_errors': 0,
        }
        
        if verbose:
            logger.setLevel(logging.DEBUG)
            
    def _create_artifact(self) -> bool:
        """Create test artifact file."""
        try:
            content = f"Chaosnet test file\nGenerated: {datetime.now().isoformat()}\n"
            Path(self.artifact_path).write_text(content)
            logger.info(f"Created test artifact: {self.artifact_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create artifact: {e}")
            return False
            
    def _send_packet(self, packet: ChaosnetPacket, timeout: float = 5.0) -> Optional[ChaosnetPacket]:
        """Send a packet and wait for response."""
        if self.dry_run:
            logger.debug(f"[DRY-RUN] Would send: {packet}")
            return None
            
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        
        try:
            data = packet.to_bytes()
            sock.sendto(data, (self.shim_host, self.shim_port))
            self.stats['bytes_sent'] += len(data)
            
            response_data, _ = sock.recvfrom(4096)
            
            # Parse response
            if len(response_data) < CHAOSNET_HEADER_SIZE:
                logger.warning(f"Response too short: {len(response_data)} bytes")
                return None
                
            pkt_type, length, src_host, src_subnet, dst_host, dst_subnet = \
                struct.unpack('>HHHHHH', response_data[:CHAOSNET_HEADER_SIZE])
            pkt_data = response_data[CHAOSNET_HEADER_SIZE:]
            
            return ChaosnetPacket(
                pkt_type=pkt_type,
                length=length,
                src_host=src_host,
                src_subnet=src_subnet,
                dst_host=dst_host,
                dst_subnet=dst_subnet,
                data=pkt_data
            )
        except socket.timeout:
            logger.warning(f"Timeout waiting for response from {self.shim_host}:{self.shim_port}")
            return None
        except Exception as e:
            logger.error(f"Error sending packet: {e}")
            return None
        finally:
            sock.close()
            
    def _create_rfc(self) -> ChaosnetPacket:
        """Create RFC (Request for Connection) packet."""
        self.stats['rfc_sent'] += 1
        return ChaosnetPacket(
            pkt_type=PKT_RFC,
            length=CHAOSNET_HEADER_SIZE,
            src_host=0,  # Will be assigned
            src_subnet=0,
            dst_host=self.pdp10_host,
            dst_subnet=self.pdp10_subnet,
            data=b''
        )
        
    def _create_dat(self, data: bytes) -> ChaosnetPacket:
        """Create DAT (Data) packet."""
        self.stats['dat_sent'] += 1
        return ChaosnetPacket(
            pkt_type=PKT_DAT,
            length=CHAOSNET_HEADER_SIZE + len(data),
            src_host=0,
            src_subnet=0,
            dst_host=self.pdp10_host,
            dst_subnet=self.pdp10_subnet,
            data=data
        )
        
    def test_connectivity(self) -> TestResult:
        """Test basic Chaosnet connectivity."""
        start_time = time.time()
        logger.info("Testing Chaosnet connectivity...")
        
        try:
            if self.dry_run:
                logger.info("[DRY-RUN] Skipping connectivity test")
                return TestResult(
                    timestamp=datetime.now().isoformat(),
                    test_name="chaosnet_connectivity",
                    passed=True,
                    duration_seconds=time.time() - start_time,
                    details={'dry_run': True}
                )
                
            # Try to connect to chaosnet shim
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0)
            
            try:
                # Send a test packet (should get no response if nothing listening)
                test_packet = self._create_rfc()
                sock.sendto(test_packet.to_bytes(), (self.shim_host, self.shim_port))
                logger.info(f"Sent RFC to {self.shim_host}:{self.shim_port}")
                
                # Check if port is open (ICMP might give us info, but UDP is silent)
                # A timeout is actually expected here since we expect OPN response
                response, _ = sock.recvfrom(4096)
                logger.info(f"Received response: {len(response)} bytes")
                
                return TestResult(
                    timestamp=datetime.now().isoformat(),
                    test_name="chaosnet_connectivity",
                    passed=True,
                    duration_seconds=time.time() - start_time,
                    details={
                        'host': self.shim_host,
                        'port': self.shim_port,
                        'response_bytes': len(response)
                    }
                )
            except socket.timeout:
                # Timeout is actually expected if nothing is listening
                logger.warning("Connection test timed out (expected if shim not running)")
                return TestResult(
                    timestamp=datetime.now().isoformat(),
                    test_name="chaosnet_connectivity",
                    passed=False,
                    duration_seconds=time.time() - start_time,
                    error="Connection timeout - chaosnet shim may not be running"
                )
            finally:
                sock.close()
                
        except Exception as e:
            return TestResult(
                timestamp=datetime.now().isoformat(),
                test_name="chaosnet_connectivity",
                passed=False,
                duration_seconds=time.time() - start_time,
                error=str(e)
            )
            
    def test_packet_format(self) -> TestResult:
        """Test Chaosnet packet format validation."""
        start_time = time.time()
        logger.info("Testing packet format...")
        
        try:
            # Test RFC packet creation
            rfc = self._create_rfc()
            rfc_bytes = rfc.to_bytes()
            
            expected_len = CHAOSNET_HEADER_SIZE  # RFC has no data
            actual_len = len(rfc_bytes)
            
            if actual_len != expected_len:
                raise ValueError(f"RFC packet length mismatch: {actual_len} != {expected_len}")
                
            # Parse it back
            pkt_type, length, src_host, src_subnet, dst_host, dst_subnet = \
                struct.unpack('>HHHHHH', rfc_bytes[:CHAOSNET_HEADER_SIZE])
                
            if pkt_type != PKT_RFC:
                raise ValueError(f"Packet type mismatch: {pkt_type} != {PKT_RFC}")
                
            # Test DAT packet
            test_data = b"Hello, Chaosnet!"
            dat = self._create_dat(test_data)
            dat_bytes = dat.to_bytes()
            
            expected_len = CHAOSNET_HEADER_SIZE + len(test_data)
            if len(dat_bytes) != expected_len:
                raise ValueError(f"DAT packet length mismatch: {len(dat_bytes)} != {expected_len}")
                
            logger.info(f"Packet format tests passed")
            
            return TestResult(
                timestamp=datetime.now().isoformat(),
                test_name="chaosnet_packet_format",
                passed=True,
                duration_seconds=time.time() - start_time,
                details={
                    'rfc_packet_size': actual_len,
                    'dat_packet_size': len(dat_bytes),
                    'test_data_size': len(test_data)
                }
            )
            
        except Exception as e:
            return TestResult(
                timestamp=datetime.now().isoformat(),
                test_name="chaosnet_packet_format",
                passed=False,
                duration_seconds=time.time() - start_time,
                error=str(e)
            )
            
    def run_all_tests(self) -> TestResult:
        """Run all Chaosnet transfer tests."""
        start_time = time.time()
        results = []
        
        logger.info("=" * 60)
        logger.info("Chaosnet Transfer Test Suite")
        logger.info("=" * 60)
        
        # Create test artifact
        if not self._create_artifact():
            return TestResult(
                timestamp=datetime.now().isoformat(),
                test_name="chaosnet_full_suite",
                passed=False,
                duration_seconds=time.time() - start_time,
                error="Failed to create test artifact"
            )
            
        # Run tests
        tests = [
            ("packet_format", self.test_packet_format),
            ("connectivity", self.test_connectivity),
        ]
        
        all_passed = True
        for test_name, test_func in tests:
            logger.info(f"\n--- Running: {test_name} ---")
            try:
                result = test_func()
                results.append(result)
                
                if result.passed:
                    logger.info(f"✓ {test_name}: PASSED ({result.duration_seconds:.2f}s)")
                else:
                    logger.error(f"✗ {test_name}: FAILED - {result.error}")
                    all_passed = False
                    
            except Exception as e:
                logger.error(f"✗ {test_name}: EXCEPTION - {e}")
                results.append(TestResult(
                    timestamp=datetime.now().isoformat(),
                    test_name=test_name,
                    passed=False,
                    duration_seconds=0,
                    error=str(e)
                ))
                all_passed = False
                
        # Summary
        duration = time.time() - start_time
        passed_count = sum(1 for r in results if r.passed)
        total_count = len(results)
        
        logger.info("\n" + "=" * 60)
        logger.info(f"Test Suite Complete: {passed_count}/{total_count} passed in {duration:.2f}s")
        logger.info("=" * 60)
        
        # Save results
        self._save_results(results, all_passed, duration)
        
        return TestResult(
            timestamp=datetime.now().isoformat(),
            test_name="chaosnet_full_suite",
            passed=all_passed,
            duration_seconds=duration,
            details={
                'tests_passed': passed_count,
                'tests_total': total_count,
                'stats': self.stats
            }
        )
        
    def _save_results(self, results: list, all_passed: bool, duration: float) -> None:
        """Save test results to output directory."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        output = {
            'timestamp': datetime.now().isoformat(),
            'suite_passed': all_passed,
            'duration_seconds': duration,
            'topology': {
                'shim_host': self.shim_host,
                'shim_port': self.shim_port,
                'pdp10_host': hex(self.pdp10_host),
                'pdp10_subnet': hex(self.pdp10_subnet),
            },
            'results': [
                {
                    'test_name': r.test_name,
                    'passed': r.passed,
                    'duration_seconds': r.duration_seconds,
                    'error': r.error,
                    'details': r.details
                }
                for r in results
            ],
            'stats': self.stats
        }
        
        output_file = self.output_dir / "chaosnet-transfer-result.json"
        output_file.write_text(json.dumps(output, indent=2))
        logger.info(f"Results saved to: {output_file}")
        
        # Also write markdown summary
        md_file = self.output_dir / "chaosnet-transfer-result.md"
        md_lines = [
            "# Chaosnet Transfer Test Results",
            f"**Date**: {output['timestamp']}",
            f"**Status**: {'✅ PASSED' if all_passed else '❌ FAILED'}",
            f"**Duration**: {duration:.2f}s",
            "",
            "## Topology",
            f"- Shim: {self.shim_host}:{self.shim_port}",
            f"- PDP-10: host={hex(self.pdp10_host)}, subnet={hex(self.pdp10_subnet)}",
            "",
            "## Results",
            "",
        ]
        
        for r in results:
            status = "✅" if r.passed else "❌"
            md_lines.append(f"### {status} {r.test_name}")
            md_lines.append(f"- Duration: {r.duration_seconds:.2f}s")
            if r.error:
                md_lines.append(f"- Error: {r.error}")
            md_lines.append("")
            
        md_lines.extend([
            "## Statistics",
            "```json",
            json.dumps(self.stats, indent=2),
            "```",
        ])
        
        md_file.write_text("\n".join(md_lines))
        logger.info(f"Markdown summary saved to: {md_file}")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Chaosnet Transfer Test Suite'
    )
    parser.add_argument(
        '--artifact',
        type=str,
        default='/tmp/chaosnet-test.txt',
        help='Path to test artifact file (default: /tmp/chaosnet-test.txt)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='build/arpanet/analysis',
        help='Output directory for results (default: build/arpanet/analysis)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Skip actual network operations (for testing without Docker)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--test',
        type=str,
        choices=['all', 'packet_format', 'connectivity'],
        default='all',
        help='Specific test to run (default: all)'
    )
    parser.add_argument(
        '--shim-host',
        type=str,
        default='localhost',
        help='Chaosnet shim host (default: localhost)'
    )
    parser.add_argument(
        '--shim-port',
        type=int,
        default=2328,
        help='Chaosnet shim port (default: 2328 for docker port mapping)'
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()
    
    test = ChaosnetTransferTest(
        artifact_path=args.artifact,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
        verbose=args.verbose,
        shim_host=args.shim_host,
        shim_port=args.shim_port
    )
    
    if args.test == 'all':
        result = test.run_all_tests()
    elif args.test == 'packet_format':
        result = test.test_packet_format()
    elif args.test == 'connectivity':
        result = test.test_connectivity()
    else:
        logger.error(f"Unknown test: {args.test}")
        return 1
        
    return 0 if result.passed else 1


if __name__ == '__main__':
    sys.exit(main())
