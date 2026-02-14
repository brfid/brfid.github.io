"""ARPANET topology management.

This package provides single-source-of-truth topology definitions for
ARPANET simulation infrastructure. Topologies are defined as immutable
dataclasses that generate Docker Compose and SIMH configurations.

Example:
    >>> from arpanet.topology.definitions import PHASE1_TOPOLOGY
    >>> from arpanet.topology.generators import generate_docker_compose
    >>> config = generate_docker_compose(PHASE1_TOPOLOGY)
"""

from arpanet.topology.definitions import TOPOLOGIES, PHASE1_TOPOLOGY, PHASE2_TOPOLOGY
from arpanet.topology.registry import (
    HostConfig,
    NetworkInterface,
    TopologyDefinition,
)

__all__ = [
    "TOPOLOGIES",
    "PHASE1_TOPOLOGY",
    "PHASE2_TOPOLOGY",
    "HostConfig",
    "NetworkInterface",
    "TopologyDefinition",
]
