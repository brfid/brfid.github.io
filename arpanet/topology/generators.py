"""Configuration generators: pure functions from topology to configs.

This module provides pure, idempotent functions that transform topology
definitions into Docker Compose YAML and SIMH .ini configurations.

All functions are stateless transformations with no side effects except
for file writing functions which are clearly marked.
"""

from pathlib import Path
from typing import Any, Dict

import yaml

from arpanet.topology.registry import HostConfig, TopologyDefinition


def generate_docker_compose(topology: TopologyDefinition) -> Dict[str, Any]:
    """Generate Docker Compose configuration from topology.

    Creates a complete docker-compose.yml structure including services,
    networks, and volumes. The generated configuration is idempotent
    and can be directly serialized to YAML.

    Args:
        topology: Network topology definition containing hosts, subnets,
            and interface configurations.

    Returns:
        Docker Compose configuration as a dictionary ready for YAML
        serialization. Follows compose file version 3.8 spec.

    Raises:
        ValueError: If topology contains invalid host configurations.

    Example:
        >>> from arpanet.topology.definitions import PHASE1_TOPOLOGY
        >>> config = generate_docker_compose(PHASE1_TOPOLOGY)
        >>> import yaml
        >>> with open("docker-compose.yml", "w") as f:
        ...     yaml.dump(config, f)
    """
    services = {}
    for host_name, host in topology.hosts.items():
        services[host_name] = _generate_service(host, topology)

    return {
        "version": "3.8",
        "services": services,
        "networks": {
            "arpanet": {
                "name": topology.network_name,
                "driver": "bridge",
                "ipam": {
                    "config": [
                        {
                            "subnet": topology.subnet,
                            "gateway": topology.gateway,
                        }
                    ]
                },
            }
        },
    }


def _generate_service(host: HostConfig, topology: TopologyDefinition) -> Dict[str, Any]:
    """Generate Docker Compose service definition for a single host.

    Args:
        host: Host configuration to generate service for.
        topology: Parent topology (for network name).

    Returns:
        Service definition dict for docker-compose.yml.
    """
    service: Dict[str, Any] = {
        "container_name": host.container_name,
        "hostname": host.hostname,
    }

    # Image or build configuration
    if host.image:
        service["image"] = host.image
    elif host.dockerfile:
        service["build"] = {
            "context": "./arpanet" if "arpanet" in host.dockerfile else ".",
            "dockerfile": host.dockerfile.replace("./arpanet/", ""),
        }

    # Ports (console + optional extras)
    service["ports"] = [f"{host.console_port}:2323"]
    if host.extra_ports:
        service["ports"].extend([f"{port}:{port}" for port in host.extra_ports])

    # Volumes
    if host.volumes:
        service["volumes"] = [
            f"{host_path}:{container_path}"
            for host_path, container_path in host.volumes
        ]

    # Network configuration
    service["networks"] = {
        "arpanet": {
            "ipv4_address": host.interfaces[0].ip_address if host.interfaces else None
        }
    }

    # Environment variables
    if host.environment:
        service["environment"] = [
            f"{key}={value}" for key, value in host.environment.items()
        ]

    # Restart policy
    service["restart"] = "unless-stopped"

    # Dependencies
    if host.depends_on:
        service["depends_on"] = host.depends_on

    return service


def generate_simh_config(host: HostConfig, topology: TopologyDefinition) -> str:
    """Generate SIMH .ini configuration for a host.

    Creates SIMH simulator configuration files with appropriate interface
    settings, debug output, and network attachments based on the host's
    component type.

    Args:
        host: Host configuration to generate SIMH config for.
        topology: Parent topology (for context in comments).

    Returns:
        SIMH configuration as a string with comments documenting the
        source topology and configuration rationale.

    Raises:
        ValueError: If host component type is not recognized.

    Example:
        >>> from arpanet.topology.definitions import PHASE1_TOPOLOGY
        >>> imp_config = generate_simh_config(
        ...     PHASE1_TOPOLOGY.hosts["imp1"],
        ...     PHASE1_TOPOLOGY
        ... )
    """
    if host.component_type == "imp":
        return _generate_imp_config(host, topology)
    elif host.component_type in ("pdp10", "its"):
        return _generate_pdp10_config(host, topology)
    elif host.component_type == "vax":
        # VAX uses base image config, no custom .ini needed
        return ""
    else:
        raise ValueError(f"Unknown component type: {host.component_type}")


def _generate_imp_config(host: HostConfig, topology: TopologyDefinition) -> str:
    """Generate SIMH H316 IMP configuration.

    Args:
        host: IMP host configuration.
        topology: Parent topology.

    Returns:
        SIMH .ini file content as string.
    """
    # Separate interfaces by type
    host_interfaces = [
        iface for iface in host.interfaces if iface.device.startswith("hi")
    ]
    modem_interfaces = [
        iface for iface in host.interfaces if iface.device.startswith("mi")
    ]

    # Extract IMP number from name (e.g., "imp1" -> 1)
    imp_number = host.name.replace("imp", "")

    # Build connection descriptions
    connections = []
    for iface in host_interfaces:
        connections.append(
            f";   - {iface.remote_host} (host) on HI{iface.device[-1]} (UDP {iface.udp_port})"
        )
    for iface in modem_interfaces:
        connections.append(
            f";   - {iface.remote_host} (IMP-to-IMP) on MI{iface.device[-1]} (UDP {iface.udp_port})"
        )

    config_lines = [
        f"; SIMH H316 IMP Configuration - {topology.name.title()} (IMP #{imp_number})",
        f"; IMP #{imp_number} connects to:",
    ]
    config_lines.extend(connections)
    config_lines.extend(
        [
            ";",
            "set debug stdout",
            "",
            "; Load generic IMP configuration",
            "do impconfig.simh",
            "",
            f"; Set IMP number to {imp_number}",
            f"set imp num={imp_number}",
            "",
            "; Load IMP firmware",
            "do impcode.simh",
            "",
        ]
    )

    # Modem interfaces (IMP-to-IMP)
    if modem_interfaces:
        config_lines.append("; MODEM INTERFACES (IMP-to-IMP)")
        for iface in modem_interfaces:
            device_num = iface.device[-1]
            config_lines.extend(
                [
                    f"set mi{device_num} enabled",
                    f"set mi{device_num} debug",
                    f"attach -u mi{device_num} {iface.udp_port}:{iface.remote_host}:{iface.remote_port}",
                    "",
                ]
            )

        # Disable unused modem interfaces
        config_lines.append("; Disable other modem interfaces")
        used_modem_nums = {int(iface.device[-1]) for iface in modem_interfaces}
        for i in range(1, 6):
            if i not in used_modem_nums:
                config_lines.append(f"set mi{i} disabled")
        config_lines.append("")
    else:
        config_lines.extend(
            [
                "; MODEM INTERFACES (IMP-to-IMP connections):",
                f"; For {topology.name.title()}, we don't have any IMP-to-IMP connections yet"
                if topology.name == "phase1"
                else "; No modem interfaces configured",
                "; These will be enabled in Phase 2 when we add a second IMP"
                if topology.name == "phase1"
                else "",
            ]
        )
        for i in range(1, 6):
            config_lines.append(f"set mi{i} disabled")
        config_lines.append("")

    # Host interfaces
    if host_interfaces:
        config_lines.append("; HOST INTERFACE")
        for iface in host_interfaces:
            device_num = iface.device[-1]
            config_lines.extend(
                [
                    f"set hi{device_num} enabled",
                    f"set hi{device_num} debug",
                    f"attach -u hi{device_num} {iface.udp_port}:{iface.remote_host}:{iface.remote_port}",
                    "",
                ]
            )

        # Disable unused host interfaces
        config_lines.append("; Disable unused host interfaces")
        used_host_nums = {int(iface.device[-1]) for iface in host_interfaces}
        for i in range(1, 5):
            if i not in used_host_nums:
                config_lines.append(f"set hi{i} disabled")
        config_lines.append("")

    # Echo startup messages
    config_lines.extend(
        [
            f"echo IMP #{imp_number} ({topology.name.title()}) starting...",
        ]
    )
    for iface in host_interfaces:
        config_lines.append(
            f"echo HI{iface.device[-1]} connected to {iface.remote_host} at {iface.remote_host}:{iface.remote_port}"
        )
    for iface in modem_interfaces:
        config_lines.append(
            f"echo MI{iface.device[-1]} connected to IMP at {iface.remote_host}:{iface.remote_port}"
        )
    config_lines.append("go")

    return "\n".join(config_lines) + "\n"


def _generate_pdp10_config(host: HostConfig, topology: TopologyDefinition) -> str:
    """Generate SIMH PDP-10 configuration.

    Args:
        host: PDP-10 host configuration.
        topology: Parent topology.

    Returns:
        SIMH .ini file content as string.
    """
    imp_interface = next(
        (iface for iface in host.interfaces if iface.device == "imp"), None
    )

    is_its = host.component_type == "its"

    config_lines = [
        "; SIMH PDP-10 KS Configuration - ITS"
        if is_its
        else "; SIMH PDP-10 KS Configuration - TOPS-20 V4.1",
        f"; {topology.name.title()}: ARPANET host for file transfer testing",
        ";",
        f"; This PDP-10 connects to IMP via network interface (UDP {imp_interface.udp_port if imp_interface else 'N/A'})",
        "",
        "set debug stdout",
        "",
        "; Configure CPU",
        "set console wru=034",
        "",
    ]

    if is_its:
        config_lines.extend(
            [
                "; ITS-specific CPU and memory configuration",
                "set cpu its",
                "; set cpu 2048k",
                "; NOTE: disabled by default; some pdp10-ks builds reject this parameter",
                "; and abort before boot. Re-enable only after validating accepted syntax",
                "; via: show version / show devices / help set cpu inside the runtime image.",
                "set tim y2k",
                "",
                "; Console and terminal multiplexer",
                "; Keep console on stdio for stability. Current pdp10-ks exits",
                "; after boot if no telnet console client attaches quickly.",
                "set console notelnet",
                "set dz enable",
                "set dz lines=8",
                "attach dz 10004",
                "",
                "; Configure disk drive (RP = RP06) for ITS system disk",
                "; KS-10 simulator uses RPA devices (RPA0..RPA7), not RP0",
                "set rpa enable",
                "set rpa0 enable",
                "set rpa0 rp06",
                "attach rpa0 /machines/data/its.dsk",
                "",
            ]
        )
    else:
        config_lines.extend(
            [
                "; Disable unused devices for minimal config",
                "set dz disabled",
                "set lp20 disabled",
                "",
                "; Configure tape drive (TUA) for installation/distribution media",
                "set tua enable",
                "set tua0 locked",
                "attach tua0 /machines/pdp10/tops20_v41.tap",
                "",
                "; Configure disk drive (RPA = RP06) for system disk",
                "set rpa enable",
                "set rpa0 rp06",
                "attach rpa0 /machines/data/tops20.dsk",
                "",
                "; Telnet console on port 2323",
                "set console telnet=2323",
                "",
            ]
        )

    if imp_interface:
        config_lines.extend(
            [
                "; IMP Network Interface for ARPANET connection",
                f"; This is the PDP-10's network interface that connects to IMP at {imp_interface.remote_host}",
                "set imp enabled",
                "set imp debug",
                "; Attach IMP interface via SIMH UDP bridge",
                f"; Local UDP {imp_interface.udp_port} <-> remote {imp_interface.remote_host}:{imp_interface.remote_port}",
                f"attach imp udp:{imp_interface.udp_port}:{imp_interface.remote_host}:{imp_interface.remote_port}",
                "",
            ]
        )

    config_lines.extend(
        [
            "echo PDP-10 ITS starting..." if is_its else "echo PDP-10 TOPS-20 V4.1 starting...",
        ]
    )

    if imp_interface:
        config_lines.append(
            f"echo IMP network interface: {host.interfaces[0].ip_address}:{imp_interface.udp_port} <-> IMP at {imp_interface.remote_host}:{imp_interface.remote_port}"
        )

    config_lines.extend(
        [
            "echo Console on stdio (telnet disabled for stability)"
            if is_its
            else "echo Telnet console on port 2323",
            "echo DZ lines attached on port 10004"
            if is_its
            else "echo Installation tape: tops20_v41.tap on TUA0",
            "echo System disk: /machines/data/its.dsk on RPA0"
            if is_its
            else "echo System disk: /machines/data/tops20.dsk on RPA0",
            "echo",
            "echo Booting ITS from disk..." if is_its else "echo Booting from installation tape...",
            f"echo Connect via: telnet localhost {host.console_port}",
            "echo",
            "",
            "; Boot from system disk" if is_its else "; Boot from installation tape",
            "; SIMH will wait for console connection before proceeding",
            "boot rpa0" if is_its else "boot tua0",
        ]
    )

    return "\n".join(config_lines) + "\n"


def write_generated_configs(topology: TopologyDefinition, output_dir: Path) -> None:
    """Write all generated configurations to disk.

    Generates Docker Compose and SIMH configuration files for the given
    topology and writes them to the specified output directory. This
    function is idempotent - running it multiple times produces identical
    output.

    Files generated:
    - docker-compose.{topology.name}.yml
    - arpanet/configs/{topology.name}/{host}.ini (for each IMP/PDP-10)

    Args:
        topology: Topology definition to generate configs for.
        output_dir: Root directory for output (project root).

    Example:
        >>> from pathlib import Path
        >>> from arpanet.topology.definitions import PHASE1_TOPOLOGY
        >>> write_generated_configs(PHASE1_TOPOLOGY, Path("."))
    """
    # Generate Docker Compose file
    compose_config = generate_docker_compose(topology)
    compose_file = output_dir / f"docker-compose.arpanet.{topology.name}.yml"

    # Add header comment to YAML output
    yaml_content = f"""# ARPANET Build Integration - {topology.name.title()}
# Generated from arpanet/topology/definitions.py - DO NOT EDIT MANUALLY
# To regenerate: arpanet-topology {topology.name}
#
# Topology: {_describe_topology(topology)}

"""
    yaml_content += yaml.dump(
        compose_config, default_flow_style=False, sort_keys=False, width=120
    )

    compose_file.write_text(yaml_content)
    print(f"Generated: {compose_file}")

    # Generate SIMH configs
    configs_dir = output_dir / "arpanet" / "configs" / topology.name
    configs_dir.mkdir(parents=True, exist_ok=True)

    for host_name, host in topology.hosts.items():
        if host.component_type in ("imp", "pdp10", "its"):
            config_content = generate_simh_config(host, topology)
            if config_content:
                config_file = configs_dir / f"{host_name}.ini"
                config_file.write_text(config_content)
                print(f"Generated: {config_file}")


def _describe_topology(topology: TopologyDefinition) -> str:
    """Generate a human-readable topology description.

    Args:
        topology: Topology to describe.

    Returns:
        ASCII art or textual description of the topology.
    """
    host_names = list(topology.hosts.keys())
    if topology.name == "phase1":
        return "[VAX/BSD] <-> [IMP #1]"
    elif topology.name == "phase2":
        return "[VAX/BSD] <-> [IMP #1] <-> [IMP #2] <-> [PDP-10/ITS]"
    else:
        return " <-> ".join(f"[{name.upper()}]" for name in host_names)
