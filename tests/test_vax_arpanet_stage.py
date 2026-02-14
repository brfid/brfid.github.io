from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from resume_generator.vax_arpanet_stage import VaxArpanetStageRunner
from resume_generator.vax_stage import VaxStageConfig


def test_arpanet_stage_paths_passthrough(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeDelegate:
        def __init__(self, *, config: VaxStageConfig, repo_root: Path) -> None:
            del config, repo_root
            self.paths = SimpleNamespace(
                site_dir=tmp_path / "site",
                repo_root=tmp_path,
                build_dir=tmp_path / "build",
            )

        def run(self) -> None:
            return

    monkeypatch.setattr("resume_generator.vax_arpanet_stage.VaxStageRunner", _FakeDelegate)

    runner = VaxArpanetStageRunner(
        config=VaxStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
        ),
        repo_root=tmp_path,
    )
    assert runner.paths.site_dir == tmp_path / "site"


def test_arpanet_stage_run_writes_scaffold_log(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {
        "delegate_run": 0,
        "start": 0,
        "transfer": 0,
        "collect": 0,
        "stop": 0,
    }

    class _FakeDelegate:
        def __init__(self, *, config: VaxStageConfig, repo_root: Path) -> None:
            del config, repo_root
            site_dir = tmp_path / "site"
            site_dir.mkdir(parents=True, exist_ok=True)
            self.paths = SimpleNamespace(
                site_dir=site_dir,
                repo_root=tmp_path,
                build_dir=tmp_path / "build",
            )

        def run(self) -> None:
            calls["delegate_run"] += 1

    monkeypatch.setattr("resume_generator.vax_arpanet_stage.VaxStageRunner", _FakeDelegate)

    def _start(self: VaxArpanetStageRunner, steps: list[str]) -> None:
        del self
        calls["start"] += 1
        steps.append("network: started (phase2 stack)")

    def _transfer(self: VaxArpanetStageRunner, steps: list[str]) -> None:
        del self
        calls["transfer"] += 1
        steps.append("transfer: executed via docker exec (SIMH automation)")

    def _validate(self: VaxArpanetStageRunner, steps: list[str]) -> None:
        del self
        steps.append("phase2_link_smoke: passed")

    def _collect(self: VaxArpanetStageRunner, steps: list[str]) -> None:
        del self
        calls["collect"] += 1
        steps.append("logs: collected via host_logging CLI (scaffold)")

    def _stop(self: VaxArpanetStageRunner, steps: list[str]) -> None:
        del self
        calls["stop"] += 1
        steps.append("network: stopped")

    monkeypatch.setattr(VaxArpanetStageRunner, "_start_arpanet_network", _start)
    monkeypatch.setattr(VaxArpanetStageRunner, "_validate_phase2_links", _validate)
    monkeypatch.setattr(VaxArpanetStageRunner, "_run_transfer_script", _transfer)
    monkeypatch.setattr(VaxArpanetStageRunner, "_collect_arpanet_logs", _collect)
    monkeypatch.setattr(VaxArpanetStageRunner, "_stop_arpanet_network", _stop)

    runner = VaxArpanetStageRunner(
        config=VaxStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
        ),
        repo_root=tmp_path,
        execute_commands=True,
    )
    runner.run()

    assert calls["delegate_run"] == 1
    assert calls["start"] == 1
    assert calls["transfer"] == 1
    assert calls["collect"] == 1
    assert calls["stop"] == 1

    transfer_log = tmp_path / "site" / "arpanet-transfer.log"
    assert transfer_log.exists()
    text = transfer_log.read_text(encoding="utf-8")
    assert "status: scaffold commands completed" in text
    assert "network: stopped" in text
    assert "phase2_link_smoke: passed" in text
    assert "transfer: executed via docker exec" in text


def test_arpanet_stage_run_writes_failure_status_and_stops(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeDelegate:
        def __init__(self, *, config: VaxStageConfig, repo_root: Path) -> None:
            del config, repo_root
            site_dir = tmp_path / "site"
            site_dir.mkdir(parents=True, exist_ok=True)
            self.paths = SimpleNamespace(
                site_dir=site_dir,
                repo_root=tmp_path,
                build_dir=tmp_path / "build",
            )

        def run(self) -> None:
            return

    stopped = {"value": False}

    def _start(self: VaxArpanetStageRunner, steps: list[str]) -> None:
        del self
        steps.append("network: started")

    def _transfer(self: VaxArpanetStageRunner, steps: list[str]) -> None:
        del self, steps
        raise RuntimeError("transfer boom")

    def _validate(self: VaxArpanetStageRunner, steps: list[str]) -> None:
        del self
        steps.append("phase2_link_smoke: passed")

    def _collect(self: VaxArpanetStageRunner, steps: list[str]) -> None:
        del self, steps
        raise AssertionError("collect should not run after transfer failure")

    def _stop(self: VaxArpanetStageRunner, steps: list[str]) -> None:
        del self
        stopped["value"] = True
        steps.append("network: stopped")

    monkeypatch.setattr("resume_generator.vax_arpanet_stage.VaxStageRunner", _FakeDelegate)
    monkeypatch.setattr(VaxArpanetStageRunner, "_start_arpanet_network", _start)
    monkeypatch.setattr(VaxArpanetStageRunner, "_validate_phase2_links", _validate)
    monkeypatch.setattr(VaxArpanetStageRunner, "_run_transfer_script", _transfer)
    monkeypatch.setattr(VaxArpanetStageRunner, "_collect_arpanet_logs", _collect)
    monkeypatch.setattr(VaxArpanetStageRunner, "_stop_arpanet_network", _stop)

    runner = VaxArpanetStageRunner(
        config=VaxStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
        ),
        repo_root=tmp_path,
        execute_commands=True,
    )

    with pytest.raises(RuntimeError, match="transfer boom"):
        runner.run()

    assert stopped["value"] is True
    transfer_log = tmp_path / "site" / "arpanet-transfer.log"
    text = transfer_log.read_text(encoding="utf-8")
    assert "status: failed" in text
    assert "error: transfer boom" in text
    assert "network: stopped" in text


def test_run_command_uses_subprocess_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeDelegate:
        def __init__(self, *, config: VaxStageConfig, repo_root: Path) -> None:
            del config, repo_root
            self.paths = SimpleNamespace(
                site_dir=tmp_path / "site",
                repo_root=tmp_path,
                build_dir=tmp_path / "build",
            )

        def run(self) -> None:
            return

    monkeypatch.setattr("resume_generator.vax_arpanet_stage.VaxStageRunner", _FakeDelegate)
    captured: dict[str, Any] = {}

    class _CP:
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake_run(command: list[str], **kwargs: Any) -> _CP:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return _CP()

    monkeypatch.setattr("resume_generator.vax_arpanet_stage.subprocess.run", _fake_run)

    runner = VaxArpanetStageRunner(
        config=VaxStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
        ),
        repo_root=tmp_path,
    )

    runner._run_command(["echo", "ok"])

    assert captured["command"] == ["echo", "ok"]
    assert captured["kwargs"]["check"] is True
    assert captured["kwargs"]["capture_output"] is True
    assert captured["kwargs"]["text"] is True


def test_run_transfer_script_executes_docker_commands_and_writes_log(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeDelegate:
        def __init__(self, *, config: VaxStageConfig, repo_root: Path) -> None:
            del config, repo_root
            self.paths = SimpleNamespace(
                site_dir=tmp_path / "site",
                repo_root=tmp_path,
                build_dir=tmp_path / "build",
                vax_build_dir=tmp_path / "build" / "vax",
            )

        def run(self) -> None:
            return

    script_path = (
        tmp_path
        / "arpanet"
        / "scripts"
        / "simh-automation"
        / "authentic-ftp-transfer.ini"
    )
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text("; test script\n", encoding="utf-8")

    monkeypatch.setattr("resume_generator.vax_arpanet_stage.VaxStageRunner", _FakeDelegate)

    commands: list[list[str]] = []

    class _CP:
        def __init__(self, stdout: str = "") -> None:
            self.stdout = stdout

    def _fake_run_command(self: VaxArpanetStageRunner, command: list[str]) -> _CP:
        del self
        commands.append(command)
        if command[1] == "exec":
            return _CP("SIMH EXEC OUTPUT\n")
        return _CP("")

    monkeypatch.setattr(
        VaxArpanetStageRunner,
        "_resolve_executable",
        lambda _s, _p: "/usr/bin/docker",
    )
    monkeypatch.setattr(VaxArpanetStageRunner, "_run_command", _fake_run_command)

    runner = VaxArpanetStageRunner(
        config=VaxStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
        ),
        repo_root=tmp_path,
        execute_commands=True,
    )
    steps: list[str] = []
    runner._run_transfer_script(steps)

    assert commands[0] == [
        "/usr/bin/docker",
        "cp",
        str(script_path),
        "arpanet-vax:/machines/data/arpanet-transfer.ini",
    ]
    assert commands[1] == [
        "/usr/bin/docker",
        "exec",
        "arpanet-vax",
        "/usr/bin/simh-vax",
        "/machines/data/arpanet-transfer.ini",
    ]

    exec_log = tmp_path / "build" / "vax" / "arpanet-transfer-exec.log"
    assert exec_log.read_text(encoding="utf-8") == "SIMH EXEC OUTPUT\n"
    assert any(s.startswith("transfer_output:") for s in steps)


def test_arpanet_stage_defaults_to_dry_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeDelegate:
        def __init__(self, *, config: VaxStageConfig, repo_root: Path) -> None:
            del config, repo_root
            site_dir = tmp_path / "site"
            site_dir.mkdir(parents=True, exist_ok=True)
            self.paths = SimpleNamespace(
                site_dir=site_dir,
                repo_root=tmp_path,
                build_dir=tmp_path / "build",
            )

        def run(self) -> None:
            return

    monkeypatch.setattr("resume_generator.vax_arpanet_stage.VaxStageRunner", _FakeDelegate)
    monkeypatch.setattr(
        VaxArpanetStageRunner,
        "_start_arpanet_network",
        lambda self, steps: (_ for _ in ()).throw(AssertionError("should not execute")),
    )

    runner = VaxArpanetStageRunner(
        config=VaxStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
        ),
        repo_root=tmp_path,
    )
    runner.run()

    text = (tmp_path / "site" / "arpanet-transfer.log").read_text(encoding="utf-8")
    assert "mode: dry-run" in text
    assert "status: command execution skipped" in text


def test_run_transfer_exec_with_retry_succeeds_on_second_attempt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeDelegate:
        def __init__(self, *, config: VaxStageConfig, repo_root: Path) -> None:
            del config, repo_root
            self.paths = SimpleNamespace(
                site_dir=tmp_path / "site",
                repo_root=tmp_path,
                build_dir=tmp_path / "build",
            )

        def run(self) -> None:
            return

    monkeypatch.setattr("resume_generator.vax_arpanet_stage.VaxStageRunner", _FakeDelegate)

    attempts = {"count": 0}

    def _fake_run_command(
        self: VaxArpanetStageRunner,
        command: list[str],
    ) -> subprocess.CompletedProcess[str]:
        del self, command
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise subprocess.CalledProcessError(
                returncode=1,
                cmd=["docker", "exec"],
                output="",
                stderr="connection reset by peer",
            )
        return subprocess.CompletedProcess(args=["docker", "exec"], returncode=0, stdout="ok")

    monkeypatch.setattr(VaxArpanetStageRunner, "_run_command", _fake_run_command)

    runner = VaxArpanetStageRunner(
        config=VaxStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
        ),
        repo_root=tmp_path,
        execute_commands=True,
    )

    steps: list[str] = []
    result = runner._run_transfer_exec_with_retry(["docker", "exec"], steps)

    assert attempts["count"] == 2
    assert result.stdout == "ok"
    assert "transfer_exec_attempt_1: failed (command-failed)" in steps
    assert "transfer_exec_attempt_1: retrying" in steps
    assert "transfer_exec_attempt_2: ok" in steps


def test_run_transfer_exec_with_retry_raises_after_second_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeDelegate:
        def __init__(self, *, config: VaxStageConfig, repo_root: Path) -> None:
            del config, repo_root
            self.paths = SimpleNamespace(
                site_dir=tmp_path / "site",
                repo_root=tmp_path,
                build_dir=tmp_path / "build",
            )

        def run(self) -> None:
            return

    monkeypatch.setattr("resume_generator.vax_arpanet_stage.VaxStageRunner", _FakeDelegate)

    def _always_fail(
        self: VaxArpanetStageRunner,
        command: list[str],
    ) -> subprocess.CompletedProcess[str]:
        del self, command
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=["docker", "exec"],
            output="",
            stderr="no such container: arpanet-vax",
        )

    monkeypatch.setattr(VaxArpanetStageRunner, "_run_command", _always_fail)

    runner = VaxArpanetStageRunner(
        config=VaxStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
        ),
        repo_root=tmp_path,
        execute_commands=True,
    )

    steps: list[str] = []
    with pytest.raises(RuntimeError, match="container-missing"):
        runner._run_transfer_exec_with_retry(["docker", "exec"], steps)

    assert "transfer_exec_attempt_1: failed (container-missing)" in steps
    assert "transfer_exec_attempt_2: failed (container-missing)" in steps


def test_classify_transfer_output_detects_fatal_markers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeDelegate:
        def __init__(self, *, config: VaxStageConfig, repo_root: Path) -> None:
            del config, repo_root
            self.paths = SimpleNamespace(
                site_dir=tmp_path / "site",
                repo_root=tmp_path,
                build_dir=tmp_path / "build",
            )

        def run(self) -> None:
            return

    monkeypatch.setattr("resume_generator.vax_arpanet_stage.VaxStageRunner", _FakeDelegate)

    runner = VaxArpanetStageRunner(
        config=VaxStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
        ),
        repo_root=tmp_path,
    )

    assert runner._classify_transfer_output("") == "empty-output"
    assert (
        runner._classify_transfer_output("SIMH panic: cannot open image")
        == "fatal-marker-detected"
    )
    assert runner._classify_transfer_output("transfer finished cleanly") == "ok"


def test_transfer_script_path_prefers_build_artifact_script(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeDelegate:
        def __init__(self, *, config: VaxStageConfig, repo_root: Path) -> None:
            del config, repo_root
            self.paths = SimpleNamespace(
                site_dir=tmp_path / "site",
                repo_root=tmp_path,
                build_dir=tmp_path / "build",
            )

        def run(self) -> None:
            return

    simh_dir = tmp_path / "arpanet" / "scripts" / "simh-automation"
    simh_dir.mkdir(parents=True, exist_ok=True)
    build_script = simh_dir / "build-artifact-transfer.ini"
    fallback_script = simh_dir / "authentic-ftp-transfer.ini"
    build_script.write_text("; build artifact\n", encoding="utf-8")
    fallback_script.write_text("; fallback\n", encoding="utf-8")

    monkeypatch.setattr("resume_generator.vax_arpanet_stage.VaxStageRunner", _FakeDelegate)

    runner = VaxArpanetStageRunner(
        config=VaxStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
        ),
        repo_root=tmp_path,
    )

    assert runner._transfer_script_path() == build_script


def test_transfer_script_path_falls_back_to_authentic_script(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeDelegate:
        def __init__(self, *, config: VaxStageConfig, repo_root: Path) -> None:
            del config, repo_root
            self.paths = SimpleNamespace(
                site_dir=tmp_path / "site",
                repo_root=tmp_path,
                build_dir=tmp_path / "build",
            )

        def run(self) -> None:
            return

    simh_dir = tmp_path / "arpanet" / "scripts" / "simh-automation"
    simh_dir.mkdir(parents=True, exist_ok=True)
    fallback_script = simh_dir / "authentic-ftp-transfer.ini"
    fallback_script.write_text("; fallback\n", encoding="utf-8")

    monkeypatch.setattr("resume_generator.vax_arpanet_stage.VaxStageRunner", _FakeDelegate)

    runner = VaxArpanetStageRunner(
        config=VaxStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
        ),
        repo_root=tmp_path,
    )

    assert runner._transfer_script_path() == fallback_script


def test_transfer_script_path_raises_when_no_script_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeDelegate:
        def __init__(self, *, config: VaxStageConfig, repo_root: Path) -> None:
            del config, repo_root
            self.paths = SimpleNamespace(
                site_dir=tmp_path / "site",
                repo_root=tmp_path,
                build_dir=tmp_path / "build",
            )

        def run(self) -> None:
            return

    monkeypatch.setattr("resume_generator.vax_arpanet_stage.VaxStageRunner", _FakeDelegate)

    runner = VaxArpanetStageRunner(
        config=VaxStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
        ),
        repo_root=tmp_path,
    )

    with pytest.raises(RuntimeError, match="Missing transfer script"):
        runner._transfer_script_path()


def test_collect_arpanet_logs_includes_pdp10_component(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeDelegate:
        def __init__(self, *, config: VaxStageConfig, repo_root: Path) -> None:
            del config, repo_root
            self.paths = SimpleNamespace(
                site_dir=tmp_path / "site",
                repo_root=tmp_path,
                build_dir=tmp_path / "build",
            )

        def run(self) -> None:
            return

    monkeypatch.setattr("resume_generator.vax_arpanet_stage.VaxStageRunner", _FakeDelegate)

    commands: list[list[str]] = []

    def _fake_run_command(
        self: VaxArpanetStageRunner,
        command: list[str],
    ) -> subprocess.CompletedProcess[str]:
        del self
        commands.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="")

    monkeypatch.setattr(
        VaxArpanetStageRunner,
        "_resolve_executable",
        lambda _s, _p: "/usr/bin/python",
    )
    monkeypatch.setattr(VaxArpanetStageRunner, "_run_command", _fake_run_command)

    runner = VaxArpanetStageRunner(
        config=VaxStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
        ),
        repo_root=tmp_path,
        execute_commands=True,
    )

    steps: list[str] = []
    runner._collect_arpanet_logs(steps)

    assert len(commands) == 1
    cmd = commands[0]
    assert cmd[:4] == ["/usr/bin/python", "-m", "host_logging", "collect"]

    components_idx = cmd.index("--components")
    assert cmd[components_idx + 1 : components_idx + 5] == [
        "vax",
        "imp1",
        "imp2",
        "pdp10",
    ]
    assert "logs: collected via host_logging CLI (scaffold)" in steps


def test_validate_phase2_links_runs_script(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeDelegate:
        def __init__(self, *, config: VaxStageConfig, repo_root: Path) -> None:
            del config, repo_root
            self.paths = SimpleNamespace(
                site_dir=tmp_path / "site",
                repo_root=tmp_path,
                build_dir=tmp_path / "build",
            )

        def run(self) -> None:
            return

    script_path = tmp_path / "arpanet" / "scripts" / "test-phase2-imp-link.sh"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text("#!/bin/bash\n", encoding="utf-8")

    monkeypatch.setattr("resume_generator.vax_arpanet_stage.VaxStageRunner", _FakeDelegate)

    commands: list[list[str]] = []

    def _fake_run_command(
        self: VaxArpanetStageRunner,
        command: list[str],
    ) -> subprocess.CompletedProcess[str]:
        del self
        commands.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="")

    monkeypatch.setattr(
        VaxArpanetStageRunner,
        "_resolve_executable",
        lambda _s, _p: "/bin/bash",
    )
    monkeypatch.setattr(VaxArpanetStageRunner, "_run_command", _fake_run_command)

    runner = VaxArpanetStageRunner(
        config=VaxStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
        ),
        repo_root=tmp_path,
        execute_commands=True,
    )

    steps: list[str] = []
    runner._validate_phase2_links(steps)

    assert commands == [["/bin/bash", str(script_path)]]
    assert "phase2_link_smoke: passed" in steps
