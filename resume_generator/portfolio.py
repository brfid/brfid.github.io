"""Render the portfolio page (``site/portfolio/index.html``) from portfolio data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .render import make_jinja_env, write_text


@dataclass(frozen=True)
class PortfolioContext:
    """Template context for the portfolio page."""

    author: str
    title: str
    description: str
    genres: list[Any]


def _load_portfolio(path: Path) -> dict[str, Any]:
    """Load portfolio data from a YAML file.

    Args:
        path: Path to the portfolio YAML file.

    Returns:
        Parsed portfolio data as a dict.
    """
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def build_portfolio_page(
    *,
    portfolio_src: Path,
    out_dir: Path,
    templates_dir: Path,
    template_name: str = "portfolio.html.j2",
    author: str = "",
) -> Path:
    """Render the portfolio page to ``<out_dir>/portfolio/index.html``.

    Args:
        portfolio_src: Path to the portfolio YAML data file.
        out_dir: Output directory (typically ``site/``).
        templates_dir: Directory containing the portfolio template.
        template_name: Template file name (default: ``portfolio.html.j2``).
        author: Optional author name to display in the page title.

    Returns:
        Path to the generated HTML file.
    """
    data = _load_portfolio(portfolio_src)
    ctx = PortfolioContext(
        author=author or str(data.get("author") or ""),
        title=str(data.get("title") or "Writing Samples"),
        description=str(data.get("description") or ""),
        genres=list(data.get("genres") or []),
    )

    env = make_jinja_env(templates_dir)
    template = env.get_template(template_name)
    html = template.render(**ctx.__dict__)

    index_path = out_dir / "portfolio" / "index.html"
    write_text(index_path, html)
    return index_path
