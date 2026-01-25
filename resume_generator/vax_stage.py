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
import subprocess
import time
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
        # Intentionally stubbed: docker/SIMH will be wired next. Keeping the
        # public module/CLI stable so later work is incremental.
        #
        # Note: `decode_marked_uuencode` is used by the planned docker/SIMH path
        # to extract `brad.1` from console transcripts.
        _ = self._decode_brad_1_from_transcript
        raise NotImplementedError("docker/SIMH mode is not implemented yet")

    def _decode_brad_1_from_transcript(self, transcript: str) -> bytes:
        """Decode `brad.1` bytes from a transcript region."""
        res = decode_marked_uuencode(
            transcript,
            begin_marker="<<<BRAD_1_UU_BEGIN>>>",
            end_marker="<<<BRAD_1_UU_END>>>",
        )
        return res.data


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
    )
    runner = VaxStageRunner(config=config, repo_root=repo_root)
    runner.run()
    print(f"Wrote: {runner.paths.brad_man_txt_path}")
    print(f"Wrote: {runner.paths.vax_build_log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
