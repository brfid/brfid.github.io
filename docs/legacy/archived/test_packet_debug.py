#!/usr/bin/env python3
"""Debug script to test chaosnet packet formatting."""

import struct
from arpanet.scripts.chaosnet_transfer import ChaosnetPacket, PKT_RFC, CHAOSNET_HEADER_SIZE

# Create RFC packet as the test does
rfc = ChaosnetPacket(
    pkt_type=PKT_RFC,
    length=CHAOSNET_HEADER_SIZE,
    src_host=0,
    src_subnet=0,
    dst_host=0x7700,
    dst_subnet=0x01,
    data=b''
)

print(f"CHAOSNET_HEADER_SIZE: {CHAOSNET_HEADER_SIZE}")
print(f"Packet bytes total: {len(rfc.to_bytes())}")
print(f"Hex dump: {rfc.to_bytes().hex()}")

# Unpack to verify
header = struct.unpack('>HHBBHH', rfc.to_bytes()[:CHAOSNET_HEADER_SIZE])
print(f"Unpacked header: {header}")
print(f"  pkt_type: {header[0]}")
print(f"  length: {header[1]}")
print(f"  src_host: {header[2]}")
print(f"  src_subnet: {header[3]}")
print(f"  dst_host: {header[4]}")
print(f"  dst_subnet: {header[5]}")

# Verify subnet is within valid range (0-255)
subnet = header[5]
print(f"\nDST_SUBNET value: {subnet}")
print(f"Is valid (0-255): {0 <= subnet <= 255}")
