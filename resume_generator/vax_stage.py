"""Generate the VAX/SIMH "quiet signal" artifacts.

This module is responsible for producing:
- `build/vax/brad.1` (internal intermediate roff)
- `site/brad.man.txt` (rendered excerpt embedded on the landing page)
- `site/vax-build.log` (muted transcript / provenance log)

It supports a local mode (compile/run `vax/bradman.c` on the host) for quick iteration,
and a future docker/SIMH mode for CI parity.
"""

from __future__ import annotations

import argparse
import select
import shutil
import socket
import struct
import subprocess
import tarfile
import time
import uuid
from dataclasses import dataclass
from datetime import date
from io import BytesIO
from pathlib import Path

from .contact_json import generate_contact_json
from .landing import build_landing_page
from .manpage import parse_brad_roff_summary, render_brad_man_txt
from .render import load_resume
from .types import Resume
from .uudecode import decode_marked_uuencode
from .vax_yaml import build_vax_resume_v1, emit_vax_yaml

DOCKER_IMAGE_DEFAULT = (
    "jguillaumes/simh-vaxbsd@sha256:"
    "1bab805b25a793fd622c29d3e9b677b002cabbdc20d9c42afaeeed542cc42215"
)


@dataclass(frozen=True)
class VaxStagePaths:
    """Commonly used paths for the VAX stage."""

    repo_root: Path
    site_dir: Path
    build_dir: Path

    @property
    def vax_build_dir(self) -> Path:
        """Return the VAX-specific build directory."""
        return self.build_dir / "vax"

    @property
    def resume_vax_yaml_path(self) -> Path:
        """Return the generated ``resume.vax.yaml`` path."""
        return self.vax_build_dir / "resume.vax.yaml"

    @property
    def brad_1_path(self) -> Path:
        """Return the generated ``brad.1`` path."""
        return self.vax_build_dir / "brad.1"

    @property
    def bradman_exe_path(self) -> Path:
        """Return the host-built ``bradman`` executable path."""
        return self.vax_build_dir / "bradman"

    @property
    def brad_man_txt_path(self) -> Path:
        """Return the published ``brad.man.txt`` path."""
        return self.site_dir / "brad.man.txt"

    @property
    def vax_build_log_path(self) -> Path:
        """Return the published ``vax-build.log`` path."""
        return self.site_dir / "vax-build.log"

    @property
    def contact_json_path(self) -> Path:
        """Return the intermediate ``contact.json`` path."""
        return self.vax_build_dir / "contact.json"

    @property
    def contact_html_path(self) -> Path:
        """Return the published ``contact.html`` path."""
        return self.site_dir / "contact.html"


class VaxBuildLog:
    """Small timestamped log for publication as "build evidence"."""

    def __init__(self) -> None:
        """Initialize an empty elapsed-time build log."""
        self._lines: list[str] = []
        self._t0 = time.time()

    def add(self, message: str) -> None:
        """Add a log line with elapsed seconds."""
        elapsed = time.time() - self._t0
        self._lines.append(f"[+{elapsed:0.2f}s] {message}".rstrip())

    def render(self) -> str:
        """Render the build log as LF-only text with a trailing newline."""
        return "\n".join(self._lines).rstrip() + "\n"


# pylint: disable=too-many-instance-attributes
@dataclass(frozen=True)
class VaxStageConfig:
    """Configuration for running the VAX stage."""

    resume_path: Path
    site_dir: Path
    build_dir: Path = Path("build")
    mode: str = "local"
    transcript_path: Path | None = None
    docker_timeout: int = 600
    send_timeout: int = 180
    docker_quick: bool = False
    docker_image: str = DOCKER_IMAGE_DEFAULT


@dataclass(frozen=True)
class DockerContext:
    """Metadata for a running SIMH Docker container."""

    docker_bin: str
    container_name: str
    host_port: int


class VaxStageRunner:
    """Runs the VAX stage in local or docker mode."""

    def __init__(self, *, config: VaxStageConfig, repo_root: Path) -> None:
        """Initialize a VAX stage runner.

        Args:
            config: Stage configuration.
            repo_root: Repository root path.
        """
        self._config = config
        self._paths = VaxStagePaths(
            repo_root=repo_root,
            site_dir=config.site_dir,
            build_dir=config.build_dir,
        )

    @property
    def paths(self) -> VaxStagePaths:
        """Paths used by the runner (useful for callers/tests)."""
        return self._paths

    def run(self) -> None:
        """Run the configured VAX stage."""
        self._paths.vax_build_dir.mkdir(parents=True, exist_ok=True)
        self._paths.site_dir.mkdir(parents=True, exist_ok=True)

        if self._config.mode == "local":
            self._run_local()
            return
        if self._config.mode == "docker":
            self._run_docker()
            return
        raise ValueError(f"Unsupported mode: {self._config.mode!r}")

    def _emit_resume_vax_yaml(self, *, build_date: date, log: VaxBuildLog) -> Resume:
        log.add(f"[1/7] Generate resume.vax.yaml from {self._config.resume_path}")
        resume = load_resume(self._config.resume_path)
        built = build_vax_resume_v1(resume, build_date=build_date)
        text = emit_vax_yaml(built)
        self._paths.resume_vax_yaml_path.write_text(text, encoding="utf-8")
        log.add(f"      Written: {self._paths.resume_vax_yaml_path}")
        return resume

    def _compile_bradman(self, *, log: VaxBuildLog) -> None:
        bradman_c = self._paths.repo_root / "vax" / "bradman.c"
        if not bradman_c.exists():
            raise FileNotFoundError(f"Missing source file: {bradman_c}")

        compiler = shutil.which("cc") or shutil.which("clang") or shutil.which("gcc")
        if not compiler:
            raise RuntimeError("No C compiler found (expected one of: cc, clang, gcc)")

        log.add("[2/7] Compile vax/bradman.c (HTML and man page generator)")
        log.add(f"      Compiler: {Path(compiler).name}")
        subprocess.run(  # noqa: S603
            [compiler, "-O", "-o", str(self._paths.bradman_exe_path), str(bradman_c)],
            check=True,
            capture_output=True,
            text=True,
        )
        log.add(f"      Binary: {self._paths.bradman_exe_path}")

    def _run_bradman(self, *, log: VaxBuildLog) -> None:
        log.add("[3/7] Generate brad.1 roff man page")
        log.add(f"      Input: {self._paths.resume_vax_yaml_path.name}")
        subprocess.run(  # noqa: S603
            [
                str(self._paths.bradman_exe_path),
                "-i",
                str(self._paths.resume_vax_yaml_path),
                "-o",
                str(self._paths.brad_1_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        log.add(f"      Output: {self._paths.brad_1_path}")

    def _generate_contact_json(self, *, resume: Resume, log: VaxBuildLog) -> None:
        log.add("[4/7] Generate contact.json (simplified for VAX HTML rendering)")
        generate_contact_json(resume=resume, out_path=self._paths.contact_json_path)
        log.add(f"      Output: {self._paths.contact_json_path}")

    def _run_bradman_html(self, *, log: VaxBuildLog) -> None:
        log.add("[5/7] Generate contact.html (VAX-rendered HTML fragment)")
        log.add(f"      Input: {self._paths.contact_json_path.name}")
        subprocess.run(  # noqa: S603
            [
                str(self._paths.bradman_exe_path),
                "-i",
                str(self._paths.contact_json_path),
                "-mode",
                "html",
                "-o",
                str(self._paths.contact_html_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        log.add(f"      Output: {self._paths.contact_html_path}")

    def _run_host_postprocess(self, *, resume: Resume, log: VaxBuildLog) -> None:
        """Run host-side post-processing: compile bradman, generate HTML fragment and man txt."""
        self._compile_bradman(log=log)
        self._generate_contact_json(resume=resume, log=log)
        self._run_bradman_html(log=log)
        self._render_brad_man_txt(log=log)

    def _render_brad_man_txt(self, *, log: VaxBuildLog) -> None:
        log.add("[6/7] Render brad.man.txt (man page text for reference)")
        log.add("      Parser: Python roff subset (host-side)")
        roff = self._paths.brad_1_path.read_text(encoding="utf-8")
        summary = parse_brad_roff_summary(roff)
        rendered = render_brad_man_txt(summary)
        self._paths.brad_man_txt_path.write_text(rendered, encoding="utf-8")
        log.add(f"      Output: {self._paths.brad_man_txt_path}")

    def _write_build_log(self, log: VaxBuildLog) -> None:
        self._paths.vax_build_log_path.write_text(log.render(), encoding="utf-8")

    def _run_local(self) -> None:
        log = VaxBuildLog()
        log.add("=" * 70)
        log.add("VAX RESUME BUILD PIPELINE")
        log.add("=" * 70)
        log.add("")
        log.add("Repository: https://github.com/brfid/brfid.github.io")
        log.add(f"Build Date: {date.today().isoformat()}")
        log.add("")
        log.add("BUILD MODE: Local (Fast Development Mode)")
        log.add("━" * 70)
        log.add("Platform:   Host machine (native C compiler)")
        log.add("Purpose:    Quick iteration without VAX emulation")
        log.add("Compiler:   Modern C compiler (not K&R)")
        log.add("Authentic:  No - compiled on host, not 4.3BSD VAX")
        log.add("")
        log.add("PIPELINE STAGES")
        log.add("━" * 70)
        resume = self._emit_resume_vax_yaml(build_date=date.today(), log=log)
        self._compile_bradman(log=log)
        self._run_bradman(log=log)
        self._generate_contact_json(resume=resume, log=log)
        self._run_bradman_html(log=log)
        self._render_brad_man_txt(log=log)
        log.add("[7/7] Render landing page")
        log.add(f"      Output: {self._paths.site_dir / 'index.html'}")
        log.add("")
        log.add("=" * 70)
        log.add("✅ BUILD COMPLETE - All artifacts generated")
        log.add("=" * 70)
        self._write_build_log(log)
        build_landing_page(
            resume=resume,
            out_dir=self._paths.site_dir,
            templates_dir=self._paths.repo_root / "templates",
        )

    def _run_docker(self) -> None:
        log = VaxBuildLog()
        log.add("=" * 70)
        log.add("VAX RESUME BUILD PIPELINE")
        log.add("=" * 70)
        log.add("")
        log.add("Repository: https://github.com/brfid/brfid.github.io")
        log.add(f"Build Date: {date.today().isoformat()}")
        log.add("")
        log.add("BUILD MODE: Docker/SIMH (Authentic VAX Emulation)")
        log.add("━" * 70)
        log.add("Platform:   SIMH VAX 11/780 Emulator")
        log.add("OS:         4.3BSD UNIX (1986)")
        log.add("Compiler:   K&R C (pre-ANSI)")
        log.add("Authentic:  Yes - running actual 4.3BSD VAX emulation")
        log.add("Transfer:   TS11 tape drive emulation")
        log.add("")
        log.add("PIPELINE STAGES")
        log.add("━" * 70)

        resume = self._emit_resume_vax_yaml(build_date=date.today(), log=log)

        if self._config.transcript_path:
            log.add(f"[2/7] Replay mode: {self._config.transcript_path}")
            transcript = self._config.transcript_path.read_text(encoding="utf-8")
            brad_1_bytes = self._decode_brad_1_from_transcript(transcript)
            self._paths.brad_1_path.write_bytes(brad_1_bytes)
            log.add(f"      Decoded: {self._paths.brad_1_path}")

            # Generate HTML fragment using host-compiled bradman
            log.add("[3/7] Compile bradman (host-side for HTML generation)")
            self._run_host_postprocess(resume=resume, log=log)

            log.add("[7/7] Render landing page")
            log.add(f"      Output: {self._paths.site_dir / 'index.html'}")
            log.add("")
            log.add("Build complete - all artifacts generated")
            self._write_build_log(log)
            build_landing_page(
                resume=resume,
                out_dir=self._paths.site_dir,
                templates_dir=self._paths.repo_root / "templates",
            )
            return

        self._run_docker_live(resume=resume, log=log)

    def _decode_brad_1_from_transcript(self, transcript: str) -> bytes:
        """Decode `brad.1` bytes from a transcript region."""
        res = decode_marked_uuencode(
            transcript,
            begin_marker="<<<BRAD_1_UU_BEGIN>>>",
            end_marker="<<<BRAD_1_UU_END>>>",
        )
        return res.data

    def _run_docker_live(self, *, resume: Resume, log: VaxBuildLog) -> None:
        docker_bin = shutil.which("docker")
        if not docker_bin:
            raise RuntimeError("Docker is not available; install Docker or use --transcript")

        simh_dir_name = "simh-tape"
        simh_dir = (self._paths.vax_build_dir / simh_dir_name).resolve()
        simh_dir.mkdir(parents=True, exist_ok=True)
        self._prepare_tape_media(simh_dir)

        context = self._start_docker_container(
            docker_bin=docker_bin,
            simh_dir=simh_dir,
            log=log,
        )
        try:
            self._init_console_log()
            session = self._wait_for_console(
                ctx=context,
                log=log,
                timeout=self._config.docker_timeout,
            )
            self._prepare_guest_session(session)
            self._write_diagnostics(session)
            if self._config.docker_quick:
                log.add("      Quick mode: skipping transfer/compile")
                transcript = ""
            else:
                log.add("[3/7] Transfer sources to VAX via tape")
                log.add("      Files: bradman.c, resume.vax.yaml")
                self._transfer_guest_inputs_tape(session)
                log.add("[4/7] Compile and run bradman on VAX")
                log.add("      Compiler: cc (VAX BSD)")
                transcript = self._compile_and_capture(session)
        finally:
            self._stop_docker_container(context)

        if self._config.docker_quick:
            self._write_build_log(log)
            return

        brad_1_bytes = self._decode_brad_1_from_transcript(transcript)
        self._paths.brad_1_path.write_bytes(brad_1_bytes)
        log.add(f"      Decoded: {self._paths.brad_1_path}")

        # Generate HTML fragment using host-compiled bradman
        log.add("[5/7] Compile bradman (host-side for HTML generation)")
        self._run_host_postprocess(resume=resume, log=log)

        log.add("[7/7] Render landing page")
        log.add(f"      Output: {self._paths.site_dir / 'index.html'}")
        log.add("")
        log.add("Build complete - all artifacts generated")
        self._write_build_log(log)
        build_landing_page(
            resume=resume,
            out_dir=self._paths.site_dir,
            templates_dir=self._paths.repo_root / "templates",
        )

    def _start_docker_container(
        self,
        *,
        docker_bin: str,
        simh_dir: Path,
        log: VaxBuildLog,
    ) -> DockerContext:
        container_name = f"vaxbsd-{uuid.uuid4().hex[:8]}"
        host_port = _find_free_port()

        log.add("[2/5] Start SIMH VAX/BSD container")
        log.add(f"      Image: {self._config.docker_image.split('@')[0]}")
        log.add(f"      Container: {container_name}")
        log.add(f"      Port: {host_port}")
        subprocess.run(  # noqa: S603
            [
                docker_bin,
                "run",
                "--name",
                container_name,
                "-d",
                "-p",
                f"{host_port}:2323",
                "-v",
                f"{simh_dir}:/machines",
                self._config.docker_image,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return DockerContext(
            docker_bin=docker_bin,
            container_name=container_name,
            host_port=host_port,
        )

    def _stop_docker_container(self, ctx: DockerContext) -> None:
        subprocess.run(  # noqa: S603
            [ctx.docker_bin, "rm", "-f", ctx.container_name],
            check=False,
            capture_output=True,
            text=True,
        )

    def _init_console_log(self) -> None:
        (self._paths.vax_build_dir / "vax-console.log").write_text(
            "[session]\n",
            encoding="utf-8",
        )

    def _append_console_log(self, section: str, output: str) -> None:
        log_path = self._paths.vax_build_dir / "vax-console.log"
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(f"\n[{section}]\n")
            fh.write(output)

    def _prepare_guest_session(self, session: TelnetSession) -> None:
        session.login_root()
        session.ensure_shell_prompt()
        session.exec_cmd("cd /tmp")
        session.exec_cmd("pwd")

    def _write_diagnostics(self, session: TelnetSession) -> None:
        diagnostics = {
            "diag mount": "mount",
            "diag ls /": "ls /",
            "diag includes": "ls /usr/include/stdarg.h /usr/include/stdlib.h",
            "diag printf": "ls /bin/printf /usr/bin/printf",
            "diag ed": "ls /bin/ed /usr/bin/ed",
            "diag ifconfig": "/etc/ifconfig de0",
            "diag netstat": "netstat -rn",
            "diag ping": "ls /etc/ping /usr/etc/ping /usr/ucb/ping",
            "diag tape dev": "ls /dev/mt* /dev/rmt* /dev/ts* /dev/ht*",
            "diag mt": "ls /bin/mt /usr/bin/mt",
        }
        for section, command in diagnostics.items():
            output = session.exec_cmd(command)
            self._append_console_log(section, output)

    def _transfer_guest_inputs_tape(self, session: TelnetSession) -> None:
        session.exec_cmd("cd /tmp")
        candidates = [
            "/dev/rmt12",
            "/dev/rmt0",
            "/dev/mt12",
            "/dev/mt0",
            "/dev/ts0",
            "/dev/ts1",
            "/dev/ht0",
            "/dev/ht1",
        ]
        selected: str | None = None
        for dev in candidates:
            status_output = session.exec_cmd(f"/bin/mt -f {dev} status", timeout=60)
            self._append_console_log(f"tape status {dev}", status_output)
            rewind_output = session.exec_cmd(f"/bin/mt -f {dev} rewind; echo $?", timeout=60)
            self._append_console_log(f"tape rewind {dev}", rewind_output)
            commands = [
                f"tar tf {dev}",
                f"tar tbf 20 {dev}",
                f"tar tbf20 {dev}",
                f"tar tfb20 {dev}",
            ]
            for cmd in commands:
                output = session.exec_cmd(
                    f"{cmd} > /tmp/tar.log 2>&1; echo __RC__=$?",
                    timeout=120,
                )
                self._append_console_log(f"tape probe {dev} {cmd}", output)
                log_output = session.exec_cmd("cat /tmp/tar.log")
                self._append_console_log(f"tape log {dev} {cmd}", log_output)
                rc: int | None = None
                for line in output.splitlines():
                    if line.startswith("__RC__="):
                        try:
                            rc = int(line.split("=", 1)[1].strip())
                        except ValueError:
                            rc = None
                if rc == 0:
                    selected = dev
                    break
            if selected:
                break
        if not selected:
            raise RuntimeError("Failed to identify tape device for tar")
        session.exec_cmd(f"/bin/mt -f {selected} rewind")
        extract_output = session.exec_cmd(
            f"tar xvf {selected} > /tmp/tar.extract 2>&1; echo __RC__=$?",
            timeout=300,
        )
        self._append_console_log("tape extract", extract_output)
        ls_output = session.exec_cmd("ls -l bradman.c resume.vax.yaml")
        self._append_console_log("tape ls", ls_output)

    def _prepare_tape_media(self, simh_dir: Path) -> None:
        tap_path = simh_dir / "inputs.tap"
        tar_bytes = _build_tar_bytes(
            [
                ("bradman.c", (self._paths.repo_root / "vax" / "bradman.c").read_bytes()),
                ("resume.vax.yaml", self._paths.resume_vax_yaml_path.read_bytes()),
            ]
        )
        _write_simh_tap(tap_path, tar_bytes)
        ini_path = simh_dir / "vax780.ini"
        if not ini_path.exists():
            for candidate in (self._paths.vax_build_dir / "simh" / "vax780.ini",):
                if candidate.exists():
                    ini_path.write_text(candidate.read_text(encoding="utf-8"), encoding="utf-8")
                    break
        if not ini_path.exists():
            return
        text = ini_path.read_text(encoding="utf-8")
        updated = False
        if "attach ts0" not in text:
            text = text.replace(
                "set ts enabled",
                "set ts enabled\nattach ts0 /machines/inputs.tap",
            )
            updated = True
        if "set ts0 online" in text:
            text = text.replace("set ts0 online\n", "")
            text = text.replace("\nset ts0 online", "")
            updated = True
        if updated:
            ini_path.write_text(text, encoding="utf-8")

    def _container_ip(self, *, docker_bin: str, container_name: str) -> str:
        result = subprocess.run(  # noqa: S603
            [
                docker_bin,
                "inspect",
                "-f",
                "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
                container_name,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        ip = result.stdout.strip()
        if not ip:
            raise RuntimeError("Failed to determine container IP")
        return ip

    def _compile_and_capture(self, session: TelnetSession) -> str:
        compile_output = session.exec_cmd("cc -O -o bradman bradman.c", timeout=600)
        self._append_console_log("compile", compile_output)
        stat_output = session.exec_cmd("ls -l bradman bradman.c resume.vax.yaml")
        self._append_console_log("ls", stat_output)
        run_output = session.exec_cmd("./bradman -i resume.vax.yaml -o brad.1")
        self._append_console_log("bradman", run_output)
        output = session.exec_cmd(
            "echo '<<<BRAD_1_UU_BEGIN>>>'; uuencode brad.1 brad.1; echo '<<<BRAD_1_UU_END>>>'"
        )
        self._append_console_log("uuencode", output)
        return output

    def _wait_for_console(
        self,
        *,
        ctx: DockerContext,
        log: VaxBuildLog,
        timeout: int = 600,
    ) -> TelnetSession:
        """Wait for the VAX console to reach a login prompt and return a session."""
        wait_log_path = self._paths.vax_build_dir / "vax-wait.log"
        wait_log_path.write_text(f"wait_for_console timeout={timeout}\n", encoding="utf-8")

        start = time.monotonic()
        deadline = start + timeout
        last_log_check = 0.0
        while time.monotonic() < deadline:
            now = time.monotonic()
            if now - last_log_check > 5:
                last_log_check = now
                logs = subprocess.run(  # noqa: S603
                    [ctx.docker_bin, "logs", ctx.container_name, "--tail", "200"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                status = subprocess.run(  # noqa: S603
                    [ctx.docker_bin, "inspect", "-f", "{{.State.Status}}", ctx.container_name],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if status.returncode != 0:
                    with wait_log_path.open("a", encoding="utf-8") as fh:
                        fh.write(f"t+{now - start:0.1f}s inspect_failed rc={status.returncode}\n")
                    _pause(1.0)
                    continue
                if status.stdout.strip() == "exited":
                    raise RuntimeError("Docker container exited before login prompt")
                with wait_log_path.open("a", encoding="utf-8") as fh:
                    fh.write(
                        f"t+{now - start:0.1f}s logs_tail_len={len(logs.stdout)} "
                        f"status={status.stdout.strip()}\n"
                    )

            try:
                session = TelnetSession(
                    host="127.0.0.1",
                    port=ctx.host_port,
                    log=log,
                    send_timeout=self._config.send_timeout,
                )
                session.wait_for_login(timeout=60)
                return session
            except (ConnectionError, TimeoutError, OSError):
                _pause(1.0)
                continue

        raise TimeoutError("Timed out waiting for VAX login prompt")


class TelnetSession:
    """Minimal telnet session helper for SIMH console control."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        log: VaxBuildLog,
        send_timeout: int = 180,
    ) -> None:
        """Initialize a telnet session to the SIMH console.

        Args:
            host: Console host.
            port: Console port.
            log: Build log sink.
            send_timeout: Max seconds to wait for XON flow-control resume.
        """
        self._log = log
        self._sock = socket.create_connection((host, port), timeout=10)
        self._sock.settimeout(5)
        self._prompt = b"BRAD#"
        self._send_timeout = send_timeout
        self._read_buffer = bytearray()
        self._flow_paused = False
        self._log.add("telnet connected")

    def wait_for_login(self, timeout: int = 120) -> None:
        """Wait until the BSD login prompt is visible.

        Args:
            timeout: Max seconds to wait.
        """
        self._send_line("")
        self._read_until(b"login:", timeout=timeout)

    def login_root(self, timeout: int = 60) -> None:
        """Authenticate as ``root`` and wait for a shell prompt.

        Args:
            timeout: Max seconds per prompt wait.
        """
        for _ in range(3):
            self._send_line("root")
            output = self._read_until_any(
                [b"Password:", b"#", b"$", b"login:"],
                timeout=timeout,
            )
            if b"Password:" in output:
                self._send_line("")
                self._read_until_any([b"#", b"$"], timeout=timeout)
                return
            if b"#" in output or b"$" in output:
                return
            if b"login:" in output:
                continue
        raise RuntimeError("Login failed; received login prompt again")

    def ensure_shell_prompt(self) -> None:
        """Normalize to a deterministic shell prompt."""
        self._send_line("sh")
        self._read_until_any([b"#", b"$"], timeout=30)
        self._send_line("PS1='BRAD# '")
        self._read_until(self._prompt, timeout=30)

    def exec_cmd(self, command: str, timeout: int = 120) -> str:
        """Execute one command and return captured terminal output.

        Args:
            command: Shell command line.
            timeout: Max seconds to wait for the prompt.

        Returns:
            Decoded command output including echoed content.
        """
        self._drain()
        self._read_buffer.clear()
        self._send_line(command)
        output = self._read_until(self._prompt, timeout=timeout)
        return output.decode("utf-8", errors="ignore")

    def _send(self, data: bytes) -> None:
        self._sock.sendall(data)

    def _interrupt(self) -> None:
        self._send(b"\x03")

    def _recover_prompt(self, timeout: int = 10) -> None:
        self._send(b"\r\n")
        self._send(b"\x04")
        self._send(b"\r\n")
        try:
            self._read_until_any([self._prompt, b"# ", b"$ "], timeout=timeout)
        except TimeoutError:
            self._interrupt()
            self._read_until_any([self._prompt, b"# ", b"$ "], timeout=timeout)

    def _send_bytes_throttled(
        self,
        data: bytes,
        *,
        chunk_size: int = 128,
        delay: float = 0.05,
    ) -> None:
        for idx in range(0, len(data), chunk_size):
            self._wait_for_xon()
            self._send(data[idx : idx + chunk_size])
            self._poll_incoming(timeout=delay)

    def _send_line(self, line: str) -> None:
        self._wait_for_xon()
        self._send(line.encode() + b"\r\n")
        self._poll_incoming()

    def _drain(self, max_reads: int = 50) -> None:
        for _ in range(max_reads):
            if not self._poll_incoming(timeout=0.05):
                break

    def _poll_incoming(self, timeout: float = 0.0) -> bool:
        readable, _, _ = select.select([self._sock], [], [], timeout)
        if not readable:
            return False
        data = self._recv_filtered()
        if data:
            self._ingest_data(data)
            return True
        return False

    def _ingest_data(self, data: bytes) -> None:
        if b"\x13" in data:
            self._flow_paused = True
        if b"\x11" in data:
            self._flow_paused = False
        cleaned = data.replace(b"\x13", b"").replace(b"\x11", b"")
        if cleaned:
            self._read_buffer.extend(cleaned)

    def _wait_for_xon(self) -> None:
        start = time.monotonic()
        while self._flow_paused:
            self._poll_incoming(timeout=0.1)
            if time.monotonic() - start > self._send_timeout:
                raise TimeoutError("Timed out waiting for XON")

    def _read_until(self, needle: bytes, timeout: int) -> bytes:
        return self._read_until_any([needle], timeout=timeout)

    def _read_until_any(self, needles: list[bytes], timeout: int) -> bytes:
        end_time = time.time() + timeout
        buf = bytearray()
        if self._read_buffer:
            buf.extend(self._read_buffer)
            self._read_buffer.clear()
        while time.time() < end_time:
            for needle in needles:
                idx = buf.find(needle)
                if idx != -1:
                    end = idx + len(needle)
                    result = bytes(buf[:end])
                    self._read_buffer.extend(buf[end:])
                    return result
            if self._poll_incoming(timeout=0.1):
                buf.extend(self._read_buffer)
                self._read_buffer.clear()
        raise TimeoutError(f"Timed out waiting for one of: {needles!r}")

    def _recv_filtered(self) -> bytes:
        try:
            data = self._sock.recv(4096)
        except TimeoutError:
            return b""
        if not data:
            return b""
        return _filter_telnet(data, self._sock)


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _pause(seconds: float) -> None:
    if seconds <= 0:
        return
    select.select([], [], [], seconds)


def _filter_telnet(data: bytes, sock: socket.socket) -> bytes:
    iac = 255
    do = 253
    dont = 254
    will = 251
    wont = 252

    out = bytearray()
    i = 0
    while i < len(data):
        byte = data[i]
        if byte == iac:
            if i + 1 >= len(data):
                break
            cmd = data[i + 1]
            if cmd == iac:
                out.append(iac)
                i += 2
                continue
            if i + 2 >= len(data):
                break
            opt = data[i + 2]
            if cmd == do:
                sock.sendall(bytes([iac, wont, opt]))
            elif cmd == will:
                sock.sendall(bytes([iac, dont, opt]))
            i += 3
            continue
        out.append(byte)
        i += 1
    return bytes(out)


def _build_tar_bytes(files: list[tuple[str, bytes]]) -> bytes:
    buffer = BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for name, data in files:
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tar.addfile(info, BytesIO(data))
    return buffer.getvalue()


def _write_simh_tap(path: Path, payload: bytes, *, record_size: int = 10240) -> None:
    with path.open("wb") as fh:
        for offset in range(0, len(payload), record_size):
            chunk = payload[offset : offset + record_size]
            fh.write(struct.pack("<I", len(chunk)))
            fh.write(chunk)
            fh.write(struct.pack("<I", len(chunk)))
        fh.write(struct.pack("<I", 0))
        fh.write(struct.pack("<I", 0))
        fh.write(struct.pack("<I", 0xFFFFFFFF))


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m resume_generator.vax_stage")
    parser.add_argument(
        "--resume",
        default="resume.yaml",
        help="Path to resume source (default: resume.yaml)",
    )
    parser.add_argument(
        "--out",
        dest="site_dir",
        default="site",
        help="Output directory for published site artifacts (default: site)",
    )
    parser.add_argument(
        "--build-dir",
        default="build",
        help="Build directory for intermediate artifacts (default: build)",
    )
    parser.add_argument(
        "--mode",
        choices=["local", "docker"],
        default="local",
        help="Stage execution mode (default: local)",
    )
    parser.add_argument(
        "--transcript",
        default=None,
        help="Replay mode: path to a console transcript containing uuencoded artifacts",
    )
    parser.add_argument(
        "--docker-timeout",
        type=int,
        default=600,
        help="Seconds to wait for SIMH login prompt (default: 600)",
    )
    parser.add_argument(
        "--send-timeout",
        type=int,
        default=180,
        help="Seconds to wait for file transfer completion (default: 180)",
    )
    parser.add_argument(
        "--docker-quick",
        action="store_true",
        help="Only boot/login and write vax-build.log (skip transfer/compile)",
    )
    parser.add_argument(
        "--docker-image",
        default=DOCKER_IMAGE_DEFAULT,
        help=(f"Docker image to run for SIMH (default: {DOCKER_IMAGE_DEFAULT})"),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for the VAX stage.

    Args:
        argv: Optional argument list (primarily for tests).

    Returns:
        Process exit code.
    """
    args = _parse_args(argv)
    repo_root = Path.cwd()
    config = VaxStageConfig(
        resume_path=Path(args.resume),
        site_dir=Path(args.site_dir),
        build_dir=Path(args.build_dir),
        mode=str(args.mode),
        transcript_path=Path(args.transcript) if args.transcript else None,
        docker_timeout=int(args.docker_timeout),
        send_timeout=int(args.send_timeout),
        docker_quick=bool(args.docker_quick),
        docker_image=str(args.docker_image),
    )
    runner = VaxStageRunner(config=config, repo_root=repo_root)
    runner.run()
    print(f"Wrote: {runner.paths.brad_man_txt_path}")
    print(f"Wrote: {runner.paths.vax_build_log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
