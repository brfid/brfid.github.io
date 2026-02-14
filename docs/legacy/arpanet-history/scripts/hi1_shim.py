#!/usr/bin/env python3
"""Host-IMP Interface shim for Phase 2 HI1 UDP framing.

This process sits between PDP-10 and IMP2 and performs boundary-only
framing adaptation:

- PDP-10 -> IMP2: wraps payload into H316 UDP envelope
- IMP2 -> PDP-10: unwraps H316 UDP envelope to payload

The goal is to provide a temporary compatibility bridge while native
host-link alignment is investigated.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import struct
from dataclasses import dataclass


MAGIC = 0x48333136  # 'H316'
HEADER_FMT = "!IIH"
HEADER_SIZE = struct.calcsize(HEADER_FMT)


@dataclass
class ShimCounters:
    """Simple runtime counters for observability."""

    pdp10_ingress_packets: int = 0
    imp_ingress_packets: int = 0
    wrapped_packets: int = 0
    unwrapped_packets: int = 0
    parse_errors: int = 0


def _to_words(payload: bytes) -> tuple[bytes, int]:
    """Pad payload to 16-bit word boundary and return count in words."""
    if len(payload) % 2:
        payload += b"\x00"
    return payload, len(payload) // 2


def wrap_h316(payload: bytes, sequence: int) -> bytes:
    """Wrap raw payload bytes into H316 UDP framing."""
    words, word_count = _to_words(payload)
    header = struct.pack(HEADER_FMT, MAGIC, sequence & 0xFFFFFFFF, word_count)
    return header + words


def unwrap_h316(packet: bytes) -> bytes:
    """Extract payload bytes from H316 UDP packet.

    Raises:
        ValueError: If packet is malformed or has unexpected magic/count.
    """
    if len(packet) < HEADER_SIZE:
        raise ValueError(f"short packet: {len(packet)} bytes")

    magic, _sequence, word_count = struct.unpack(HEADER_FMT, packet[:HEADER_SIZE])
    if magic != MAGIC:
        raise ValueError(f"bad magic: {magic:08x}")

    expected = HEADER_SIZE + (word_count * 2)
    if len(packet) < expected:
        raise ValueError(
            f"truncated payload: got={len(packet)} expected>={expected}"
        )
    return packet[HEADER_SIZE:expected]


class _ForwardProtocol(asyncio.DatagramProtocol):
    """Datagram handler that forwards via shim transform callbacks."""

    def __init__(
        self,
        *,
        name: str,
        on_packet,
        logger: logging.Logger,
    ) -> None:
        self.name = name
        self.on_packet = on_packet
        self.logger = logger
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport) -> None:  # type: ignore[override]
        self.transport = transport
        sockname = transport.get_extra_info("sockname")
        self.logger.info("%s listening on %s", self.name, sockname)

    def datagram_received(self, data: bytes, addr) -> None:  # type: ignore[override]
        self.on_packet(data, addr)

    def error_received(self, exc: Exception) -> None:  # type: ignore[override]
        self.logger.warning("%s UDP error: %s", self.name, exc)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 2 Host-IMP Interface shim (PDP-10 <-> IMP2 HI1)"
    )
    parser.add_argument("--bind", default="0.0.0.0", help="Local bind address")
    parser.add_argument("--pdp10-port", type=int, default=2001)
    parser.add_argument("--imp-port", type=int, default=2000)
    parser.add_argument("--pdp10-host", default="172.20.0.40")
    parser.add_argument("--pdp10-target-port", type=int, default=2000)
    parser.add_argument("--imp-host", default="172.20.0.30")
    parser.add_argument("--imp-target-port", type=int, default=2000)
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> None:
    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logger = logging.getLogger("hi1-shim")

    counters = ShimCounters()
    sequence = 0
    loop = asyncio.get_running_loop()

    pdp_transport: asyncio.DatagramTransport | None = None
    imp_transport: asyncio.DatagramTransport | None = None

    def from_pdp10(data: bytes, addr) -> None:
        nonlocal sequence
        del addr
        counters.pdp10_ingress_packets += 1
        wrapped = wrap_h316(data, sequence)
        sequence = (sequence + 1) & 0xFFFFFFFF
        counters.wrapped_packets += 1
        if imp_transport is not None:
            imp_transport.sendto(wrapped, (args.imp_host, args.imp_target_port))

    def from_imp(data: bytes, addr) -> None:
        del addr
        counters.imp_ingress_packets += 1
        try:
            payload = unwrap_h316(data)
        except ValueError as exc:
            counters.parse_errors += 1
            logger.debug("drop IMP packet: %s", exc)
            return

        counters.unwrapped_packets += 1
        if pdp_transport is not None:
            pdp_transport.sendto(payload, (args.pdp10_host, args.pdp10_target_port))

    pdp_transport, _ = await loop.create_datagram_endpoint(
        lambda: _ForwardProtocol(name="pdp10-side", on_packet=from_pdp10, logger=logger),
        local_addr=(args.bind, args.pdp10_port),
    )
    imp_transport, _ = await loop.create_datagram_endpoint(
        lambda: _ForwardProtocol(name="imp-side", on_packet=from_imp, logger=logger),
        local_addr=(args.bind, args.imp_port),
    )

    logger.info(
        "Host-IMP Interface active: pdp10 %s:%s -> imp %s:%s",
        args.bind,
        args.pdp10_port,
        args.imp_host,
        args.imp_target_port,
    )

    try:
        while True:
            await asyncio.sleep(10)
            logger.info(
                "counters pdp10_in=%d imp_in=%d wrapped=%d unwrapped=%d parse_errors=%d",
                counters.pdp10_ingress_packets,
                counters.imp_ingress_packets,
                counters.wrapped_packets,
                counters.unwrapped_packets,
                counters.parse_errors,
            )
    finally:
        pdp_transport.close()
        imp_transport.close()


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    asyncio.run(_run(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
