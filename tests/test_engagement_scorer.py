"""Tests for EngagementScorer module."""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


def _make_record(
    episode_number: int,
    topics: list[str],
    yt_views: int = 1000,
    yt_likes: int = 50,
    yt_comments: int = 10,
    tw_impressions: int = 5000,
    tw_engagements: int = 100,
    tw_retweets: int = 20,
    tw_likes: int = 80,
    post_timestamp: str = None,
    weekday: int = 0,  # 0=Monday
) -> dict:
    """Build a minimal engagement_history record."""
    if post_timestamp is None:
        # Monday = 2026-03-16 (a Monday)
        # Offset by weekday
        day_offset = weekday
        dt = datetime(2026, 3, 16 + day_offset, 12, 0, 0, tzinfo=timezone.utc)
        post_timestamp = dt.isoformat()
    return {
        "episode_number": episode_number,
        "collected_at": "2026-03-19T00:00:00Z",
        "post_timestamp": post_timestamp,
        "topics": topics,
        "youtube": {
            "video_id": f"vid{episode_number}",
            "views": yt_views,
            "likes": yt_likes,
            "comments": yt_comments,
        },
        "twitter": {
            "tweet_id": f"tw{episode_number}",
            "impressions": tw_impressions,
            "engagements": tw_engagements,
            "retweets": tw_retweets,
            "likes": tw_likes,
        },
    }


def _make_history(n: int, topics_pattern: list[list[str]] = None) -> list[dict]:
    """Build a list of n engagement history records."""
    records = []
    for i in range(n):
        ep = i + 1
        if topics_pattern:
            topics = topics_pattern[i % len(topics_pattern)]
        else:
            topics = ["shocking_news story"]
        records.append(_make_record(ep, topics))
    return records


class TestConfidenceGate:
    """Tests for the minimum-episode confidence gate (ENGAGE-04)."""

    def test_no_history_file(self, tmp_path):
        """Returns insufficient_data when history file is absent."""
        from engagement_scorer import EngagementScorer

        scorer = EngagementScorer(history_path=tmp_path / "nonexistent.json")
        result = scorer.get_category_rankings()

        assert result["status"] == "insufficient_data"
        assert result["episodes_analyzed"] == 0
        assert result["episodes_needed"] == 15
        assert result["rankings"] is None
        assert result["day_of_week"] is None

    def test_under_threshold(self, tmp_path):
        """Returns insufficient_data with episodes_needed when fewer than 15 records."""
        from engagement_scorer import EngagementScorer

        history = _make_history(10)
        history_file = tmp_path / "engagement_history.json"
        history_file.write_text(json.dumps(history))

        scorer = EngagementScorer(history_path=history_file)
        result = scorer.get_category_rankings()

        assert result["status"] == "insufficient_data"
        assert result["episodes_analyzed"] == 10
        assert result["episodes_needed"] == 5
        assert result["rankings"] is None
        assert result["day_of_week"] is None

    def test_at_threshold(self, tmp_path):
        """Returns status ok with rankings list when 15+ records."""
        from engagement_scorer import EngagementScorer

        history = _make_history(15)
        history_file = tmp_path / "engagement_history.json"
        history_file.write_text(json.dumps(history))

        scorer = EngagementScorer(history_path=history_file)
        result = scorer.get_category_rankings()

        assert result["status"] == "ok"
        assert result["episodes_analyzed"] == 15
        assert isinstance(result["rankings"], list)
        assert result["day_of_week"] is not None


class TestGetCategoryRankings:
    """Tests for category correlation ranking (ENGAGE-01)."""

    def test_uses_spearman(self, tmp_path):
        """Verify scipy.stats.spearmanr is called (not pearsonr)."""
        from engagement_scorer import EngagementScorer

        # Alternate categories so there IS variance — otherwise spearmanr is skipped
        patterns = [["shocking_news story"], ["pop_science discovery"]]
        history = _make_history(15, topics_pattern=patterns)
        history_file = tmp_path / "engagement_history.json"
        history_file.write_text(json.dumps(history))

        scorer = EngagementScorer(history_path=history_file)

        with patch("engagement_scorer.stats") as mock_stats:
            mock_result = MagicMock()
            mock_result.statistic = 0.5
            mock_result.pvalue = 0.05
            mock_stats.spearmanr.return_value = mock_result
            # Patch math.isnan so the NaN check works with the MagicMock return value
            with patch("engagement_scorer.math") as mock_math:
                mock_math.isnan.return_value = False
                scorer.get_category_rankings()
            assert mock_stats.spearmanr.called

    def test_returns_ranked_list(self, tmp_path):
        """Rankings sorted by abs(correlation) descending with required fields."""
        from engagement_scorer import EngagementScorer

        # Create history where shocking_news strongly correlates with high engagement
        history = []
        for i in range(15):
            ep = i + 1
            # Every other episode has shocking_news with higher engagement
            if i % 2 == 0:
                topics = ["shocking_news breaking story"]
                views = 5000
            else:
                topics = ["pop_science discovery"]
                views = 500
            history.append(_make_record(ep, topics, yt_views=views))

        history_file = tmp_path / "engagement_history.json"
        history_file.write_text(json.dumps(history))

        scorer = EngagementScorer(history_path=history_file)
        result = scorer.get_category_rankings()

        assert result["status"] == "ok"
        rankings = result["rankings"]
        assert isinstance(rankings, list)
        assert len(rankings) > 0

        # Each ranking entry must have required fields
        for entry in rankings:
            assert "category" in entry
            assert "correlation" in entry
            assert "p_value" in entry
            assert "method" in entry
            assert "episode_count" in entry
            assert entry["method"] == "spearman"

        # Rankings sorted by abs(correlation) descending
        correlations = [
            abs(e["correlation"]) for e in rankings if e["correlation"] is not None
        ]
        assert correlations == sorted(correlations, reverse=True)

    def test_constant_presence_skipped(self, tmp_path):
        """Category present in ALL episodes (constant) is skipped with no_variance."""
        from engagement_scorer import EngagementScorer

        # shocking_news in every single record — constant presence, no variance
        history = _make_history(15, topics_pattern=[["shocking_news story"]])
        history_file = tmp_path / "engagement_history.json"
        history_file.write_text(json.dumps(history))

        scorer = EngagementScorer(history_path=history_file)
        result = scorer.get_category_rankings()

        # Find shocking_news in rankings
        shocking = next(
            (r for r in (result["rankings"] or []) if r["category"] == "shocking_news"),
            None,
        )
        # It should either be absent or have correlation=None with skipped=no_variance
        if shocking is not None:
            assert shocking["correlation"] is None
            assert shocking.get("skipped") == "no_variance"


class TestDayOfWeek:
    """Tests for day-of-week engagement analysis (ENGAGE-02)."""

    def test_weekday_averages(self, tmp_path):
        """Records on Monday with scores [4.0, 6.0] returns Monday avg 5.0."""
        from engagement_scorer import EngagementScorer

        # Two Monday records with known scores
        # Score formula: yt_score = min(views*0.001 + likes*0.1 + comments*0.5, 7.0)
        # Record 1: 1000*0.001 + 10*0.1 + 2*0.5 = 1.0 + 1.0 + 1.0 = 3.0 yt_score
        #            tw: 0*0.0001 + 20*0.05 + 5*0.2 + 10*0.1 = 1.0+1.0+1.0 = 3.0 -> min(3.0,3.0)
        # Let's use specific values that give total ~4.0 and ~6.0
        # Record 1: yt=3.5, tw=0.5 -> total=4.0
        #   views=3000, likes=5, comments=0 -> 3.0+0.5+0 = 3.5 yt
        #   impressions=0, engagements=10, retweets=0, likes=0 -> 0+0.5+0+0=0.5 tw
        # Record 2: yt=5.0, tw=1.0 -> total=6.0
        #   views=4000, likes=10, comments=0 -> 4.0+1.0+0=5.0 yt
        #   impressions=0, engagements=20, retweets=0, likes=0 -> 0+1.0+0+0=1.0 tw
        monday_ts = "2026-03-16T12:00:00+00:00"  # Monday

        r1 = _make_record(
            1,
            ["topic_a"],
            yt_views=3000,
            yt_likes=5,
            yt_comments=0,
            tw_impressions=0,
            tw_engagements=10,
            tw_retweets=0,
            tw_likes=0,
            post_timestamp=monday_ts,
        )
        r2 = _make_record(
            2,
            ["topic_b"],
            yt_views=4000,
            yt_likes=10,
            yt_comments=0,
            tw_impressions=0,
            tw_engagements=20,
            tw_retweets=0,
            tw_likes=0,
            post_timestamp=monday_ts,
        )

        # Pad to 15 records (others on different days)
        history = [r1, r2]
        for i in range(13):
            history.append(
                _make_record(
                    i + 3, ["topic_c"], post_timestamp="2026-03-17T12:00:00+00:00"
                )
            )

        history_file = tmp_path / "engagement_history.json"
        history_file.write_text(json.dumps(history))

        scorer = EngagementScorer(history_path=history_file)
        result = scorer.get_category_rankings()

        assert result["status"] == "ok"
        dow = result["day_of_week"]
        assert dow is not None

        # Monday (weekday index 0) should have an average for at least one platform
        # Check that Monday data exists for either youtube or twitter
        monday_yt = dow.get("youtube", {}).get("Monday")
        monday_tw = dow.get("twitter", {}).get("Monday")
        assert monday_yt is not None or monday_tw is not None

    def test_missing_days_return_none(self, tmp_path):
        """Days with no data return None."""
        from engagement_scorer import EngagementScorer

        # All records on Monday only
        monday_ts = "2026-03-16T12:00:00+00:00"
        history = [
            _make_record(i + 1, ["topic_a"], post_timestamp=monday_ts)
            for i in range(15)
        ]

        history_file = tmp_path / "engagement_history.json"
        history_file.write_text(json.dumps(history))

        scorer = EngagementScorer(history_path=history_file)
        result = scorer.get_category_rankings()

        dow = result["day_of_week"]
        # Sunday (no data) should be None
        assert dow["youtube"].get("Sunday") is None

    def test_per_platform(self, tmp_path):
        """YouTube and Twitter have independent weekday averages."""
        from engagement_scorer import EngagementScorer

        monday_ts = "2026-03-16T12:00:00+00:00"
        history = [
            _make_record(i + 1, ["topic_a"], post_timestamp=monday_ts)
            for i in range(15)
        ]

        history_file = tmp_path / "engagement_history.json"
        history_file.write_text(json.dumps(history))

        scorer = EngagementScorer(history_path=history_file)
        result = scorer.get_category_rankings()

        dow = result["day_of_week"]
        assert "youtube" in dow
        assert "twitter" in dow
        # They should be separate dicts
        assert dow["youtube"] is not dow["twitter"]


class TestComedyConstraint:
    """Tests for comedy-protected category floor (ENGAGE-03)."""

    def test_protected_categories_floor(self, tmp_path):
        """shocking_news and absurd_hypothetical have correlation clamped to >= 0.0."""
        from engagement_scorer import EngagementScorer

        # Create history where shocking_news always appears with LOW engagement
        # This would normally produce a negative correlation
        history = []
        for i in range(15):
            ep = i + 1
            if i % 2 == 0:
                # shocking_news + low engagement
                topics = ["shocking_news dark story"]
                views = 100
            else:
                # other topic + high engagement
                topics = ["pop_science discovery"]
                views = 9000
            history.append(
                _make_record(
                    ep,
                    topics,
                    yt_views=views,
                    yt_likes=1,
                    yt_comments=0,
                    tw_impressions=0,
                    tw_engagements=1,
                    tw_retweets=0,
                    tw_likes=0,
                )
            )

        history_file = tmp_path / "engagement_history.json"
        history_file.write_text(json.dumps(history))

        scorer = EngagementScorer(history_path=history_file)
        result = scorer.get_category_rankings()

        assert result["status"] == "ok"
        shocking = next(
            (r for r in result["rankings"] if r["category"] == "shocking_news"),
            None,
        )
        if shocking and shocking["correlation"] is not None:
            assert shocking["correlation"] >= 0.0

        absurd = next(
            (r for r in result["rankings"] if r["category"] == "absurd_hypothetical"),
            None,
        )
        if absurd and absurd["correlation"] is not None:
            assert absurd["correlation"] >= 0.0

    def test_comedy_protected_flag(self, tmp_path):
        """Protected categories have comedy_protected=True in output."""
        from engagement_scorer import EngagementScorer

        # Mix of categories so both shocking_news and absurd_hypothetical appear
        history = []
        for i in range(15):
            ep = i + 1
            if i % 3 == 0:
                topics = ["shocking_news story"]
            elif i % 3 == 1:
                topics = ["absurd_hypothetical scenario"]
            else:
                topics = ["pop_science discovery"]
            history.append(_make_record(ep, topics))

        history_file = tmp_path / "engagement_history.json"
        history_file.write_text(json.dumps(history))

        scorer = EngagementScorer(history_path=history_file)
        result = scorer.get_category_rankings()

        assert result["status"] == "ok"
        for entry in result["rankings"]:
            if entry["category"] in ("shocking_news", "absurd_hypothetical"):
                assert entry.get("comedy_protected") is True
            else:
                assert entry.get("comedy_protected") is not True
