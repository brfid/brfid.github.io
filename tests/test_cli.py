from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from resume_generator.cli import main
from tests.helpers import write_minimal_resume


def test_cli_html_only_writes_site(tmp_path: Path) -> None:
    resume_src = tmp_path / "resume.yaml"
    write_minimal_resume(resume_src)

    out_dir = tmp_path / "site"

    rc = main(
        [
            "--in",
            str(resume_src),
            "--out",
            str(out_dir),
            "--templates",
            "templates",
            "--html-only",
        ]
    )
    assert rc == 0

    assert (out_dir / "index.html").exists()
    assert (out_dir / "resume" / "index.html").exists()
    assert (out_dir / ".nojekyll").exists()


def test_cli_with_arpanet_requires_with_vax() -> None:
    with pytest.raises(SystemExit):
        main(["--with-arpanet", "--html-only"])


def test_cli_arpanet_execute_requires_with_arpanet() -> None:
    with pytest.raises(SystemExit):
        main(["--with-vax", "--arpanet-execute", "--html-only"])


def test_cli_with_arpanet_uses_arpanet_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resume_src = tmp_path / "resume.yaml"
    write_minimal_resume(resume_src)

    out_dir = tmp_path / "site"
    calls = {"arpanet_runner_run": 0, "execute_commands": False}

    def _fake_build_html(
        *,
        src: Path,
        out_dir: Path,
        templates_dir: Path,
    ) -> tuple[Path, dict[str, dict[str, str]]]:
        del src, templates_dir
        resume_dir = out_dir / "resume"
        resume_dir.mkdir(parents=True, exist_ok=True)
        index_path = resume_dir / "index.html"
        index_path.write_text("<html></html>", encoding="utf-8")
        return index_path, {"basics": {"name": "Brad"}}

    class _FakeArpanetRunner:
        def __init__(self, **kwargs: Any) -> None:
            calls["execute_commands"] = bool(kwargs.get("execute_commands", False))
            self.paths = SimpleNamespace(
                brad_man_txt_path=out_dir / "brad.man.txt",
                vax_build_log_path=out_dir / "vax-build.log",
            )

        def run(self) -> None:
            calls["arpanet_runner_run"] += 1

    monkeypatch.setattr("resume_generator.cli.build_html", _fake_build_html)
    monkeypatch.setattr(
        "resume_generator.cli.build_landing_page",
        lambda **kwargs: kwargs["out_dir"] / "index.html",
    )
    monkeypatch.setattr(
        "resume_generator.cli.write_manifest",
        lambda root, out_path: out_path,
    )
    monkeypatch.setattr(
        "resume_generator.vax_arpanet_stage.VaxArpanetStageRunner",
        _FakeArpanetRunner,
    )

    rc = main(
        [
            "--in",
            str(resume_src),
            "--out",
            str(out_dir),
            "--templates",
            "templates",
            "--html-only",
            "--with-vax",
            "--with-arpanet",
            "--arpanet-execute",
        ]
    )

    assert rc == 0
    assert calls["arpanet_runner_run"] == 1
    assert calls["execute_commands"] is True
