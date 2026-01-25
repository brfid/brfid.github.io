from __future__ import annotations

from pathlib import Path

from resume_generator.vax_stage import VaxBuildLog, VaxStagePaths


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
