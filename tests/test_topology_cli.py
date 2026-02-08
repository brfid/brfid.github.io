from __future__ import annotations

from pathlib import Path

import pytest

import arpanet.topology.cli as topology_cli


def test_topology_cli_list_prints_available_topologies(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("sys.argv", ["arpanet-topology", "--list"])

    rc = topology_cli.main()
    output = capsys.readouterr().out

    assert rc == 0
    assert "Available topologies:" in output
    assert "phase1" in output
    assert "phase2" in output


def test_topology_cli_requires_topology_or_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["arpanet-topology"])

    with pytest.raises(SystemExit) as exc_info:
        topology_cli.main()

    assert exc_info.value.code == 2


def test_topology_cli_generates_configs_with_selected_topology(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: dict[str, Path] = {}

    def _fake_write_generated_configs(topology: object, output_dir: Path) -> None:
        del topology
        calls["output_dir"] = output_dir

    monkeypatch.setattr(topology_cli, "write_generated_configs", _fake_write_generated_configs)
    monkeypatch.setattr(
        "sys.argv",
        ["arpanet-topology", "phase2", "--output", str(tmp_path)],
    )

    rc = topology_cli.main()

    assert rc == 0
    assert calls["output_dir"] == tmp_path.resolve()


def test_topology_cli_returns_error_when_generation_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _failing_write_generated_configs(topology: object, output_dir: Path) -> None:
        del topology, output_dir
        raise RuntimeError("generation failed")

    monkeypatch.setattr(
        topology_cli,
        "write_generated_configs",
        _failing_write_generated_configs,
    )
    monkeypatch.setattr(
        "sys.argv",
        ["arpanet-topology", "phase1", "--output", str(tmp_path)],
    )

    rc = topology_cli.main()
    captured = capsys.readouterr()

    assert rc == 1
    assert "Error generating topology: generation failed" in captured.err
