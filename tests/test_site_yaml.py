from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import yaml


def test_site_yaml_is_the_complete_public_landing_source() -> None:
    site = yaml.safe_load(Path("site.yaml").read_text(encoding="utf-8"))
    resume = yaml.safe_load(Path("resume.yaml").read_text(encoding="utf-8"))

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


def test_resume_profiles_are_a_consistent_subset_of_the_landing_links() -> None:
    """The resume shows a professional subset of the landing links, never a divergent one."""
    site = yaml.safe_load(Path("site.yaml").read_text(encoding="utf-8"))
    resume = yaml.safe_load(Path("resume.yaml").read_text(encoding="utf-8"))

    landing = {link["label"]: link for link in site["links"]}
    profiles = resume["basics"]["profiles"]
    assert profiles

    for profile in profiles:
        link = landing.get(profile["network"])
        assert link is not None, f"resume profile has no landing link: {profile['network']}"
        assert profile["icon"] == link["icon"]
        assert profile["url"] == link["url"]

    order = [label for label in landing if label in {profile["network"] for profile in profiles}]
    assert [profile["network"] for profile in profiles] == order
