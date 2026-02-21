from __future__ import annotations

import struct
import tarfile
import uuid
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any, cast

import pytest
from pytest import MonkeyPatch

from resume_generator.vintage_stage import (
    DockerContext,
    TelnetSession,
    VintageBuildLog,
    VintageStageConfig,
    VintageStagePaths,
    VintageStageRunner,
    _build_tar_bytes,
    _filter_telnet,
    _parse_args,
    _pause,
    _write_simh_tap,
)
from tests.helpers import uuencode_bytes, write_minimal_resume


def test_build_log_renders_with_trailing_newline() -> None:
    log = VintageBuildLog()
    log.add("step one")
    rendered = log.render()
    assert rendered.endswith("\n")
    assert "step one" in rendered


def test_stage_paths_are_stable() -> None:
    paths = VintageStagePaths(repo_root=Path("/repo"), site_dir=Path("site"), build_dir=Path("build"))
    assert paths.vintage_build_dir.as_posix().endswith("build/vintage")
    assert paths.brad_1_path.as_posix().endswith("build/vintage/brad.1")
    assert paths.brad_man_txt_path.as_posix().endswith("site/brad.man.txt")


def test_docker_replay_mode_writes_outputs(tmp_path: Path) -> None:
    resume_path = tmp_path / "resume.yaml"
    write_minimal_resume(resume_path)

    transcript_path = tmp_path / "transcript.log"
    brad_1 = b".TH BRAD 1 \"2026-01-25\" \"brfid.github.io\" \"\"\n.SH NAME\nbrad \\\\- Test\n"
    block = uuencode_bytes(brad_1, filename="brad.1")
    transcript = "\n".join(
        [
            "booting...",
            "<<<BRAD_1_UU_BEGIN>>>",
            block.rstrip("\n"),
            "<<<BRAD_1_UU_END>>>",
        ]
    )
    transcript_path.write_text(transcript, encoding="utf-8")

    runner = VintageStageRunner(
        config=VintageStageConfig(
            resume_path=resume_path,
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
            mode="docker",
            transcript_path=transcript_path,
        ),
        repo_root=Path.cwd(),
    )
    runner.run()

    assert (tmp_path / "build" / "vintage" / "brad.1").exists()
    assert (tmp_path / "site" / "brad.man.txt").exists()
    assert (tmp_path / "site" / "vintage-build.log").exists()
    assert (tmp_path / "site" / "index.html").exists()


def test_run_rejects_unsupported_mode(tmp_path: Path) -> None:
    runner = VintageStageRunner(
        config=VintageStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
            mode="invalid",
        ),
        repo_root=tmp_path,
    )
    with pytest.raises(ValueError, match="Unsupported mode"):
        runner.run()


def test_parse_args_applies_defaults_and_overrides() -> None:
    defaults = _parse_args([])
    assert defaults.resume == "resume.yaml"
    assert defaults.mode == "local"
    assert defaults.docker_timeout == 600

    parsed = _parse_args(["--mode", "docker", "--docker-timeout", "10", "--docker-quick"])
    assert parsed.mode == "docker"
    assert parsed.docker_timeout == 10
    assert parsed.docker_quick is True


def test_parse_args_rejects_invalid_mode() -> None:
    with pytest.raises(SystemExit):
        _parse_args(["--mode", "bad-mode"])


def test_build_tar_bytes_contains_expected_files() -> None:
    payload = _build_tar_bytes([("alpha.txt", b"alpha"), ("beta.bin", b"\x00\x01")])
    with tarfile.open(fileobj=BytesIO(payload), mode="r:") as tf:
        names = tf.getnames()
        assert names == ["alpha.txt", "beta.bin"]
        assert tf.extractfile("alpha.txt").read() == b"alpha"  # type: ignore[union-attr]
        assert tf.extractfile("beta.bin").read() == b"\x00\x01"  # type: ignore[union-attr]


def test_write_simh_tap_writes_record_wrappers(tmp_path: Path) -> None:
    tap_path = tmp_path / "inputs.tap"
    _write_simh_tap(tap_path, b"abcdef", record_size=4)

    data = tap_path.read_bytes()
    cursor = 0

    def _u32() -> int:
        nonlocal cursor
        value = int(struct.unpack("<I", data[cursor : cursor + 4])[0])
        cursor += 4
        return value

    first_len = _u32()
    assert first_len == 4
    assert data[cursor : cursor + 4] == b"abcd"
    cursor += 4
    assert _u32() == 4

    second_len = _u32()
    assert second_len == 2
    assert data[cursor : cursor + 2] == b"ef"
    cursor += 2
    assert _u32() == 2

    assert _u32() == 0
    assert _u32() == 0
    assert _u32() == 0xFFFFFFFF


def test_filter_telnet_negotiation_and_escaped_iac() -> None:
    class _FakeSock:
        def __init__(self) -> None:
            self.sent: list[bytes] = []

        def sendall(self, payload: bytes) -> None:
            self.sent.append(payload)

    sock = _FakeSock()
    stream = bytes([
        255,
        253,
        1,
        255,
        251,
        3,
        ord("A"),
        255,
        255,
        ord("B"),
    ])

    out = _filter_telnet(stream, sock)  # type: ignore[arg-type]
    assert out == b"A\xffB"
    assert sock.sent == [bytes([255, 252, 1]), bytes([255, 254, 3])]


def test_prepare_tape_media_writes_tap_and_updates_ini(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / "vintage" / "machines" / "vax").mkdir(parents=True)
    (repo_root / "vintage" / "machines" / "vax" / "bradman.c").write_text(
        "int main(void){return 0;}\n",
        encoding="utf-8",
    )

    runner = VintageStageRunner(
        config=VintageStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
        ),
        repo_root=repo_root,
    )
    runner.paths.vintage_build_dir.mkdir(parents=True, exist_ok=True)
    runner.paths.resume_vintage_yaml_path.write_text('schemaVersion: "v1"\n', encoding="utf-8")

    simh_cfg_dir = runner.paths.vintage_build_dir / "simh"
    simh_cfg_dir.mkdir(parents=True)
    (simh_cfg_dir / "vax780.ini").write_text(
        "set ts enabled\nset ts0 online\n",
        encoding="utf-8",
    )

    simh_dir = runner.paths.vintage_build_dir / "simh-tape"
    simh_dir.mkdir(parents=True)
    runner._prepare_tape_media(simh_dir)

    assert (simh_dir / "inputs.tap").exists()
    ini_text = (simh_dir / "vax780.ini").read_text(encoding="utf-8")
    assert "attach ts0 /machines/inputs.tap" in ini_text
    assert "set ts0 online" not in ini_text


def test_emit_resume_vintage_yaml_writes_output_and_returns_resume(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    resume_path = tmp_path / "resume.yaml"
    resume_path.write_text("basics: {name: T}\n", encoding="utf-8")

    runner = VintageStageRunner(
        config=VintageStageConfig(
            resume_path=resume_path,
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
        ),
        repo_root=tmp_path,
    )
    runner.paths.vintage_build_dir.mkdir(parents=True, exist_ok=True)

    fake_resume = cast(Any, {"name": "Test"})
    monkeypatch.setattr("resume_generator.vintage_stage.load_resume", lambda _p: fake_resume)

    def _build_vax(_resume: Any, build_date: date) -> dict[str, str]:
        return {"date": str(build_date)}

    monkeypatch.setattr("resume_generator.vintage_stage.build_vintage_resume_v1", _build_vax)
    monkeypatch.setattr(
        "resume_generator.vintage_stage.emit_vintage_yaml",
        lambda _built: 'schemaVersion: "v1"\n',
    )

    log = VintageBuildLog()
    result = runner._emit_resume_vintage_yaml(build_date=date(2026, 2, 8), log=log)

    assert result is fake_resume
    assert runner.paths.resume_vintage_yaml_path.read_text(encoding="utf-8") == 'schemaVersion: "v1"\n'


def test_compile_bradman_raises_when_source_missing(tmp_path: Path) -> None:
    runner = VintageStageRunner(
        config=VintageStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
        ),
        repo_root=tmp_path,
    )

    with pytest.raises(FileNotFoundError, match="Missing source file"):
        runner._compile_bradman(log=VintageBuildLog())


def test_compile_bradman_raises_when_compiler_missing(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    (tmp_path / "vintage" / "machines" / "vax").mkdir(parents=True)
    (tmp_path / "vintage" / "machines" / "vax" / "bradman.c").write_text(
        "int main(void){return 0;}\n",
        encoding="utf-8",
    )

    runner = VintageStageRunner(
        config=VintageStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
        ),
        repo_root=tmp_path,
    )

    monkeypatch.setattr("resume_generator.vintage_stage.shutil.which", lambda _name: None)
    with pytest.raises(RuntimeError, match="No C compiler found"):
        runner._compile_bradman(log=VintageBuildLog())


def test_compile_and_run_commands_are_formed_correctly(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    (tmp_path / "vintage" / "machines" / "vax").mkdir(parents=True)
    (tmp_path / "vintage" / "machines" / "vax" / "bradman.c").write_text(
        "int main(void){return 0;}\n",
        encoding="utf-8",
    )

    runner = VintageStageRunner(
        config=VintageStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
        ),
        repo_root=tmp_path,
    )
    runner.paths.vintage_build_dir.mkdir(parents=True, exist_ok=True)
    runner.paths.resume_vintage_yaml_path.write_text('schemaVersion: "v1"\n', encoding="utf-8")
    runner.paths.contact_json_path.write_text("{}\n", encoding="utf-8")

    monkeypatch.setattr(
        "resume_generator.vintage_stage.shutil.which",
        lambda name: "/usr/bin/cc" if name == "cc" else None,
    )

    calls: list[list[str]] = []

    def _fake_run(command: list[str], **kwargs: Any) -> Any:
        calls.append(command)
        assert kwargs["check"] is True
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        return cast(Any, object())

    monkeypatch.setattr("resume_generator.vintage_stage.subprocess.run", _fake_run)
    log = VintageBuildLog()

    runner._compile_bradman(log=log)
    runner._run_bradman(log=log)
    runner._run_bradman_html(log=log)

    assert calls[0][0] == "/usr/bin/cc"
    assert calls[0][1:3] == ["-O", "-o"]
    assert calls[1][0] == str(runner.paths.bradman_exe_path)
    assert calls[1][1:] == [
        "-i",
        str(runner.paths.resume_vintage_yaml_path),
        "-o",
        str(runner.paths.brad_1_path),
    ]
    assert calls[2][0] == str(runner.paths.bradman_exe_path)
    assert calls[2][1:] == [
        "-i",
        str(runner.paths.contact_json_path),
        "-mode",
        "html",
        "-o",
        str(runner.paths.contact_html_path),
    ]


def test_run_docker_live_raises_when_docker_missing(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    runner = VintageStageRunner(
        config=VintageStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
            mode="docker",
        ),
        repo_root=tmp_path,
    )
    monkeypatch.setattr("resume_generator.vintage_stage.shutil.which", lambda _name: None)
    with pytest.raises(RuntimeError, match="Docker is not available"):
        runner._run_docker_live(resume=cast(Any, {}), log=VintageBuildLog())


def test_run_docker_live_quick_mode_stops_after_log_write(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    runner = VintageStageRunner(
        config=VintageStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
            mode="docker",
            docker_quick=True,
        ),
        repo_root=tmp_path,
    )
    runner.paths.vintage_build_dir.mkdir(parents=True, exist_ok=True)

    flags: dict[str, bool] = {
        "prepared_tape": False,
        "started": False,
        "init_log": False,
        "guest": False,
        "diag": False,
        "stopped": False,
        "wrote_log": False,
    }

    monkeypatch.setattr(
        "resume_generator.vintage_stage.shutil.which",
        lambda name: "/usr/bin/docker" if name == "docker" else None,
    )

    def _prepare_tape_media(_simh_dir: Path) -> None:
        flags["prepared_tape"] = True

    def _start_docker_container(
        *,
        docker_bin: str,
        simh_dir: Path,
        log: VintageBuildLog,
    ) -> DockerContext:
        del simh_dir, log
        flags["started"] = True
        return DockerContext(docker_bin=docker_bin, container_name="fake", host_port=2323)

    def _wait_for_console(*, ctx: DockerContext, log: VintageBuildLog, timeout: int) -> Any:
        del ctx, log, timeout
        return cast(Any, object())

    def _init_console_log() -> None:
        flags["init_log"] = True

    def _prepare_guest_session(_session: Any) -> None:
        flags["guest"] = True

    def _write_diagnostics(_session: Any) -> None:
        flags["diag"] = True

    def _stop_docker_container(_ctx: DockerContext) -> None:
        flags["stopped"] = True

    def _write_build_log(_log: VintageBuildLog) -> None:
        flags["wrote_log"] = True

    monkeypatch.setattr(runner, "_prepare_tape_media", _prepare_tape_media)
    monkeypatch.setattr(runner, "_start_docker_container", _start_docker_container)
    monkeypatch.setattr(runner, "_wait_for_console", _wait_for_console)
    monkeypatch.setattr(runner, "_init_console_log", _init_console_log)
    monkeypatch.setattr(runner, "_prepare_guest_session", _prepare_guest_session)
    monkeypatch.setattr(runner, "_write_diagnostics", _write_diagnostics)
    monkeypatch.setattr(runner, "_stop_docker_container", _stop_docker_container)
    monkeypatch.setattr(runner, "_write_build_log", _write_build_log)
    monkeypatch.setattr(
        runner,
        "_transfer_guest_inputs_tape",
        lambda _session: (_ for _ in ()).throw(AssertionError("transfer should be skipped")),
    )
    monkeypatch.setattr(
        runner,
        "_compile_and_capture",
        lambda _session: (_ for _ in ()).throw(AssertionError("compile should be skipped")),
    )

    runner._run_docker_live(resume=cast(Any, {}), log=VintageBuildLog())

    assert flags == {
        "prepared_tape": True,
        "started": True,
        "init_log": True,
        "guest": True,
        "diag": True,
        "stopped": True,
        "wrote_log": True,
    }


def test_run_docker_live_full_path_runs_transfer_decode_and_render(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    runner = VintageStageRunner(
        config=VintageStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
            mode="docker",
            docker_quick=False,
        ),
        repo_root=tmp_path,
    )
    runner.paths.vintage_build_dir.mkdir(parents=True, exist_ok=True)
    runner.paths.site_dir.mkdir(parents=True, exist_ok=True)

    events: list[str] = []
    monkeypatch.setattr(
        "resume_generator.vintage_stage.shutil.which",
        lambda name: "/usr/bin/docker" if name == "docker" else None,
    )

    def _prepare_tape_media(_simh_dir: Path) -> None:
        events.append("prepare_tape")

    def _start_docker_container(
        *,
        docker_bin: str,
        simh_dir: Path,
        log: VintageBuildLog,
    ) -> DockerContext:
        del simh_dir, log
        events.append(f"start:{docker_bin}")
        return DockerContext(docker_bin=docker_bin, container_name="fake", host_port=2323)

    def _wait_for_console(*, ctx: DockerContext, log: VintageBuildLog, timeout: int) -> Any:
        del ctx, log, timeout
        events.append("wait")
        return cast(Any, object())

    def _init_console_log() -> None:
        events.append("init")

    def _prepare_guest_session(_session: Any) -> None:
        events.append("guest")

    def _write_diagnostics(_session: Any) -> None:
        events.append("diag")

    def _transfer_guest_inputs_tape(_session: Any) -> None:
        events.append("transfer")

    def _compile_and_capture(_session: Any) -> str:
        events.append("capture")
        return "fake transcript"

    def _stop_docker_container(_ctx: DockerContext) -> None:
        events.append("stop")

    def _decode_brad_1_from_transcript(transcript: str) -> bytes:
        assert transcript == "fake transcript"
        events.append("decode")
        return b".TH BRAD 1\n"

    def _compile_bradman(*, log: VintageBuildLog) -> None:
        del log
        events.append("compile_host")

    def _generate_contact_json(*, resume: Any, log: VintageBuildLog) -> None:
        del resume, log
        events.append("contact")

    def _run_bradman_html(*, log: VintageBuildLog) -> None:
        del log
        events.append("html")

    def _render_brad_man_txt(*, log: VintageBuildLog) -> None:
        del log
        events.append("render")

    def _write_build_log(_log: VintageBuildLog) -> None:
        events.append("write_log")

    monkeypatch.setattr(runner, "_prepare_tape_media", _prepare_tape_media)
    monkeypatch.setattr(runner, "_start_docker_container", _start_docker_container)
    monkeypatch.setattr(runner, "_wait_for_console", _wait_for_console)
    monkeypatch.setattr(runner, "_init_console_log", _init_console_log)
    monkeypatch.setattr(runner, "_prepare_guest_session", _prepare_guest_session)
    monkeypatch.setattr(runner, "_write_diagnostics", _write_diagnostics)
    monkeypatch.setattr(runner, "_transfer_guest_inputs_tape", _transfer_guest_inputs_tape)
    monkeypatch.setattr(runner, "_compile_and_capture", _compile_and_capture)
    monkeypatch.setattr(runner, "_stop_docker_container", _stop_docker_container)
    monkeypatch.setattr(runner, "_decode_brad_1_from_transcript", _decode_brad_1_from_transcript)
    monkeypatch.setattr(runner, "_compile_bradman", _compile_bradman)
    monkeypatch.setattr(runner, "_generate_contact_json", _generate_contact_json)
    monkeypatch.setattr(runner, "_run_bradman_html", _run_bradman_html)
    monkeypatch.setattr(runner, "_render_brad_man_txt", _render_brad_man_txt)
    monkeypatch.setattr(runner, "_write_build_log", _write_build_log)
    monkeypatch.setattr(
        "resume_generator.vintage_stage.build_landing_page",
        lambda **_kwargs: events.append("landing"),
    )

    runner._run_docker_live(resume=cast(Any, {"name": "t"}), log=VintageBuildLog())

    assert "transfer" in events
    assert "capture" in events
    assert "decode" in events
    assert "compile_host" in events
    assert "landing" in events
    assert events.index("stop") < events.index("decode")
    assert runner.paths.brad_1_path.exists()


def test_run_docker_live_stops_container_when_wait_fails(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    runner = VintageStageRunner(
        config=VintageStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
            mode="docker",
        ),
        repo_root=tmp_path,
    )
    runner.paths.vintage_build_dir.mkdir(parents=True, exist_ok=True)

    stopped = {"value": False}
    monkeypatch.setattr(
        "resume_generator.vintage_stage.shutil.which",
        lambda name: "/usr/bin/docker" if name == "docker" else None,
    )
    monkeypatch.setattr(runner, "_prepare_tape_media", lambda _simh_dir: None)
    monkeypatch.setattr(
        runner,
        "_start_docker_container",
        lambda **_kwargs: DockerContext(
            docker_bin="/usr/bin/docker",
            container_name="fake",
            host_port=2323,
        ),
    )
    monkeypatch.setattr(runner, "_init_console_log", lambda: None)
    monkeypatch.setattr(
        runner,
        "_wait_for_console",
        lambda **_kwargs: (_ for _ in ()).throw(TimeoutError("boom")),
    )
    monkeypatch.setattr(
        runner,
        "_stop_docker_container",
        lambda _ctx: stopped.__setitem__("value", True),
    )

    with pytest.raises(TimeoutError, match="boom"):
        runner._run_docker_live(resume=cast(Any, {}), log=VintageBuildLog())
    assert stopped["value"] is True


def test_start_docker_container_builds_expected_command(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    runner = VintageStageRunner(
        config=VintageStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
            docker_image="example/image:latest",
        ),
        repo_root=tmp_path,
    )
    simh_dir = tmp_path / "simh"
    simh_dir.mkdir(parents=True)

    monkeypatch.setattr(
        "resume_generator.vintage_stage.uuid.uuid4",
        lambda: uuid.UUID("12345678-1234-5678-1234-567812345678"),
    )
    monkeypatch.setattr("resume_generator.vintage_stage._find_free_port", lambda: 3456)

    called: dict[str, Any] = {}

    def _fake_run(command: list[str], **kwargs: Any) -> Any:
        called["command"] = command
        called["kwargs"] = kwargs
        return cast(Any, object())

    monkeypatch.setattr("resume_generator.vintage_stage.subprocess.run", _fake_run)

    ctx = runner._start_docker_container(
        docker_bin="/usr/bin/docker",
        simh_dir=simh_dir,
        log=VintageBuildLog(),
    )

    assert ctx.container_name == "vintagebsd-12345678"
    assert ctx.host_port == 3456
    assert called["command"] == [
        "/usr/bin/docker",
        "run",
        "--name",
        "vintagebsd-12345678",
        "-d",
        "-p",
        "3456:2323",
        "-v",
        f"{simh_dir}:/machines",
        "example/image:latest",
    ]
    assert called["kwargs"]["check"] is True


def test_stop_docker_container_best_effort(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    runner = VintageStageRunner(
        config=VintageStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
        ),
        repo_root=tmp_path,
    )

    called: dict[str, Any] = {}

    def _fake_run(command: list[str], **kwargs: Any) -> Any:
        called["command"] = command
        called["kwargs"] = kwargs
        return cast(Any, object())

    monkeypatch.setattr("resume_generator.vintage_stage.subprocess.run", _fake_run)

    runner._stop_docker_container(
        DockerContext(docker_bin="/usr/bin/docker", container_name="abc", host_port=2323)
    )

    assert called["command"] == ["/usr/bin/docker", "rm", "-f", "abc"]
    assert called["kwargs"]["check"] is False


def test_container_ip_parses_output_and_validates_non_empty(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = VintageStageRunner(
        config=VintageStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
        ),
        repo_root=tmp_path,
    )

    class _CP:
        def __init__(self, stdout: str) -> None:
            self.stdout = stdout

    monkeypatch.setattr(
        "resume_generator.vintage_stage.subprocess.run",
        lambda *args, **kwargs: _CP("172.20.0.10\n"),
    )
    ip = runner._container_ip(docker_bin="/usr/bin/docker", container_name="abc")
    assert ip == "172.20.0.10"

    monkeypatch.setattr(
        "resume_generator.vintage_stage.subprocess.run",
        lambda *args, **kwargs: _CP("\n"),
    )
    with pytest.raises(RuntimeError, match="Failed to determine container IP"):
        runner._container_ip(docker_bin="/usr/bin/docker", container_name="abc")


def test_compile_and_capture_executes_expected_guest_commands(tmp_path: Path) -> None:
    runner = VintageStageRunner(
        config=VintageStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
        ),
        repo_root=tmp_path,
    )
    runner.paths.vintage_build_dir.mkdir(parents=True, exist_ok=True)
    runner._init_console_log()

    class _FakeSession:
        def __init__(self) -> None:
            self.commands: list[str] = []

        def exec_cmd(self, command: str, timeout: int = 120) -> str:
            del timeout
            self.commands.append(command)
            if "uuencode brad.1" in command:
                return "<<<BRAD_1_UU_BEGIN>>>\nbegin 644 brad.1\n`\nend\n<<<BRAD_1_UU_END>>>"
            return "ok"

    session = _FakeSession()
    transcript = runner._compile_and_capture(cast(Any, session))

    assert session.commands[0] == "cc -O -o bradman bradman.c"
    assert session.commands[1] == "ls -l bradman bradman.c resume.vintage.yaml"
    assert session.commands[2] == "./bradman -i resume.vintage.yaml -o brad.1"
    assert "uuencode brad.1 brad.1" in session.commands[3]
    assert "<<<BRAD_1_UU_BEGIN>>>" in transcript


def test_write_diagnostics_runs_expected_commands_and_sections(tmp_path: Path) -> None:
    runner = VintageStageRunner(
        config=VintageStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
        ),
        repo_root=tmp_path,
    )

    class _FakeSession:
        def __init__(self) -> None:
            self.commands: list[str] = []

        def exec_cmd(self, command: str, timeout: int = 120) -> str:
            del timeout
            self.commands.append(command)
            return f"OUT:{command}"

    logged: list[tuple[str, str]] = []
    session = _FakeSession()
    cast(Any, runner)._append_console_log = lambda section, output: logged.append((section, output))

    runner._write_diagnostics(cast(Any, session))

    expected = [
        ("diag mount", "mount"),
        ("diag ls /", "ls /"),
        ("diag includes", "ls /usr/include/stdarg.h /usr/include/stdlib.h"),
        ("diag printf", "ls /bin/printf /usr/bin/printf"),
        ("diag ed", "ls /bin/ed /usr/bin/ed"),
        ("diag ifconfig", "/etc/ifconfig de0"),
        ("diag netstat", "netstat -rn"),
        ("diag ping", "ls /etc/ping /usr/etc/ping /usr/ucb/ping"),
        ("diag tape dev", "ls /dev/mt* /dev/rmt* /dev/ts* /dev/ht*"),
        ("diag mt", "ls /bin/mt /usr/bin/mt"),
    ]
    assert session.commands == [cmd for _, cmd in expected]
    assert logged == [(section, f"OUT:{cmd}") for section, cmd in expected]


def test_transfer_guest_inputs_tape_selects_working_device(tmp_path: Path) -> None:
    runner = VintageStageRunner(
        config=VintageStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
        ),
        repo_root=tmp_path,
    )

    class _FakeSession:
        def __init__(self) -> None:
            self.commands: list[str] = []

        def exec_cmd(self, command: str, timeout: int = 120) -> str:
            del timeout
            self.commands.append(command)
            if command.startswith("tar tf /dev/rmt12"):
                return "__RC__=1"
            if command.startswith("tar tbf 20 /dev/rmt12"):
                return "__RC__=0"
            if command == "cat /tmp/tar.log":
                return "tar log"
            return "ok"

    logged_sections: list[str] = []
    session = _FakeSession()
    cast(Any, runner)._append_console_log = lambda section, output: logged_sections.append(section)

    runner._transfer_guest_inputs_tape(cast(Any, session))

    assert "/bin/mt -f /dev/rmt12 status" in session.commands
    assert "tar tf /dev/rmt12 > /tmp/tar.log 2>&1; echo __RC__=$?" in session.commands
    assert "tar tbf 20 /dev/rmt12 > /tmp/tar.log 2>&1; echo __RC__=$?" in session.commands
    assert "/bin/mt -f /dev/rmt12 rewind" in session.commands
    assert "tar xvf /dev/rmt12 > /tmp/tar.extract 2>&1; echo __RC__=$?" in session.commands
    assert "ls -l bradman.c resume.vintage.yaml" in session.commands
    assert "/bin/mt -f /dev/rmt0 status" not in session.commands
    assert "tape extract" in logged_sections
    assert "tape ls" in logged_sections


def test_transfer_guest_inputs_tape_raises_when_no_device_works(tmp_path: Path) -> None:
    runner = VintageStageRunner(
        config=VintageStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
        ),
        repo_root=tmp_path,
    )

    class _FakeSession:
        def __init__(self) -> None:
            self.commands: list[str] = []

        def exec_cmd(self, command: str, timeout: int = 120) -> str:
            del timeout
            self.commands.append(command)
            if command.startswith("tar "):
                return "__RC__=1"
            if command == "cat /tmp/tar.log":
                return "probe failed"
            return "ok"

    session = _FakeSession()
    cast(Any, runner)._append_console_log = lambda _section, _output: None

    with pytest.raises(RuntimeError, match="Failed to identify tape device"):
        runner._transfer_guest_inputs_tape(cast(Any, session))

    assert "/bin/mt -f /dev/ht1 status" in session.commands


def test_wait_for_console_raises_if_container_exits(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    runner = VintageStageRunner(
        config=VintageStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
        ),
        repo_root=tmp_path,
    )
    runner.paths.vintage_build_dir.mkdir(parents=True, exist_ok=True)

    class _CP:
        def __init__(self, stdout: str, returncode: int = 0) -> None:
            self.stdout = stdout
            self.returncode = returncode

    calls = {"count": 0}

    def _fake_run(command: list[str], **kwargs: Any) -> Any:
        del kwargs
        calls["count"] += 1
        if "logs" in command:
            return _CP("simh logs", 0)
        return _CP("exited\n", 0)

    ticks = iter([0.0, 0.1, 6.1])
    monkeypatch.setattr("resume_generator.vintage_stage.subprocess.run", _fake_run)
    monkeypatch.setattr("resume_generator.vintage_stage.time.monotonic", lambda: next(ticks))

    with pytest.raises(RuntimeError, match="Docker container exited"):
        runner._wait_for_console(
            ctx=DockerContext(docker_bin="/usr/bin/docker", container_name="c1", host_port=2323),
            log=VintageBuildLog(),
            timeout=30,
        )

    assert calls["count"] == 2


def test_wait_for_console_recovers_after_inspect_failure(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    runner = VintageStageRunner(
        config=VintageStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
            send_timeout=9,
        ),
        repo_root=tmp_path,
    )
    runner.paths.vintage_build_dir.mkdir(parents=True, exist_ok=True)

    class _CP:
        def __init__(self, stdout: str, returncode: int = 0) -> None:
            self.stdout = stdout
            self.returncode = returncode

    def _fake_run(command: list[str], **kwargs: Any) -> Any:
        del kwargs
        if "logs" in command:
            return _CP("boot output", 0)
        return _CP("", 1)

    pauses: list[float] = []

    class _FakeTelnetSession:
        def __init__(self, *, host: str, port: int, log: VintageBuildLog, send_timeout: int) -> None:
            del log
            assert host == "127.0.0.1"
            assert port == 2323
            assert send_timeout == 9

        def wait_for_login(self, timeout: int = 120) -> None:
            assert timeout == 60

    ticks = iter([0.0, 1.0, 6.2, 7.0, 7.1])
    monkeypatch.setattr("resume_generator.vintage_stage.subprocess.run", _fake_run)
    monkeypatch.setattr("resume_generator.vintage_stage.time.monotonic", lambda: next(ticks))
    monkeypatch.setattr("resume_generator.vintage_stage._pause", lambda seconds: pauses.append(seconds))
    monkeypatch.setattr("resume_generator.vintage_stage.TelnetSession", _FakeTelnetSession)

    session = runner._wait_for_console(
        ctx=DockerContext(docker_bin="/usr/bin/docker", container_name="c2", host_port=2323),
        log=VintageBuildLog(),
        timeout=30,
    )

    assert isinstance(session, _FakeTelnetSession)
    assert pauses == [1.0]
    wait_log = (runner.paths.vintage_build_dir / "vintage-wait.log").read_text(encoding="utf-8")
    assert "inspect_failed rc=1" in wait_log


def test_wait_for_console_times_out_when_telnet_never_connects(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    runner = VintageStageRunner(
        config=VintageStageConfig(
            resume_path=tmp_path / "resume.yaml",
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
        ),
        repo_root=tmp_path,
    )
    runner.paths.vintage_build_dir.mkdir(parents=True, exist_ok=True)

    class _FailingTelnetSession:
        def __init__(self, **kwargs: Any) -> None:
            del kwargs
            raise ConnectionError("not ready")

    ticks = iter([0.0, 1.0, 2.0, 3.0])
    monkeypatch.setattr("resume_generator.vintage_stage.time.monotonic", lambda: next(ticks))
    monkeypatch.setattr("resume_generator.vintage_stage.TelnetSession", _FailingTelnetSession)
    monkeypatch.setattr("resume_generator.vintage_stage._pause", lambda _seconds: None)

    with pytest.raises(TimeoutError, match="Timed out waiting for vintage login prompt"):
        runner._wait_for_console(
            ctx=DockerContext(docker_bin="/usr/bin/docker", container_name="c3", host_port=2323),
            log=VintageBuildLog(),
            timeout=2,
        )


def test_telnet_recv_filtered_returns_empty_on_timeout_and_eof() -> None:
    session = cast(Any, object.__new__(TelnetSession))

    class _FakeSock:
        def __init__(self) -> None:
            self.calls = 0

        def recv(self, size: int) -> bytes:
            del size
            self.calls += 1
            if self.calls == 1:
                raise TimeoutError("timed out")
            return b""

    session._sock = _FakeSock()

    assert session._recv_filtered() == b""
    assert session._recv_filtered() == b""


def test_pause_skips_select_for_non_positive(monkeypatch: MonkeyPatch) -> None:
    calls: list[float] = []

    def _fake_select(
        _r: list[Any],
        _w: list[Any],
        _x: list[Any],
        timeout: float,
    ) -> tuple[list[Any], list[Any], list[Any]]:
        calls.append(timeout)
        return ([], [], [])

    monkeypatch.setattr("resume_generator.vintage_stage.select.select", _fake_select)

    _pause(0)
    _pause(-0.5)
    assert calls == []

    _pause(0.25)
    assert calls == [0.25]


def test_filter_telnet_ignores_truncated_iac_sequences() -> None:
    class _FakeSock:
        def sendall(self, payload: bytes) -> None:
            del payload

    sock = _FakeSock()
    assert _filter_telnet(bytes([255]), sock) == b""  # type: ignore[arg-type]
    assert _filter_telnet(bytes([ord("A"), 255, 253]), sock) == b"A"  # type: ignore[arg-type]


def test_telnet_ingest_data_handles_xon_xoff_and_buffer() -> None:
    session = cast(Any, object.__new__(TelnetSession))
    session._flow_paused = False
    session._read_buffer = bytearray()

    session._ingest_data(b"ab\x13cd\x11ef")
    assert session._flow_paused is False
    assert bytes(session._read_buffer) == b"abcdef"


def test_telnet_read_until_uses_prefilled_buffer() -> None:
    session = cast(Any, object.__new__(TelnetSession))
    session._read_buffer = bytearray(b"hello BRAD# tail")

    def _poll_incoming(timeout: float = 0.0) -> bool:
        del timeout
        return False

    session._poll_incoming = _poll_incoming
    result = session._read_until(b"BRAD#", timeout=1)
    assert result.endswith(b"BRAD#")
    assert bytes(session._read_buffer) == b" tail"


def test_telnet_read_until_any_timeout(monkeypatch: MonkeyPatch) -> None:
    session = cast(Any, object.__new__(TelnetSession))
    session._read_buffer = bytearray()

    def _poll_incoming(timeout: float = 0.0) -> bool:
        del timeout
        return False

    session._poll_incoming = _poll_incoming

    ticks = iter([100.0, 100.2, 100.4, 100.6])
    monkeypatch.setattr("resume_generator.vintage_stage.time.time", lambda: next(ticks))

    with pytest.raises(TimeoutError, match="Timed out waiting for one of"):
        session._read_until_any([b"login:", b"#"], timeout=0)


def test_telnet_wait_for_xon_raises_after_send_timeout(monkeypatch: MonkeyPatch) -> None:
    session = cast(Any, object.__new__(TelnetSession))
    session._flow_paused = True
    session._send_timeout = 1

    def _poll_incoming(timeout: float = 0.0) -> bool:
        del timeout
        return False

    session._poll_incoming = _poll_incoming

    ticks = iter([10.0, 10.1, 10.2, 11.5])
    monkeypatch.setattr("resume_generator.vintage_stage.time.monotonic", lambda: next(ticks))

    with pytest.raises(TimeoutError, match="Timed out waiting for XON"):
        session._wait_for_xon()
