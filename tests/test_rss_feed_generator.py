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


def _find_itunes(elem, local_name):
    """Find an itunes-prefixed child element by local name."""
    for child in elem:
        if child.tag == f"itunes:{local_name}":
            return child
    return None


class TestCreateFeedWithArtwork:
    """Tests for create_feed with artwork URL."""

    def test_artwork_creates_image_elements(self):
        """Artwork URL creates itunes:image and image elements."""
        gen = RSSFeedGenerator()
        rss = gen.create_feed(
            title="Test",
            description="Desc",
            website_url="https://example.com",
            author="Host",
            email="host@example.com",
            categories=["Comedy"],
            artwork_url="https://example.com/art.jpg",
        )
        channel = rss.find("channel")
        img = _find_itunes(channel, "image")
        assert img is not None
        assert img.get("href") == "https://example.com/art.jpg"

        std_img = channel.find("image")
        assert std_img is not None
        assert std_img.find("url").text == "https://example.com/art.jpg"


class TestAddEpisodeDetails:
    """Tests for add_episode edge cases."""

    def test_short_duration_format(self):
        """Duration under an hour uses MM:SS format."""
        gen, rss = _make_feed()
        item = gen.add_episode(
            rss=rss,
            episode_number=1,
            title="Short",
            description="Short ep",
            audio_url="https://example.com/ep1.mp3",
            audio_file_size=5000,
            duration_seconds=125,
            pub_date=datetime(2026, 1, 1),
        )
        dur = _find_itunes(item, "duration")
        assert dur.text == "02:05"

    def test_long_duration_format(self):
        """Duration over an hour uses HH:MM:SS format."""
        gen, rss = _make_feed()
        item = gen.add_episode(
            rss=rss,
            episode_number=2,
            title="Long",
            description="Long ep",
            audio_url="https://example.com/ep2.mp3",
            audio_file_size=50000,
            duration_seconds=3661,
            pub_date=datetime(2026, 1, 2),
        )
        dur = _find_itunes(item, "duration")
        assert dur.text == "01:01:01"

    def test_season_number(self):
        """Season number is added when provided."""
        gen, rss = _make_feed()
        item = gen.add_episode(
            rss=rss,
            episode_number=3,
            title="S2E1",
            description="New season",
            audio_url="https://example.com/ep3.mp3",
            audio_file_size=5000,
            duration_seconds=600,
            pub_date=datetime(2026, 1, 3),
            season_number=2,
        )
        season = _find_itunes(item, "season")
        assert season is not None
        assert season.text == "2"

    def test_keywords(self):
        """Keywords are joined and added."""
        gen, rss = _make_feed()
        item = gen.add_episode(
            rss=rss,
            episode_number=4,
            title="Tagged",
            description="With tags",
            audio_url="https://example.com/ep4.mp3",
            audio_file_size=5000,
            duration_seconds=600,
            pub_date=datetime(2026, 1, 4),
            keywords=["comedy", "news", "funny"],
        )
        kw = _find_itunes(item, "keywords")
        assert kw is not None
        assert "comedy" in kw.text


class TestSaveAndLoadFeed:
    """Tests for save_feed and load_feed."""

    def test_save_and_load_roundtrip(self, tmp_path):
        """Save then load preserves feed structure."""
        gen = RSSFeedGenerator(feed_path=str(tmp_path / "feed.xml"))
        rss = gen.create_feed(
            title="Test Podcast",
            description="A test",
            website_url="https://example.com",
            author="Host",
            email="host@example.com",
            categories=["Comedy"],
        )
        gen.add_episode(
            rss=rss,
            episode_number=1,
            title="Ep 1",
            description="First",
            audio_url="https://example.com/ep1.mp3",
            audio_file_size=10000,
            duration_seconds=300,
            pub_date=datetime(2026, 1, 1),
        )
        gen.save_feed(rss)

        loaded = gen.load_feed()
        assert loaded is not None
        channel = loaded.find("channel")
        assert channel.find("title").text == "Test Podcast"
        items = channel.findall("item")
        assert len(items) == 1

    def test_load_nonexistent_returns_none(self, tmp_path):
        """Loading nonexistent feed returns None."""
        gen = RSSFeedGenerator(feed_path=str(tmp_path / "nope.xml"))
        assert gen.load_feed() is None


class TestMetadata:
    """Tests for save/load podcast metadata."""

    def test_save_and_load_metadata(self, tmp_path):
        """Metadata roundtrip preserves data."""
        gen = RSSFeedGenerator()
        gen.metadata_path = tmp_path / "meta.json"

        gen.save_podcast_metadata({"title": "Test", "author": "Host"})

        loaded = gen.load_podcast_metadata()
        assert loaded["title"] == "Test"
        assert loaded["author"] == "Host"

    def test_load_missing_metadata(self, tmp_path):
        """Loading missing metadata returns empty dict."""
        gen = RSSFeedGenerator()
        gen.metadata_path = tmp_path / "nope.json"

        assert gen.load_podcast_metadata() == {}


class TestGetEpisodeCount:
    """Tests for get_episode_count."""

    def test_count_episodes(self, tmp_path):
        """Counts episodes in feed."""
        gen = RSSFeedGenerator(feed_path=str(tmp_path / "feed.xml"))
        rss = gen.create_feed(
            title="Test",
            description="Test",
            website_url="https://example.com",
            author="Host",
            email="host@example.com",
            categories=["Comedy"],
        )
        for i in range(3):
            gen.add_episode(
                rss=rss,
                episode_number=i + 1,
                title=f"Ep {i + 1}",
                description="Test",
                audio_url=f"https://example.com/ep{i + 1}.mp3",
                audio_file_size=10000,
                duration_seconds=300,
                pub_date=datetime(2026, 1, i + 1),
            )
        gen.save_feed(rss)

        assert gen.get_episode_count() == 3

    def test_count_no_feed(self, tmp_path):
        """Returns 0 when no feed exists."""
        gen = RSSFeedGenerator(feed_path=str(tmp_path / "nope.xml"))
        assert gen.get_episode_count() == 0


class TestValidateFeed:
    """Tests for validate_feed."""

    def test_valid_feed(self, tmp_path):
        """Valid feed passes validation."""
        gen = RSSFeedGenerator(feed_path=str(tmp_path / "feed.xml"))
        rss = gen.create_feed(
            title="Test",
            description="Test",
            website_url="https://example.com",
            author="Host",
            email="host@example.com",
            categories=["Comedy"],
            artwork_url="https://example.com/art.jpg",
        )
        gen.add_episode(
            rss=rss,
            episode_number=1,
            title="Ep 1",
            description="Test",
            audio_url="https://example.com/ep1.mp3",
            audio_file_size=10000,
            duration_seconds=300,
            pub_date=datetime(2026, 1, 1),
        )
        gen.save_feed(rss)

        result = gen.validate_feed()
        assert result["valid"] is True
        assert result["episode_count"] == 1

    def test_missing_feed_file(self, tmp_path):
        """Returns invalid for missing feed file."""
        gen = RSSFeedGenerator(feed_path=str(tmp_path / "nope.xml"))
        result = gen.validate_feed()
        assert result["valid"] is False

    def test_malformed_xml(self, tmp_path):
        """Returns invalid for malformed XML."""
        feed = tmp_path / "bad.xml"
        feed.write_text("<not valid xml")
        gen = RSSFeedGenerator(feed_path=str(feed))
        result = gen.validate_feed()
        assert result["valid"] is False


class TestUpdateOrCreateFeed:
    """Tests for update_or_create_feed."""

    def test_creates_new_feed(self, tmp_path):
        """Creates a new feed when none exists."""
        gen = RSSFeedGenerator(feed_path=str(tmp_path / "feed.xml"))

        episode_data = {
            "episode_number": 1,
            "title": "Ep 1",
            "description": "First episode",
            "audio_url": "https://example.com/ep1.mp3",
            "audio_file_size": 10000,
            "duration_seconds": 300,
            "pub_date": datetime(2026, 1, 1),
        }
        metadata = {
            "title": "Test Podcast",
            "description": "A test podcast",
            "website_url": "https://example.com",
            "author": "Host",
            "email": "host@example.com",
            "categories": ["Comedy"],
        }

        rss = gen.update_or_create_feed(episode_data, metadata)
        channel = rss.find("channel")
        assert channel.find("title").text == "Test Podcast"
        items = channel.findall("item")
        assert len(items) == 1


class TestFormatDuration:
    """Tests for format_duration standalone function."""

    def test_short_duration(self):
        """Formats short duration as MM:SS."""
        from rss_feed_generator import format_duration

        assert format_duration(65) == "01:05"

    def test_long_duration(self):
        """Formats long duration as HH:MM:SS."""
        from rss_feed_generator import format_duration

        assert format_duration(3661) == "01:01:01"


# Ensure pytest picks up this module even without chapter_generator
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
