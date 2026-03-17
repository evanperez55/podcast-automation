"""Tests for RSSFeedGenerator chapter tag support — RED phase."""

import pytest
from datetime import datetime

from rss_feed_generator import RSSFeedGenerator

PODCAST_NS = "https://podcastindex.org/namespace/1.0"


def _make_feed():
    gen = RSSFeedGenerator()
    rss = gen.create_feed(
        title="Fake Problems Podcast",
        description="Test feed",
        website_url="https://example.com",
        author="Test Host",
        email="test@example.com",
        categories=["Comedy"],
    )
    return gen, rss


class TestAddEpisodeChapters:
    def test_adds_podcast_chapters_tag_when_url_provided(self):
        gen, rss = _make_feed()
        chapters_url = "https://example.com/ep29_chapters.json"
        item = gen.add_episode(
            rss=rss,
            episode_number=29,
            title="Episode #29",
            description="Test",
            audio_url="https://example.com/ep29.mp3",
            audio_file_size=1000000,
            duration_seconds=4200,
            pub_date=datetime(2026, 3, 1),
            chapters_url=chapters_url,
        )
        # Find podcast:chapters child element
        ns = f"{{{PODCAST_NS}}}"
        chap_elem = item.find(f"{ns}chapters")
        assert chap_elem is not None, "No podcast:chapters element found in item"
        assert chap_elem.get("url") == chapters_url
        assert chap_elem.get("type") == "application/json+chapters"

    def test_omits_podcast_chapters_tag_when_no_url(self):
        gen, rss = _make_feed()
        item = gen.add_episode(
            rss=rss,
            episode_number=28,
            title="Episode #28",
            description="Test",
            audio_url="https://example.com/ep28.mp3",
            audio_file_size=1000000,
            duration_seconds=3600,
            pub_date=datetime(2026, 2, 1),
        )
        ns = f"{{{PODCAST_NS}}}"
        chap_elem = item.find(f"{ns}chapters")
        assert chap_elem is None, (
            "podcast:chapters element should be absent when no URL"
        )

    def test_rss_root_has_podcast_namespace(self):
        gen, rss = _make_feed()
        assert rss.get("xmlns:podcast") == PODCAST_NS, (
            f"Expected xmlns:podcast={PODCAST_NS!r} on rss root, got: {rss.attrib}"
        )


# Ensure pytest picks up this module even without chapter_generator
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
