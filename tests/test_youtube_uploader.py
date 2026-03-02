"""Tests for YouTube uploader module."""

import pytest
from unittest.mock import Mock, patch, mock_open

from uploaders.youtube_uploader import (
    YouTubeUploader,
    create_episode_metadata,
    _format_chapters_for_youtube,
)


class TestYouTubeUploader:
    """Test cases for YouTubeUploader class."""

    @patch("uploaders.youtube_uploader.Path.exists")
    @patch("uploaders.youtube_uploader.build")
    @patch("builtins.open", new_callable=mock_open)
    def test_init_with_existing_token(self, mock_file, mock_build, mock_exists):
        """Test initialization with existing valid token."""
        mock_exists.return_value = True

        # Mock credentials
        mock_creds = Mock()
        mock_creds.valid = True

        # Mock pickle load
        with patch("pickle.load", return_value=mock_creds):
            uploader = YouTubeUploader()

        assert uploader.youtube is not None
        mock_build.assert_called_once()

    @patch("uploaders.youtube_uploader.Path.exists")
    def test_init_without_credentials_file(self, mock_exists):
        """Test initialization fails without credentials file."""
        mock_exists.return_value = False

        with pytest.raises(
            FileNotFoundError, match="YouTube credentials file not found"
        ):
            YouTubeUploader()

    @patch("uploaders.youtube_uploader.YouTubeUploader._authenticate")
    def test_upload_episode_file_not_found(self, mock_auth):
        """Test upload_episode with non-existent file."""
        uploader = YouTubeUploader()
        uploader.youtube = Mock()

        result = uploader.upload_episode(
            video_path="/nonexistent/video.mp4",
            title="Test Episode",
            description="Test description",
        )

        assert result is None

    @patch("uploaders.youtube_uploader.YouTubeUploader._authenticate")
    @patch("uploaders.youtube_uploader.Path.exists")
    @patch("uploaders.youtube_uploader.MediaFileUpload")
    def test_upload_episode_success(self, mock_media, mock_exists, mock_auth):
        """Test successful episode upload."""
        mock_exists.return_value = True
        uploader = YouTubeUploader()

        # Mock YouTube API
        mock_youtube = Mock()
        mock_request = Mock()
        mock_request.next_chunk.side_effect = [
            (Mock(progress=lambda: 0.5), None),
            (Mock(progress=lambda: 1.0), {"id": "test_video_id"}),
        ]
        mock_youtube.videos().insert.return_value = mock_request
        uploader.youtube = mock_youtube

        result = uploader.upload_episode(
            video_path=__file__,  # Use this file as dummy video
            title="Test Episode",
            description="Test description",
        )

        assert result is not None
        assert result["video_id"] == "test_video_id"
        assert result["status"] == "success"
        assert "video_url" in result

    @patch("uploaders.youtube_uploader.YouTubeUploader._authenticate")
    def test_upload_short(self, mock_auth):
        """Test upload_short adds #Shorts tag."""
        uploader = YouTubeUploader()
        uploader.youtube = Mock()

        with patch.object(uploader, "upload_episode") as mock_upload:
            mock_upload.return_value = {"video_id": "test_id"}

            uploader.upload_short(
                video_path="/test/video.mp4",
                title="Test Short",
                description="Test description",
            )

            # Verify #Shorts was added to title
            call_args = mock_upload.call_args
            assert "#Shorts" in call_args.kwargs["title"]

    @patch("uploaders.youtube_uploader.YouTubeUploader._authenticate")
    @patch("uploaders.youtube_uploader.Path.exists")
    @patch("uploaders.youtube_uploader.MediaFileUpload")
    def test_upload_thumbnail_success(self, mock_media, mock_exists, mock_auth):
        """Test successful thumbnail upload."""
        mock_exists.return_value = True
        uploader = YouTubeUploader()

        # Mock YouTube API
        mock_youtube = Mock()
        mock_request = Mock()
        mock_request.execute.return_value = {"items": [{"id": "thumb_id"}]}
        mock_youtube.thumbnails().set.return_value = mock_request
        uploader.youtube = mock_youtube

        result = uploader._upload_thumbnail("video123", __file__)

        assert result is True

    @patch("uploaders.youtube_uploader.YouTubeUploader._authenticate")
    def test_update_video_metadata_success(self, mock_auth):
        """Test successful video metadata update."""
        uploader = YouTubeUploader()

        # Mock YouTube API
        mock_youtube = Mock()
        mock_list = Mock()
        mock_list.execute.return_value = {
            "items": [
                {
                    "snippet": {
                        "title": "Old Title",
                        "description": "Old description",
                        "tags": [],
                    }
                }
            ]
        }
        mock_youtube.videos().list.return_value = mock_list

        mock_update = Mock()
        mock_update.execute.return_value = {}
        mock_youtube.videos().update.return_value = mock_update

        uploader.youtube = mock_youtube

        result = uploader.update_video_metadata(
            video_id="test_id", title="New Title", description="New description"
        )

        assert result is True

    @patch("uploaders.youtube_uploader.YouTubeUploader._authenticate")
    def test_get_upload_quota_usage(self, mock_auth):
        """Test quota usage information."""
        uploader = YouTubeUploader()

        quota_info = uploader.get_upload_quota_usage()

        assert "daily_limit" in quota_info
        assert "upload_cost" in quota_info
        assert quota_info["daily_limit"] == 10000


class TestCreateEpisodeMetadata:
    """Test cases for create_episode_metadata function."""

    def test_create_metadata_for_episode(self):
        """Test metadata creation for full episode."""
        metadata = create_episode_metadata(
            episode_number=25,
            episode_summary="Test summary",
            social_captions={"youtube": "YouTube caption"},
            clip_info=None,
        )

        assert "Episode #25" in metadata["title"]
        assert "Test summary" in metadata["description"]
        assert "tags" in metadata
        assert "podcast" in metadata["tags"]

    def test_create_metadata_for_clip(self):
        """Test metadata creation for clip/short."""
        clip_info = {"title": "Funny Moment", "description": "A funny clip"}

        metadata = create_episode_metadata(
            episode_number=25,
            episode_summary="Test summary",
            social_captions={"youtube": "YouTube caption"},
            clip_info=clip_info,
        )

        assert "Funny Moment" in metadata["title"]
        assert "A funny clip" in metadata["description"]
        assert "Episode #25" in metadata["description"]

    def test_metadata_includes_required_fields(self):
        """Test that metadata includes all required fields."""
        metadata = create_episode_metadata(
            episode_number=1,
            episode_summary="Summary",
            social_captions={},
            clip_info=None,
        )

        assert "title" in metadata
        assert "description" in metadata
        assert "tags" in metadata
        assert isinstance(metadata["tags"], list)


class TestFormatChaptersForYouTube:
    """Test cases for _format_chapters_for_youtube function."""

    def test_format_chapters_basic(self):
        """Test basic chapter formatting."""
        chapters = [
            {"start_timestamp": "00:00:00", "title": "Intro", "start_seconds": 0},
            {"start_timestamp": "00:05:30", "title": "Topic 1", "start_seconds": 330},
            {"start_timestamp": "00:15:00", "title": "Topic 2", "start_seconds": 900},
        ]
        result = _format_chapters_for_youtube(chapters)
        assert "0:00 Intro" in result
        assert "5:30 Topic 1" in result
        assert "15:00 Topic 2" in result

    def test_format_chapters_with_hours(self):
        """Test chapter formatting with hours."""
        chapters = [
            {"start_timestamp": "00:00:00", "title": "Intro", "start_seconds": 0},
            {"start_timestamp": "00:30:00", "title": "Middle", "start_seconds": 1800},
            {"start_timestamp": "01:05:00", "title": "End", "start_seconds": 3900},
        ]
        result = _format_chapters_for_youtube(chapters)
        assert "1:05:00 End" in result

    def test_format_chapters_too_few(self):
        """Test that fewer than 3 chapters returns empty string."""
        chapters = [
            {"start_timestamp": "00:00:00", "title": "Intro", "start_seconds": 0},
            {"start_timestamp": "00:05:00", "title": "Topic", "start_seconds": 300},
        ]
        result = _format_chapters_for_youtube(chapters)
        assert result == ""

    def test_format_chapters_empty(self):
        """Test that empty chapters returns empty string."""
        assert _format_chapters_for_youtube([]) == ""
        assert _format_chapters_for_youtube(None) == ""

    def test_format_chapters_first_not_zero(self):
        """Test that chapters not starting at 0 returns empty string."""
        chapters = [
            {"start_timestamp": "00:01:00", "title": "Topic", "start_seconds": 60},
            {"start_timestamp": "00:10:00", "title": "Topic 2", "start_seconds": 600},
            {"start_timestamp": "00:20:00", "title": "Topic 3", "start_seconds": 1200},
        ]
        result = _format_chapters_for_youtube(chapters)
        assert result == ""


class TestCreateEpisodeMetadataShowNotes:
    """Test cases for show_notes and chapters in create_episode_metadata."""

    def test_show_notes_in_full_episode_description(self):
        """Test that show_notes replaces episode_summary in description."""
        metadata = create_episode_metadata(
            episode_number=25,
            episode_summary="Short summary",
            social_captions={"youtube": "YouTube caption"},
            show_notes="Detailed show notes with bullets",
        )
        assert "Detailed show notes with bullets" in metadata["description"]
        assert "Short summary" not in metadata["description"]

    def test_fallback_to_summary_without_show_notes(self):
        """Test fallback to episode_summary when no show_notes."""
        metadata = create_episode_metadata(
            episode_number=25,
            episode_summary="Short summary",
            social_captions={"youtube": "YouTube caption"},
        )
        assert "Short summary" in metadata["description"]

    def test_chapters_appended_to_description(self):
        """Test that chapters are appended to episode description."""
        chapters = [
            {"start_timestamp": "00:00:00", "title": "Intro", "start_seconds": 0},
            {"start_timestamp": "00:05:00", "title": "Topic 1", "start_seconds": 300},
            {"start_timestamp": "00:15:00", "title": "Topic 2", "start_seconds": 900},
        ]
        metadata = create_episode_metadata(
            episode_number=25,
            episode_summary="Summary",
            social_captions={},
            chapters=chapters,
        )
        assert "Chapters:" in metadata["description"]
        assert "Intro" in metadata["description"]
        assert "Topic 1" in metadata["description"]

    def test_hook_caption_in_clip_description(self):
        """Test that hook_caption is prepended for clips."""
        clip_info = {
            "title": "Funny Moment",
            "description": "A funny clip",
            "hook_caption": "Wait for it...",
        }
        metadata = create_episode_metadata(
            episode_number=25,
            episode_summary="Summary",
            social_captions={"youtube": "YouTube caption"},
            clip_info=clip_info,
        )
        assert metadata["description"].startswith("Wait for it...")

    def test_clip_without_hook_caption(self):
        """Test clip description without hook_caption."""
        clip_info = {"title": "Funny Moment", "description": "A funny clip"}
        metadata = create_episode_metadata(
            episode_number=25,
            episode_summary="Summary",
            social_captions={"youtube": "YouTube caption"},
            clip_info=clip_info,
        )
        assert "A funny clip" in metadata["description"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
