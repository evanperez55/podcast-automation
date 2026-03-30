"""Regression tests for TopicScorer engagement bonus bug fix."""

from unittest.mock import MagicMock, patch


class TestTopicScorer:
    """Tests for TopicScorer engagement bonus episode number handling."""

    def _make_mock_topic_with_episode(self, episode_number: int) -> dict:
        return {
            "title": "Test Topic",
            "selftext": "",
            "episode_number": episode_number,
        }

    def _make_mock_topic_without_episode(self) -> dict:
        return {
            "title": "Scraped Future Topic",
            "selftext": "",
            # No episode_number key — scraped future topic
        }

    def _make_mock_scorer_and_response(self):
        """Return (mock_ollama, mock_response) for a single-topic batch."""
        mock_ollama = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=(
                    '[{"topic_number": 1, "total_score": 7.0, "shock_value": 2,'
                    ' "relatability": 2, "absurdity": 2, "title_hook": 1,'
                    ' "visual_imagery": 0, "reason": "test",'
                    ' "category": "shocking_news", "recommended": true}]'
                )
            )
        ]
        mock_ollama.messages.create.return_value = mock_response
        return mock_ollama

    def test_engagement_bonus_uses_episode_number(self):
        """get_engagement_bonus is called with actual episode_number from topic dict."""
        from topic_scorer import TopicScorer

        mock_ollama = self._make_mock_scorer_and_response()

        with patch("topic_scorer.Ollama", return_value=mock_ollama):
            scorer = TopicScorer()

        topic = self._make_mock_topic_with_episode(25)

        mock_eng_scorer_instance = MagicMock()
        mock_eng_scorer_instance.get_engagement_bonus.return_value = 0.5
        mock_eng_scorer_class = MagicMock(return_value=mock_eng_scorer_instance)

        with patch("analytics.TopicEngagementScorer", mock_eng_scorer_class):
            scorer._score_batch([topic])

        # Must be called with 25, not with loop index 0+1=1
        mock_eng_scorer_instance.get_engagement_bonus.assert_called_once_with(25)

    def test_engagement_bonus_skipped_without_episode_number(self):
        """get_engagement_bonus is NOT called when topic has no episode_number."""
        from topic_scorer import TopicScorer

        mock_ollama = self._make_mock_scorer_and_response()

        with patch("topic_scorer.Ollama", return_value=mock_ollama):
            scorer = TopicScorer()

        topic = self._make_mock_topic_without_episode()

        mock_eng_scorer_instance = MagicMock()
        mock_eng_scorer_instance.get_engagement_bonus.return_value = 0.5
        mock_eng_scorer_class = MagicMock(return_value=mock_eng_scorer_instance)

        with patch("analytics.TopicEngagementScorer", mock_eng_scorer_class):
            result = scorer._score_batch([topic])

        # get_engagement_bonus should NOT be called for scraped future topics
        mock_eng_scorer_instance.get_engagement_bonus.assert_not_called()

        # engagement_bonus should be None in the score dict
        assert result[0]["score"]["engagement_bonus"] is None


class TestScoringProfile:
    """Tests for configurable scoring profiles."""

    def test_default_profile_used_without_config(self):
        """TopicScorer uses DEFAULT_SCORING_PROFILE when Config has none."""
        from topic_scorer import TopicScorer, DEFAULT_SCORING_PROFILE

        mock_ollama = MagicMock()
        with patch("topic_scorer.Ollama", return_value=mock_ollama):
            scorer = TopicScorer()

        assert scorer.profile == DEFAULT_SCORING_PROFILE
        assert scorer.profile["criteria"][0]["name"] == "Shock Value"

    def test_custom_profile_from_config(self):
        """TopicScorer uses Config.SCORING_PROFILE when set."""
        from topic_scorer import TopicScorer
        from config import Config

        custom_profile = {
            "description": "a business podcast",
            "criteria": [
                {"name": "Actionability", "key": "actionability", "max": 5},
                {"name": "Novelty", "key": "novelty", "max": 5},
            ],
            "style": ["Professional but approachable"],
            "high_examples": ['"AI replacing middle management"'],
            "low_examples": ["Generic earnings reports"],
            "categories": ["strategy", "leadership", "tech_trends"],
        }
        Config.SCORING_PROFILE = custom_profile
        try:
            mock_ollama = MagicMock()
            with patch("topic_scorer.Ollama", return_value=mock_ollama):
                scorer = TopicScorer()

            assert scorer.profile["description"] == "a business podcast"
            assert len(scorer.profile["criteria"]) == 2
            assert scorer.profile["criteria"][0]["key"] == "actionability"
        finally:
            delattr(Config, "SCORING_PROFILE")

    def test_build_prompt_uses_profile_criteria(self):
        """_build_scoring_prompt includes criteria from the active profile."""
        from topic_scorer import TopicScorer
        from config import Config

        custom_profile = {
            "description": "a true crime podcast",
            "criteria": [
                {
                    "name": "Mystery Factor",
                    "key": "mystery_factor",
                    "max": 5,
                    "description": "How mysterious is this?",
                },
                {
                    "name": "Public Interest",
                    "key": "public_interest",
                    "max": 5,
                    "description": "How much does the public care?",
                },
            ],
            "style": ["Investigative deep-dives"],
            "high_examples": ['"Cold case solved after 30 years"'],
            "low_examples": ["Already solved cases"],
            "categories": ["cold_case", "missing_person"],
        }
        Config.SCORING_PROFILE = custom_profile

        try:
            mock_ollama = MagicMock()
            with patch("topic_scorer.Ollama", return_value=mock_ollama):
                scorer = TopicScorer()

            topics = [{"title": "Test Topic"}]
            prompt = scorer._build_scoring_prompt(topics, "1. Test Topic")

            assert "true crime podcast" in prompt
            assert "Mystery Factor" in prompt
            assert "Public Interest" in prompt
            assert "0-10" in prompt  # total max = 5+5
            assert "cold_case" in prompt
            assert "Shock Value" not in prompt  # comedy criteria NOT present
        finally:
            delattr(Config, "SCORING_PROFILE")

    def test_score_extraction_uses_profile_keys(self):
        """Score dict uses dynamic keys from the profile, not hardcoded ones."""
        from topic_scorer import TopicScorer

        mock_ollama = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=(
                    '[{"topic_number": 1, "total_score": 8.0, "shock_value": 2,'
                    ' "relatability": 2, "absurdity": 2, "title_hook": 1,'
                    ' "visual_imagery": 1, "reason": "test",'
                    ' "category": "shocking_news", "recommended": true}]'
                )
            )
        ]
        mock_ollama.messages.create.return_value = mock_response

        with patch("topic_scorer.Ollama", return_value=mock_ollama):
            scorer = TopicScorer()

        result = scorer._score_batch([{"title": "Test"}])
        score = result[0]["score"]

        # Default profile keys should be present
        assert "shock_value" in score
        assert "relatability" in score
        assert "total" in score
        assert score["total"] == 8.0


class TestFilterAndSort:
    """Tests for filter, sort, and group methods."""

    def _make_scorer(self):
        mock_ollama = MagicMock()
        with patch("topic_scorer.Ollama", return_value=mock_ollama):
            from topic_scorer import TopicScorer

            return TopicScorer()

    def test_filter_recommended(self):
        """Filters to only recommended topics."""
        scorer = self._make_scorer()
        topics = [
            {"title": "A", "score": {"recommended": True, "total": 8}},
            {"title": "B", "score": {"recommended": False, "total": 3}},
            {"title": "C", "score": {"recommended": True, "total": 7}},
        ]
        result = scorer.filter_recommended(topics)
        assert len(result) == 2
        assert all(t["score"]["recommended"] for t in result)

    def test_sort_by_score(self):
        """Sorts topics by total score descending."""
        scorer = self._make_scorer()
        topics = [
            {"title": "Low", "score": {"total": 3}},
            {"title": "High", "score": {"total": 9}},
            {"title": "Mid", "score": {"total": 6}},
        ]
        result = scorer.sort_by_score(topics)
        assert [t["title"] for t in result] == ["High", "Mid", "Low"]

    def test_group_by_category(self):
        """Groups topics by category."""
        scorer = self._make_scorer()
        topics = [
            {"title": "A", "score": {"category": "news"}},
            {"title": "B", "score": {"category": "comedy"}},
            {"title": "C", "score": {"category": "news"}},
        ]
        result = scorer.group_by_category(topics)
        assert len(result["news"]) == 2
        assert len(result["comedy"]) == 1


class TestSaveScoredTopics:
    """Tests for save_scored_topics."""

    def test_save_creates_json(self, tmp_path):
        """Saves scored topics to JSON file."""
        import json

        mock_ollama = MagicMock()
        with patch("topic_scorer.Ollama", return_value=mock_ollama):
            from topic_scorer import TopicScorer

            scorer = TopicScorer()

        topics = [
            {
                "title": "A",
                "score": {"total": 8, "recommended": True, "category": "news"},
            },
            {
                "title": "B",
                "score": {"total": 3, "recommended": False, "category": "comedy"},
            },
        ]

        with patch("topic_scorer.Path", return_value=tmp_path):
            # Override the output dir to use tmp_path
            import topic_scorer

            original_path = topic_scorer.Path
            topic_scorer.Path = lambda x: (
                tmp_path if x == "topic_data" else original_path(x)
            )
            try:
                output = scorer.save_scored_topics(topics, filename="test_scored.json")
            finally:
                topic_scorer.Path = original_path

        assert output.exists()
        data = json.loads(output.read_text())
        assert data["statistics"]["total_topics"] == 2
        assert data["statistics"]["recommended"] == 1


class TestScoreTopics:
    """Tests for score_topics batching."""

    def test_score_topics_batches(self):
        """score_topics processes topics in batches."""
        mock_ollama = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=(
                    '[{"topic_number": 1, "total_score": 7.0, "shock_value": 2,'
                    ' "relatability": 2, "absurdity": 2, "title_hook": 1,'
                    ' "visual_imagery": 0, "reason": "test",'
                    ' "category": "news", "recommended": true}]'
                )
            )
        ]
        mock_ollama.messages.create.return_value = mock_response

        with patch("topic_scorer.Ollama", return_value=mock_ollama):
            from topic_scorer import TopicScorer

            scorer = TopicScorer()

        topics = [{"title": f"Topic {i}"} for i in range(3)]
        result = scorer.score_topics(topics, batch_size=2)

        # Should have called _score_batch twice (batch of 2 + batch of 1)
        assert mock_ollama.messages.create.call_count == 2
        assert len(result) == 3


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
