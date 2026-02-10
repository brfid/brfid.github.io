from __future__ import annotations

from dataclasses import dataclass

import pytest

import arpanet.scripts.test_phase1 as phase1_script
import arpanet.scripts.test_phase2 as phase2_script
import arpanet.scripts.test_phase2_hi1_framing as phase2_hi1_script


@dataclass
class _FakeContainer:
    name: str


def _silence_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(phase1_script, "print_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(phase1_script, "print_step", lambda *args, **kwargs: None)
    monkeypatch.setattr(phase1_script, "print_success", lambda *args, **kwargs: None)
    monkeypatch.setattr(phase1_script, "print_error", lambda *args, **kwargs: None)
    monkeypatch.setattr(phase1_script, "print_info", lambda *args, **kwargs: None)
    monkeypatch.setattr(phase1_script, "print_next_steps", lambda *args, **kwargs: None)

    monkeypatch.setattr(phase2_script, "print_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(phase2_script, "print_step", lambda *args, **kwargs: None)
    monkeypatch.setattr(phase2_script, "print_success", lambda *args, **kwargs: None)
    monkeypatch.setattr(phase2_script, "print_error", lambda *args, **kwargs: None)
    monkeypatch.setattr(phase2_script, "print_info", lambda *args, **kwargs: None)
    monkeypatch.setattr(phase2_script, "print_next_steps", lambda *args, **kwargs: None)

    monkeypatch.setattr(phase2_hi1_script, "print_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(phase2_hi1_script, "print_step", lambda *args, **kwargs: None)
    monkeypatch.setattr(phase2_hi1_script, "print_success", lambda *args, **kwargs: None)
    monkeypatch.setattr(phase2_hi1_script, "print_error", lambda *args, **kwargs: None)
    monkeypatch.setattr(phase2_hi1_script, "print_info", lambda *args, **kwargs: None)


def test_phase1_main_success_without_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    _silence_output(monkeypatch)

    containers = {
        "arpanet-vax": _FakeContainer(name="arpanet-vax"),
        "arpanet-imp1": _FakeContainer(name="arpanet-imp1"),
    }

    monkeypatch.setattr(phase1_script, "get_docker_client", lambda: object())
    monkeypatch.setattr(
        phase1_script,
        "check_containers_running",
        lambda client, names: True,
    )
    monkeypatch.setattr(phase1_script, "get_container", lambda client, name: containers[name])
    monkeypatch.setattr(phase1_script, "get_container_logs", lambda container, tail=10: "ok")
    monkeypatch.setattr(
        phase1_script,
        "get_container_ip",
        lambda container: "172.20.0.10" if container.name == "arpanet-vax" else "172.20.0.20",
    )

    assert phase1_script.main() == 0


def test_phase1_main_container_check_failure_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    _silence_output(monkeypatch)

    captured: dict[str, str] = {}

    def _fail(message: str, suggestion: str = "") -> None:
        captured["message"] = message
        captured["suggestion"] = suggestion
        raise SystemExit(1)

    monkeypatch.setattr(phase1_script, "get_docker_client", lambda: object())
    monkeypatch.setattr(phase1_script, "check_containers_running", lambda client, names: False)
    monkeypatch.setattr(phase1_script, "fail_with_message", _fail)

    with pytest.raises(SystemExit) as exc_info:
        phase1_script.main()

    assert exc_info.value.code == 1

    assert captured["message"] == "Containers not running"
    assert "docker-compose -f docker-compose.arpanet.phase1.yml up -d" in captured["suggestion"]


def test_phase2_main_success_without_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    _silence_output(monkeypatch)

    containers = {
        "arpanet-vax": _FakeContainer(name="arpanet-vax"),
        "arpanet-imp1": _FakeContainer(name="arpanet-imp1"),
        "arpanet-imp2": _FakeContainer(name="arpanet-imp2"),
        "arpanet-pdp10": _FakeContainer(name="arpanet-pdp10"),
    }

    ip_map = {
        "arpanet-vax": "172.20.0.10",
        "arpanet-imp1": "172.20.0.20",
        "arpanet-imp2": "172.20.0.30",
        "arpanet-pdp10": "172.20.0.40",
    }

    monkeypatch.setattr(phase2_script, "get_docker_client", lambda: object())
    monkeypatch.setattr(phase2_script, "check_containers_running", lambda client, names: True)
    monkeypatch.setattr(phase2_script, "get_container", lambda client, name: containers[name])
    monkeypatch.setattr(phase2_script, "get_container_ip", lambda container: ip_map[container.name])
    monkeypatch.setattr(phase2_script, "check_logs_for_pattern", lambda container, pattern: True)
    monkeypatch.setattr(phase2_script, "get_container_logs", lambda container, tail=20: "ok")

    assert phase2_script.main() == 0


def test_phase2_main_returns_nonzero_when_imp1_markers_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _silence_output(monkeypatch)

    containers = {
        "arpanet-vax": _FakeContainer(name="arpanet-vax"),
        "arpanet-imp1": _FakeContainer(name="arpanet-imp1"),
        "arpanet-imp2": _FakeContainer(name="arpanet-imp2"),
        "arpanet-pdp10": _FakeContainer(name="arpanet-pdp10"),
    }

    monkeypatch.setattr(phase2_script, "get_docker_client", lambda: object())
    monkeypatch.setattr(phase2_script, "check_containers_running", lambda client, names: True)
    monkeypatch.setattr(phase2_script, "get_container", lambda client, name: containers[name])
    monkeypatch.setattr(phase2_script, "get_container_ip", lambda container: "172.20.0.10")
    monkeypatch.setattr(phase2_script, "check_logs_for_pattern", lambda container, pattern: False)

    assert phase2_script.main() == 1


def test_phase2_hi1_main_success_without_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    _silence_output(monkeypatch)

    containers = {
        "arpanet-imp2": _FakeContainer(name="arpanet-imp2"),
        "arpanet-pdp10": _FakeContainer(name="arpanet-pdp10"),
    }

    monkeypatch.setattr(phase2_hi1_script, "get_docker_client", lambda: object())
    monkeypatch.setattr(
        phase2_hi1_script,
        "check_containers_running",
        lambda client, names: True,
    )
    monkeypatch.setattr(
        phase2_hi1_script,
        "get_container",
        lambda client, name: containers[name],
    )
    monkeypatch.setattr(
        phase2_hi1_script,
        "get_container_logs",
        lambda container, tail=10: (
            "HI1 UDP: link 1 - received packet w/bad magic number (magic=feffffff)\n"
            if container.name == "arpanet-imp2"
            else "Eth: opened OS device udp:2000:172.20.0.30:2000\n"
        ),
    )

    artifact_paths: list[str] = []

    monkeypatch.setattr(
        phase2_hi1_script,
        "_artifact_path",
        lambda: phase2_hi1_script.Path("/tmp/fake-hi1-artifact.md"),
    )

    def _fake_write(path, bad_magic_counts, hi1_samples, pdp10_summary_lines):
        artifact_paths.append(str(path))
        assert bad_magic_counts["feffffff"] == 1
        assert hi1_samples
        assert pdp10_summary_lines

    monkeypatch.setattr(phase2_hi1_script, "_write_artifact", _fake_write)

    assert phase2_hi1_script.main() == 0
    assert artifact_paths == ["/tmp/fake-hi1-artifact.md"]


def test_phase2_hi1_main_container_check_failure_exits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _silence_output(monkeypatch)

    captured: dict[str, str] = {}

    def _fail(message: str, suggestion: str = "") -> None:
        captured["message"] = message
        captured["suggestion"] = suggestion
        raise SystemExit(1)

    monkeypatch.setattr(phase2_hi1_script, "get_docker_client", lambda: object())
    monkeypatch.setattr(phase2_hi1_script, "check_containers_running", lambda client, names: False)
    monkeypatch.setattr(phase2_hi1_script, "fail_with_message", _fail)

    with pytest.raises(SystemExit) as exc_info:
        phase2_hi1_script.main()

    assert exc_info.value.code == 1
    assert captured["message"] == "Required containers are not running"
    assert "Not auto-starting" in captured["suggestion"]


def test_phase2_hi1_write_artifact_adds_native_first_hint_for_known_magic(
    tmp_path: pytest.TempPathFactory,
) -> None:
    out_path = tmp_path / "hi1.md"

    phase2_hi1_script._write_artifact(
        out_path,
        bad_magic_counts=phase2_hi1_script.Counter({"feffffff": 2, "00000219": 1}),
        hi1_samples=["HI1 UDP: link 1 - received packet w/bad magic number (magic=feffffff)"],
        pdp10_summary_lines=["Eth: opened OS device udp:2000:172.20.0.30:2000"],
    )

    content = out_path.read_text()
    assert "| `feffffff` | 2 |" in content
    assert "| `00000219` | 1 |" in content
    assert "Prioritize native host-link/header-contract validation" in content


def test_phase2_hi1_write_artifact_without_bad_magic_has_rerun_guidance(
    tmp_path: pytest.TempPathFactory,
) -> None:
    out_path = tmp_path / "hi1-empty.md"

    phase2_hi1_script._write_artifact(
        out_path,
        bad_magic_counts=phase2_hi1_script.Counter(),
        hi1_samples=[],
        pdp10_summary_lines=[],
    )

    content = out_path.read_text()
    assert "No `bad magic` markers detected" in content
    assert "No bad-magic evidence in this capture window" in content
    assert "Prioritize native host-link/header-contract validation" not in content
