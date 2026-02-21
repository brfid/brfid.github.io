from __future__ import annotations

import socket
from typing import Any

import pytest

from test_infra.lib import network_utils


class _FakeSocket:
    def __init__(self, connect_result: int = 1, send_error: Exception | None = None) -> None:
        self.connect_result = connect_result
        self.send_error = send_error
        self.timeout_value: float | int | None = None
        self.closed = False
        self.sent_packets: list[tuple[bytes, tuple[str, int]]] = []

    def settimeout(self, timeout: float | int) -> None:
        self.timeout_value = timeout

    def connect_ex(self, _addr: tuple[str, int]) -> int:
        return self.connect_result

    def sendto(self, data: bytes, addr: tuple[str, int]) -> int:
        if self.send_error is not None:
            raise self.send_error
        self.sent_packets.append((data, addr))
        return len(data)

    def close(self) -> None:
        self.closed = True


def test_check_port_open_true_for_successful_connect(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        network_utils.socket,
        "socket",
        lambda *_args, **_kwargs: _FakeSocket(connect_result=0),
    )
    assert network_utils.check_port_open("127.0.0.1", 80) is True


def test_check_port_open_false_on_socket_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_gaierror(*_args: Any, **_kwargs: Any) -> Any:
        raise socket.gaierror("dns failure")

    monkeypatch.setattr(network_utils.socket, "socket", _raise_gaierror)
    assert network_utils.check_port_open("bad-host", 80) is False


def test_wait_for_port_retries_until_success(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    def _fake_socket(*_args: Any, **_kwargs: Any) -> _FakeSocket:
        calls["count"] += 1
        if calls["count"] < 3:
            return _FakeSocket(connect_result=1)
        return _FakeSocket(connect_result=0)

    monkeypatch.setattr(network_utils.socket, "socket", _fake_socket)

    # Deterministic time progression: each sleep advances 0.2 seconds.
    now = {"t": 0.0}

    def _fake_time() -> float:
        return now["t"]

    def _fake_sleep(seconds: float) -> None:
        now["t"] += seconds

    monkeypatch.setattr(network_utils.time, "time", _fake_time)
    monkeypatch.setattr(network_utils.time, "sleep", _fake_sleep)

    assert network_utils.wait_for_port("127.0.0.1", 2000, timeout=2, check_interval=0.2) is True
    assert calls["count"] == 3


def test_test_udp_connectivity_true_when_send_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeSocket()
    monkeypatch.setattr(network_utils.socket, "socket", lambda *_args, **_kwargs: fake)

    ok = network_utils.test_udp_connectivity("127.0.0.1", 2000)
    assert ok is True
    assert fake.sent_packets == [(b"test", ("127.0.0.1", 2000))]
    assert fake.closed is True


def test_test_udp_connectivity_false_on_os_error(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeSocket(send_error=OSError("network unreachable"))
    monkeypatch.setattr(network_utils.socket, "socket", lambda *_args, **_kwargs: fake)

    ok = network_utils.test_udp_connectivity("127.0.0.1", 2000)
    assert ok is False
