from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

import arpanet.scripts.test_utils as test_utils


@dataclass
class _FakeContainer:
    name: str = "example"
    attrs: dict[str, object] | None = None
    log_bytes: bytes = b""

    def logs(self, **_kwargs: object) -> bytes:
        return self.log_bytes


class _RaisingContainer:
    def logs(self, **_kwargs: object) -> bytes:
        raise RuntimeError("boom")


def test_get_docker_client_uses_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = object()
    monkeypatch.setattr(test_utils.docker, "from_env", lambda: fake_client)
    assert test_utils.get_docker_client() is fake_client


def test_get_docker_client_exits_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        test_utils.docker,
        "from_env",
        lambda: (_ for _ in ()).throw(RuntimeError("x")),
    )
    with pytest.raises(SystemExit) as exc_info:
        test_utils.get_docker_client()
    assert exc_info.value.code == 1


def test_check_containers_running_true_and_false() -> None:
    client = SimpleNamespace(
        containers=SimpleNamespace(
            list=lambda: [SimpleNamespace(name="arpanet-vax"), SimpleNamespace(name="arpanet-imp1")]
        )
    )
    assert test_utils.check_containers_running(client, ["arpanet-vax", "arpanet-imp1"]) is True
    assert test_utils.check_containers_running(client, ["arpanet-vax", "missing"]) is False


def test_get_container_handles_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    class _NotFound(Exception):
        pass

    monkeypatch.setattr(test_utils.docker.errors, "NotFound", _NotFound)
    client = SimpleNamespace(
        containers=SimpleNamespace(
            get=lambda _name: (_ for _ in ()).throw(_NotFound()),
        )
    )
    assert test_utils.get_container(client, "missing") is None


def test_get_container_ip_success_and_unknown() -> None:
    with_ip = _FakeContainer(
        attrs={
            "NetworkSettings": {
                "Networks": {
                    "arpanet-build": {"IPAddress": "172.20.0.10"},
                }
            }
        }
    )
    assert test_utils.get_container_ip(with_ip) == "172.20.0.10"

    unknown = _FakeContainer(attrs={"NetworkSettings": {"Networks": {}}})
    assert test_utils.get_container_ip(unknown) == "unknown"


def test_get_container_logs_success_and_error() -> None:
    ok = _FakeContainer(log_bytes=b"line1\nline2\n")
    assert "line1" in test_utils.get_container_logs(ok)

    error_text = test_utils.get_container_logs(_RaisingContainer())
    assert "Error getting logs" in error_text


def test_check_logs_for_pattern_regex_and_literal() -> None:
    container = _FakeContainer(log_bytes=b"IMP #1 startup marker\n")
    assert test_utils.check_logs_for_pattern(container, r"IMP #1") is True
    assert test_utils.check_logs_for_pattern(container, "startup", regex=False) is True
    assert test_utils.check_logs_for_pattern(container, "missing", regex=False) is False


def test_check_logs_for_pattern_returns_false_on_error() -> None:
    assert test_utils.check_logs_for_pattern(_RaisingContainer(), "x") is False


def test_fail_with_message_exits() -> None:
    with pytest.raises(SystemExit) as exc_info:
        test_utils.fail_with_message("oops", "do thing")
    assert exc_info.value.code == 1
