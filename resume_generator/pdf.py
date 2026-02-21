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


def build_pdf(*, out_dir: Path, resume_url_path: str, pdf_name: str) -> Path:
    """Render a PDF from the generated resume HTML.

    Args:
        out_dir: Directory containing the generated resume site (served as root).
        resume_url_path: URL path to the resume HTML (for example: "/resume/").
        pdf_name: Output PDF filename relative to `out_dir` (for example: "resume.pdf").

    Returns:
        Path to the generated PDF.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / pdf_name

    # pylint: disable=import-outside-toplevel
    from playwright.sync_api import sync_playwright

    with _serve_directory(out_dir) as port:
        url = f"http://127.0.0.1:{port}{resume_url_path}"
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.emulate_media(media="print")
            page.goto(url, wait_until="networkidle")
            page.pdf(
                path=str(pdf_path),
                format="Letter",
                print_background=True,
                margin={"top": "0.5in", "right": "0.5in", "bottom": "0.5in", "left": "0.5in"},
            )
            browser.close()

    return pdf_path
