"""Print rendered resume HTML to PDF with Playwright."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import yaml


class _QuietHandler(SimpleHTTPRequestHandler):
    """HTTP handler that suppresses request logging."""

    def log_message(self, _format: str, *_args: object) -> None:  # pylint: disable=arguments-differ
        return


@contextmanager
def _serve_directory(root: Path) -> Iterator[int]:
    """Serve a directory on localhost and yield its ephemeral port."""
    handler = partial(_QuietHandler, directory=str(root))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def load_private_phone(path: Path | None) -> str | None:
    """Load the phone number from an optional, untracked resume overlay."""
    if path is None:
        return None
    if not path.exists():
        raise FileNotFoundError(f"private resume overlay does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"private resume overlay must be a regular file: {path}")

    data: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"private resume overlay must be a mapping: {path}")

    basics = data.get("basics")
    if not isinstance(basics, dict):
        raise ValueError(f"private resume overlay must contain a basics mapping: {path}")

    phone = basics.get("phone")
    if not isinstance(phone, str) or not phone.strip():
        raise ValueError(f"private resume overlay basics.phone must be a non-empty string: {path}")
    return phone.strip()


def build_pdf(
    *,
    site_dir: Path,
    resume_url_path: str,
    pdf_path: Path,
    private_resume_path: Path | None = None,
) -> Path:
    """Render a PDF from the generated resume HTML.

    Args:
        site_dir: Directory containing the generated resume site (served as root).
        resume_url_path: URL path to the resume HTML (for example: "/resume/").
        pdf_path: Output PDF path. It may be outside `site_dir`.
        private_resume_path: Optional untracked YAML overlay whose `basics.phone`
            is injected into the PDF render only.

    Returns:
        Path to the generated PDF.

    Raises:
        FileNotFoundError: If an explicitly requested private resume overlay is
            missing.
        RuntimeError: If the resume page or its fonts do not load cleanly.
        ValueError: If a private overlay is invalid or its PDF output path is
            inside the public site directory.
    """
    if private_resume_path is not None and pdf_path.resolve().is_relative_to(site_dir.resolve()):
        raise ValueError(f"private resume PDF must be written outside the public site directory: {pdf_path}")

    private_phone = load_private_phone(private_resume_path)
    site_dir.mkdir(parents=True, exist_ok=True)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    # pylint: disable=import-outside-toplevel
    from playwright.sync_api import sync_playwright

    with _serve_directory(site_dir) as port:
        url = f"http://127.0.0.1:{port}{resume_url_path}"
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page()
                # Force the light palette before print CSS hides the site chrome.
                page.emulate_media(media="print", color_scheme="light")
                # Vendored font loading is the only asynchronous layout dependency.
                response = page.goto(url, wait_until="load")
                if response is None or not response.ok:
                    status = "no response" if response is None else response.status
                    raise RuntimeError(f"resume page did not load cleanly ({status}): {url}")
                if private_phone:
                    page.evaluate(
                        """phone => {
                            const template = document.querySelector("#resume-private-phone-template");
                            const container = document.querySelector(".resume-header-right");
                            if (!(template instanceof HTMLTemplateElement) || !container) {
                                throw new Error("private phone injection target is missing");
                            }
                            const contact = template.content.firstElementChild?.cloneNode(true);
                            const text = contact?.querySelector("[data-resume-private-phone-text]");
                            if (!(contact instanceof HTMLAnchorElement) || !text) {
                                throw new Error("private phone template is invalid");
                            }
                            contact.href = `tel:${phone}`;
                            text.textContent = phone;
                            const profiles = container.querySelector(".resume-profile-links");
                            container.insertBefore(contact, profiles);
                        }""",
                        private_phone,
                    )
                # FontFaceSet status can be "loaded" even when a required face failed.
                missing_fonts: list[str] = page.evaluate(
                    """async () => {
                        const requiredFamilies = ["Newsreader", "IBM Plex Mono"];
                        const results = await Promise.all(requiredFamilies.map(async family => {
                            const descriptor = `1em "${family}"`;
                            try {
                                const faces = await document.fonts.load(descriptor, "A");
                                return faces.length > 0 && document.fonts.check(descriptor, "A")
                                    ? null
                                    : family;
                            } catch {
                                return family;
                            }
                        }));
                        await document.fonts.ready;
                        return results.filter(family => family !== null);
                    }"""
                )
                if missing_fonts:
                    raise RuntimeError(f"required resume fonts did not load: {', '.join(missing_fonts)}")
                page.pdf(
                    path=str(pdf_path),
                    print_background=True,
                    # Preserve document tags and expose headings in the PDF outline.
                    tagged=True,
                    outline=True,
                    # The page's `@page` rule controls PDF size and margins.
                    prefer_css_page_size=True,
                )
            finally:
                browser.close()

    return pdf_path
