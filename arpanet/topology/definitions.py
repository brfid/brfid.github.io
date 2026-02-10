"""Concrete topology definitions for ARPANET phases.

This module contains the actual topology specifications for each ARPANET
phase. These are the single source of truth for network configurations.

Topologies are defined in Python (not YAML) to provide:
- Type safety via frozen dataclasses
- IDE autocomplete and validation
- Reviewable changes in git diffs
- No YAML parsing errors
"""

from arpanet.topology.registry import (
    HostConfig,
    NetworkInterface,
    TopologyDefinition,
)

# Phase 1: VAX + IMP #1 (basic ARPANET connectivity)
PHASE1_TOPOLOGY = TopologyDefinition(
    name="phase1",
    subnet="172.20.0.0/16",
    gateway="172.20.0.1",
    hosts={
        "vax": HostConfig(
            name="vax",
            component_type="vax",
            hostname="vax-host",
            container_name="arpanet-vax",
            console_port=2323,
            interfaces=[
                NetworkInterface(
                    network_type="arpanet",
                    ip_address="172.20.0.10",
                    udp_port=2000,
                    device="de0",
                    remote_host="172.20.0.20",
                    remote_port=2000,
                )
            ],
            image="jguillaumes/simh-vaxbsd@sha256:1bab805b25a793fd622c29d3e9b677b002cabbdc20d9c42afaeeed542cc42215",
            volumes=[
                ("./build/vax/simh-tape", "/machines"),
                ("./arpanet/scripts/simh-automation", "/machines/automation:ro"),
            ],
            environment={
                "SIMH_NETWORK": "enabled",
            },
        ),
        "imp1": HostConfig(
            name="imp1",
            component_type="imp",
            hostname="imp-1",
            container_name="arpanet-imp1",
            console_port=2324,
            interfaces=[
                NetworkInterface(
                    network_type="arpanet",
                    ip_address="172.20.0.20",
                    udp_port=2000,
                    device="hi1",
                    remote_host="172.20.0.10",
                    remote_port=2000,
                )
            ],
            dockerfile="./arpanet/Dockerfile.imp",
            volumes=[
                ("./build/arpanet/imp1", "/machines/data"),
                ("./arpanet/configs/imp-phase1.ini", "/machines/imp.ini:ro"),
                ("./arpanet/configs/impcode.simh", "/machines/impcode.simh:ro"),
                ("./arpanet/configs/impconfig.simh", "/machines/impconfig.simh:ro"),
            ],
            environment={
                "IMP_NUMBER": "1",
                "HOST_LINK_0": "172.20.0.10:2000",
            },
            depends_on=["vax"],
        ),
    },
)

# Phase 2: VAX + IMP #1 + IMP #2 + PDP-10/ITS (multi-hop routing)
PHASE2_TOPOLOGY = TopologyDefinition(
    name="phase2",
    subnet="172.20.0.0/16",
    gateway="172.20.0.1",
    hosts={
        "vax": HostConfig(
            name="vax",
            component_type="vax",
            hostname="vax-host",
            container_name="arpanet-vax",
            console_port=2323,
            interfaces=[
                NetworkInterface(
                    network_type="arpanet",
                    ip_address="172.20.0.10",
                    udp_port=2000,
                    device="de0",
                    remote_host="172.20.0.20",
                    remote_port=2000,
                )
            ],
            image="jguillaumes/simh-vaxbsd@sha256:1bab805b25a793fd622c29d3e9b677b002cabbdc20d9c42afaeeed542cc42215",
            volumes=[
                ("./build/vax/simh-tape", "/machines"),
                ("./arpanet/scripts/simh-automation", "/machines/automation:ro"),
            ],
            environment={
                "SIMH_NETWORK": "enabled",
            },
        ),
        "imp1": HostConfig(
            name="imp1",
            component_type="imp",
            hostname="imp-1",
            container_name="arpanet-imp1",
            console_port=2324,
            interfaces=[
                NetworkInterface(
                    network_type="arpanet",
                    ip_address="172.20.0.20",
                    udp_port=2000,
                    device="hi1",
                    remote_host="172.20.0.10",
                    remote_port=2000,
                ),
                NetworkInterface(
                    network_type="arpanet",
                    ip_address="172.20.0.20",
                    udp_port=3001,
                    device="mi1",
                    remote_host="172.20.0.30",
                    remote_port=3001,
                ),
            ],
            dockerfile="./arpanet/Dockerfile.imp",
            volumes=[
                ("./build/arpanet/imp1", "/machines/data"),
                ("./arpanet/configs/imp1-phase2.ini", "/machines/imp.ini:ro"),
                ("./arpanet/configs/impcode.simh", "/machines/impcode.simh:ro"),
                ("./arpanet/configs/impconfig.simh", "/machines/impconfig.simh:ro"),
            ],
            depends_on=["vax"],
        ),
        "imp2": HostConfig(
            name="imp2",
            component_type="imp",
            hostname="imp-2",
            container_name="arpanet-imp2",
            console_port=2325,
            interfaces=[
                NetworkInterface(
                    network_type="arpanet",
                    ip_address="172.20.0.30",
                    udp_port=3001,
                    device="mi1",
                    remote_host="172.20.0.20",
                    remote_port=3001,
                ),
                NetworkInterface(
                    network_type="arpanet",
                    ip_address="172.20.0.30",
                    udp_port=2000,
                    device="hi1",
                    remote_host="172.20.0.50",
                    remote_port=2000,
                ),
            ],
            dockerfile="./arpanet/Dockerfile.imp",
            volumes=[
                ("./build/arpanet/imp2", "/machines/data"),
                ("./arpanet/configs/imp2.ini", "/machines/imp.ini:ro"),
                ("./arpanet/configs/impcode.simh", "/machines/impcode.simh:ro"),
                ("./arpanet/configs/impconfig.simh", "/machines/impconfig.simh:ro"),
            ],
            depends_on=["imp1", "pdp10"],
        ),
        "pdp10": HostConfig(
            name="pdp10",
            component_type="its",
            hostname="pdp10-host",
            container_name="arpanet-pdp10",
            console_port=2326,
            extra_ports=[10004],
            interfaces=[
                NetworkInterface(
                    network_type="arpanet",
                    ip_address="172.20.0.40",
                    udp_port=2000,
                    device="imp",
                    remote_host="172.20.0.50",
                    remote_port=2001,
                )
            ],
            dockerfile="./arpanet/Dockerfile.pdp10-its",
            volumes=[
                ("./build/arpanet/pdp10", "/machines/data"),
                ("./arpanet/configs/phase2/pdp10.ini", "/machines/pdp10.ini:ro"),
            ],
            environment={
                "ITS_FORCE_RESEED": "0",
            },
        ),
        "hi1shim": HostConfig(
            name="hi1shim",
            component_type="shim",
            hostname="hi1-host-imp-interface",
            container_name="arpanet-hi1shim",
            console_port=2327,
            interfaces=[
                NetworkInterface(
                    network_type="arpanet",
                    ip_address="172.20.0.50",
                    udp_port=2000,
                    device="shim",
                    remote_host="172.20.0.30",
                    remote_port=2000,
                )
            ],
            dockerfile="./arpanet/Dockerfile.hi1shim",
            depends_on=["imp2", "pdp10"],
        ),
    },
)

# Registry of all available topologies
TOPOLOGIES = {
    "phase1": PHASE1_TOPOLOGY,
    "phase2": PHASE2_TOPOLOGY,
}
