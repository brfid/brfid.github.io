from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import yaml


def test_site_yaml_is_the_complete_public_landing_source() -> None:
    site = yaml.safe_load(Path("site.yaml").read_text(encoding="utf-8"))
    resume = yaml.safe_load(Path("resume.yaml").read_text(encoding="utf-8"))

    # The landing bio text lives in resume.yaml `basics.summary`; site.yaml owns the
    # public identity and links.
    assert set(site) == {"name", "headline", "links"}
    for field in ("name", "headline"):
        assert isinstance(site[field], str)
        assert site[field].strip()

    links = site["links"]
    assert isinstance(links, list)
    assert links

    labels: list[str] = []
    for link in links:
        assert isinstance(link, dict)
        assert set(link) == {"label", "icon", "url"}
        assert all(isinstance(link[field], str) and link[field].strip() for field in ("label", "icon", "url"))
        parsed_url = urlparse(link["url"])
        assert parsed_url.scheme == "https"
        assert parsed_url.netloc
        labels.append(link["label"])

    assert len(labels) == len(set(labels))
    assert site["name"] == resume["basics"]["name"]
    assert site["headline"] == resume["basics"]["label"]
    assert labels == ["LinkedIn", "GitHub", "GitLab", "ORCID", "Strava"]
