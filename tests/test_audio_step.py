"""Tests for pipeline/steps/audio.py — run_audio step function."""

import json

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from pipeline.context import PipelineContext
from pipeline.steps.audio import run_audio


def _make_ctx(tmp_path):
    """Create a minimal PipelineContext for testing."""
    audio_file = tmp_path / "test_ep.wav"
    audio_file.write_text("fake")
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return PipelineContext(
        episode_folder="ep1",
        episode_number=1,
        episode_output_dir=output_dir,
        timestamp="20260331",
        audio_file=audio_file,
    )


def _make_components():
    """Create mock components dict used by run_audio."""
    transcriber = Mock()
    transcriber.transcribe.return_value = {"segments": [], "words": []}
    audio_processor = Mock()
    audio_processor.apply_censorship.return_value = Path("/fake/censored.wav")
    audio_processor.denoise_audio.return_value = Path("/fake/denoised.wav")
    audio_processor.normalize_audio.return_value = Path("/fake/normalized.wav")
    audio_processor.convert_to_mp3.return_value = Path("/fake/episode.mp3")
    return {
        "transcriber": transcriber,
        "audio_processor": audio_processor,
    }


class TestRunAudioDenoise:
    """Tests for the denoise step (4.3) gated by Config.DENOISE_ENABLED."""

    def test_denoise_called_when_enabled(self, tmp_path, monkeypatch):
        """denoise_audio is invoked between censor and normalize when enabled."""
        from config import Config

        monkeypatch.setattr(Config, "DENOISE_ENABLED", True)
        ctx = _make_ctx(tmp_path)
        components = _make_components()

        with patch("pipeline.steps.audio.subprocess.run"):
            run_audio(ctx, components, state=None)

        components["audio_processor"].denoise_audio.assert_called_once()
        # Must run before normalize (normalize's input is denoise's output)
        denoise_result = components["audio_processor"].denoise_audio.return_value
        components["audio_processor"].normalize_audio.assert_called_once_with(
            denoise_result
        )

    def test_denoise_skipped_when_disabled(self, tmp_path, monkeypatch):
        """denoise_audio is NOT called when DENOISE_ENABLED=False."""
        from config import Config

        monkeypatch.setattr(Config, "DENOISE_ENABLED", False)
        ctx = _make_ctx(tmp_path)
        components = _make_components()

        with patch("pipeline.steps.audio.subprocess.run"):
            run_audio(ctx, components, state=None)

        components["audio_processor"].denoise_audio.assert_not_called()
        # Normalize still runs, with censor's output directly
        censor_result = components["audio_processor"].apply_censorship.return_value
        components["audio_processor"].normalize_audio.assert_called_once_with(
            censor_result
        )

    def test_denoise_resume_loads_from_state(self, tmp_path, monkeypatch):
        """When denoise step is checkpointed, skip the ffmpeg call and reload path."""
        from config import Config

        monkeypatch.setattr(Config, "DENOISE_ENABLED", True)
        ctx = _make_ctx(tmp_path)
        components = _make_components()

        state = Mock()

        def is_completed(step):
            return step in ("censor", "denoise")

        state.is_step_completed.side_effect = is_completed

        def get_outputs(step):
            if step == "censor":
                return {
                    "censored_audio": "/fake/censored.wav",
                    "raw_snapshot_path": None,
                }
            if step == "denoise":
                return {"denoised_audio": "/fake/denoised_checkpoint.wav"}
            return {}

        state.get_step_outputs.side_effect = get_outputs

        run_audio(ctx, components, state=state)

        components["audio_processor"].denoise_audio.assert_not_called()
        components["audio_processor"].normalize_audio.assert_called_once_with(
            Path("/fake/denoised_checkpoint.wav")
        )


class TestRunAudioResumeTranscribe:
    """Tests for resuming transcription from checkpoint (lines 31-36)."""

    def test_resume_transcribe_loads_from_state(self, tmp_path):
        """When transcribe step is completed, load transcript from disk instead of running."""
        ctx = _make_ctx(tmp_path)
        components = _make_components()

        # Write a transcript file to load
        transcript_path = tmp_path / "output" / "transcript.json"
        transcript_data = {"segments": [{"text": "hello"}], "words": ["hello"]}
        transcript_path.write_text(json.dumps(transcript_data), encoding="utf-8")

        state = Mock()
        state.is_step_completed.side_effect = lambda step: step == "transcribe"
        state.get_step_outputs.return_value = {
            "transcript_path": str(transcript_path),
        }

        with patch("pipeline.steps.audio.subprocess.run"):
            result = run_audio(ctx, components, state=state)

        # Transcriber should NOT have been called
        components["transcriber"].transcribe.assert_not_called()
        assert result.transcript_data == transcript_data
        assert result.transcript_path == transcript_path


class TestRunAudioRawSnapshotFailure:
    """Tests for raw snapshot FFmpeg failure path (lines 85-87)."""

    def test_snapshot_ffmpeg_failure_sets_none(self, tmp_path):
        """When FFmpeg snapshot fails, raw_snapshot_path is set to None."""
        ctx = _make_ctx(tmp_path)
        components = _make_components()

        with patch(
            "pipeline.steps.audio.subprocess.run",
            side_effect=Exception("FFmpeg crashed"),
        ):
            result = run_audio(ctx, components, state=None)

        assert result.raw_snapshot_path is None


class TestRunAudioResumeNormalize:
    """Tests for resuming normalization from checkpoint (lines 121-124)."""

    def test_resume_normalize_loads_from_state(self, tmp_path):
        """When normalize step is completed, load path from state and skip processing."""
        ctx = _make_ctx(tmp_path)
        components = _make_components()

        state = Mock()

        def is_completed(step):
            return step in ("normalize", "censor")

        state.is_step_completed.side_effect = is_completed

        def get_outputs(step):
            if step == "transcribe":
                return {}
            if step == "censor":
                return {
                    "censored_audio": "/fake/censored.wav",
                    "raw_snapshot_path": None,
                }
            if step == "normalize":
                return {"normalized_audio": "/fake/normalized.wav"}
            return {}

        state.get_step_outputs.side_effect = get_outputs

        result = run_audio(ctx, components, state=state)

        # normalize_audio should NOT have been called
        components["audio_processor"].normalize_audio.assert_not_called()
        assert result.censored_audio == Path("/fake/normalized.wav")


class TestRunAudioResumeConvertMp3:
    """Tests for resuming MP3 conversion from checkpoint (lines 137-140)."""

    def test_resume_convert_mp3_loads_from_state(self, tmp_path):
        """When convert_mp3 step is completed, load mp3_path from state."""
        ctx = _make_ctx(tmp_path)
        components = _make_components()

        state = Mock()

        def is_completed(step):
            return step in ("censor", "normalize", "convert_mp3")

        state.is_step_completed.side_effect = is_completed

        def get_outputs(step):
            if step == "censor":
                return {
                    "censored_audio": "/fake/censored.wav",
                    "raw_snapshot_path": None,
                }
            if step == "normalize":
                return {"normalized_audio": "/fake/normalized.wav"}
            if step == "convert_mp3":
                return {"mp3_path": "/fake/episode.mp3"}
            return {}

        state.get_step_outputs.side_effect = get_outputs

        result = run_audio(ctx, components, state=state)

        components["audio_processor"].convert_to_mp3.assert_not_called()
        assert result.mp3_path == Path("/fake/episode.mp3")


class TestRunAudioChapterEmbedding:
    """Tests for ID3 chapter embedding (lines 148-150)."""

    def test_embeds_id3_chapters_when_available(self, tmp_path):
        """When chapter_generator is enabled and chapters exist, embed ID3 chapters."""
        ctx = _make_ctx(tmp_path)
        ctx.analysis = {
            "chapters": [{"title": "Intro", "start": 0, "end": 60}],
        }
        chapter_gen = Mock()
        chapter_gen.enabled = True
        components = _make_components()
        components["chapter_generator"] = chapter_gen

        with patch("pipeline.steps.audio.subprocess.run"):
            run_audio(ctx, components, state=None)

        chapter_gen.embed_id3_chapters.assert_called_once()
        call_args = chapter_gen.embed_id3_chapters.call_args
        assert call_args[0][1] == [{"title": "Intro", "start": 0, "end": 60}]

    def test_skips_chapters_when_generator_disabled(self, tmp_path):
        """When chapter_generator is disabled, skip embedding."""
        ctx = _make_ctx(tmp_path)
        ctx.analysis = {
            "chapters": [{"title": "Intro", "start": 0, "end": 60}],
        }
        chapter_gen = Mock()
        chapter_gen.enabled = False
        components = _make_components()
        components["chapter_generator"] = chapter_gen

        with patch("pipeline.steps.audio.subprocess.run"):
            run_audio(ctx, components, state=None)

        chapter_gen.embed_id3_chapters.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
