from __future__ import annotations

from pathlib import Path

from resume_generator.vax_stage import VaxBuildLog, VaxStageConfig, VaxStagePaths, VaxStageRunner
from tests.helpers import uuencode_bytes, write_minimal_resume


def test_build_log_renders_with_trailing_newline() -> None:
    log = VaxBuildLog()
    log.add("step one")
    rendered = log.render()
    assert rendered.endswith("\n")
    assert "step one" in rendered


def test_stage_paths_are_stable() -> None:
    paths = VaxStagePaths(repo_root=Path("/repo"), site_dir=Path("site"), build_dir=Path("build"))
    assert paths.vax_build_dir.as_posix().endswith("build/vax")
    assert paths.brad_1_path.as_posix().endswith("build/vax/brad.1")
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

    runner = VaxStageRunner(
        config=VaxStageConfig(
            resume_path=resume_path,
            site_dir=tmp_path / "site",
            build_dir=tmp_path / "build",
            mode="docker",
            transcript_path=transcript_path,
        ),
        repo_root=Path.cwd(),
    )
    runner.run()

    assert (tmp_path / "build" / "vax" / "brad.1").exists()
    assert (tmp_path / "site" / "brad.man.txt").exists()
    assert (tmp_path / "site" / "vax-build.log").exists()
    assert (tmp_path / "site" / "index.html").exists()
