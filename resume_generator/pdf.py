"""Generate a PDF from the rendered resume HTML using Playwright.

We serve the output directory over an ephemeral localhost HTTP server so
relative assets (CSS, images) resolve consistently in Playwright.
"""

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
    """Serve a directory on an ephemeral localhost port.

    Args:
        root: Directory to serve.

    Yields:
        The chosen port number.
    """
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
    if path is None or not path.exists():
        return None

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
    """
    site_dir.mkdir(parents=True, exist_ok=True)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    private_phone = load_private_phone(private_resume_path)

    # pylint: disable=import-outside-toplevel
    from playwright.sync_api import sync_playwright

    with _serve_directory(site_dir) as port:
        url = f"http://127.0.0.1:{port}{resume_url_path}"
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            # Force light so the PDF never inherits a dark palette; the page's
            # print CSS then finishes shaping it (white background, no chrome).
            page.emulate_media(media="print", color_scheme="light")
            # Wait for `load` (deterministic) rather than the flaky/soft-deprecated
            # `networkidle`; the page is self-contained (vendored fonts, no external
            # requests), so the only async work that moves line breaks is font swap.
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
            # Block until web fonts are applied, so pagination reflects the final
            # metrics instead of the fallback face.
            page.evaluate("() => document.fonts.ready")
            page.pdf(
                path=str(pdf_path),
                print_background=True,
                # Page size and margins come from the page's own `@page` rule, so
                # the résumé's CSS is the single source for print geometry and the
                # PDF column matches the on-screen measure.
                prefer_css_page_size=True,
            )
            browser.close()

    return pdf_path
