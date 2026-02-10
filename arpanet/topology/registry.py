"""Topology registry: immutable dataclass models for ARPANET topologies.

This module defines the core data structures for representing ARPANET
network topologies. All structures are frozen dataclasses to ensure
immutability and prevent configuration errors.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Literal


@dataclass(frozen=True)
class NetworkInterface:
    """Single network interface configuration for a host.

    Represents either a host interface (IMP-to-host connection) or a
    modem interface (IMP-to-IMP connection). Each interface specifies
    the network type, addressing, and connection parameters.

    Attributes:
        network_type: Protocol type for this interface.
        ip_address: IPv4 address for this interface.
        udp_port: Local UDP port for SIMH network attachment.
        device: SIMH device name (e.g., "de0" for VAX, "hi1" for IMP host).
        remote_host: IP address of remote endpoint (None for unconnected).
        remote_port: UDP port of remote endpoint (None for unconnected).

    Example:
        >>> # VAX interface to IMP
        >>> NetworkInterface(
        ...     network_type="arpanet",
        ...     ip_address="172.20.0.10",
        ...     udp_port=2000,
        ...     device="de0",
        ...     remote_host="172.20.0.20",
        ...     remote_port=2000,
        ... )
    """

    network_type: Literal["arpanet", "decnet", "uucp"]
    ip_address: str
    udp_port: int
    device: str
    remote_host: str | None = None
    remote_port: int | None = None


@dataclass(frozen=True)
class HostConfig:
    """Configuration for a single host system in the topology.

    Encapsulates all parameters needed to generate Docker Compose service
    definitions and SIMH configuration files for a host. Supports multiple
    component types (VAX, PDP-10, IMP) with flexible interface configurations.

    Attributes:
        name: Short identifier for this host (e.g., "vax", "imp1").
        component_type: Type of system being simulated.
        hostname: DNS hostname for Docker container.
        container_name: Full Docker container name.
        console_port: External telnet console port (host-side mapping).
        interfaces: Network interfaces attached to this host.
        dockerfile: Custom Dockerfile path (None to use pre-built image).
        image: Docker image name (alternative to dockerfile).
        volumes: Volume mounts as (host_path, container_path) tuples.
        environment: Environment variables for the container.
        depends_on: Container dependencies (must start after these).
        extra_ports: Additional TCP port mappings exposed as host:container.

    Example:
        >>> HostConfig(
        ...     name="vax",
        ...     component_type="vax",
        ...     hostname="vax-host",
        ...     container_name="arpanet-vax",
        ...     console_port=2323,
        ...     interfaces=[...],
        ...     image="jguillaumes/simh-vaxbsd@sha256:...",
        ... )
    """

    name: str
    component_type: Literal["vax", "pdp10", "pdp11", "its", "imp", "shim"]
    hostname: str
    container_name: str
    console_port: int
    interfaces: List[NetworkInterface]
    dockerfile: str | None = None
    image: str | None = None
    volumes: List[tuple[str, str]] = field(default_factory=list)
    environment: Dict[str, str] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    extra_ports: List[int] = field(default_factory=list)


@dataclass(frozen=True)
class TopologyDefinition:
    """Complete network topology specification.

    Represents a full ARPANET topology with all hosts, network configuration,
    and inter-host connections. This is the single source of truth from which
    all Docker Compose and SIMH configurations are generated.

    Attributes:
        name: Topology identifier (e.g., "phase1", "phase2").
        subnet: CIDR notation for Docker network subnet.
        gateway: Gateway IP address for the network.
        hosts: Mapping of host names to their configurations.
        network_name: Docker network name (defaults to "arpanet-build").

    Example:
        >>> TopologyDefinition(
        ...     name="phase1",
        ...     subnet="172.20.0.0/16",
        ...     gateway="172.20.0.1",
        ...     hosts={"vax": vax_config, "imp1": imp1_config},
        ... )
    """

    name: str
    subnet: str
    gateway: str
    hosts: Dict[str, HostConfig]
    network_name: str = "arpanet-build"
