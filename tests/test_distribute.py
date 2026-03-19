"""Tests for distribute step — platform ID capture after upload."""

import json
from unittest.mock import patch, MagicMock

from pipeline.steps.distribute import _upload_to_social_media


# ---------------------------------------------------------------------------
# Platform ID capture tests
# ---------------------------------------------------------------------------


class TestPlatformIdCapture:
    """Tests that platform_ids.json is written after uploads complete."""

    def test_platform_ids_written_after_youtube_upload(self, tmp_path):
        """YouTube upload result video_id is persisted to platform_ids.json."""
        youtube_mock = MagicMock()
        youtube_mock.upload_episode.return_value = {
            "video_id": "abc123",
            "video_url": "https://youtu.be/abc123",
        }
        components = {"uploaders": {"youtube": youtube_mock}}

        with (
            patch("pipeline.steps.distribute._upload_youtube") as mock_yt,
            patch("pipeline.steps.distribute._upload_twitter", return_value=None),
            patch("pipeline.steps.distribute._upload_instagram", return_value=None),
        ):
            mock_yt.return_value = {
                "clips": [],
                "full_episode": {
                    "video_id": "abc123",
                    "video_url": "https://youtu.be/abc123",
                },
            }

            _upload_to_social_media(
                episode_number=99,
                mp3_path=tmp_path / "ep.mp3",
                video_clip_paths=[],
                analysis={},
                components=components,
                test_mode=False,
                full_episode_video_path=None,
                episode_output_dir=tmp_path,
            )

        platform_ids_path = tmp_path / "platform_ids.json"
        assert platform_ids_path.exists(), (
            "platform_ids.json should be created after YouTube upload"
        )
        data = json.loads(platform_ids_path.read_text(encoding="utf-8"))
        assert data.get("youtube") == "abc123"

    def test_platform_ids_written_after_twitter_upload(self, tmp_path):
        """Twitter upload result tweet_id is persisted to platform_ids.json."""
        twitter_mock = MagicMock()
        components = {"uploaders": {"twitter": twitter_mock}}

        with (
            patch("pipeline.steps.distribute._upload_youtube", return_value=None),
            patch("pipeline.steps.distribute._upload_twitter") as mock_tw,
            patch("pipeline.steps.distribute._upload_instagram", return_value=None),
        ):
            mock_tw.return_value = [{"tweet_id": "999", "text": "Episode out!"}]

            _upload_to_social_media(
                episode_number=99,
                mp3_path=tmp_path / "ep.mp3",
                video_clip_paths=[],
                analysis={},
                components=components,
                test_mode=False,
                full_episode_video_path=None,
                episode_output_dir=tmp_path,
            )

        platform_ids_path = tmp_path / "platform_ids.json"
        assert platform_ids_path.exists(), (
            "platform_ids.json should be created after Twitter upload"
        )
        data = json.loads(platform_ids_path.read_text(encoding="utf-8"))
        assert data.get("twitter") == "999"

    def test_platform_ids_not_written_when_no_uploads(self, tmp_path):
        """platform_ids.json is NOT created when neither uploader returns results."""
        components = {"uploaders": {}}

        with (
            patch("pipeline.steps.distribute._upload_youtube", return_value=None),
            patch("pipeline.steps.distribute._upload_twitter", return_value=None),
            patch("pipeline.steps.distribute._upload_instagram", return_value=None),
        ):
            _upload_to_social_media(
                episode_number=99,
                mp3_path=tmp_path / "ep.mp3",
                video_clip_paths=[],
                analysis={},
                components=components,
                test_mode=False,
                full_episode_video_path=None,
                episode_output_dir=tmp_path,
            )

        platform_ids_path = tmp_path / "platform_ids.json"
        assert not platform_ids_path.exists(), (
            "platform_ids.json should NOT be created when no uploads succeed"
        )

    def test_platform_ids_combines_both_platforms(self, tmp_path):
        """Both YouTube video_id and Twitter tweet_id are stored in single platform_ids.json."""
        components = {"uploaders": {"youtube": MagicMock(), "twitter": MagicMock()}}

        with (
            patch("pipeline.steps.distribute._upload_youtube") as mock_yt,
            patch("pipeline.steps.distribute._upload_twitter") as mock_tw,
            patch("pipeline.steps.distribute._upload_instagram", return_value=None),
        ):
            mock_yt.return_value = {
                "clips": [],
                "full_episode": {
                    "video_id": "yt_vid_111",
                    "video_url": "https://youtu.be/yt_vid_111",
                },
            }
            mock_tw.return_value = [{"tweet_id": "tw_789", "text": "Episode out!"}]

            _upload_to_social_media(
                episode_number=99,
                mp3_path=tmp_path / "ep.mp3",
                video_clip_paths=[],
                analysis={},
                components=components,
                test_mode=False,
                full_episode_video_path=None,
                episode_output_dir=tmp_path,
            )

        platform_ids_path = tmp_path / "platform_ids.json"
        assert platform_ids_path.exists()
        data = json.loads(platform_ids_path.read_text(encoding="utf-8"))
        assert data.get("youtube") == "yt_vid_111"
        assert data.get("twitter") == "tw_789"
