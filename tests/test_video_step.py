"""Tests for pipeline.steps.video (run_video)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pipeline.context import PipelineContext
from pipeline.steps.video import run_video


def _make_ctx(tmp_path, **overrides):
    """Create a minimal PipelineContext for testing."""
    defaults = {
        "episode_folder": str(tmp_path),
        "episode_number": 25,
        "episode_output_dir": tmp_path,
        "timestamp": "20260329",
        "audio_file": tmp_path / "ep25.wav",
        "censored_audio": tmp_path / "ep25_censored.wav",
        "transcript_data": {"words": []},
        "analysis": {
            "best_clips": [
                {"start_seconds": 10, "end_seconds": 30, "title": "Clip 1"},
                {"start_seconds": 60, "end_seconds": 90, "title": "Clip 2"},
            ],
            "episode_title": "Test Episode",
        },
        "clip_paths": [],
        "srt_paths": [],
        "video_clip_paths": [],
        "has_video_source": False,
        "auto_approve": True,
    }
    defaults.update(overrides)
    return PipelineContext(**defaults)


def _make_components(**overrides):
    """Create a minimal components dict with mocks."""
    audio_proc = MagicMock()
    audio_proc.create_clips.return_value = [
        Path("/clips/clip_1.wav"),
        Path("/clips/clip_2.wav"),
    ]

    defaults = {
        "audio_processor": audio_proc,
        "clip_previewer": MagicMock(),
        "video_converter": None,
        "audiogram_generator": None,
        "subtitle_clip_generator": None,
        "thumbnail_generator": None,
    }
    defaults.update(overrides)
    return defaults


class TestRunVideoClipCreation:
    """Tests for Step 5: clip creation."""

    def test_creates_clips_from_analysis(self, tmp_path):
        """Clips are created via audio_processor.create_clips."""
        ctx = _make_ctx(tmp_path)
        components = _make_components()

        result = run_video(ctx, components)

        components["audio_processor"].create_clips.assert_called_once()
        assert len(result.clip_paths) == 2

    def test_resumes_clip_creation_from_state(self, tmp_path):
        """When state has completed create_clips, skips creation."""
        ctx = _make_ctx(tmp_path)
        components = _make_components()
        state = MagicMock()
        state.is_step_completed.side_effect = lambda step: step == "create_clips"
        state.get_step_outputs.return_value = {
            "clip_paths": ["/clips/clip_1.wav", "/clips/clip_2.wav"]
        }

        result = run_video(ctx, components, state=state)

        components["audio_processor"].create_clips.assert_not_called()
        assert len(result.clip_paths) == 2

    def test_saves_clip_state(self, tmp_path):
        """Clip creation saves state via complete_step."""
        ctx = _make_ctx(tmp_path)
        components = _make_components()
        state = MagicMock()
        state.is_step_completed.return_value = False

        run_video(ctx, components, state=state)

        state.complete_step.assert_any_call(
            "create_clips",
            {
                "clip_paths": [
                    str(p)
                    for p in components["audio_processor"].create_clips.return_value
                ]
            },
        )


class TestRunVideoClipApproval:
    """Tests for Step 5.1: clip approval."""

    def test_auto_approve_skips_preview(self, tmp_path):
        """With auto_approve=True, clip previewer is not called."""
        ctx = _make_ctx(tmp_path, auto_approve=True)
        components = _make_components()

        run_video(ctx, components)

        components["clip_previewer"].preview_clips.assert_not_called()

    def test_manual_approval_calls_previewer(self, tmp_path):
        """With auto_approve=False, clip previewer is called."""
        ctx = _make_ctx(tmp_path, auto_approve=False)
        components = _make_components()
        components["clip_previewer"].preview_clips.return_value = [0, 1]
        components["clip_previewer"].filter_clips.return_value = (
            [Path("/clips/clip_1.wav"), Path("/clips/clip_2.wav")],
            [{"start_seconds": 10, "end_seconds": 30}],
        )

        run_video(ctx, components)

        components["clip_previewer"].preview_clips.assert_called_once()
        components["clip_previewer"].filter_clips.assert_called_once()


class TestRunVideoSubtitles:
    """Tests for Step 5.4: subtitle generation."""

    @patch("pipeline.steps.video.SubtitleGenerator", create=True)
    def test_generates_subtitles_for_each_clip(self, mock_sub_cls, tmp_path):
        """Generates one SRT per clip."""
        mock_sub = MagicMock()
        mock_sub.generate_clip_srt.return_value = "/clips/clip_1.srt"
        mock_sub_cls.return_value = mock_sub
        ctx = _make_ctx(tmp_path)
        components = _make_components()

        with patch("pipeline.steps.video.SubtitleGenerator", mock_sub_cls):
            result = run_video(ctx, components)

        assert len(result.srt_paths) == 2

    def test_subtitle_failure_continues_without_subtitles(self, tmp_path):
        """If subtitle generation throws, pipeline continues."""
        ctx = _make_ctx(tmp_path)
        components = _make_components()

        with patch.dict("sys.modules", {"subtitle_generator": None}):
            result = run_video(ctx, components)

        # Should have None for each srt path
        assert all(s is None for s in result.srt_paths)

    def test_resumes_subtitles_from_state(self, tmp_path):
        """When state has completed subtitles, skips generation."""
        ctx = _make_ctx(tmp_path)
        components = _make_components()
        state = MagicMock()
        state.is_step_completed.side_effect = lambda step: (
            step in ("create_clips", "subtitles")
        )
        state.get_step_outputs.side_effect = lambda step: {
            "create_clips": {"clip_paths": ["/clips/clip_1.wav", "/clips/clip_2.wav"]},
            "subtitles": {"srt_paths": ["/clips/clip_1.srt", None]},
        }[step]

        result = run_video(ctx, components, state=state)

        assert len(result.srt_paths) == 2


class TestRunVideoConversion:
    """Tests for Step 5.5: video conversion."""

    def test_no_converter_skips_video(self, tmp_path):
        """When no video_converter and no audiogram, skips video creation."""
        ctx = _make_ctx(tmp_path)
        components = _make_components(video_converter=None, audiogram_generator=None)

        result = run_video(ctx, components)

        assert result.video_clip_paths == []

    def test_video_converter_creates_clips(self, tmp_path):
        """When video_converter is available, creates vertical clips."""
        vc = MagicMock()
        vc.convert_clips_to_videos.return_value = [
            "/clips/clip_1.mp4",
            "/clips/clip_2.mp4",
        ]
        vc.create_episode_video.return_value = "/output/episode.mp4"

        ctx = _make_ctx(tmp_path)
        components = _make_components(video_converter=vc)

        result = run_video(ctx, components)

        vc.convert_clips_to_videos.assert_called_once()
        assert len(result.video_clip_paths) == 2
        assert result.full_episode_video_path == "/output/episode.mp4"

    def test_audiogram_generator_creates_clips(self, tmp_path):
        """When audiogram_generator is enabled, creates audiogram clips."""
        ag = MagicMock()
        ag.enabled = True
        ag.create_audiogram_clips.return_value = ["/clips/clip_1.mp4"]

        ctx = _make_ctx(tmp_path)
        components = _make_components(audiogram_generator=ag)

        result = run_video(ctx, components)

        ag.create_audiogram_clips.assert_called_once()
        assert len(result.video_clip_paths) == 1

    def test_subtitle_clip_generator_creates_clips(self, tmp_path):
        """When subtitle_clip_generator is enabled, creates subtitle clips."""
        scg = MagicMock()
        scg.enabled = True
        scg.create_subtitle_clips.return_value = [
            "/clips/clip_1.mp4",
            "/clips/clip_2.mp4",
        ]

        ctx = _make_ctx(tmp_path)
        components = _make_components(subtitle_clip_generator=scg)

        result = run_video(ctx, components)

        scg.create_subtitle_clips.assert_called_once()
        assert len(result.video_clip_paths) == 2

    def test_resumes_video_conversion_from_state(self, tmp_path):
        """When state has completed convert_videos, skips conversion."""
        ctx = _make_ctx(tmp_path)
        components = _make_components()
        state = MagicMock()
        state.is_step_completed.side_effect = lambda step: (
            step
            in (
                "create_clips",
                "subtitles",
                "convert_videos",
            )
        )
        state.get_step_outputs.side_effect = lambda step: {
            "create_clips": {"clip_paths": ["/clips/clip_1.wav"]},
            "subtitles": {"srt_paths": ["/clips/clip_1.srt"]},
            "convert_videos": {
                "video_clip_paths": ["/clips/clip_1.mp4"],
                "full_episode_video_path": "/output/episode.mp4",
            },
        }[step]

        result = run_video(ctx, components, state=state)

        assert len(result.video_clip_paths) == 1
        assert result.full_episode_video_path == "/output/episode.mp4"


class TestRunVideoThumbnail:
    """Tests for Step 5.6: thumbnail generation."""

    def test_generates_thumbnail(self, tmp_path):
        """Thumbnail is generated when generator is available."""
        tg = MagicMock()
        tg.generate_thumbnail.return_value = "/output/thumb.png"

        ctx = _make_ctx(tmp_path)
        components = _make_components(thumbnail_generator=tg)

        result = run_video(ctx, components)

        tg.generate_thumbnail.assert_called_once_with(
            episode_title="Test Episode",
            episode_number=25,
            output_path=str(tmp_path / "ep25_20260329_thumbnail.png"),
        )
        assert result.thumbnail_path == "/output/thumb.png"

    def test_no_thumbnail_generator(self, tmp_path):
        """No thumbnail generator means thumbnail_path is None."""
        ctx = _make_ctx(tmp_path)
        components = _make_components(thumbnail_generator=None)

        result = run_video(ctx, components)

        assert result.thumbnail_path is None

    def test_thumbnail_failure_returns_none(self, tmp_path):
        """If thumbnail generation fails, thumbnail_path is None."""
        tg = MagicMock()
        tg.generate_thumbnail.return_value = None

        ctx = _make_ctx(tmp_path)
        components = _make_components(thumbnail_generator=tg)

        result = run_video(ctx, components)

        assert result.thumbnail_path is None


class TestRunVideoSourceBranch:
    """Tests for has_video_source branch — cut clips from source video."""

    @patch("video_utils.mux_audio_to_video")
    @patch("video_utils.cut_video_clip")
    def test_video_source_cuts_clips(self, mock_cut, mock_mux, tmp_path):
        """Cuts clips from source video when has_video_source is True."""
        clip_dir = tmp_path / "clips"
        clip_dir.mkdir()
        (tmp_path / "ep25.wav").write_text("fake")

        mock_cut.return_value = str(clip_dir / "clip_01_video.mp4")

        # Override analysis to have 1 clip, and audio_processor to return 1 clip
        audio_proc = MagicMock()
        audio_proc.create_clips.return_value = [clip_dir / "clip_01.wav"]

        ctx = _make_ctx(
            tmp_path,
            has_video_source=True,
            source_video_path=tmp_path / "source.mp4",
            analysis={
                "best_clips": [
                    {"start_seconds": 10, "end_seconds": 30, "title": "Clip 1"},
                ],
                "episode_title": "Test Episode",
            },
        )
        components = _make_components(
            audio_processor=audio_proc,
            subtitle_clip_generator=None,
            audiogram_generator=None,
        )

        result = run_video(ctx, components)

        mock_cut.assert_called_once()
        assert len(result.video_clip_paths) == 1

    @patch("video_utils.mux_audio_to_video")
    @patch("video_utils.cut_video_clip")
    def test_video_source_muxes_full_episode(self, mock_cut, mock_mux, tmp_path):
        """Muxes censored audio onto source video for full episode."""
        clip_dir = tmp_path / "clips"
        clip_dir.mkdir()
        (tmp_path / "ep25.wav").write_text("fake")
        censored = tmp_path / "ep25_censored.wav"
        censored.write_text("fake")

        mock_cut.return_value = None  # No clips
        mock_mux.return_value = str(tmp_path / "episode.mp4")

        ctx = _make_ctx(
            tmp_path,
            has_video_source=True,
            source_video_path=tmp_path / "source.mp4",
            censored_audio=censored,
            clip_paths=[],
        )
        components = _make_components()

        result = run_video(ctx, components)

        mock_mux.assert_called_once()
        assert result.full_episode_video_path is not None

    @patch("video_utils.mux_audio_to_video", return_value=None)
    @patch("video_utils.cut_video_clip")
    def test_video_source_mux_failure(self, mock_cut, mock_mux, tmp_path):
        """Handles mux failure gracefully."""
        clip_dir = tmp_path / "clips"
        clip_dir.mkdir()
        (tmp_path / "ep25.wav").write_text("fake")
        censored = tmp_path / "ep25_censored.wav"
        censored.write_text("fake")

        ctx = _make_ctx(
            tmp_path,
            has_video_source=True,
            source_video_path=tmp_path / "source.mp4",
            censored_audio=censored,
            clip_paths=[],
        )
        components = _make_components()

        result = run_video(ctx, components)
        assert result.full_episode_video_path is None

    @patch("video_utils.mux_audio_to_video")
    @patch("video_utils.cut_video_clip")
    def test_video_source_with_subtitles(self, mock_cut, mock_mux, tmp_path):
        """Video source branch generates ASS subtitles when subtitle_clip_generator enabled."""
        clip_dir = tmp_path / "clips"
        clip_dir.mkdir()
        (tmp_path / "ep25.wav").write_text("fake")

        mock_cut.return_value = str(clip_dir / "clip_01_video.mp4")

        mock_scg = MagicMock()
        mock_scg.enabled = True

        ctx = _make_ctx(
            tmp_path,
            has_video_source=True,
            source_video_path=tmp_path / "source.mp4",
            clip_paths=[clip_dir / "clip_01.wav"],
            transcript_data={
                "words": [{"word": "hello", "start": 10.0, "end": 10.5}],
            },
        )
        components = _make_components(subtitle_clip_generator=mock_scg)

        with patch("subtitle_generator.SubtitleGenerator") as mock_sub:
            mock_sub_instance = MagicMock()
            mock_sub_instance.extract_words_for_clip.return_value = [
                {"word": "hello", "start": 0.0, "end": 0.5}
            ]
            mock_sub.return_value = mock_sub_instance

            with patch(
                "subtitle_clip_generator.normalize_word_timestamps", return_value=[]
            ):
                run_video(ctx, components)

        assert mock_cut.called


class TestSubtitleClipFullEpisode:
    """Tests for subtitle_clip_generator branch creating full episode video."""

    def test_subtitle_clip_creates_full_episode(self, tmp_path):
        """Subtitle clip branch also creates full episode via video_converter."""
        clip_dir = tmp_path / "clips"
        clip_dir.mkdir()

        mock_scg = MagicMock()
        mock_scg.enabled = True
        mock_scg.create_subtitle_clips.return_value = [str(clip_dir / "clip_01.mp4")]

        mock_vc = MagicMock()
        mock_vc.create_episode_video.return_value = str(tmp_path / "episode.mp4")

        ctx = _make_ctx(
            tmp_path,
            clip_paths=[clip_dir / "clip_01.wav"],
            srt_paths=[clip_dir / "clip_01.srt"],
        )
        components = _make_components(
            subtitle_clip_generator=mock_scg,
            video_converter=mock_vc,
        )

        result = run_video(ctx, components)

        mock_scg.create_subtitle_clips.assert_called_once()
        mock_vc.create_episode_video.assert_called_once()
        assert result.full_episode_video_path is not None


class TestVideoConverterFullEpisodeFailure:
    """Tests for video_converter branch edge cases."""

    def test_full_episode_failure_logged(self, tmp_path):
        """When full episode video creation fails, warning logged but no crash."""
        clip_dir = tmp_path / "clips"
        clip_dir.mkdir()

        mock_vc = MagicMock()
        mock_vc.convert_clips_to_videos.return_value = [Path(clip_dir / "clip_01.mp4")]
        mock_vc.create_episode_video.return_value = None  # Failure

        ctx = _make_ctx(
            tmp_path,
            clip_paths=[clip_dir / "clip_01.wav"],
            srt_paths=[clip_dir / "clip_01.srt"],
        )
        components = _make_components(video_converter=mock_vc)

        result = run_video(ctx, components)

        assert result.full_episode_video_path is None
        assert len(result.video_clip_paths) == 1

    def test_no_clips_message(self, tmp_path):
        """When video_converter exists but no clips, logs 'No clips to convert'."""
        mock_vc = MagicMock()

        ctx = _make_ctx(tmp_path, clip_paths=[])
        # Override audio_processor to return empty clips
        audio_proc = MagicMock()
        audio_proc.create_clips.return_value = []
        components = _make_components(
            video_converter=mock_vc,
            audio_processor=audio_proc,
        )

        result = run_video(ctx, components)

        mock_vc.convert_clips_to_videos.assert_not_called()
        assert result.video_clip_paths == []


class TestAudiogramStateCheckpoint:
    """Tests for audiogram generator branch with state checkpoint."""

    def test_audiogram_saves_state(self, tmp_path):
        """Audiogram branch saves state checkpoint."""
        clip_dir = tmp_path / "clips"
        clip_dir.mkdir()

        mock_ag = MagicMock()
        mock_ag.enabled = True
        mock_ag.create_audiogram_clips.return_value = [str(clip_dir / "clip_01.mp4")]

        state = MagicMock()
        state.is_step_completed.return_value = False

        ctx = _make_ctx(
            tmp_path,
            clip_paths=[clip_dir / "clip_01.wav"],
            srt_paths=[None],
        )
        components = _make_components(audiogram_generator=mock_ag)

        run_video(ctx, components, state=state)

        # Verify state was saved for convert_videos
        convert_call = [
            c for c in state.complete_step.call_args_list if c[0][0] == "convert_videos"
        ]
        assert len(convert_call) == 1
        saved = convert_call[0][0][1]
        assert str(clip_dir / "clip_01.mp4") in saved["video_clip_paths"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
