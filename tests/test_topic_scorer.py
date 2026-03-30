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


class TestSelftextContext:
    """Tests for selftext context inclusion in topic list."""

    def test_selftext_included_in_prompt(self):
        """Topics with selftext include context in the prompt sent to LLM."""
        from topic_scorer import TopicScorer

        mock_ollama = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=(
                    '[{"topic_number": 1, "total_score": 5.0, "shock_value": 1,'
                    ' "relatability": 1, "absurdity": 1, "title_hook": 1,'
                    ' "visual_imagery": 1, "reason": "test",'
                    ' "category": "news", "recommended": false}]'
                )
            )
        ]
        mock_ollama.messages.create.return_value = mock_response

        with patch("topic_scorer.Ollama", return_value=mock_ollama):
            scorer = TopicScorer()

        topic = {"title": "Test Topic", "selftext": "Some extra context here"}
        scorer._score_batch([topic])

        # Check that the prompt sent to Ollama includes the selftext context
        call_args = mock_ollama.messages.create.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "Context: Some extra context here" in prompt


class TestJsonExtractionFallback:
    """Tests for JSON extraction fallback when response has wrapping text."""

    def _make_scorer(self):
        mock_ollama = MagicMock()
        with patch("topic_scorer.Ollama", return_value=mock_ollama):
            from topic_scorer import TopicScorer

            return TopicScorer(), mock_ollama

    def test_regex_fallback_extracts_json(self):
        """JSON is extracted via regex when response has surrounding text."""
        scorer, mock_ollama = self._make_scorer()

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=(
                    "Here are the scores:\n"
                    '[{"topic_number": 1, "total_score": 7.0, "shock_value": 2,'
                    ' "relatability": 2, "absurdity": 2, "title_hook": 1,'
                    ' "visual_imagery": 0, "reason": "test",'
                    ' "category": "news", "recommended": true}]\n'
                    "Hope this helps!"
                )
            )
        ]
        mock_ollama.messages.create.return_value = mock_response

        result = scorer._score_batch([{"title": "Test"}])
        assert result[0]["score"]["total"] == 7.0

    def test_unparseable_response_returns_original_topics(self):
        """Returns original topics when response has no valid JSON."""
        scorer, mock_ollama = self._make_scorer()

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="I cannot score these topics, sorry.")]
        mock_ollama.messages.create.return_value = mock_response

        topics = [{"title": "Test Topic"}]
        result = scorer._score_batch(topics)
        # Should return original topics unchanged
        assert result == topics
        assert "score" not in result[0]


class TestScoreBatchExceptionHandling:
    """Tests for exception handling in _score_batch."""

    def _make_scorer(self):
        mock_ollama = MagicMock()
        with patch("topic_scorer.Ollama", return_value=mock_ollama):
            from topic_scorer import TopicScorer

            return TopicScorer(), mock_ollama

    def test_analytics_exception_swallowed(self):
        """Analytics import failure doesn't break scoring."""
        scorer, mock_ollama = self._make_scorer()

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=(
                    '[{"topic_number": 1, "total_score": 8.0, "shock_value": 2,'
                    ' "relatability": 2, "absurdity": 2, "title_hook": 1,'
                    ' "visual_imagery": 1, "reason": "test",'
                    ' "category": "news", "recommended": true}]'
                )
            )
        ]
        mock_ollama.messages.create.return_value = mock_response

        topic = {"title": "Test", "episode_number": 5}

        # Make TopicEngagementScorer raise an exception
        with patch(
            "analytics.TopicEngagementScorer", side_effect=RuntimeError("broken")
        ):
            result = scorer._score_batch([topic])

        # Score should still be present despite analytics failure
        assert result[0]["score"]["total"] == 8.0
        assert result[0]["score"]["engagement_bonus"] is None

    def test_general_exception_returns_original_topics(self):
        """General exception in LLM call returns original topics."""
        scorer, mock_ollama = self._make_scorer()

        mock_ollama.messages.create.side_effect = RuntimeError("LLM down")

        topics = [{"title": "Test Topic"}]
        result = scorer._score_batch(topics)
        assert result == topics


class TestSaveScoredTopicsAutoFilename:
    """Tests for auto-generated filename in save_scored_topics."""

    def test_auto_filename_uses_timestamp(self, tmp_path):
        """save_scored_topics generates timestamped filename when none provided."""
        mock_ollama = MagicMock()
        with patch("topic_scorer.Ollama", return_value=mock_ollama):
            from topic_scorer import TopicScorer

            scorer = TopicScorer()

        topics = [
            {
                "title": "A",
                "score": {"total": 7, "recommended": True, "category": "news"},
            },
        ]

        import topic_scorer

        original_path = topic_scorer.Path

        topic_scorer.Path = lambda x: (
            tmp_path if x == "topic_data" else original_path(x)
        )
        try:
            output = scorer.save_scored_topics(topics)
        finally:
            topic_scorer.Path = original_path

        assert output.exists()
        assert output.name.startswith("scored_topics_")
        assert output.suffix == ".json"


class TestScoreScrapedTopics:
    """Tests for the score_scraped_topics standalone function."""

    def test_score_scraped_topics_with_input_file(self, tmp_path):
        """score_scraped_topics loads and scores topics from a file."""
        import json
        from topic_scorer import score_scraped_topics

        # Create input file
        input_file = tmp_path / "scraped_topics_test.json"
        input_file.write_text(
            json.dumps({"topics": [{"title": "Topic 1"}, {"title": "Topic 2"}]})
        )

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

        import topic_scorer

        original_path = topic_scorer.Path

        topic_scorer.Path = lambda x: (
            tmp_path if x == "topic_data" else original_path(x)
        )
        try:
            with patch("topic_scorer.Ollama", return_value=mock_ollama):
                result = score_scraped_topics(input_file=str(input_file))
        finally:
            topic_scorer.Path = original_path

        assert result is not None
        assert result.exists()

    def test_score_scraped_topics_no_topic_data_dir(self, tmp_path):
        """score_scraped_topics returns None when no topic_data dir exists."""
        from topic_scorer import score_scraped_topics

        with patch("topic_scorer.Path") as mock_path:
            mock_dir = MagicMock()
            mock_dir.exists.return_value = False
            mock_path.return_value = mock_dir

            result = score_scraped_topics(input_file=None)

        assert result is None

    def test_score_scraped_topics_no_scraped_files(self, tmp_path):
        """score_scraped_topics returns None when no scraped files found."""
        from topic_scorer import score_scraped_topics

        with patch("topic_scorer.Path") as mock_path:
            mock_dir = MagicMock()
            mock_dir.exists.return_value = True
            mock_dir.glob.return_value = []
            mock_path.return_value = mock_dir

            result = score_scraped_topics(input_file=None)

        assert result is None

    def test_score_scraped_topics_finds_most_recent(self, tmp_path):
        """score_scraped_topics picks the most recent scraped file."""
        import json
        from topic_scorer import score_scraped_topics

        # Create two scraped files with different mtimes
        old_file = tmp_path / "scraped_topics_old.json"
        old_file.write_text(json.dumps({"topics": [{"title": "Old"}]}))

        new_file = tmp_path / "scraped_topics_new.json"
        new_file.write_text(json.dumps({"topics": [{"title": "New"}]}))

        mock_ollama = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=(
                    '[{"topic_number": 1, "total_score": 6.0, "shock_value": 1,'
                    ' "relatability": 1, "absurdity": 1, "title_hook": 1,'
                    ' "visual_imagery": 1, "reason": "test",'
                    ' "category": "news", "recommended": true}]'
                )
            )
        ]
        mock_ollama.messages.create.return_value = mock_response

        import topic_scorer

        original_path = topic_scorer.Path

        # Mock Path("topic_data") to return tmp_path contents
        def mock_path_factory(x):
            if x == "topic_data":
                mock_dir = MagicMock()
                mock_dir.exists.return_value = True
                mock_dir.glob.return_value = [old_file, new_file]
                return mock_dir
            return original_path(x)

        topic_scorer.Path = mock_path_factory
        try:
            with patch("topic_scorer.Ollama", return_value=mock_ollama):
                with patch(
                    "topic_scorer.TopicScorer.save_scored_topics",
                    return_value=tmp_path / "output.json",
                ):
                    score_scraped_topics(input_file=None)
        finally:
            topic_scorer.Path = original_path


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
