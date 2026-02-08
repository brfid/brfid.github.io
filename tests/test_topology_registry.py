"""Tests for topology registry dataclass models."""

import pytest

from arpanet.topology.definitions import PHASE1_TOPOLOGY, PHASE2_TOPOLOGY, TOPOLOGIES
from arpanet.topology.registry import HostConfig, NetworkInterface, TopologyDefinition


class TestNetworkInterface:
    """Test NetworkInterface dataclass."""

    def test_interface_is_frozen(self) -> None:
        """Network interfaces should be immutable (frozen)."""
        interface = NetworkInterface(
            network_type="arpanet",
            ip_address="172.20.0.10",
            udp_port=2000,
            device="de0",
            remote_host="172.20.0.20",
            remote_port=2000,
        )
        with pytest.raises(AttributeError):
            interface.ip_address = "192.168.1.1"  # type: ignore[misc]

    def test_interface_device_types(self) -> None:
        """Test different device types (de0, hi1, mi1, imp)."""
        devices = ["de0", "hi1", "mi1", "imp"]
        for device in devices:
            interface = NetworkInterface(
                network_type="arpanet",
                ip_address="172.20.0.10",
                udp_port=2000,
                device=device,
            )
            assert interface.device == device


class TestHostConfig:
    """Test HostConfig dataclass."""

    def test_host_is_frozen(self) -> None:
        """Host configs should be immutable (frozen)."""
        host = HostConfig(
            name="test",
            component_type="vax",
            hostname="test-host",
            container_name="test-container",
            console_port=2323,
            interfaces=[],
        )
        with pytest.raises(AttributeError):
            host.name = "modified"  # type: ignore[misc]

    def test_host_with_multiple_interfaces(self) -> None:
        """Test host with multiple network interfaces."""
        interfaces = [
            NetworkInterface(
                network_type="arpanet",
                ip_address="172.20.0.20",
                udp_port=2000,
                device="hi1",
            ),
            NetworkInterface(
                network_type="arpanet",
                ip_address="172.20.0.20",
                udp_port=3001,
                device="mi1",
            ),
        ]
        host = HostConfig(
            name="imp1",
            component_type="imp",
            hostname="imp-1",
            container_name="arpanet-imp1",
            console_port=2324,
            interfaces=interfaces,
        )
        assert len(host.interfaces) == 2
        assert host.interfaces[0].device == "hi1"
        assert host.interfaces[1].device == "mi1"


class TestTopologyDefinition:
    """Test TopologyDefinition dataclass."""

    def test_topology_is_frozen(self) -> None:
        """Topologies should be immutable (frozen)."""
        topology = TopologyDefinition(
            name="test",
            subnet="172.20.0.0/16",
            gateway="172.20.0.1",
            hosts={},
        )
        with pytest.raises(AttributeError):
            topology.name = "modified"  # type: ignore[misc]

    def test_topology_dict_is_frozen(self) -> None:
        """Topology hosts dict should not be modifiable."""
        topology = PHASE1_TOPOLOGY
        # The dict itself is frozen as part of the dataclass
        with pytest.raises(AttributeError):
            topology.hosts = {}  # type: ignore[misc]


class TestPredefinedTopologies:
    """Test predefined topology definitions."""

    def test_get_topology_invalid_name(self) -> None:
        """Getting an invalid topology name should raise KeyError."""
        with pytest.raises(KeyError):
            _ = TOPOLOGIES["invalid_phase"]

    def test_phase1_has_required_hosts(self) -> None:
        """Phase1 should have VAX and IMP #1."""
        assert "vax" in PHASE1_TOPOLOGY.hosts
        assert "imp1" in PHASE1_TOPOLOGY.hosts
        assert len(PHASE1_TOPOLOGY.hosts) == 2

    def test_phase2_has_required_hosts(self) -> None:
        """Phase2 should have VAX, IMP #1, IMP #2, and PDP-10."""
        assert "vax" in PHASE2_TOPOLOGY.hosts
        assert "imp1" in PHASE2_TOPOLOGY.hosts
        assert "imp2" in PHASE2_TOPOLOGY.hosts
        assert "pdp10" in PHASE2_TOPOLOGY.hosts
        assert len(PHASE2_TOPOLOGY.hosts) == 4

    def test_phase1_topology_subnet(self) -> None:
        """Phase1 should use correct subnet."""
        assert PHASE1_TOPOLOGY.subnet == "172.20.0.0/16"
        assert PHASE1_TOPOLOGY.gateway == "172.20.0.1"
        assert PHASE1_TOPOLOGY.network_name == "arpanet-build"

    def test_phase2_topology_dependencies(self) -> None:
        """Phase2 should have correct dependency chain."""
        # IMP1 depends on VAX
        assert PHASE2_TOPOLOGY.hosts["imp1"].depends_on == ["vax"]
        # IMP2 depends on IMP1 and PDP10
        assert set(PHASE2_TOPOLOGY.hosts["imp2"].depends_on) == {"imp1", "pdp10"}
        # VAX and PDP10 have no dependencies
        assert PHASE2_TOPOLOGY.hosts["vax"].depends_on == []
        assert PHASE2_TOPOLOGY.hosts["pdp10"].depends_on == []

    def test_phase1_imp1_interfaces(self) -> None:
        """Phase1 IMP1 should have only host interface."""
        imp1 = PHASE1_TOPOLOGY.hosts["imp1"]
        assert len(imp1.interfaces) == 1
        assert imp1.interfaces[0].device == "hi1"
        assert imp1.interfaces[0].remote_host == "172.20.0.10"

    def test_phase2_imp1_interfaces(self) -> None:
        """Phase2 IMP1 should have host and modem interfaces."""
        imp1 = PHASE2_TOPOLOGY.hosts["imp1"]
        assert len(imp1.interfaces) == 2
        # Should have both HI1 and MI1
        devices = {iface.device for iface in imp1.interfaces}
        assert devices == {"hi1", "mi1"}

    def test_all_hosts_have_unique_ips(self) -> None:
        """Each host should have a unique primary IP address.

        Note: Hosts can have multiple interfaces with the same IP but different
        ports (e.g., IMP with HI1 and MI1 both on 172.20.0.20).
        """
        for topology in TOPOLOGIES.values():
            # Get the primary IP (first interface) for each host
            primary_ips = [
                host.interfaces[0].ip_address
                for host in topology.hosts.values()
                if host.interfaces
            ]
            # All primary IPs should be unique
            assert len(primary_ips) == len(set(primary_ips)), (
                f"Duplicate primary IPs in {topology.name}"
            )

    def test_all_hosts_have_unique_console_ports(self) -> None:
        """All hosts in a topology should have unique console ports."""
        for topology in TOPOLOGIES.values():
            ports = [host.console_port for host in topology.hosts.values()]
            # All ports should be unique
            assert len(ports) == len(set(ports)), f"Duplicate ports in {topology.name}"
