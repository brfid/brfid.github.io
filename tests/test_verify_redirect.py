from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


def _load_verifier() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "scripts" / "verify_redirect.py"
    spec = importlib.util.spec_from_file_location("verify_redirect_under_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load verifier from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verifier = _load_verifier()


def _document(target_path: str) -> str:
    target = f"{verifier.DESTINATION_BASE}{target_path}"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta name="robots" content="{verifier.ROBOTS_DIRECTIVE}">
<meta http-equiv="refresh" content="0; url={target}">
<link rel="canonical" href="{target}">
<script>
(() => {{
const destination = new URL("{verifier.DESTINATION_BASE}");
destination.pathname = window.location.pathname;
destination.search = window.location.search;
destination.hash = window.location.hash;
window.location.replace(destination.href);
}})();
</script>
</head>
<body><a href="{target}">Continue</a></body>
</html>
"""


def _write_valid_tree(tmp_path: Path) -> Path:
    site_dir = tmp_path / "site"
    for relative_path, target_path in verifier.EXPECTED_REDIRECTS.items():
        output = site_dir / relative_path
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(_document(target_path), encoding="utf-8")
    (site_dir / "robots.txt").write_text(verifier.ROBOTS_TEXT, encoding="utf-8")
    return site_dir


def test_verify_redirect_accepts_the_exact_redirect_tree(tmp_path: Path) -> None:
    site_dir = _write_valid_tree(tmp_path)

    verifier.verify_redirect(site_dir)


def test_verify_redirect_rejects_a_retained_site_artifact(tmp_path: Path) -> None:
    site_dir = _write_valid_tree(tmp_path)
    (site_dir / "resume.pdf").write_bytes(b"%PDF-1.7\n")

    with pytest.raises(ValueError, match="unexpected redirect output files:.*resume.pdf"):
        verifier.verify_redirect(site_dir)


def test_verify_redirect_rejects_a_wrong_known_route_target(tmp_path: Path) -> None:
    site_dir = _write_valid_tree(tmp_path)
    resume = site_dir / "resume" / "index.html"
    resume.write_text(_document("/"), encoding="utf-8")

    with pytest.raises(ValueError, match="wrong refresh target"):
        verifier.verify_redirect(site_dir)


def test_verify_redirect_requires_query_and_fragment_preservation(tmp_path: Path) -> None:
    site_dir = _write_valid_tree(tmp_path)
    index = site_dir / "index.html"
    index.write_text(
        index.read_text(encoding="utf-8").replace(
            "destination.search = window.location.search;",
            "destination.search = '';",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="redirect script changed"):
        verifier.verify_redirect(site_dir)


def test_verify_redirect_rejects_a_visitor_controlled_host(tmp_path: Path) -> None:
    site_dir = _write_valid_tree(tmp_path)
    index = site_dir / "index.html"
    index.write_text(
        index.read_text(encoding="utf-8").replace(
            "destination.pathname = window.location.pathname;",
            'destination.host = new URLSearchParams(window.location.search).get("host");\n'
            "destination.pathname = window.location.pathname;",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="redirect script changed"):
        verifier.verify_redirect(site_dir)


def test_main_reports_an_invalid_output_directory(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing = tmp_path / "missing"

    assert verifier.main([str(missing)]) == 1
    assert f"redirect verification: unsafe output directory: {missing}\n" == capsys.readouterr().err
