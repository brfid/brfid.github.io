"""Tests for topology configuration generators."""

import re
from pathlib import Path

import pytest
import yaml

from arpanet.topology.definitions import PHASE1_TOPOLOGY, PHASE2_TOPOLOGY
from arpanet.topology.generators import (
    generate_docker_compose,
    generate_simh_config,
    write_generated_configs,
)


class TestDockerComposeGeneration:
    """Test Docker Compose configuration generation."""

    def test_generate_docker_compose_valid_yaml(self) -> None:
        """Generated Docker Compose should be valid YAML."""
        config = generate_docker_compose(PHASE1_TOPOLOGY)
        # Should be serializable to YAML
        yaml_str = yaml.dump(config)
        # Should be deserializable
        reloaded = yaml.safe_load(yaml_str)
        assert reloaded["version"] == "3.8"

    def test_generate_phase1_services(self) -> None:
        """Phase1 should generate VAX and IMP1 services."""
        config = generate_docker_compose(PHASE1_TOPOLOGY)
        assert "services" in config
        assert "vax" in config["services"]
        assert "imp1" in config["services"]
        assert len(config["services"]) == 2

    def test_generate_phase2_services(self) -> None:
        """Phase2 should generate all four services."""
        config = generate_docker_compose(PHASE2_TOPOLOGY)
        assert "services" in config
        assert "vax" in config["services"]
        assert "imp1" in config["services"]
        assert "imp2" in config["services"]
        assert "pdp10" in config["services"]
        assert len(config["services"]) == 4

    def test_vax_uses_image_not_build(self) -> None:
        """VAX should use pre-built image."""
        config = generate_docker_compose(PHASE1_TOPOLOGY)
        vax_service = config["services"]["vax"]
        assert "image" in vax_service
        assert "jguillaumes/simh-vaxbsd" in vax_service["image"]
        assert "build" not in vax_service

    def test_imp_uses_build_not_image(self) -> None:
        """IMP should use Dockerfile build."""
        config = generate_docker_compose(PHASE1_TOPOLOGY)
        imp_service = config["services"]["imp1"]
        assert "build" in imp_service
        assert imp_service["build"]["context"] == "./arpanet"
        assert "image" not in imp_service

    def test_network_configuration(self) -> None:
        """Generated config should have correct network settings."""
        config = generate_docker_compose(PHASE1_TOPOLOGY)
        assert "networks" in config
        assert "arpanet" in config["networks"]
        network = config["networks"]["arpanet"]
        assert network["name"] == "arpanet-build"
        assert network["driver"] == "bridge"
        assert network["ipam"]["config"][0]["subnet"] == "172.20.0.0/16"
        assert network["ipam"]["config"][0]["gateway"] == "172.20.0.1"

    def test_service_has_static_ip(self) -> None:
        """Services should have static IP addresses."""
        config = generate_docker_compose(PHASE1_TOPOLOGY)
        vax_service = config["services"]["vax"]
        assert "networks" in vax_service
        assert "arpanet" in vax_service["networks"]
        assert vax_service["networks"]["arpanet"]["ipv4_address"] == "172.20.0.10"

    def test_service_has_console_port(self) -> None:
        """Services should expose console port."""
        config = generate_docker_compose(PHASE1_TOPOLOGY)
        vax_service = config["services"]["vax"]
        assert "ports" in vax_service
        assert "2323:2323" in vax_service["ports"]

    def test_service_has_restart_policy(self) -> None:
        """Services should have restart policy."""
        config = generate_docker_compose(PHASE1_TOPOLOGY)
        for service in config["services"].values():
            assert service["restart"] == "unless-stopped"

    def test_dependencies_preserved(self) -> None:
        """Service dependencies should be preserved."""
        config = generate_docker_compose(PHASE2_TOPOLOGY)
        imp1_service = config["services"]["imp1"]
        assert "depends_on" in imp1_service
        assert imp1_service["depends_on"] == ["vax"]

        imp2_service = config["services"]["imp2"]
        assert "depends_on" in imp2_service
        assert set(imp2_service["depends_on"]) == {"imp1", "pdp10"}


class TestSIMHConfigGeneration:
    """Test SIMH .ini configuration generation."""

    def test_generate_imp_config_has_interfaces(self) -> None:
        """IMP config should configure network interfaces."""
        imp1_host = PHASE1_TOPOLOGY.hosts["imp1"]
        config = generate_simh_config(imp1_host, PHASE1_TOPOLOGY)
        assert "set hi1 enabled" in config
        assert "attach -u hi1" in config

    def test_imp_config_disables_unused_interfaces(self) -> None:
        """IMP config should disable unused interfaces."""
        imp1_host = PHASE1_TOPOLOGY.hosts["imp1"]
        config = generate_simh_config(imp1_host, PHASE1_TOPOLOGY)
        # Should disable unused host interfaces
        assert "set hi2 disabled" in config
        assert "set hi3 disabled" in config
        assert "set hi4 disabled" in config
        # Should disable all modem interfaces in phase1
        assert "set mi1 disabled" in config
        assert "set mi2 disabled" in config

    def test_phase2_imp1_has_modem_interface(self) -> None:
        """Phase2 IMP1 should enable modem interface."""
        imp1_host = PHASE2_TOPOLOGY.hosts["imp1"]
        config = generate_simh_config(imp1_host, PHASE2_TOPOLOGY)
        assert "set mi1 enabled" in config
        assert "attach -u mi1 3001:172.20.0.30:3001" in config

    def test_pdp10_config_has_imp_interface(self) -> None:
        """PDP-10 config should configure IMP network interface."""
        pdp10_host = PHASE2_TOPOLOGY.hosts["pdp10"]
        config = generate_simh_config(pdp10_host, PHASE2_TOPOLOGY)
        assert "set imp enabled" in config
        assert "attach imp udp:" in config
        assert "172.20.0.30:2000" in config

    def test_config_has_header_comment(self) -> None:
        """Generated configs should have descriptive headers."""
        imp1_host = PHASE1_TOPOLOGY.hosts["imp1"]
        config = generate_simh_config(imp1_host, PHASE1_TOPOLOGY)
        # Should identify configuration type
        assert "SIMH H316 IMP Configuration" in config
        # Should identify phase
        assert "Phase1" in config or "phase1" in config.lower()

    def test_config_includes_topology_info(self) -> None:
        """Generated configs should document topology connections."""
        imp1_host = PHASE2_TOPOLOGY.hosts["imp1"]
        config = generate_simh_config(imp1_host, PHASE2_TOPOLOGY)
        # Should document what this IMP connects to
        assert "172.20.0.10" in config  # VAX IP
        assert "172.20.0.30" in config  # IMP2 IP

    def test_vax_returns_empty_config(self) -> None:
        """VAX uses base image config, should return empty string."""
        vax_host = PHASE1_TOPOLOGY.hosts["vax"]
        config = generate_simh_config(vax_host, PHASE1_TOPOLOGY)
        assert config == ""

    def test_unknown_component_type_raises(self) -> None:
        """Unknown component types should raise ValueError."""
        from arpanet.topology.registry import HostConfig

        unknown_host = HostConfig(
            name="unknown",
            component_type="pdp11",  # Not implemented yet
            hostname="unknown-host",
            container_name="unknown-container",
            console_port=2323,
            interfaces=[],
        )
        with pytest.raises(ValueError, match="Unknown component type"):
            generate_simh_config(unknown_host, PHASE1_TOPOLOGY)


class TestConfigFileWriting:
    """Test writing generated configs to disk."""

    def test_write_generated_configs(self, tmp_path: Path) -> None:
        """Test writing complete topology configuration."""
        write_generated_configs(PHASE1_TOPOLOGY, tmp_path)

        # Check Docker Compose file exists
        compose_file = tmp_path / "docker-compose.arpanet.phase1.yml"
        assert compose_file.exists()

        # Check SIMH configs exist
        imp1_config = tmp_path / "arpanet" / "configs" / "phase1" / "imp1.ini"
        assert imp1_config.exists()

        # VAX should not generate config
        vax_config = tmp_path / "arpanet" / "configs" / "phase1" / "vax.ini"
        assert not vax_config.exists()

    def test_generated_compose_has_header(self, tmp_path: Path) -> None:
        """Generated Docker Compose should have explanatory header."""
        write_generated_configs(PHASE1_TOPOLOGY, tmp_path)
        compose_file = tmp_path / "docker-compose.arpanet.phase1.yml"
        content = compose_file.read_text()

        # Should have header comment
        assert "# ARPANET Build Integration" in content
        assert "# Generated from" in content
        assert "DO NOT EDIT MANUALLY" in content  # Part of the generated header

    def test_generated_compose_is_valid_yaml(self, tmp_path: Path) -> None:
        """Generated Docker Compose should be parseable YAML."""
        write_generated_configs(PHASE1_TOPOLOGY, tmp_path)
        compose_file = tmp_path / "docker-compose.arpanet.phase1.yml"

        # Should be valid YAML (skip header comments)
        content = compose_file.read_text()
        # Remove comment lines for YAML parsing
        yaml_content = "\n".join(
            line for line in content.split("\n") if not line.strip().startswith("#")
        )
        config = yaml.safe_load(yaml_content)
        assert config["version"] == "3.8"

    def test_phase2_generates_all_configs(self, tmp_path: Path) -> None:
        """Phase2 should generate configs for IMP1, IMP2, and PDP10."""
        write_generated_configs(PHASE2_TOPOLOGY, tmp_path)

        configs_dir = tmp_path / "arpanet" / "configs" / "phase2"
        assert (configs_dir / "imp1.ini").exists()
        assert (configs_dir / "imp2.ini").exists()
        assert (configs_dir / "pdp10.ini").exists()

    def test_idempotent_generation(self, tmp_path: Path) -> None:
        """Generating twice should produce identical output."""
        # Generate first time
        write_generated_configs(PHASE1_TOPOLOGY, tmp_path)
        compose_file = tmp_path / "docker-compose.arpanet.phase1.yml"
        first_content = compose_file.read_text()

        # Generate second time
        write_generated_configs(PHASE1_TOPOLOGY, tmp_path)
        second_content = compose_file.read_text()

        # Should be identical
        assert first_content == second_content


class TestGeneratedConfigAccuracy:
    """Test generated configs match expected patterns from manual configs."""

    def test_phase1_imp_has_correct_structure(self) -> None:
        """Phase1 IMP config should match expected structure."""
        imp1_host = PHASE1_TOPOLOGY.hosts["imp1"]
        config = generate_simh_config(imp1_host, PHASE1_TOPOLOGY)

        # Check for key configuration commands in order
        lines = config.split("\n")
        config_str = "\n".join(lines)

        # Should load base config
        assert re.search(r"do impconfig\.simh", config_str)
        assert re.search(r"set imp num=1", config_str)
        assert re.search(r"do impcode\.simh", config_str)

        # Should configure HI1 for VAX connection
        assert re.search(r"set hi1 enabled", config_str)
        assert re.search(r"attach -u hi1 2000:172\.20\.0\.10:2000", config_str)

        # Should end with go command
        assert config.strip().endswith("go")

    def test_phase2_pdp10_has_boot_command(self) -> None:
        """Phase2 PDP-10 should have boot command."""
        pdp10_host = PHASE2_TOPOLOGY.hosts["pdp10"]
        config = generate_simh_config(pdp10_host, PHASE2_TOPOLOGY)

        assert "boot tua0" in config

    def test_imp_config_echo_messages(self) -> None:
        """IMP configs should have informative echo messages."""
        imp1_host = PHASE2_TOPOLOGY.hosts["imp1"]
        config = generate_simh_config(imp1_host, PHASE2_TOPOLOGY)

        # Should echo what it's connecting to
        assert re.search(r"echo.*starting", config, re.IGNORECASE)
        assert re.search(r"echo.*connected", config, re.IGNORECASE)
