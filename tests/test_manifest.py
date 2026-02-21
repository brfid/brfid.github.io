from __future__ import annotations

from pathlib import Path

from resume_generator.manifest import build_manifest_entries, render_manifest, write_manifest


def test_manifest_is_deterministic_and_excludes_self(tmp_path: Path) -> None:
    root = tmp_path / "site"
    root.mkdir(parents=True, exist_ok=True)
    (root / "a.txt").write_text("aaa", encoding="utf-8")
    (root / "b.txt").write_text("bbb", encoding="utf-8")
    (root / "sub").mkdir()
    (root / "sub" / "c.txt").write_text("ccc", encoding="utf-8")

    out_path = root / "vintage-manifest.txt"
    written = write_manifest(root=root, out_path=out_path)
    assert written.exists()

    text1 = out_path.read_text(encoding="utf-8")
    text2 = write_manifest(root=root, out_path=out_path).read_text(encoding="utf-8")
    assert text1 == text2
    assert "vintage-manifest.txt" not in text1

    # Order is lexicographic by relative path.
    entries = build_manifest_entries(root=root, exclude_relpaths={"vintage-manifest.txt"})
    rendered = render_manifest(entries)
    lines = [line for line in rendered.splitlines() if line.strip()]
    assert lines[0].endswith("  a.txt")
    assert lines[1].endswith("  b.txt")
    assert lines[2].endswith("  sub/c.txt")
