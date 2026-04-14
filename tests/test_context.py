"""Tests for pipeline/context.py — PipelineContext dataclass."""

from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.context import PipelineContext


def _minimal_ctx() -> PipelineContext:
    """Create a PipelineContext with only required fields."""
    return PipelineContext(
        episode_folder="test_ep",
        episode_number=1,
        episode_output_dir=Path("/tmp/ep"),
        timestamp="20260101_120000",
    )


class TestRequiredFields:
    def test_cannot_construct_without_required_fields(self):
        """The 4 required fields must be provided — dataclass enforces this."""
        with pytest.raises(TypeError):
            PipelineContext()  # type: ignore[call-arg]

    def test_required_fields_roundtrip(self):
        ctx = _minimal_ctx()
        assert ctx.episode_folder == "test_ep"
        assert ctx.episode_number == 1
        assert ctx.episode_output_dir == Path("/tmp/ep")
        assert ctx.timestamp == "20260101_120000"

    def test_episode_number_accepts_none(self):
        """episode_number is Optional — pre-pipeline we may not know the number yet."""
        ctx = PipelineContext(
            episode_folder="anon",
            episode_number=None,
            episode_output_dir=Path("/tmp/anon"),
            timestamp="t",
        )
        assert ctx.episode_number is None


class TestDefaults:
    def test_audio_fields_default_to_none(self):
        ctx = _minimal_ctx()
        assert ctx.audio_file is None
        assert ctx.transcript_path is None
        assert ctx.transcript_data is None
        assert ctx.analysis is None
        assert ctx.censored_audio is None
        assert ctx.raw_snapshot_path is None
        assert ctx.mp3_path is None

    def test_list_fields_default_to_empty_lists(self):
        """default_factory=list means each instance gets its own list —
        not a shared mutable default (classic Python footgun)."""
        ctx1 = _minimal_ctx()
        ctx2 = _minimal_ctx()
        assert ctx1.clip_paths == []
        assert ctx1.video_clip_paths == []
        assert ctx1.srt_paths == []
        assert ctx1.uploaded_clip_paths == []

        # Mutating one must not affect the other
        ctx1.clip_paths.append("foo.mp4")
        assert ctx2.clip_paths == []

    def test_run_mode_flags_default_false(self):
        ctx = _minimal_ctx()
        assert ctx.test_mode is False
        assert ctx.dry_run is False
        assert ctx.auto_approve is False
        assert ctx.resume is False
        assert ctx.force is False
        assert ctx.has_video_source is False

    def test_compliance_defaults(self):
        ctx = _minimal_ctx()
        assert ctx.compliance_result is None


class TestFieldsSetAfterConstruction:
    """Steps mutate fields on the context as they run — verify mutation works."""

    def test_assign_audio_fields(self):
        ctx = _minimal_ctx()
        ctx.audio_file = Path("/tmp/audio.wav")
        ctx.transcript_data = {"segments": []}
        assert ctx.audio_file == Path("/tmp/audio.wav")
        assert ctx.transcript_data == {"segments": []}

    def test_append_clip_paths(self):
        ctx = _minimal_ctx()
        ctx.clip_paths.append("clip1.mp4")
        ctx.clip_paths.append("clip2.mp4")
        assert ctx.clip_paths == ["clip1.mp4", "clip2.mp4"]

    def test_flip_flags(self):
        ctx = _minimal_ctx()
        ctx.dry_run = True
        ctx.force = True
        assert ctx.dry_run is True
        assert ctx.force is True
