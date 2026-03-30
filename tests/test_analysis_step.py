"""Tests for pipeline.steps.analysis (run_analysis and _load_scored_topics)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from config import Config
from pipeline.context import PipelineContext
from pipeline.steps.analysis import _load_scored_topics, run_analysis


def _make_ctx(tmp_path, **overrides):
    """Create a minimal PipelineContext for testing."""
    defaults = {
        "episode_folder": str(tmp_path),
        "episode_number": 25,
        "episode_output_dir": tmp_path,
        "timestamp": "20260329",
        "audio_file": tmp_path / "ep25.wav",
        "transcript_data": {
            "segments": [{"text": "Hello world"}],
            "words": [],
        },
    }
    defaults.update(overrides)
    return PipelineContext(**defaults)


def _make_components(**overrides):
    """Create a minimal components dict with mocks."""
    editor = MagicMock()
    editor.analyze_content.return_value = {
        "episode_title": "Test Episode",
        "episode_summary": "A summary.",
        "best_clips": [],
        "show_notes": "Show notes content.",
    }

    defaults = {
        "editor": editor,
        "topic_tracker": None,
    }
    defaults.update(overrides)
    return defaults


class TestLoadScoredTopics:
    """Tests for _load_scored_topics helper."""

    def test_returns_none_when_no_topic_dir(self, tmp_path, monkeypatch):
        """Returns None when topic_data/ doesn't exist."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        result = _load_scored_topics()
        assert result is None

    def test_returns_none_when_no_scored_files(self, tmp_path, monkeypatch):
        """Returns None when topic_data/ has no scored_topics files."""
        (tmp_path / "topic_data").mkdir()
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        result = _load_scored_topics()
        assert result is None

    def test_loads_recommended_topics(self, tmp_path, monkeypatch):
        """Loads and sorts recommended topics from scored file."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        topic_dir = tmp_path / "topic_data"
        topic_dir.mkdir()
        data = {
            "topics_by_category": {
                "comedy": [
                    {
                        "title": "Topic A",
                        "score": {
                            "total": 80,
                            "recommended": True,
                            "category": "comedy",
                        },
                    },
                    {
                        "title": "Topic B",
                        "score": {
                            "total": 50,
                            "recommended": False,
                            "category": "comedy",
                        },
                    },
                ],
                "news": [
                    {
                        "title": "Topic C",
                        "score": {"total": 90, "recommended": True, "category": "news"},
                    },
                ],
            }
        }
        with open(topic_dir / "scored_topics_2026-03-29.json", "w") as f:
            json.dump(data, f)

        result = _load_scored_topics()

        assert len(result) == 2
        assert result[0]["topic"] == "Topic C"
        assert result[0]["score"] == 90
        assert result[1]["topic"] == "Topic A"

    def test_returns_none_on_bad_json(self, tmp_path, monkeypatch):
        """Returns None when scored file has invalid JSON."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        topic_dir = tmp_path / "topic_data"
        topic_dir.mkdir()
        (topic_dir / "scored_topics_2026-03-29.json").write_text("not json")

        result = _load_scored_topics()
        assert result is None


class TestRunAnalysis:
    """Tests for run_analysis step function."""

    @patch("pipeline.steps.analysis.EngagementScorer")
    @patch("pipeline.steps.analysis._load_scored_topics", return_value=None)
    def test_analyzes_content(self, mock_topics, mock_scorer_cls, tmp_path):
        """Calls editor.analyze_content and saves analysis JSON."""
        mock_scorer_cls.return_value.get_category_rankings.return_value = {
            "status": "ok",
            "episodes_analyzed": 5,
        }
        ctx = _make_ctx(tmp_path)
        components = _make_components()

        result = run_analysis(ctx, components)

        components["editor"].analyze_content.assert_called_once()
        assert result.analysis["episode_title"] == "Test Episode"
        # Check analysis JSON was saved
        analysis_files = list(tmp_path.glob("*_analysis.json"))
        assert len(analysis_files) == 1

    @patch("pipeline.steps.analysis.EngagementScorer")
    @patch("pipeline.steps.analysis._load_scored_topics", return_value=None)
    def test_saves_show_notes(self, mock_topics, mock_scorer_cls, tmp_path):
        """Show notes are saved to a separate text file."""
        mock_scorer_cls.return_value.get_category_rankings.return_value = {
            "status": "ok",
            "episodes_analyzed": 0,
        }
        ctx = _make_ctx(tmp_path)
        components = _make_components()

        run_analysis(ctx, components)

        notes_files = list(tmp_path.glob("*_show_notes.txt"))
        assert len(notes_files) == 1
        assert notes_files[0].read_text() == "Show notes content."

    @patch("pipeline.steps.analysis.EngagementScorer")
    @patch("pipeline.steps.analysis._load_scored_topics", return_value=None)
    def test_resumes_from_state(self, mock_topics, mock_scorer_cls, tmp_path):
        """When state has completed analyze, loads from saved file."""
        mock_scorer_cls.return_value.get_category_rankings.return_value = {
            "status": "ok",
            "episodes_analyzed": 0,
        }
        # Write a pre-existing analysis file
        analysis_path = tmp_path / "ep25_20260329_analysis.json"
        saved = {"episode_title": "Saved", "best_clips": []}
        analysis_path.write_text(json.dumps(saved))

        ctx = _make_ctx(tmp_path)
        components = _make_components()
        state = MagicMock()
        state.is_step_completed.return_value = True
        state.get_step_outputs.return_value = {"analysis_path": str(analysis_path)}

        result = run_analysis(ctx, components, state=state)

        components["editor"].analyze_content.assert_not_called()
        assert result.analysis["episode_title"] == "Saved"

    @patch("pipeline.steps.analysis.EngagementScorer")
    @patch("pipeline.steps.analysis._load_scored_topics", return_value=None)
    def test_updates_topic_tracker(self, mock_topics, mock_scorer_cls, tmp_path):
        """When topic_tracker is provided, updates topics for episode."""
        mock_scorer_cls.return_value.get_category_rankings.return_value = {
            "status": "ok",
            "episodes_analyzed": 0,
        }
        tracker = MagicMock()
        ctx = _make_ctx(tmp_path)
        components = _make_components(topic_tracker=tracker)

        run_analysis(ctx, components)

        tracker.update_topics_for_episode.assert_called_once()

    @patch("pipeline.steps.analysis.EngagementScorer")
    @patch("pipeline.steps.analysis._load_scored_topics", return_value=None)
    def test_skips_topic_tracker_when_none(
        self, mock_topics, mock_scorer_cls, tmp_path
    ):
        """When no topic_tracker, skips without error."""
        mock_scorer_cls.return_value.get_category_rankings.return_value = {
            "status": "ok",
            "episodes_analyzed": 0,
        }
        ctx = _make_ctx(tmp_path)
        components = _make_components(topic_tracker=None)

        result = run_analysis(ctx, components)

        assert result.analysis is not None

    @patch("pipeline.steps.analysis.EngagementScorer")
    @patch("pipeline.steps.analysis._load_scored_topics", return_value=None)
    def test_engagement_scorer_failure_nonfatal(
        self, mock_topics, mock_scorer_cls, tmp_path
    ):
        """EngagementScorer failure doesn't block analysis."""
        mock_scorer_cls.side_effect = Exception("scorer broke")
        ctx = _make_ctx(tmp_path)
        components = _make_components()

        result = run_analysis(ctx, components)

        assert result.analysis is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
