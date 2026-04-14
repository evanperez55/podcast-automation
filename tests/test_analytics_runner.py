"""Tests for pipeline/analytics_runner.py — analytics CLI + backfill commands."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from pipeline import analytics_runner as ar


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_output_dir(tmp_path, monkeypatch):
    """Point Config.OUTPUT_DIR at a tmp directory."""
    from config import Config

    monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def fake_collector():
    c = MagicMock()
    c._load_platform_ids.return_value = {"youtube": "abc123"}
    c.collect_analytics.return_value = {
        "youtube": {"views": 100, "likes": 10},
        "twitter": {"impressions": 200, "engagements": 20},
    }
    return c


@pytest.fixture
def fake_scorer():
    s = MagicMock()
    s.calculate_engagement_score.return_value = 7.5
    return s


# ---------------------------------------------------------------------------
# run_analytics
# ---------------------------------------------------------------------------


class TestRunAnalytics:
    def test_single_episode_by_number(
        self, mock_output_dir, fake_collector, fake_scorer, capsys
    ):
        with (
            patch("analytics.AnalyticsCollector", return_value=fake_collector),
            patch("analytics.TopicEngagementScorer", return_value=fake_scorer),
        ):
            ar.run_analytics("25")

        out = capsys.readouterr().out
        assert "ANALYTICS FEEDBACK LOOP" in out
        assert "Episode 25" in out
        fake_collector.collect_analytics.assert_called_once()
        # episode_number arg should be 25, video_id picked up from platform_ids
        call_kwargs = fake_collector.collect_analytics.call_args
        assert (
            call_kwargs.args[0] == 25 or call_kwargs.kwargs.get("episode_number") == 25
        )

    def test_accepts_ep_prefixed_arg(
        self, mock_output_dir, fake_collector, fake_scorer, capsys
    ):
        """'ep25' and '25' should both resolve to episode 25."""
        with (
            patch("analytics.AnalyticsCollector", return_value=fake_collector),
            patch("analytics.TopicEngagementScorer", return_value=fake_scorer),
        ):
            ar.run_analytics("ep25")
        # Collector was called once with 25
        fake_collector.collect_analytics.assert_called_once()

    def test_invalid_episode_arg(
        self, mock_output_dir, fake_collector, fake_scorer, capsys
    ):
        with (
            patch("analytics.AnalyticsCollector", return_value=fake_collector),
            patch("analytics.TopicEngagementScorer", return_value=fake_scorer),
        ):
            ar.run_analytics("not-a-number")
        out = capsys.readouterr().out
        assert "Invalid episode" in out
        fake_collector.collect_analytics.assert_not_called()

    def test_all_episodes(self, mock_output_dir, fake_collector, fake_scorer, capsys):
        """'all' iterates every ep_N directory."""
        (mock_output_dir / "ep_10").mkdir()
        (mock_output_dir / "ep_20").mkdir()
        (mock_output_dir / "ep_30").mkdir()
        (mock_output_dir / "unrelated").mkdir()  # should NOT be processed

        with (
            patch("analytics.AnalyticsCollector", return_value=fake_collector),
            patch("analytics.TopicEngagementScorer", return_value=fake_scorer),
        ):
            ar.run_analytics("all")

        assert fake_collector.collect_analytics.call_count == 3

    def test_prints_platform_metrics(
        self, mock_output_dir, fake_collector, fake_scorer, capsys
    ):
        with (
            patch("analytics.AnalyticsCollector", return_value=fake_collector),
            patch("analytics.TopicEngagementScorer", return_value=fake_scorer),
        ):
            ar.run_analytics("5")
        out = capsys.readouterr().out
        assert "YouTube: 100 views" in out
        assert "Twitter: 200 impressions" in out
        assert "7.5/10" in out


# ---------------------------------------------------------------------------
# _load_episode_topics
# ---------------------------------------------------------------------------


class TestLoadEpisodeTopics:
    def test_returns_empty_when_ep_dir_missing(self, mock_output_dir):
        result = ar._load_episode_topics(99)
        assert result == []

    def test_returns_empty_when_no_analysis_file(self, mock_output_dir):
        (mock_output_dir / "ep_5").mkdir()
        assert ar._load_episode_topics(5) == []

    def test_extracts_suggested_titles(self, mock_output_dir):
        ep_dir = mock_output_dir / "ep_5"
        ep_dir.mkdir()
        analysis = {
            "best_clips": [
                {"suggested_title": "Clip A"},
                {"suggested_title": "Clip B"},
                {"suggested_title": "Clip C"},
            ]
        }
        (ep_dir / "foo_analysis.json").write_text(
            json.dumps(analysis), encoding="utf-8"
        )
        assert ar._load_episode_topics(5) == ["Clip A", "Clip B", "Clip C"]

    def test_falls_back_to_title_key(self, mock_output_dir):
        ep_dir = mock_output_dir / "ep_7"
        ep_dir.mkdir()
        analysis = {"best_clips": [{"title": "Fallback Title"}]}
        (ep_dir / "foo_analysis.json").write_text(
            json.dumps(analysis), encoding="utf-8"
        )
        assert ar._load_episode_topics(7) == ["Fallback Title"]

    def test_skips_clips_without_title(self, mock_output_dir):
        ep_dir = mock_output_dir / "ep_8"
        ep_dir.mkdir()
        analysis = {
            "best_clips": [{"suggested_title": ""}, {"suggested_title": "Real"}]
        }
        (ep_dir / "foo_analysis.json").write_text(
            json.dumps(analysis), encoding="utf-8"
        )
        assert ar._load_episode_topics(8) == ["Real"]

    def test_malformed_json_returns_empty(self, mock_output_dir):
        ep_dir = mock_output_dir / "ep_9"
        ep_dir.mkdir()
        (ep_dir / "bad_analysis.json").write_text("{not json", encoding="utf-8")
        assert ar._load_episode_topics(9) == []

    def test_picks_most_recent_analysis_file(self, mock_output_dir):
        """When multiple *_analysis.json exist, takes the last one alphabetically."""
        ep_dir = mock_output_dir / "ep_10"
        ep_dir.mkdir()
        (ep_dir / "a_analysis.json").write_text(
            json.dumps({"best_clips": [{"suggested_title": "Old"}]}), encoding="utf-8"
        )
        (ep_dir / "z_analysis.json").write_text(
            json.dumps({"best_clips": [{"suggested_title": "New"}]}), encoding="utf-8"
        )
        assert ar._load_episode_topics(10) == ["New"]


# ---------------------------------------------------------------------------
# run_backfill_ids
# ---------------------------------------------------------------------------


class TestRunBackfillIds:
    def test_no_output_dir(self, tmp_path, monkeypatch, capsys):
        from config import Config

        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path / "nonexistent")

        fake_collector = MagicMock()
        fake_collector._build_youtube_client.return_value = MagicMock()
        with patch("analytics.AnalyticsCollector", return_value=fake_collector):
            ar.run_backfill_ids()

        out = capsys.readouterr().out
        assert "No output directory" in out

    def test_no_episode_dirs(self, mock_output_dir, capsys):
        fake_collector = MagicMock()
        fake_collector._build_youtube_client.return_value = MagicMock()
        with patch("analytics.AnalyticsCollector", return_value=fake_collector):
            ar.run_backfill_ids()

        out = capsys.readouterr().out
        assert "No episode directories" in out

    def test_youtube_client_build_failure(self, mock_output_dir, capsys):
        fake_collector = MagicMock()
        fake_collector._build_youtube_client.return_value = None
        with patch("analytics.AnalyticsCollector", return_value=fake_collector):
            ar.run_backfill_ids()

        out = capsys.readouterr().out
        assert "Cannot build YouTube client" in out

    def test_skips_existing_platform_ids(self, mock_output_dir, capsys):
        ep_dir = mock_output_dir / "ep_5"
        ep_dir.mkdir()
        (ep_dir / "platform_ids.json").write_text('{"youtube": "x"}', encoding="utf-8")

        fake_yt = MagicMock()
        fake_collector = MagicMock()
        fake_collector._build_youtube_client.return_value = fake_yt
        with (
            patch("analytics.AnalyticsCollector", return_value=fake_collector),
            patch("time.sleep"),
        ):  # skip the 1.5s rate-limit in tests
            ar.run_backfill_ids()

        out = capsys.readouterr().out
        assert "[SKIP] ep_5" in out
        fake_yt.search.assert_not_called()

    def test_writes_platform_ids_from_search(
        self, mock_output_dir, capsys, monkeypatch
    ):
        monkeypatch.setenv("YOUTUBE_CHANNEL_ID", "UCtestchannel")
        (mock_output_dir / "ep_7").mkdir()

        fake_yt = MagicMock()
        fake_yt.search().list().execute.return_value = {
            "items": [{"id": {"videoId": "vid_xyz"}}]
        }
        fake_collector = MagicMock()
        fake_collector._build_youtube_client.return_value = fake_yt

        with (
            patch("analytics.AnalyticsCollector", return_value=fake_collector),
            patch("time.sleep"),
        ):
            ar.run_backfill_ids()

        platform_ids = json.loads(
            (mock_output_dir / "ep_7" / "platform_ids.json").read_text(encoding="utf-8")
        )
        assert platform_ids == {"youtube": "vid_xyz", "twitter": None}

    def test_writes_none_when_search_returns_empty(self, mock_output_dir, monkeypatch):
        monkeypatch.setenv("YOUTUBE_CHANNEL_ID", "UCx")
        (mock_output_dir / "ep_8").mkdir()

        fake_yt = MagicMock()
        fake_yt.search().list().execute.return_value = {"items": []}
        fake_collector = MagicMock()
        fake_collector._build_youtube_client.return_value = fake_yt

        with (
            patch("analytics.AnalyticsCollector", return_value=fake_collector),
            patch("time.sleep"),
        ):
            ar.run_backfill_ids()

        platform_ids = json.loads(
            (mock_output_dir / "ep_8" / "platform_ids.json").read_text(encoding="utf-8")
        )
        assert platform_ids == {"youtube": None, "twitter": None}

    def test_api_exception_does_not_abort_backfill(
        self, mock_output_dir, monkeypatch, capsys
    ):
        """One episode's API failure shouldn't prevent others from processing."""
        monkeypatch.setenv("YOUTUBE_CHANNEL_ID", "UCx")
        (mock_output_dir / "ep_10").mkdir()
        (mock_output_dir / "ep_11").mkdir()

        call_count = {"n": 0}

        def search_side_effect(*args, **kwargs):
            return MagicMock()

        fake_yt = MagicMock()

        def execute_side_effect():
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("api limit")
            return {"items": [{"id": {"videoId": "ok_vid"}}]}

        fake_yt.search.return_value.list.return_value.execute.side_effect = (
            execute_side_effect
        )
        fake_collector = MagicMock()
        fake_collector._build_youtube_client.return_value = fake_yt

        with (
            patch("analytics.AnalyticsCollector", return_value=fake_collector),
            patch("time.sleep"),
        ):
            ar.run_backfill_ids()

        # Both episodes produced a platform_ids.json
        assert (mock_output_dir / "ep_10" / "platform_ids.json").exists()
        assert (mock_output_dir / "ep_11" / "platform_ids.json").exists()
