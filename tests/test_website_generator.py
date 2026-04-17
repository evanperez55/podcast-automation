"""Tests for website_generator module."""

import json
import pytest
from unittest.mock import patch, MagicMock

from website_generator import WebsiteGenerator


@pytest.fixture
def generator(tmp_path):
    """Create a WebsiteGenerator with temp output dir and test template."""
    # Create a minimal template
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    template = templates_dir / "website_index.html"
    template.write_text(
        "<html>{{LATEST_EPISODE}} {{CLIPS}} {{QUOTES}} {{OLDER_EPISODES}}</html>",
        encoding="utf-8",
    )

    with patch("website_generator.Config") as mock_config:
        mock_config.OUTPUT_DIR = str(tmp_path / "output")
        mock_config.PODCAST_NAME = "Test Podcast"
        gen = WebsiteGenerator()
        gen.template_path = template
        gen.output_dir = tmp_path / "output"
    return gen


@pytest.fixture
def sample_analysis():
    """Sample analysis data for one episode."""
    return {
        "episode_title": "Test Episode Title",
        "episode_summary": "A great test episode.",
        "best_clips": [
            {
                "suggested_title": "Clip One",
                "description": "First clip",
                "hook_caption": "Hook 1",
                "start": "00:05:00",
                "end": "00:05:30",
            },
            {
                "suggested_title": "Clip Two",
                "description": "Second clip",
                "hook_caption": "Hook 2",
                "start": "00:10:00",
                "end": "00:10:25",
            },
        ],
        "best_quotes": [
            {
                "quote": "This is a great quote.",
                "timestamp": "00:15:00",
                "speaker_context": "one of the hosts",
            },
        ],
        "chapters": [],
    }


class TestCollectEpisodes:
    """Tests for _collect_episodes."""

    def test_no_output_dir(self, generator):
        """Returns empty list when output dir doesn't exist."""
        result = generator._collect_episodes()
        assert result == []

    def test_finds_episodes(self, generator, sample_analysis, tmp_path):
        """Finds and parses episode analysis files."""
        ep_dir = tmp_path / "output" / "ep_30"
        ep_dir.mkdir(parents=True)
        analysis_path = ep_dir / "ep30_analysis.json"
        analysis_path.write_text(json.dumps(sample_analysis), encoding="utf-8")

        result = generator._collect_episodes()
        assert len(result) == 1
        assert result[0]["number"] == 30
        assert result[0]["title"] == "Test Episode Title"

    def test_skips_bad_json(self, generator, tmp_path):
        """Skips directories with invalid JSON."""
        ep_dir = tmp_path / "output" / "ep_5"
        ep_dir.mkdir(parents=True)
        (ep_dir / "ep5_analysis.json").write_text("not json", encoding="utf-8")

        result = generator._collect_episodes()
        assert result == []

    def test_sorted_newest_first(self, generator, sample_analysis, tmp_path):
        """Episodes are sorted newest first."""
        for n in [10, 30, 20]:
            ep_dir = tmp_path / "output" / f"ep_{n}"
            ep_dir.mkdir(parents=True)
            analysis = {**sample_analysis, "episode_title": f"Episode {n}"}
            (ep_dir / f"ep{n}_analysis.json").write_text(
                json.dumps(analysis), encoding="utf-8"
            )

        result = generator._collect_episodes()
        assert [ep["number"] for ep in result] == [30, 20, 10]


class TestCollectYoutubeIds:
    """Tests for _collect_youtube_ids."""

    def test_no_calendar(self, generator, monkeypatch, tmp_path):
        """Returns empty dict when no calendar file exists."""
        monkeypatch.chdir(tmp_path)
        result = generator._collect_youtube_ids()
        assert result == {}

    def test_reads_video_ids(self, generator, monkeypatch, tmp_path):
        """Extracts YouTube video IDs from calendar slots."""
        monkeypatch.chdir(tmp_path)
        cal_dir = tmp_path / "topic_data"
        cal_dir.mkdir()
        calendar = {
            "ep_30": {
                "slots": {
                    "episode": {
                        "content": {"youtube_video_id": "abc123"},
                        "upload_results": {},
                    },
                    "clip_1": {
                        "content": {"youtube_video_id": "def456"},
                        "upload_results": {},
                    },
                }
            }
        }
        (cal_dir / "content_calendar.json").write_text(
            json.dumps(calendar), encoding="utf-8"
        )

        result = generator._collect_youtube_ids()
        assert result["ep_30"]["episode"] == "abc123"
        assert result["ep_30"]["clip_1"] == "def456"

    def test_content_youtube_id_overrides_stale_upload_results(
        self, generator, monkeypatch, tmp_path
    ):
        """content.youtube_video_id is source of truth over upload_results.

        Regression guard: when an episode is re-published (e.g. denoised
        rerun), the distribute step updates content.youtube_video_id but
        may not rewrite upload_results.youtube.video_id. The fresh content
        field must win so the website embeds the new video, not a stale
        one from an earlier test/upload.
        """
        monkeypatch.chdir(tmp_path)
        cal_dir = tmp_path / "topic_data"
        cal_dir.mkdir()
        calendar = {
            "ep_31": {
                "slots": {
                    "episode": {
                        "content": {"youtube_video_id": "NEW_ID_xyz"},
                        "upload_results": {"youtube": {"video_id": "stale_abc123"}},
                    },
                }
            }
        }
        (cal_dir / "content_calendar.json").write_text(
            json.dumps(calendar), encoding="utf-8"
        )

        result = generator._collect_youtube_ids()

        assert result["ep_31"]["episode"] == "NEW_ID_xyz"

    def test_falls_back_to_upload_results_when_content_empty(
        self, generator, monkeypatch, tmp_path
    ):
        """When content.youtube_video_id is empty/missing, use upload_results."""
        monkeypatch.chdir(tmp_path)
        cal_dir = tmp_path / "topic_data"
        cal_dir.mkdir()
        calendar = {
            "ep_29": {
                "slots": {
                    "episode": {
                        "content": {},
                        "upload_results": {"youtube": {"video_id": "fallback_vid"}},
                    },
                }
            }
        }
        (cal_dir / "content_calendar.json").write_text(
            json.dumps(calendar), encoding="utf-8"
        )

        result = generator._collect_youtube_ids()

        assert result["ep_29"]["episode"] == "fallback_vid"

    def test_reads_clip_ids_from_platform_ids_json(
        self, generator, monkeypatch, tmp_path
    ):
        """Clip YouTube IDs come from output/ep_N/platform_ids.json, indexed 0..N.

        This decouples clip-video lookup from the content calendar's
        staggered-posting slot names (clip_3, clip_4, ...) which only
        cover a subset of clips and use day-offset, not clip-index.
        """
        monkeypatch.chdir(tmp_path)
        ep_dir = tmp_path / "output" / "ep_31"
        ep_dir.mkdir(parents=True)
        (ep_dir / "platform_ids.json").write_text(
            json.dumps(
                {
                    "youtube": "MAIN_ep31",
                    "youtube_clips": ["clip_ONE", "clip_TWO", "clip_THREE"],
                    "twitter": "999",
                }
            ),
            encoding="utf-8",
        )
        generator.output_dir = tmp_path / "output"

        result = generator._collect_youtube_ids()

        assert result["ep_31"]["episode"] == "MAIN_ep31"
        assert result["ep_31"]["clip_1"] == "clip_ONE"
        assert result["ep_31"]["clip_2"] == "clip_TWO"
        assert result["ep_31"]["clip_3"] == "clip_THREE"

    def test_platform_ids_takes_precedence_over_calendar(
        self, generator, monkeypatch, tmp_path
    ):
        """When platform_ids.json exists, it wins over calendar entries."""
        monkeypatch.chdir(tmp_path)
        ep_dir = tmp_path / "output" / "ep_31"
        ep_dir.mkdir(parents=True)
        (ep_dir / "platform_ids.json").write_text(
            json.dumps({"youtube": "PID_MAIN", "youtube_clips": ["PID_CLIP1"]}),
            encoding="utf-8",
        )
        generator.output_dir = tmp_path / "output"

        cal_dir = tmp_path / "topic_data"
        cal_dir.mkdir()
        (cal_dir / "content_calendar.json").write_text(
            json.dumps(
                {
                    "ep_31": {
                        "slots": {
                            "episode": {
                                "content": {"youtube_video_id": "CAL_MAIN"},
                                "upload_results": {},
                            },
                            "clip_1": {
                                "content": {"youtube_video_id": "CAL_CLIP1"},
                                "upload_results": {},
                            },
                        }
                    }
                }
            ),
            encoding="utf-8",
        )

        result = generator._collect_youtube_ids()

        assert result["ep_31"]["episode"] == "PID_MAIN"
        assert result["ep_31"]["clip_1"] == "PID_CLIP1"

    def test_calendar_fills_gaps_when_platform_ids_missing_a_clip(
        self, generator, monkeypatch, tmp_path
    ):
        """If platform_ids.json lacks a slot, calendar fills the gap."""
        monkeypatch.chdir(tmp_path)
        ep_dir = tmp_path / "output" / "ep_31"
        ep_dir.mkdir(parents=True)
        (ep_dir / "platform_ids.json").write_text(
            json.dumps(
                {"youtube": "PID_MAIN", "youtube_clips": ["PID_CLIP1"]}  # only clip 1
            ),
            encoding="utf-8",
        )
        generator.output_dir = tmp_path / "output"

        cal_dir = tmp_path / "topic_data"
        cal_dir.mkdir()
        (cal_dir / "content_calendar.json").write_text(
            json.dumps(
                {
                    "ep_31": {
                        "slots": {
                            "clip_3": {
                                "content": {"youtube_video_id": "CAL_CLIP3"},
                                "upload_results": {},
                            },
                        }
                    }
                }
            ),
            encoding="utf-8",
        )

        result = generator._collect_youtube_ids()

        assert result["ep_31"]["clip_1"] == "PID_CLIP1"
        assert result["ep_31"]["clip_3"] == "CAL_CLIP3"


class TestGenerateHtml:
    """Tests for generate_html."""

    def test_generates_with_episodes(self, generator, sample_analysis, tmp_path):
        """Generates HTML with episode data populated."""
        ep_dir = tmp_path / "output" / "ep_30"
        ep_dir.mkdir(parents=True)
        (ep_dir / "ep30_analysis.json").write_text(
            json.dumps(sample_analysis), encoding="utf-8"
        )

        html = generator.generate_html()
        assert "Test Episode Title" in html
        assert "Episode 30" in html

    def test_generates_empty_site(self, generator):
        """Generates HTML even with no episodes."""
        html = generator.generate_html()
        assert "No episodes yet" in html

    def test_html_escapes_content(self, generator, tmp_path):
        """Episode titles with HTML chars are escaped."""
        ep_dir = tmp_path / "output" / "ep_1"
        ep_dir.mkdir(parents=True)
        analysis = {
            "episode_title": "Test <script>alert('xss')</script>",
            "episode_summary": "Summary",
            "best_clips": [],
            "best_quotes": [],
            "chapters": [],
        }
        (ep_dir / "ep1_analysis.json").write_text(
            json.dumps(analysis), encoding="utf-8"
        )

        html = generator.generate_html()
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


class TestSaveHtml:
    """Tests for save_html."""

    def test_saves_to_output_dir(self, generator, tmp_path):
        """Saves HTML to output/website/index.html."""
        path = generator.save_html("<html>test</html>")
        assert path.exists()
        assert path.name == "index.html"
        assert path.read_text(encoding="utf-8") == "<html>test</html>"


class TestDeploy:
    """Tests for deploy to GitHub."""

    def test_skips_without_token(self, generator):
        """Skips deploy when GITHUB_TOKEN is missing."""
        generator.github_token = ""
        result = generator.deploy("<html>test</html>")
        assert result is None

    def test_skips_without_pygithub(self, generator):
        """Skips deploy when PyGithub is not installed."""
        generator.github_token = "test-token"
        generator.github_repo = "org/repo"
        with patch("website_generator.Github", None):
            result = generator.deploy("<html>test</html>")
        assert result is None

    @patch("website_generator.Github")
    def test_creates_file_on_first_deploy(self, mock_github_cls, generator):
        """Creates index.html when it doesn't exist yet."""
        generator.github_token = "test-token"
        generator.github_repo = "fakeproblemspodcast/fakeproblemspodcast.github.io"

        mock_repo = MagicMock()
        mock_repo.get_contents.side_effect = Exception("not found")
        mock_github_cls.return_value.get_repo.return_value = mock_repo

        result = generator.deploy("<html>test</html>")
        assert result is not None
        mock_repo.create_file.assert_called_once()

    @patch("website_generator.Github")
    def test_updates_existing_file(self, mock_github_cls, generator):
        """Updates index.html when it already exists."""
        generator.github_token = "test-token"
        generator.github_repo = "fakeproblemspodcast/fakeproblemspodcast.github.io"

        mock_existing = MagicMock()
        mock_existing.sha = "abc123"
        mock_repo = MagicMock()
        mock_repo.get_contents.return_value = mock_existing
        mock_github_cls.return_value.get_repo.return_value = mock_repo

        result = generator.deploy("<html>test</html>")
        assert result is not None
        mock_repo.update_file.assert_called_once()


class TestGenerateAndDeploy:
    """Tests for the combined generate_and_deploy method."""

    def test_disabled_returns_none(self, generator):
        """Returns None when disabled."""
        generator.enabled = False
        result = generator.generate_and_deploy()
        assert result is None

    def test_enabled_calls_deploy(self, generator, sample_analysis, tmp_path):
        """When enabled, generates HTML and calls deploy."""
        ep_dir = tmp_path / "output" / "ep_30"
        ep_dir.mkdir(parents=True)
        (ep_dir / "ep30_analysis.json").write_text(
            json.dumps(sample_analysis), encoding="utf-8"
        )
        generator.github_token = ""  # Will skip actual deploy

        result = generator.generate_and_deploy()
        # Deploy returns None because no token, but HTML was generated
        assert result is None
        assert (tmp_path / "output" / "website" / "index.html").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
