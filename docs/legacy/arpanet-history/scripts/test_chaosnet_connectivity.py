"""Test Chaosnet connectivity between ARPANET and PDP-10.

This script sends a test RFC (Request for Connection) packet to the
Chaosnet shim and verifies it responds with OPN (Open).
"""

import json
import socket
import struct
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

# Chaosnet constants
CHAOSNET_PORT = 173
PKT_RFC = 1
PKT_OPN = 2

# Test configuration
SHIM_HOST = "172.20.0.50"  # Chaosnet shim IP
SHIM_PORT = CHAOSNET_PORT
TEST_SRC_HOST = 0o1  # Test source host
TEST_SRC_SUBNET = 0o1  # Test source subnet
PDP10_HOST = 0o7700  # PDP-10 target host
PDP10_SUBNET = 0o01  # PDP-10 target subnet


def create_rfc_packet(src_host: int, src_subnet: int, dest_host: int, dest_subnet: int) -> bytes:
    """Create an RFC (Request for Connection) packet.

    Args:
        src_host: Source host number
        src_subnet: Source subnet number
        dest_host: Destination host number
        dest_subnet: Destination subnet number

    Returns:
        Serialized packet bytes
    """
    # Simplified 16-byte header
    header = struct.pack(
        "!BBBBBBH8s",
        PKT_RFC,  # Packet type
        dest_host,  # Destination host
        dest_subnet,  # Destination subnet
        src_host,  # Source host
        src_subnet,  # Source subnet
        0,  # Reserved
        0,  # Data length
        b"\x00" * 8,  # Padding
    )
    return header


def parse_response(data: bytes) -> dict:
    """Parse response packet.

    Args:
        data: Raw packet bytes

    Returns:
        Parsed packet dictionary
    """
    if len(data) < 16:
        return {"error": "packet too short"}

    header = struct.unpack("!BBBBBBH8s", data[:16])

    return {
        "pkt_type": header[0],
        "dest_host": oct(header[1]),
        "dest_subnet": oct(header[2]),
        "src_host": oct(header[3]),
        "src_subnet": oct(header[4]),
        "data_len": header[6],
    }


def test_connectivity(output_file: str = None) -> bool:
    """Test Chaosnet connectivity to shim.

    Args:
        output_file: Optional path to write JSON results

    Returns:
        True if connectivity test passed
    """
    result = {
        "test": "chaosnet_connectivity",
        "timestamp": datetime.now(UTC).isoformat(),
        "shim_host": SHIM_HOST,
        "shim_port": SHIM_PORT,
        "pdp10_host": oct(PDP10_HOST),
        "pdp10_subnet": oct(PDP10_SUBNET),
        "status": "unknown",
        "details": {},
    }

    print("=" * 60)
    print("Chaosnet Connectivity Test")
    print("=" * 60)
    print(f"Shim: {SHIM_HOST}:{SHIM_PORT}")
    print(f"PDP-10 target: host={oct(PDP10_HOST)} subnet={oct(PDP10_SUBNET)}")
    print()

    try:
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5.0)  # 5 second timeout

        # Create RFC packet
        print("📨 Sending RFC (Request for Connection)...")
        rfc_packet = create_rfc_packet(TEST_SRC_HOST, TEST_SRC_SUBNET, PDP10_HOST, PDP10_SUBNET)

        # Send packet
        start_time = time.time()
        sock.sendto(rfc_packet, (SHIM_HOST, SHIM_PORT))
        result["rfc_sent"] = True

        # Wait for response
        print("⏳ Waiting for OPN (Open) response...")
        try:
            data, addr = sock.recvfrom(4096)
            elapsed = time.time() - start_time

            result["response_received"] = True
            result["response_time_ms"] = int(elapsed * 1000)
            result["response_from"] = f"{addr[0]}:{addr[1]}"

            # Parse response
            response = parse_response(data)
            result["response"] = response

            print(f"✅ Response received in {elapsed * 1000:.1f}ms")
            print(f"   From: {addr[0]}:{addr[1]}")
            print(f"   Type: {response.get('pkt_type')} (expected {PKT_OPN} for OPN)")
            print(f"   Source: host={response.get('src_host')} subnet={response.get('src_subnet')}")

            # Check if response is OPN
            if response.get("pkt_type") == PKT_OPN:
                print("\n✅ TEST PASSED: Received OPN response")
                result["status"] = "pass"
                result["details"]["message"] = "Chaosnet connectivity confirmed"
                success = True
            else:
                print(
                    f"\n⚠️  TEST WARNING: Expected OPN ({PKT_OPN}), got {response.get('pkt_type')}"
                )
                result["status"] = "unexpected_response"
                result["details"]["message"] = "Received response but wrong packet type"
                success = False

        except TimeoutError:
            print("❌ No response received (timeout)")
            result["response_received"] = False
            result["status"] = "timeout"
            result["details"]["message"] = "Shim did not respond within 5 seconds"
            success = False

        sock.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        result["status"] = "error"
        result["details"]["error"] = str(e)
        success = False

    # Write results to file
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n📝 Results written to: {output_file}")

    print()
    return success


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Test Chaosnet connectivity to shim")
    parser.add_argument("--output", help="Output file for JSON results")

    args = parser.parse_args()

    success = test_connectivity(args.output)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
