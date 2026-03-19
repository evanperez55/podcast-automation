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
