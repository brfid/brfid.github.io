from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from test_infra.lib import docker_utils


def test_check_docker_available_true_on_zero_return(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_run(*_args: Any, **_kwargs: Any) -> Any:
        return type("Result", (), {"returncode": 0})()

    monkeypatch.setattr(docker_utils.subprocess, "run", _fake_run)
    assert docker_utils.check_docker_available() is True


def test_check_docker_available_false_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_run(*_args: Any, **_kwargs: Any) -> Any:
        raise subprocess.TimeoutExpired(cmd="docker info", timeout=5)

    monkeypatch.setattr(docker_utils.subprocess, "run", _fake_run)
    assert docker_utils.check_docker_available() is False


def test_compose_build_uses_expected_command_and_cwd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text("services: {}\n", encoding="utf-8")

    captured: dict[str, Any] = {}

    def _fake_run(cmd: list[str], **kwargs: Any) -> Any:
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return type("Result", (), {"returncode": 0})()

    monkeypatch.setattr(docker_utils.subprocess, "run", _fake_run)

    ok = docker_utils.compose_build(compose_file=compose_file, verbose=True)
    assert ok is True
    assert captured["cmd"] == [
        "docker",
        "compose",
        "-f",
        str(compose_file),
        "build",
        "--progress=plain",
    ]
    assert captured["kwargs"]["cwd"] == compose_file.parent


def test_compose_down_omits_volumes_flag_when_disabled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text("services: {}\n", encoding="utf-8")

    captured: dict[str, Any] = {}

    def _fake_run(cmd: list[str], **kwargs: Any) -> Any:
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return type("Result", (), {"returncode": 0})()

    monkeypatch.setattr(docker_utils.subprocess, "run", _fake_run)

    ok = docker_utils.compose_down(compose_file=compose_file, volumes=False)
    assert ok is True
    assert captured["cmd"] == ["docker", "compose", "-f", str(compose_file), "down"]
    assert captured["kwargs"]["cwd"] == compose_file.parent


def test_container_is_running_matches_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_run(*_args: Any, **_kwargs: Any) -> Any:
        return type("Result", (), {"stdout": "arpanet-vax\n"})()

    monkeypatch.setattr(docker_utils.subprocess, "run", _fake_run)
    assert docker_utils.container_is_running("arpanet-vax") is True
    assert docker_utils.container_is_running("arpanet-imp1") is False


def test_get_container_logs_uses_tail_and_handles_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def _fake_run(cmd: list[str], **_kwargs: Any) -> Any:
        captured["cmd"] = cmd
        return type("Result", (), {"stdout": "line1\nline2\n"})()

    monkeypatch.setattr(docker_utils.subprocess, "run", _fake_run)

    logs = docker_utils.get_container_logs("arpanet-vax", tail=10)
    assert logs == "line1\nline2\n"
    assert captured["cmd"] == ["docker", "logs", "arpanet-vax", "--tail", "10"]

    def _fake_timeout(*_args: Any, **_kwargs: Any) -> Any:
        raise subprocess.TimeoutExpired(cmd="docker logs", timeout=10)

    monkeypatch.setattr(docker_utils.subprocess, "run", _fake_timeout)
    assert docker_utils.get_container_logs("arpanet-vax") == "Failed to retrieve logs (timeout)"
