"""Unit tests for ProspectFinder — iTunes search, RSS enrichment, YAML scaffolding."""

import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from prospect_finder import ProspectFinder, GENRE_IDS, GENRE_DEFAULTS


# ---------------------------------------------------------------------------
# Shared sample data
# ---------------------------------------------------------------------------

SAMPLE_ITUNES_RESULT = {
    "collectionId": 123456789,
    "collectionName": "Test Comedy Podcast",
    "artistName": "Test Host",
    "feedUrl": "https://feeds.example.com/test-comedy.xml",
    "trackCount": 150,
    "primaryGenreName": "Comedy",
    "collectionViewUrl": "https://podcasts.apple.com/podcast/id123456789",
    "releaseDate": "2024-01-15T00:00:00Z",
}

SAMPLE_ITUNES_RESPONSE = {
    "resultCount": 1,
    "results": [SAMPLE_ITUNES_RESULT],
}

SAMPLE_RSS_DATA = {
    "contact_email": "host@example.com",
    "website": "https://example.com",
    "social_links": {"twitter": "https://twitter.com/testpodcast"},
    "last_pub_date": "2024-01-15",
    "episode_count": 150,
}


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


class TestModuleConstants:
    """Tests for GENRE_IDS and GENRE_DEFAULTS module constants."""

    def test_genre_ids_has_comedy(self):
        """GENRE_IDS should contain comedy key with value 1303."""
        assert GENRE_IDS["comedy"] == 1303

    def test_genre_ids_has_true_crime(self):
        """GENRE_IDS should contain true-crime key with value 1488."""
        assert GENRE_IDS["true-crime"] == 1488

    def test_genre_ids_has_business(self):
        """GENRE_IDS should contain business key with value 1321."""
        assert GENRE_IDS["business"] == 1321

    def test_genre_ids_has_technology(self):
        """GENRE_IDS should contain technology key with value 1318."""
        assert GENRE_IDS["technology"] == 1318

    def test_genre_ids_has_society(self):
        """GENRE_IDS should contain society key with value 1324."""
        assert GENRE_IDS["society"] == 1324

    def test_genre_defaults_has_comedy(self):
        """GENRE_DEFAULTS should contain comedy key with voice_persona and compliance_style."""
        assert "comedy" in GENRE_DEFAULTS
        assert "voice_persona" in GENRE_DEFAULTS["comedy"]
        assert "compliance_style" in GENRE_DEFAULTS["comedy"]
        assert "categories" in GENRE_DEFAULTS["comedy"]

    def test_genre_defaults_has_true_crime(self):
        """GENRE_DEFAULTS should contain true-crime key."""
        assert "true-crime" in GENRE_DEFAULTS
        assert GENRE_DEFAULTS["true-crime"]["compliance_style"] == "strict"

    def test_genre_defaults_has_business(self):
        """GENRE_DEFAULTS should contain business key."""
        assert "business" in GENRE_DEFAULTS
        assert GENRE_DEFAULTS["business"]["compliance_style"] == "standard"

    def test_genre_defaults_comedy_compliance_lenient(self):
        """Comedy genre should have lenient compliance style."""
        assert GENRE_DEFAULTS["comedy"]["compliance_style"] == "lenient"


# ---------------------------------------------------------------------------
# ProspectFinder init
# ---------------------------------------------------------------------------


class TestProspectFinderInit:
    """Tests for ProspectFinder.__init__."""

    def test_init_enabled_by_default(self):
        """ProspectFinder should be enabled with no credentials required."""
        finder = ProspectFinder()
        assert finder.enabled is True


# ---------------------------------------------------------------------------
# ProspectFinder.search()
# ---------------------------------------------------------------------------


class TestProspectFinderSearch:
    """Tests for ProspectFinder.search()."""

    @patch("prospect_finder.requests.get")
    def test_search_calls_itunes_api(self, mock_get):
        """search() should call the iTunes Search API endpoint."""
        mock_resp = Mock()
        mock_resp.json.return_value = SAMPLE_ITUNES_RESPONSE
        mock_get.return_value = mock_resp

        finder = ProspectFinder()
        finder.search("comedy")

        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args
        assert "itunes.apple.com/search" in call_kwargs[0][0]

    @patch("prospect_finder.requests.get")
    def test_search_passes_term_param(self, mock_get):
        """search() should pass the term parameter to the API."""
        mock_resp = Mock()
        mock_resp.json.return_value = SAMPLE_ITUNES_RESPONSE
        mock_get.return_value = mock_resp

        finder = ProspectFinder()
        finder.search("comedy")

        call_kwargs = mock_get.call_args
        params = call_kwargs[1].get(
            "params", call_kwargs[0][1] if len(call_kwargs[0]) > 1 else {}
        )
        assert params.get("term") == "comedy"

    @patch("prospect_finder.requests.get")
    def test_search_passes_media_podcast(self, mock_get):
        """search() should pass media=podcast to the API."""
        mock_resp = Mock()
        mock_resp.json.return_value = SAMPLE_ITUNES_RESPONSE
        mock_get.return_value = mock_resp

        finder = ProspectFinder()
        finder.search("comedy")

        params = mock_get.call_args[1]["params"]
        assert params.get("media") == "podcast"

    @patch("prospect_finder.requests.get")
    def test_search_passes_genre_id_when_provided(self, mock_get):
        """search() should pass genreId param when genre_id is provided."""
        mock_resp = Mock()
        mock_resp.json.return_value = SAMPLE_ITUNES_RESPONSE
        mock_get.return_value = mock_resp

        finder = ProspectFinder()
        finder.search("comedy", genre_id=1303)

        params = mock_get.call_args[1]["params"]
        assert params.get("genreId") == 1303

    @patch("prospect_finder.requests.get")
    def test_search_omits_genre_id_when_none(self, mock_get):
        """search() should omit genreId param when genre_id is None."""
        mock_resp = Mock()
        mock_resp.json.return_value = SAMPLE_ITUNES_RESPONSE
        mock_get.return_value = mock_resp

        finder = ProspectFinder()
        finder.search("comedy", genre_id=None)

        params = mock_get.call_args[1]["params"]
        assert "genreId" not in params

    @patch("prospect_finder.requests.get")
    def test_search_filters_by_min_episodes(self, mock_get):
        """search() should filter out results below min_episodes."""
        results = [
            {**SAMPLE_ITUNES_RESULT, "trackCount": 5},  # too few
            {**SAMPLE_ITUNES_RESULT, "collectionId": 2, "trackCount": 100},  # ok
        ]
        mock_resp = Mock()
        mock_resp.json.return_value = {"resultCount": 2, "results": results}
        mock_get.return_value = mock_resp

        finder = ProspectFinder()
        filtered = finder.search("comedy", min_episodes=20, max_episodes=500)

        assert len(filtered) == 1
        assert filtered[0]["trackCount"] == 100

    @patch("prospect_finder.requests.get")
    def test_search_filters_by_max_episodes(self, mock_get):
        """search() should filter out results above max_episodes."""
        results = [
            {**SAMPLE_ITUNES_RESULT, "trackCount": 100},  # ok
            {**SAMPLE_ITUNES_RESULT, "collectionId": 2, "trackCount": 999},  # too many
        ]
        mock_resp = Mock()
        mock_resp.json.return_value = {"resultCount": 2, "results": results}
        mock_get.return_value = mock_resp

        finder = ProspectFinder()
        filtered = finder.search("comedy", min_episodes=20, max_episodes=500)

        assert len(filtered) == 1
        assert filtered[0]["trackCount"] == 100

    @patch("prospect_finder.requests.get")
    def test_search_respects_limit(self, mock_get):
        """search() should return at most `limit` results."""
        results = [
            {**SAMPLE_ITUNES_RESULT, "collectionId": i, "trackCount": 100}
            for i in range(50)
        ]
        mock_resp = Mock()
        mock_resp.json.return_value = {"resultCount": 50, "results": results}
        mock_get.return_value = mock_resp

        finder = ProspectFinder()
        limited = finder.search("comedy", limit=5)

        assert len(limited) == 5

    @patch("prospect_finder.requests.get")
    def test_search_returns_empty_list_on_api_error(self, mock_get):
        """search() should return empty list on API error, not raise."""
        mock_get.side_effect = Exception("Connection error")

        finder = ProspectFinder()
        result = finder.search("comedy")

        assert result == []

    @patch("prospect_finder.requests.get")
    def test_search_returns_empty_list_on_http_error(self, mock_get):
        """search() should return empty list on HTTP error status."""
        import requests as req_module

        mock_resp = Mock()
        mock_resp.raise_for_status.side_effect = req_module.HTTPError("503")
        mock_get.return_value = mock_resp

        finder = ProspectFinder()
        result = finder.search("comedy")

        assert result == []

    @patch("prospect_finder.requests.get")
    def test_search_returns_full_result_dicts(self, mock_get):
        """search() should return the raw iTunes result dicts."""
        mock_resp = Mock()
        mock_resp.json.return_value = SAMPLE_ITUNES_RESPONSE
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        finder = ProspectFinder()
        results = finder.search("comedy", min_episodes=100, max_episodes=200)

        assert len(results) == 1
        assert results[0]["collectionName"] == "Test Comedy Podcast"
        assert results[0]["feedUrl"] == "https://feeds.example.com/test-comedy.xml"


# ---------------------------------------------------------------------------
# ProspectFinder.enrich_from_rss()
# ---------------------------------------------------------------------------


class TestEnrichFromRss:
    """Tests for ProspectFinder.enrich_from_rss()."""

    def _make_feed(
        self,
        owner_email=None,
        itunes_email=None,
        author_email=None,
        description="",
        link="",
        entries=None,
        bozo=False,
    ):
        """Build a mock feedparser result."""
        feed_dict = {
            "link": link,
            "description": description,
        }
        if owner_email is not None:
            feed_dict["itunes_owner"] = {"email": owner_email}
        if itunes_email is not None:
            feed_dict["itunes_email"] = itunes_email
        if author_email is not None:
            feed_dict["author_detail"] = {"email": author_email}

        mock_feed = Mock()
        mock_feed.feed = feed_dict
        mock_feed.bozo = bozo
        mock_feed.entries = entries or []
        return mock_feed

    @patch("prospect_finder.feedparser.parse")
    def test_enrich_extracts_email_from_itunes_owner(self, mock_parse):
        """enrich_from_rss() should extract email from itunes_owner first."""
        mock_parse.return_value = self._make_feed(owner_email="owner@example.com")

        finder = ProspectFinder()
        result = finder.enrich_from_rss("https://feeds.example.com/test.xml")

        assert result["contact_email"] == "owner@example.com"

    @patch("prospect_finder.feedparser.parse")
    def test_enrich_falls_back_to_itunes_email(self, mock_parse):
        """enrich_from_rss() should fall back to itunes_email if no owner email."""
        mock_parse.return_value = self._make_feed(itunes_email="itunes@example.com")

        finder = ProspectFinder()
        result = finder.enrich_from_rss("https://feeds.example.com/test.xml")

        assert result["contact_email"] == "itunes@example.com"

    @patch("prospect_finder.feedparser.parse")
    def test_enrich_falls_back_to_author_detail(self, mock_parse):
        """enrich_from_rss() should fall back to author_detail.email."""
        mock_parse.return_value = self._make_feed(author_email="author@example.com")

        finder = ProspectFinder()
        result = finder.enrich_from_rss("https://feeds.example.com/test.xml")

        assert result["contact_email"] == "author@example.com"

    @patch("prospect_finder.feedparser.parse")
    def test_enrich_prefers_itunes_owner_over_fallbacks(self, mock_parse):
        """enrich_from_rss() should prefer itunes_owner.email over other sources."""
        mock_parse.return_value = self._make_feed(
            owner_email="owner@example.com",
            itunes_email="itunes@example.com",
            author_email="author@example.com",
        )

        finder = ProspectFinder()
        result = finder.enrich_from_rss("https://feeds.example.com/test.xml")

        assert result["contact_email"] == "owner@example.com"

    @patch("prospect_finder.feedparser.parse")
    def test_enrich_extracts_website(self, mock_parse):
        """enrich_from_rss() should extract website from feed.link."""
        mock_parse.return_value = self._make_feed(link="https://example.com")

        finder = ProspectFinder()
        result = finder.enrich_from_rss("https://feeds.example.com/test.xml")

        assert result["website"] == "https://example.com"

    @patch("prospect_finder.feedparser.parse")
    def test_enrich_extracts_twitter_link(self, mock_parse):
        """enrich_from_rss() should extract twitter link from feed description."""
        mock_parse.return_value = self._make_feed(
            description="Follow us at twitter.com/testpodcast for updates!"
        )

        finder = ProspectFinder()
        result = finder.enrich_from_rss("https://feeds.example.com/test.xml")

        assert "twitter" in result["social_links"]
        assert "testpodcast" in result["social_links"]["twitter"]

    @patch("prospect_finder.feedparser.parse")
    def test_enrich_extracts_instagram_link(self, mock_parse):
        """enrich_from_rss() should extract instagram link from feed description."""
        mock_parse.return_value = self._make_feed(
            description="Follow us on instagram.com/testpodcast_ig"
        )

        finder = ProspectFinder()
        result = finder.enrich_from_rss("https://feeds.example.com/test.xml")

        assert "instagram" in result["social_links"]
        assert "testpodcast_ig" in result["social_links"]["instagram"]

    @patch("prospect_finder.feedparser.parse")
    def test_enrich_returns_empty_social_when_none_found(self, mock_parse):
        """enrich_from_rss() should return empty social_links dict when none found."""
        mock_parse.return_value = self._make_feed(description="No social links here.")

        finder = ProspectFinder()
        result = finder.enrich_from_rss("https://feeds.example.com/test.xml")

        assert result["social_links"] == {}

    @patch("prospect_finder.feedparser.parse")
    def test_enrich_returns_last_pub_date_iso(self, mock_parse):
        """enrich_from_rss() should return last_pub_date as ISO date string."""
        entry = Mock()
        entry.published_parsed = (2024, 1, 15, 12, 0, 0, 0, 0, 0)
        mock_parse.return_value = self._make_feed(entries=[entry])

        finder = ProspectFinder()
        result = finder.enrich_from_rss("https://feeds.example.com/test.xml")

        assert result["last_pub_date"] == "2024-01-15"

    @patch("prospect_finder.feedparser.parse")
    def test_enrich_returns_none_last_pub_when_no_entries(self, mock_parse):
        """enrich_from_rss() should return None for last_pub_date when no entries."""
        mock_parse.return_value = self._make_feed(entries=[])

        finder = ProspectFinder()
        result = finder.enrich_from_rss("https://feeds.example.com/test.xml")

        assert result["last_pub_date"] is None

    @patch("prospect_finder.feedparser.parse")
    def test_enrich_returns_episode_count(self, mock_parse):
        """enrich_from_rss() should return episode_count from len(feed.entries)."""
        entries = [Mock() for _ in range(75)]
        for e in entries:
            e.get = lambda k, d=None: None
        mock_parse.return_value = self._make_feed(entries=entries)

        finder = ProspectFinder()
        result = finder.enrich_from_rss("https://feeds.example.com/test.xml")

        assert result["episode_count"] == 75

    @patch("prospect_finder.feedparser.parse")
    def test_enrich_handles_bozo_feed_gracefully(self, mock_parse):
        """enrich_from_rss() should log warning on bozo feed but continue parsing."""
        mock_parse.return_value = self._make_feed(
            owner_email="host@example.com",
            bozo=True,
        )

        finder = ProspectFinder()
        result = finder.enrich_from_rss("https://feeds.example.com/test.xml")

        # Should still return data despite bozo flag
        assert result["contact_email"] == "host@example.com"

    @patch("prospect_finder.feedparser.parse")
    def test_enrich_returns_empty_dict_on_parse_failure(self, mock_parse):
        """enrich_from_rss() should return empty dict on total parse failure."""
        mock_parse.side_effect = Exception("Parse failed")

        finder = ProspectFinder()
        result = finder.enrich_from_rss("https://feeds.example.com/test.xml")

        assert result == {}

    @patch("prospect_finder.feedparser.parse")
    def test_enrich_returns_none_email_when_not_found(self, mock_parse):
        """enrich_from_rss() should return None for contact_email when not found."""
        mock_parse.return_value = self._make_feed()

        finder = ProspectFinder()
        result = finder.enrich_from_rss("https://feeds.example.com/test.xml")

        assert result["contact_email"] is None


# ---------------------------------------------------------------------------
# ProspectFinder._genre_key_from_name()
# ---------------------------------------------------------------------------


class TestGenreKeyFromName:
    """Tests for ProspectFinder._genre_key_from_name()."""

    def test_maps_comedy_to_comedy(self):
        """'Comedy' should map to 'comedy'."""
        finder = ProspectFinder()
        assert finder._genre_key_from_name("Comedy") == "comedy"

    def test_maps_true_crime_to_true_crime(self):
        """'True Crime' should map to 'true-crime'."""
        finder = ProspectFinder()
        assert finder._genre_key_from_name("True Crime") == "true-crime"

    def test_maps_business_to_business(self):
        """'Business' should map to 'business'."""
        finder = ProspectFinder()
        assert finder._genre_key_from_name("Business") == "business"

    def test_returns_none_for_unknown_genre(self):
        """Unknown genre names should return None."""
        finder = ProspectFinder()
        assert finder._genre_key_from_name("Cooking") is None

    def test_case_insensitive_mapping(self):
        """Genre name mapping should be case-insensitive."""
        finder = ProspectFinder()
        assert finder._genre_key_from_name("COMEDY") == "comedy"


# ---------------------------------------------------------------------------
# ProspectFinder.save_prospect()
# ---------------------------------------------------------------------------


class TestSaveProspect:
    """Tests for ProspectFinder.save_prospect()."""

    @pytest.fixture
    def mock_tracker(self):
        """Mock OutreachTracker instance."""
        tracker = Mock()
        tracker.add_prospect.return_value = True
        return tracker

    @pytest.fixture
    def itunes_data(self):
        """Sample iTunes result dict."""
        return SAMPLE_ITUNES_RESULT.copy()

    @pytest.fixture
    def rss_data(self):
        """Sample RSS enrichment dict."""
        return SAMPLE_RSS_DATA.copy()

    def _make_minimal_yaml(self):
        """Return a minimal YAML string that satisfies load_client_config requirements."""
        return "podcast_name: Test Comedy Podcast\ncontent:\n  names_to_remove: []\n"

    @patch("prospect_finder.OutreachTracker")
    @patch("prospect_finder.init_client")
    def test_save_prospect_calls_init_client_when_yaml_missing(
        self, mock_init, mock_tracker_cls, tmp_path, itunes_data, rss_data
    ):
        """save_prospect() should call init_client() when YAML does not exist."""
        mock_tracker_cls.return_value = Mock()
        mock_tracker_cls.return_value.add_prospect.return_value = True

        # init_client should create the YAML when called
        def create_yaml(name):
            clients_dir = tmp_path / "clients"
            clients_dir.mkdir(exist_ok=True)
            yaml_path = clients_dir / f"{name}.yaml"
            yaml_path.write_text(self._make_minimal_yaml(), encoding="utf-8")

        mock_init.side_effect = create_yaml

        with patch("prospect_finder.Config") as mock_config:
            mock_config.BASE_DIR = tmp_path
            finder = ProspectFinder()
            finder.save_prospect("test-comedy", itunes_data, rss_data)

        mock_init.assert_called_once_with("test-comedy")

    @patch("prospect_finder.OutreachTracker")
    @patch("prospect_finder.init_client")
    def test_save_prospect_does_not_call_init_client_when_yaml_exists(
        self, mock_init, mock_tracker_cls, tmp_path, itunes_data, rss_data
    ):
        """save_prospect() should not call init_client() when YAML already exists."""
        mock_tracker_cls.return_value = Mock()
        mock_tracker_cls.return_value.add_prospect.return_value = True

        # Pre-create the YAML
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        yaml_path = clients_dir / "test-comedy.yaml"
        yaml_path.write_text(self._make_minimal_yaml(), encoding="utf-8")

        with patch("prospect_finder.Config") as mock_config:
            mock_config.BASE_DIR = tmp_path
            finder = ProspectFinder()
            finder.save_prospect("test-comedy", itunes_data, rss_data)

        mock_init.assert_not_called()

    @patch("prospect_finder.OutreachTracker")
    @patch("prospect_finder.init_client")
    def test_save_prospect_writes_prospect_block(
        self, mock_init, mock_tracker_cls, tmp_path, itunes_data, rss_data
    ):
        """save_prospect() should write a prospect: block to the YAML."""
        import yaml

        mock_tracker_cls.return_value = Mock()
        mock_tracker_cls.return_value.add_prospect.return_value = True

        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        yaml_path = clients_dir / "test-comedy.yaml"
        yaml_path.write_text(self._make_minimal_yaml(), encoding="utf-8")

        with patch("prospect_finder.Config") as mock_config:
            mock_config.BASE_DIR = tmp_path
            finder = ProspectFinder()
            finder.save_prospect("test-comedy", itunes_data, rss_data)

        saved = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert "prospect" in saved
        assert saved["prospect"]["itunes_id"] == str(itunes_data["collectionId"])
        assert saved["prospect"]["feed_url"] == itunes_data["feedUrl"]
        assert saved["prospect"]["episode_count"] == itunes_data["trackCount"]

    @patch("prospect_finder.OutreachTracker")
    @patch("prospect_finder.init_client")
    def test_save_prospect_writes_contact_info(
        self, mock_init, mock_tracker_cls, tmp_path, itunes_data, rss_data
    ):
        """save_prospect() should write contact_email and website from rss_data."""
        import yaml

        mock_tracker_cls.return_value = Mock()
        mock_tracker_cls.return_value.add_prospect.return_value = True

        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        yaml_path = clients_dir / "test-comedy.yaml"
        yaml_path.write_text(self._make_minimal_yaml(), encoding="utf-8")

        with patch("prospect_finder.Config") as mock_config:
            mock_config.BASE_DIR = tmp_path
            finder = ProspectFinder()
            finder.save_prospect("test-comedy", itunes_data, rss_data)

        saved = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert saved["prospect"]["contact_email"] == rss_data["contact_email"]
        assert saved["prospect"]["website"] == rss_data["website"]

    @patch("prospect_finder.OutreachTracker")
    @patch("prospect_finder.init_client")
    def test_save_prospect_sets_episode_source_rss(
        self, mock_init, mock_tracker_cls, tmp_path, itunes_data, rss_data
    ):
        """save_prospect() should set episode_source=rss and rss_source.feed_url."""
        import yaml

        mock_tracker_cls.return_value = Mock()
        mock_tracker_cls.return_value.add_prospect.return_value = True

        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        yaml_path = clients_dir / "test-comedy.yaml"
        yaml_path.write_text(self._make_minimal_yaml(), encoding="utf-8")

        with patch("prospect_finder.Config") as mock_config:
            mock_config.BASE_DIR = tmp_path
            finder = ProspectFinder()
            finder.save_prospect("test-comedy", itunes_data, rss_data)

        saved = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert saved.get("episode_source") == "rss"
        assert saved.get("rss_source", {}).get("feed_url") == itunes_data["feedUrl"]

    @patch("prospect_finder.OutreachTracker")
    @patch("prospect_finder.init_client")
    def test_save_prospect_prefills_genre_defaults(
        self, mock_init, mock_tracker_cls, tmp_path, itunes_data, rss_data
    ):
        """save_prospect() should pre-fill voice_persona and compliance_style from GENRE_DEFAULTS."""
        import yaml

        mock_tracker_cls.return_value = Mock()
        mock_tracker_cls.return_value.add_prospect.return_value = True

        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        yaml_path = clients_dir / "test-comedy.yaml"
        yaml_path.write_text(self._make_minimal_yaml(), encoding="utf-8")

        with patch("prospect_finder.Config") as mock_config:
            mock_config.BASE_DIR = tmp_path
            finder = ProspectFinder()
            finder.save_prospect(
                "test-comedy", itunes_data, rss_data, genre_key="comedy"
            )

        saved = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        content = saved.get("content", {})
        assert content.get("voice_persona") == GENRE_DEFAULTS["comedy"]["voice_persona"]
        assert content.get("compliance_style") == "lenient"

    @patch("prospect_finder.OutreachTracker")
    @patch("prospect_finder.init_client")
    def test_save_prospect_no_genre_defaults_when_genre_key_none(
        self, mock_init, mock_tracker_cls, tmp_path, itunes_data, rss_data
    ):
        """save_prospect() should not overwrite content settings when genre_key is None."""
        import yaml

        mock_tracker_cls.return_value = Mock()
        mock_tracker_cls.return_value.add_prospect.return_value = True

        original_yaml = (
            "podcast_name: Test Comedy Podcast\n"
            "content:\n"
            "  names_to_remove: []\n"
            "  voice_persona: Custom persona here\n"
        )
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        yaml_path = clients_dir / "test-comedy.yaml"
        yaml_path.write_text(original_yaml, encoding="utf-8")

        with patch("prospect_finder.Config") as mock_config:
            mock_config.BASE_DIR = tmp_path
            finder = ProspectFinder()
            finder.save_prospect("test-comedy", itunes_data, rss_data, genre_key=None)

        saved = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        # Original voice_persona should be preserved
        assert saved["content"]["voice_persona"] == "Custom persona here"

    @patch("prospect_finder.OutreachTracker")
    @patch("prospect_finder.init_client")
    def test_save_prospect_registers_in_outreach_tracker(
        self, mock_init, mock_tracker_cls, tmp_path, itunes_data, rss_data
    ):
        """save_prospect() should call OutreachTracker.add_prospect() at 'identified' status."""
        mock_tracker = Mock()
        mock_tracker.add_prospect.return_value = True
        mock_tracker_cls.return_value = mock_tracker

        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        yaml_path = clients_dir / "test-comedy.yaml"
        yaml_path.write_text(self._make_minimal_yaml(), encoding="utf-8")

        with patch("prospect_finder.Config") as mock_config:
            mock_config.BASE_DIR = tmp_path
            finder = ProspectFinder()
            finder.save_prospect("test-comedy", itunes_data, rss_data)

        mock_tracker.add_prospect.assert_called_once()
        call_args = mock_tracker.add_prospect.call_args
        slug_arg = call_args[0][0]
        data_arg = call_args[0][1]
        assert slug_arg == "test-comedy"
        assert data_arg.get("status") == "identified"

    @patch("prospect_finder.OutreachTracker")
    @patch("prospect_finder.init_client")
    def test_save_prospect_returns_yaml_path(
        self, mock_init, mock_tracker_cls, tmp_path, itunes_data, rss_data
    ):
        """save_prospect() should return the Path to the YAML file."""
        mock_tracker_cls.return_value = Mock()
        mock_tracker_cls.return_value.add_prospect.return_value = True

        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        yaml_path = clients_dir / "test-comedy.yaml"
        yaml_path.write_text(self._make_minimal_yaml(), encoding="utf-8")

        with patch("prospect_finder.Config") as mock_config:
            mock_config.BASE_DIR = tmp_path
            finder = ProspectFinder()
            result = finder.save_prospect("test-comedy", itunes_data, rss_data)

        assert isinstance(result, Path)
        assert result.name == "test-comedy.yaml"

    @patch("prospect_finder.OutreachTracker")
    @patch("prospect_finder.init_client")
    def test_save_prospect_is_idempotent(
        self, mock_init, mock_tracker_cls, tmp_path, itunes_data, rss_data
    ):
        """save_prospect() called twice with same slug should not error."""
        mock_tracker_cls.return_value = Mock()
        mock_tracker_cls.return_value.add_prospect.return_value = (
            False  # already exists
        )

        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        yaml_path = clients_dir / "test-comedy.yaml"
        yaml_path.write_text(self._make_minimal_yaml(), encoding="utf-8")

        with patch("prospect_finder.Config") as mock_config:
            mock_config.BASE_DIR = tmp_path
            finder = ProspectFinder()
            # Call twice — should not raise
            finder.save_prospect("test-comedy", itunes_data, rss_data)
            result = finder.save_prospect("test-comedy", itunes_data, rss_data)

        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
