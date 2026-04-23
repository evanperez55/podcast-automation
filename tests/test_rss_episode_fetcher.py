"""Tests for rss_episode_fetcher module — RSSEpisodeFetcher, EpisodeMeta, extract_episode_number_from_filename."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from rss_episode_fetcher import (
    EpisodeMeta,
    RSSEpisodeFetcher,
    _parse_itunes_duration,
    extract_episode_number_from_filename,
)

# ---------------------------------------------------------------------------
# Sample RSS feed XML (minimal valid RSS 2.0 with iTunes namespace, 2 entries)
# ---------------------------------------------------------------------------

SAMPLE_RSS_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>Test Podcast</title>
    <link>https://example.com</link>
    <description>Test podcast feed</description>
    <item>
      <title>Episode 43 - The Latest One</title>
      <enclosure url="https://example.com/audio/episode-43.mp3" length="50000000" type="audio/mpeg"/>
      <itunes:episode>43</itunes:episode>
      <itunes:duration>01:12:34</itunes:duration>
      <pubDate>Mon, 28 Mar 2026 10:00:00 +0000</pubDate>
      <description>Latest episode description.</description>
    </item>
    <item>
      <title>Episode 42 - The Previous One</title>
      <enclosure url="https://example.com/audio/episode-42.mp3" length="45000000" type="audio/mpeg"/>
      <itunes:episode>42</itunes:episode>
      <itunes:duration>4354</itunes:duration>
      <pubDate>Mon, 14 Mar 2026 10:00:00 +0000</pubDate>
      <description>Previous episode description.</description>
    </item>
  </channel>
</rss>
"""

# ---------------------------------------------------------------------------
# Helper: build a fake feedparser result dict mirroring feedparser's output
# ---------------------------------------------------------------------------


def _make_feed_entry(
    title,
    enclosure_url,
    itunes_episode="43",
    itunes_duration="01:12:34",
    pub_date="Mon, 28 Mar 2026 10:00:00 +0000",
    pub_parsed=(2026, 3, 28, 10, 0, 0, 0, 0, 0),
    description="Episode description.",
):
    """Return a dict mimicking a feedparser entry object."""
    entry = MagicMock()
    entry.title = title
    entry.get = lambda key, default=None: {
        "itunes_episode": itunes_episode,
        "itunes_duration": itunes_duration,
    }.get(key, default)
    entry.enclosures = [
        {"url": enclosure_url, "type": "audio/mpeg", "length": "50000000"}
    ]
    entry.published = pub_date
    entry.published_parsed = pub_parsed
    entry.summary = description
    return entry


def _make_parsed_feed(entries, bozo=False, bozo_exception=None):
    """Return a dict mimicking feedparser.parse() output."""
    result = MagicMock()
    result.bozo = bozo
    result.bozo_exception = bozo_exception or Exception("parse error")
    result.entries = entries
    return result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fetcher():
    """Create a default RSSEpisodeFetcher instance."""
    return RSSEpisodeFetcher()


@pytest.fixture
def entry_43():
    """Return a fake feedparser entry for episode 43."""
    return _make_feed_entry(
        title="Episode 43 - The Latest One",
        enclosure_url="https://example.com/audio/episode-43.mp3",
        itunes_episode="43",
        itunes_duration="01:12:34",
        pub_date="Mon, 28 Mar 2026 10:00:00 +0000",
        pub_parsed=(2026, 3, 28, 10, 0, 0, 0, 0, 0),
        description="Latest episode description.",
    )


@pytest.fixture
def entry_42():
    """Return a fake feedparser entry for episode 42."""
    return _make_feed_entry(
        title="Episode 42 - The Previous One",
        enclosure_url="https://example.com/audio/episode-42.mp3",
        itunes_episode="42",
        itunes_duration="4354",
        pub_date="Mon, 14 Mar 2026 10:00:00 +0000",
        pub_parsed=(2026, 3, 14, 10, 0, 0, 0, 0, 0),
        description="Previous episode description.",
    )


# ---------------------------------------------------------------------------
# TestFetchLatest
# ---------------------------------------------------------------------------


class TestFetchLatest:
    """Tests for RSSEpisodeFetcher.fetch_latest()."""

    def test_returns_episode_meta_with_audio_url(self, fetcher, entry_43, entry_42):
        """fetch_latest returns EpisodeMeta with the correct audio_url from newest entry."""
        feed = _make_parsed_feed([entry_43, entry_42])
        with patch("rss_episode_fetcher.feedparser.parse", return_value=feed):
            meta = fetcher.fetch_latest("https://example.com/feed.xml")
        assert isinstance(meta, EpisodeMeta)
        assert meta.audio_url == "https://example.com/audio/episode-43.mp3"

    def test_returns_correct_title(self, fetcher, entry_43, entry_42):
        """fetch_latest returns EpisodeMeta with the title of the most recent entry."""
        feed = _make_parsed_feed([entry_43, entry_42])
        with patch("rss_episode_fetcher.feedparser.parse", return_value=feed):
            meta = fetcher.fetch_latest("https://example.com/feed.xml")
        assert meta.title == "Episode 43 - The Latest One"

    def test_itunes_episode_number_converted_to_int(self, fetcher, entry_43, entry_42):
        """iTunes episode number string '43' is returned as int 43."""
        feed = _make_parsed_feed([entry_43, entry_42])
        with patch("rss_episode_fetcher.feedparser.parse", return_value=feed):
            meta = fetcher.fetch_latest("https://example.com/feed.xml")
        assert meta.episode_number == 43
        assert isinstance(meta.episode_number, int)

    def test_itunes_duration_hh_mm_ss_converted_to_seconds(
        self, fetcher, entry_43, entry_42
    ):
        """iTunes duration '01:12:34' is converted to 4354 seconds."""
        feed = _make_parsed_feed([entry_43, entry_42])
        with patch("rss_episode_fetcher.feedparser.parse", return_value=feed):
            meta = fetcher.fetch_latest("https://example.com/feed.xml")
        assert meta.duration_seconds == 4354

    def test_description_populated(self, fetcher, entry_43, entry_42):
        """fetch_latest returns description from entry summary."""
        feed = _make_parsed_feed([entry_43, entry_42])
        with patch("rss_episode_fetcher.feedparser.parse", return_value=feed):
            meta = fetcher.fetch_latest("https://example.com/feed.xml")
        assert meta.description == "Latest episode description."

    def test_raw_seconds_duration_converted(self, fetcher, entry_42, entry_43):
        """fetch_latest with entry using raw seconds string '4354' returns 4354."""
        # Put entry_42 as "latest" by making it newer via pub_parsed
        entry_42_newer = _make_feed_entry(
            title="Episode 42 - The Previous One",
            enclosure_url="https://example.com/audio/episode-42.mp3",
            itunes_episode="42",
            itunes_duration="4354",
            pub_date="Mon, 14 Mar 2026 10:00:00 +0000",
            pub_parsed=(2027, 1, 1, 0, 0, 0, 0, 0, 0),  # make it newer
            description="Ep 42.",
        )
        feed = _make_parsed_feed([entry_43, entry_42_newer])
        with patch("rss_episode_fetcher.feedparser.parse", return_value=feed):
            meta = fetcher.fetch_latest("https://example.com/feed.xml")
        assert meta.duration_seconds == 4354

    def test_oldest_first_feed_sorted_correctly(self, fetcher, entry_43, entry_42):
        """Entries sorted by published_parsed descending — oldest-first feeds handled."""
        # entry_42 is older; even if it comes first in list, entry_43 should win
        feed = _make_parsed_feed([entry_42, entry_43])
        with patch("rss_episode_fetcher.feedparser.parse", return_value=feed):
            meta = fetcher.fetch_latest("https://example.com/feed.xml")
        assert meta.episode_number == 43

    def test_entry_without_published_parsed_does_not_crash(self, fetcher, entry_43):
        """Some feeds (e.g. Subsplash) return entries where published_parsed is
        missing. Accessing it on a real feedparser FeedParserDict raises
        AttributeError, not a falsy value — sorting must handle this via
        getattr, not truthiness."""
        from feedparser.util import FeedParserDict

        # Real feedparser entry: AttributeError on missing keys
        broken = FeedParserDict(
            title="Missing pub_parsed",
            enclosures=[{"url": "https://example.com/audio/x.mp3"}],
        )
        # No 'published_parsed' attribute — accessing raises AttributeError
        broken.get = lambda key, default=None: {
            "itunes_episode": "99",
            "itunes_duration": "00:10:00",
        }.get(key, default)

        feed = _make_parsed_feed([broken, entry_43])
        with patch("rss_episode_fetcher.feedparser.parse", return_value=feed):
            # Should not raise — the missing-pub entry should sort last
            meta = fetcher.fetch_episode("https://example.com/feed.xml", index=0)
        assert meta.episode_number == 43  # The one with a real date wins


# ---------------------------------------------------------------------------
# TestFetchEpisode
# ---------------------------------------------------------------------------


class TestFetchEpisode:
    """Tests for RSSEpisodeFetcher.fetch_episode() by index."""

    def test_index_zero_returns_latest(self, fetcher, entry_43, entry_42):
        """fetch_episode(url, index=0) returns the most recent entry."""
        feed = _make_parsed_feed([entry_43, entry_42])
        with patch("rss_episode_fetcher.feedparser.parse", return_value=feed):
            meta = fetcher.fetch_episode("https://example.com/feed.xml", index=0)
        assert meta.episode_number == 43

    def test_index_one_returns_second_entry(self, fetcher, entry_43, entry_42):
        """fetch_episode(url, index=1) returns the second-most-recent entry."""
        feed = _make_parsed_feed([entry_43, entry_42])
        with patch("rss_episode_fetcher.feedparser.parse", return_value=feed):
            meta = fetcher.fetch_episode("https://example.com/feed.xml", index=1)
        assert meta.episode_number == 42

    def test_fallback_episode_number_from_filename(self, fetcher):
        """When itunes_episode is absent, falls back to filename-based extraction."""
        entry = _make_feed_entry(
            title="Some Show",
            enclosure_url="https://example.com/audio/ep25-show.mp3",
            itunes_episode=None,
            itunes_duration=None,
            pub_parsed=(2026, 3, 28, 10, 0, 0, 0, 0, 0),
        )
        entry.get = lambda key, default=None: None  # no itunes tags
        feed = _make_parsed_feed([entry])
        with patch("rss_episode_fetcher.feedparser.parse", return_value=feed):
            meta = fetcher.fetch_episode("https://example.com/feed.xml")
        assert meta.episode_number == 25


# ---------------------------------------------------------------------------
# TestFetchLatestErrors
# ---------------------------------------------------------------------------


class TestFetchLatestErrors:
    """Tests for ValueError conditions in fetch_latest."""

    def test_raises_on_bozo_feed(self, fetcher):
        """fetch_latest raises ValueError when feedparser returns bozo=True."""
        feed = _make_parsed_feed([], bozo=True)
        with patch("rss_episode_fetcher.feedparser.parse", return_value=feed):
            with pytest.raises(ValueError, match="bozo"):
                fetcher.fetch_latest("https://example.com/bad-feed.xml")

    def test_raises_on_empty_entries(self, fetcher):
        """fetch_latest raises ValueError when feed has zero entries."""
        feed = _make_parsed_feed([], bozo=False)
        with patch("rss_episode_fetcher.feedparser.parse", return_value=feed):
            with pytest.raises(ValueError, match="[Nn]o entries"):
                fetcher.fetch_latest("https://example.com/empty-feed.xml")

    def test_raises_when_no_enclosure(self, fetcher):
        """fetch_latest raises ValueError when entry has no audio enclosure."""
        entry = _make_feed_entry(
            title="No Enclosure Episode",
            enclosure_url="https://example.com/audio/ep.mp3",
            pub_parsed=(2026, 3, 28, 10, 0, 0, 0, 0, 0),
        )
        entry.enclosures = []  # strip enclosures
        feed = _make_parsed_feed([entry])
        with patch("rss_episode_fetcher.feedparser.parse", return_value=feed):
            with pytest.raises(ValueError, match="[Nn]o audio enclosure"):
                fetcher.fetch_latest("https://example.com/feed.xml")


# ---------------------------------------------------------------------------
# TestDownloadAudio
# ---------------------------------------------------------------------------


class TestDownloadAudio:
    """Tests for RSSEpisodeFetcher.download_audio()."""

    def test_downloads_and_returns_path(self, fetcher, tmp_path):
        """download_audio streams file to dest_dir and returns Path."""
        mock_response = MagicMock()
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-length": "100"}
        mock_response.iter_content = Mock(return_value=[b"audio_data"])
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)

        with patch("rss_episode_fetcher.requests.get", return_value=mock_response):
            with patch("rss_episode_fetcher.tqdm") as mock_tqdm:
                mock_tqdm_instance = MagicMock()
                mock_tqdm_instance.__enter__ = Mock(return_value=mock_tqdm_instance)
                mock_tqdm_instance.__exit__ = Mock(return_value=False)
                mock_tqdm.return_value = mock_tqdm_instance
                result = fetcher.download_audio(
                    "https://example.com/audio/episode-43.mp3", tmp_path
                )

        assert isinstance(result, Path)
        assert result.name == "episode-43.mp3"

    def test_skips_download_if_file_exists(self, fetcher, tmp_path):
        """download_audio returns existing Path without downloading when file already exists."""
        dest = tmp_path / "episode-43.mp3"
        dest.write_bytes(b"existing_audio")

        with patch("rss_episode_fetcher.requests.get") as mock_get:
            result = fetcher.download_audio(
                "https://example.com/audio/episode-43.mp3", tmp_path
            )

        mock_get.assert_not_called()
        assert result == dest

    def test_raises_http_error_on_404(self, fetcher, tmp_path):
        """download_audio raises requests.HTTPError when server returns 404."""
        import requests

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)

        with patch("rss_episode_fetcher.requests.get", return_value=mock_response):
            with pytest.raises(requests.HTTPError):
                fetcher.download_audio(
                    "https://example.com/audio/missing.mp3", tmp_path
                )

    def test_filename_extracted_from_url_strips_query_params(self, fetcher, tmp_path):
        """Filename is extracted from URL path without query parameters."""
        mock_response = MagicMock()
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-length": "100"}
        mock_response.iter_content = Mock(return_value=[b"data"])
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)

        with patch("rss_episode_fetcher.requests.get", return_value=mock_response):
            with patch("rss_episode_fetcher.tqdm") as mock_tqdm:
                mock_tqdm_instance = MagicMock()
                mock_tqdm_instance.__enter__ = Mock(return_value=mock_tqdm_instance)
                mock_tqdm_instance.__exit__ = Mock(return_value=False)
                mock_tqdm.return_value = mock_tqdm_instance
                result = fetcher.download_audio(
                    "https://cdn.example.com/episode-43.mp3?token=abc123&expires=9999",
                    tmp_path,
                )

        assert result.name == "episode-43.mp3"


# ---------------------------------------------------------------------------
# TestExtractEpisodeNumber
# ---------------------------------------------------------------------------


class TestExtractEpisodeNumber:
    """Tests for the module-level extract_episode_number_from_filename function."""

    def test_episode_word_format(self):
        """'Episode 25 - Title.wav' returns 25."""
        assert extract_episode_number_from_filename("Episode 25 - Title.wav") == 25

    def test_ep_underscore_format(self):
        """'ep_25_title.mp3' returns 25."""
        assert extract_episode_number_from_filename("ep_25_title.mp3") == 25

    def test_ep_space_format(self):
        """'Ep 25 - Title.wav' returns 25."""
        assert extract_episode_number_from_filename("Ep 25 - Title.wav") == 25

    def test_leading_number_format(self):
        """'25 - Title.wav' returns 25."""
        assert extract_episode_number_from_filename("25 - Title.wav") == 25

    def test_hash_format(self):
        """'podcast #25.mp3' returns 25."""
        assert extract_episode_number_from_filename("podcast #25.mp3") == 25

    def test_returns_none_for_unknown_format(self):
        """'random_audio.mp3' returns None."""
        assert extract_episode_number_from_filename("random_audio.mp3") is None

    def test_returns_int_not_string(self):
        """Return type is int, not str."""
        result = extract_episode_number_from_filename("Episode 10 - Test.wav")
        assert isinstance(result, int)


# ---------------------------------------------------------------------------
# TestParseItunesDuration
# ---------------------------------------------------------------------------


class TestParseItunesDuration:
    """Tests for the _parse_itunes_duration helper."""

    def test_hh_mm_ss_format(self):
        """'01:12:34' is converted to 4354 seconds."""
        assert _parse_itunes_duration("01:12:34") == 4354

    def test_mm_ss_format(self):
        """'02:30' is converted to 150 seconds."""
        assert _parse_itunes_duration("02:30") == 150

    def test_raw_seconds_string(self):
        """'4354' as a plain string is returned as int 4354."""
        assert _parse_itunes_duration("4354") == 4354

    def test_none_returns_none(self):
        """None input returns None."""
        assert _parse_itunes_duration(None) is None

    def test_empty_string_returns_none(self):
        """Empty string returns None."""
        assert _parse_itunes_duration("") is None

    def test_non_numeric_returns_none(self):
        """Non-numeric, non-colon string returns None."""
        assert _parse_itunes_duration("unknown") is None


class TestCleanDownloadFilename:
    """_clean_download_filename replaces encoded-URL filenames with a clean hash.

    Regression guard for B022 (2026-04-22): Subsplash + anchor-cloudfront
    feeds leak base64 or URL-encoded enclosure URLs into the download
    filename, which then propagates into ep_dir and every derived asset.
    """

    def test_clean_filename_passes_through(self):
        """A normal podcast URL keeps its original filename."""
        from rss_episode_fetcher import _clean_download_filename

        url = "https://feeds.example.com/audio/episode-042.mp3"
        assert _clean_download_filename(url) == "episode-042.mp3"

    def test_base64_filename_replaced(self):
        """Subsplash-style base64-encoded filename → hash-based replacement."""
        from rss_episode_fetcher import _clean_download_filename

        url = (
            "https://podcasts.subsplash.com/wdp33ry/play/"
            "aHR0cHM6Ly9jZG4uc3Vic3BsYXNoLmNvbS9hdWRpb3MvOVc1VkNGLzFhMi5tcDM.mp3"
        )
        out = _clean_download_filename(url)
        assert out.startswith("ep_")
        assert out.endswith(".mp3")
        assert "aHR0c" not in out
        assert len(out) < 20

    def test_url_encoded_filename_replaced(self):
        """URL-encoded enclosure filename (anchor.fm to cloudfront) also cleaned."""
        from rss_episode_fetcher import _clean_download_filename

        url = (
            "https://anchor.fm/s/ac7d788/play/"
            "https%3A%2F%2Fd3ctxlq1ktw2nl.cloudfront.net%2Fstaging%2F"
            "2026-3-13%2F0c4d6f58-cf76-476f-c815-1e6fcfdf3ed8.mp3"
        )
        out = _clean_download_filename(url)
        assert out.startswith("ep_")
        assert out.endswith(".mp3")
        assert "%3A" not in out

    def test_deterministic_hash(self):
        """Same URL always produces the same filename (important for dedupe)."""
        from rss_episode_fetcher import _clean_download_filename

        url = (
            "https://podcasts.subsplash.com/wdp33ry/play/"
            "aHR0cHM6Ly9jZG4uc3Vic3BsYXNoLmNvbS9hdWRpb3MvOVc1VkNGLzFhMi5tcDM.mp3"
        )
        assert _clean_download_filename(url) == _clean_download_filename(url)

    def test_overly_long_filename_replaced(self):
        """Even non-base64 filenames get replaced if they exceed 60 chars."""
        from rss_episode_fetcher import _clean_download_filename

        url = (
            "https://example.com/path/"
            + ("this-is-a-really-long-filename-" * 3)
            + ".mp3"
        )
        out = _clean_download_filename(url)
        assert out.startswith("ep_")
        assert out.endswith(".mp3")
        assert len(out) < 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
