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
import shutil
import socket
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .landing import build_landing_page
from .manpage import parse_brad_roff_summary, render_brad_man_txt
from .render import load_resume
from .types import Resume
from .uudecode import decode_marked_uuencode
from .vax_yaml import build_vax_resume_v1, emit_vax_yaml


@dataclass(frozen=True)
class VaxStagePaths:
    """Commonly used paths for the VAX stage."""

    repo_root: Path
    site_dir: Path
    build_dir: Path

    @property
    def vax_build_dir(self) -> Path:
        return self.build_dir / "vax"

    @property
    def resume_vax_yaml_path(self) -> Path:
        return self.vax_build_dir / "resume.vax.yaml"

    @property
    def brad_1_path(self) -> Path:
        return self.vax_build_dir / "brad.1"

    @property
    def bradman_exe_path(self) -> Path:
        return self.vax_build_dir / "bradman"

    @property
    def brad_man_txt_path(self) -> Path:
        return self.site_dir / "brad.man.txt"

    @property
    def vax_build_log_path(self) -> Path:
        return self.site_dir / "vax-build.log"


class VaxBuildLog:
    """Small timestamped log for publication as "build evidence"."""

    def __init__(self) -> None:
        self._lines: list[str] = []
        self._t0 = time.time()

    def add(self, message: str) -> None:
        """Add a log line with elapsed seconds."""
        elapsed = time.time() - self._t0
        self._lines.append(f"[+{elapsed:0.2f}s] {message}".rstrip())

    def render(self) -> str:
        """Render the build log as LF-only text with a trailing newline."""
        return "\n".join(self._lines).rstrip() + "\n"


@dataclass(frozen=True)
class VaxStageConfig:
    """Configuration for running the VAX stage."""

    resume_path: Path
    site_dir: Path
    build_dir: Path = Path("build")
    mode: str = "local"
    transcript_path: Path | None = None


class VaxStageRunner:
    """Runs the VAX stage in local or docker mode."""

    def __init__(self, *, config: VaxStageConfig, repo_root: Path) -> None:
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
        log.add(f"emit resume.vax.yaml from {self._config.resume_path}")
        resume = load_resume(self._config.resume_path)
        built = build_vax_resume_v1(resume, build_date=build_date)
        text = emit_vax_yaml(built)
        self._paths.resume_vax_yaml_path.write_text(text, encoding="utf-8")
        return resume

    def _compile_bradman(self, *, log: VaxBuildLog) -> None:
        bradman_c = self._paths.repo_root / "vax" / "bradman.c"
        if not bradman_c.exists():
            raise FileNotFoundError(f"Missing source file: {bradman_c}")

        compiler = shutil.which("cc") or shutil.which("clang") or shutil.which("gcc")
        if not compiler:
            raise RuntimeError("No C compiler found (expected one of: cc, clang, gcc)")

        log.add(f"compile bradman.c with {Path(compiler).name}")
        subprocess.run(  # noqa: S603
            [compiler, "-O", "-o", str(self._paths.bradman_exe_path), str(bradman_c)],
            check=True,
            capture_output=True,
            text=True,
        )

    def _run_bradman(self, *, log: VaxBuildLog) -> None:
        log.add("run bradman to generate brad.1")
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

    def _render_brad_man_txt(self, *, log: VaxBuildLog) -> None:
        log.add("render brad.man.txt from brad.1 (host-side)")
        roff = self._paths.brad_1_path.read_text(encoding="utf-8")
        summary = parse_brad_roff_summary(roff)
        rendered = render_brad_man_txt(summary)
        self._paths.brad_man_txt_path.write_text(rendered, encoding="utf-8")

    def _write_build_log(self, log: VaxBuildLog) -> None:
        self._paths.vax_build_log_path.write_text(log.render(), encoding="utf-8")

    def _run_local(self) -> None:
        log = VaxBuildLog()
        log.add("vax stage mode=local (host compilation)")
        resume = self._emit_resume_vax_yaml(build_date=date.today(), log=log)
        self._compile_bradman(log=log)
        self._run_bradman(log=log)
        self._render_brad_man_txt(log=log)
        log.add("render landing page (index.html)")
        build_landing_page(
            resume=resume,
            out_dir=self._paths.site_dir,
            templates_dir=self._paths.repo_root / "templates",
        )
        log.add("done")
        self._write_build_log(log)

    def _run_docker(self) -> None:
        log = VaxBuildLog()
        log.add("vax stage mode=docker")

        resume = self._emit_resume_vax_yaml(build_date=date.today(), log=log)

        if self._config.transcript_path:
            log.add(f"replay transcript: {self._config.transcript_path}")
            transcript = self._config.transcript_path.read_text(encoding="utf-8")
            brad_1_bytes = self._decode_brad_1_from_transcript(transcript)
            self._paths.brad_1_path.write_bytes(brad_1_bytes)
            self._render_brad_man_txt(log=log)
            log.add("render landing page (index.html)")
            build_landing_page(
                resume=resume,
                out_dir=self._paths.site_dir,
                templates_dir=self._paths.repo_root / "templates",
            )
            log.add("done")
            self._write_build_log(log)
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

        simh_dir = self._paths.vax_build_dir / "simh"
        simh_dir.mkdir(parents=True, exist_ok=True)

        container_name = f"vaxbsd-{uuid.uuid4().hex[:8]}"
        host_port = _find_free_port()

        log.add(f"docker run {container_name} on port {host_port}")
        subprocess.run(  # noqa: S603
            [
                docker_bin,
                "run",
                "--rm",
                "--name",
                container_name,
                "-d",
                "-p",
                f"{host_port}:2323",
                "-v",
                f"{simh_dir}:/machines",
                "jguillaumes/simh-vaxbsd",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        transcript_parts: list[str] = []
        try:
            session = TelnetSession(host="127.0.0.1", port=host_port, log=log)
            session.wait_for_login()
            session.login_root()
            session.ensure_shell_prompt()

            session.exec_cmd("cd /machines")

            bradman_c = (self._paths.repo_root / "vax" / "bradman.c").read_text(encoding="utf-8")
            session.send_heredoc("bradman.c", bradman_c)

            resume_yaml = self._paths.resume_vax_yaml_path.read_text(encoding="utf-8")
            session.send_heredoc("resume.vax.yaml", resume_yaml)

            session.exec_cmd("cc -O -o bradman bradman.c")
            session.exec_cmd("./bradman -i resume.vax.yaml -o brad.1")

            output = session.exec_cmd(
                "echo '<<<BRAD_1_UU_BEGIN>>>'; uuencode brad.1 brad.1; "
                "echo '<<<BRAD_1_UU_END>>>'"
            )
            transcript_parts.append(output)
        finally:
            subprocess.run(  # noqa: S603
                [docker_bin, "rm", "-f", container_name],
                check=False,
                capture_output=True,
                text=True,
            )

        transcript = "\n".join(transcript_parts)
        brad_1_bytes = self._decode_brad_1_from_transcript(transcript)
        self._paths.brad_1_path.write_bytes(brad_1_bytes)
        self._render_brad_man_txt(log=log)
        log.add("render landing page (index.html)")
        build_landing_page(
            resume=resume,
            out_dir=self._paths.site_dir,
            templates_dir=self._paths.repo_root / "templates",
        )
        log.add("done")
        self._write_build_log(log)


class TelnetSession:
    """Minimal telnet session helper for SIMH console control."""

    def __init__(self, *, host: str, port: int, log: VaxBuildLog) -> None:
        self._log = log
        self._sock = socket.create_connection((host, port), timeout=10)
        self._sock.settimeout(5)
        self._prompt = b"BRAD# "
        self._log.add(f"telnet connected to {host}:{port}")

    def wait_for_login(self, timeout: int = 120) -> None:
        self._read_until(b"login:", timeout=timeout)

    def login_root(self, timeout: int = 60) -> None:
        self._send(b"root\n")
        output = self._read_until(b"Password:", timeout=5)
        if b"Password:" in output:
            self._send(b"\n")
        self._read_until(b"#", timeout=timeout)

    def ensure_shell_prompt(self) -> None:
        self._send(b"sh\n")
        self._read_until(b"#", timeout=30)
        self._send(b"PS1='BRAD# '\n")
        self._read_until(self._prompt, timeout=30)

    def exec_cmd(self, command: str, timeout: int = 120) -> str:
        self._send(command.encode() + b"\n")
        output = self._read_until(self._prompt, timeout=timeout)
        return output.decode("utf-8", errors="ignore")

    def send_heredoc(self, filename: str, content: str) -> None:
        marker = f"BRAD_EOF_{uuid.uuid4().hex[:8]}"
        self._send(f"cat > {filename} <<'{marker}'\n".encode())
        self._send(content.encode() + b"\n")
        self._send(f"{marker}\n".encode())
        self._read_until(self._prompt, timeout=60)

    def _send(self, data: bytes) -> None:
        self._sock.sendall(data)

    def _read_until(self, needle: bytes, timeout: int) -> bytes:
        end_time = time.time() + timeout
        buf = bytearray()
        while time.time() < end_time:
            chunk = self._recv_filtered()
            if chunk:
                buf.extend(chunk)
                if needle in buf:
                    return bytes(buf)
            else:
                time.sleep(0.05)
        raise TimeoutError(f"Timed out waiting for {needle!r}")

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
    )
    runner = VaxStageRunner(config=config, repo_root=repo_root)
    runner.run()
    print(f"Wrote: {runner.paths.brad_man_txt_path}")
    print(f"Wrote: {runner.paths.vax_build_log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
