"""Tests for subtitle_clip_generator module."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from subtitle_clip_generator import (
    SubtitleClipGenerator,
    normalize_word_timestamps,
    _group_into_cards,
)
from config import Config


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Remove subtitle-clip-related env vars so each test starts from defaults."""
    for key in (
        "USE_SUBTITLE_CLIPS",
        "SUBTITLE_FONT_SIZE",
        "SUBTITLE_ACCENT_COLOR",
        "SUBTITLE_FONT_COLOR",
        "SUBTITLE_BG_COLOR",
    ):
        monkeypatch.delenv(key, raising=False)


# ---------------------------------------------------------------------------
# 1. TestInitDefaults
# ---------------------------------------------------------------------------
class TestInitDefaults:
    def test_defaults_when_env_unset(self):
        gen = SubtitleClipGenerator()
        assert gen.enabled is True
        assert gen.accent_color == "0x00e0ff"
        assert gen.font_size == 72
        assert gen.ffmpeg_path == Config.FFMPEG_PATH

    def test_disabled_when_env_false(self, monkeypatch):
        monkeypatch.setenv("USE_SUBTITLE_CLIPS", "false")
        gen = SubtitleClipGenerator()
        assert gen.enabled is False


# ---------------------------------------------------------------------------
# 2. TestNormalizeWordTimestamps
# ---------------------------------------------------------------------------
class TestNormalizeWordTimestamps:
    def test_empty_list_returns_empty(self):
        assert normalize_word_timestamps([]) == []

    def test_gaps_under_150ms_are_closed(self):
        words = [
            {"word": "hello", "start": 0.0, "end": 0.5},
            {"word": "world", "start": 0.6, "end": 1.0},  # 100ms gap — should close
        ]
        result = normalize_word_timestamps(words)
        assert result[0]["end"] == pytest.approx(0.6)

    def test_gaps_over_150ms_are_not_closed(self):
        words = [
            {"word": "hello", "start": 0.0, "end": 0.5},
            {"word": "world", "start": 0.8, "end": 1.2},  # 300ms gap — leave it
        ]
        result = normalize_word_timestamps(words)
        assert result[0]["end"] == pytest.approx(0.5)

    def test_overlapping_timestamps_resolved(self):
        words = [
            {"word": "hello", "start": 0.0, "end": 0.8},
            {"word": "world", "start": 0.7, "end": 1.2},  # overlaps
        ]
        result = normalize_word_timestamps(words)
        assert result[0]["end"] < result[1]["start"]
        assert result[0]["end"] == pytest.approx(0.699, abs=0.001)

    def test_missing_timestamps_interpolated(self):
        words = [
            {"word": "hello", "start": 0.0, "end": 0.5},
            {"word": "missing", "start": 0.0, "end": 0.0},  # unaligned
            {"word": "world", "start": 1.0, "end": 1.5},
        ]
        result = normalize_word_timestamps(words)
        # The unaligned word should get non-zero timestamps
        assert result[1]["start"] >= 0.5
        assert result[1]["end"] > result[1]["start"]

    def test_single_word_with_missing_timestamps(self):
        words = [{"word": "lonely", "start": 0.0, "end": 0.0}]
        result = normalize_word_timestamps(words)
        assert result[0]["end"] > result[0]["start"]


# ---------------------------------------------------------------------------
# 3. TestEscapeFilterPath
# ---------------------------------------------------------------------------
class TestEscapeFilterPath:
    def test_windows_path_colon_escaped(self):
        gen = SubtitleClipGenerator()
        result = gen._escape_ffmpeg_filter_path(r"C:\Users\foo\file.ass")
        assert result == "C\\:/Users/foo/file.ass"

    def test_unix_path_passes_through(self):
        gen = SubtitleClipGenerator()
        result = gen._escape_ffmpeg_filter_path("/home/user/file.ass")
        assert result == "/home/user/file.ass"

    def test_relative_path_passes_through(self):
        gen = SubtitleClipGenerator()
        result = gen._escape_ffmpeg_filter_path("relative/path/file.ass")
        assert result == "relative/path/file.ass"


# ---------------------------------------------------------------------------
# 4. TestGroupIntoCards
# ---------------------------------------------------------------------------
class TestGroupIntoCards:
    def test_7_words_produces_3_cards(self):
        words = [
            {"word": f"w{i}", "start": float(i), "end": float(i) + 0.5}
            for i in range(7)
        ]
        cards = _group_into_cards(words, max_words=3)
        assert len(cards) == 3
        assert len(cards[0]) == 3
        assert len(cards[1]) == 3
        assert len(cards[2]) == 1

    def test_empty_list_returns_empty(self):
        assert _group_into_cards([], max_words=3) == []


# ---------------------------------------------------------------------------
# 5. TestToBgrHex
# ---------------------------------------------------------------------------
class TestToBgrHex:
    def test_cyan_rgb_converts_to_bgr(self):
        gen = SubtitleClipGenerator()
        # 0x00e0ff is R=00, G=e0, B=ff -> BGR = ffe000
        result = gen._to_bgr_hex("0x00e0ff")
        assert result == "ffe000"

    def test_accent_color_converts_correctly(self):
        gen = SubtitleClipGenerator()
        # 0xe94560 is R=e9, G=45, B=60 -> BGR = 6045e9
        result = gen._to_bgr_hex("0xe94560")
        assert result == "6045e9"

    def test_hash_prefix_works(self):
        gen = SubtitleClipGenerator()
        # Same as above but with # prefix
        result = gen._to_bgr_hex("#00e0ff")
        assert result == "ffe000"


# ---------------------------------------------------------------------------
# 6. TestGenerateAssFile
# ---------------------------------------------------------------------------
class TestGenerateAssFile:
    def test_ass_file_has_v4_styles_section(self, tmp_path):
        gen = SubtitleClipGenerator()
        words = [
            {"word": "hello", "start": 0.0, "end": 0.5},
            {"word": "world", "start": 0.5, "end": 1.0},
        ]
        ass_path = str(tmp_path / "test.ass")
        gen._generate_ass_file(words, ass_path, 720, 1280)
        content = Path(ass_path).read_text(encoding="utf-8")
        assert "[V4+ Styles]" in content

    def test_style_uses_anton_font_at_72(self, tmp_path):
        gen = SubtitleClipGenerator()
        words = [
            {"word": "hello", "start": 0.0, "end": 0.5},
        ]
        ass_path = str(tmp_path / "test.ass")
        gen._generate_ass_file(words, ass_path, 720, 1280)
        content = Path(ass_path).read_text(encoding="utf-8")
        assert "Anton" in content
        assert "72" in content

    def test_active_word_has_accent_color_tag(self, tmp_path):
        gen = SubtitleClipGenerator()
        words = [
            {"word": "hello", "start": 0.0, "end": 0.5},
            {"word": "world", "start": 0.5, "end": 1.0},
        ]
        ass_path = str(tmp_path / "test.ass")
        gen._generate_ass_file(words, ass_path, 720, 1280)
        content = Path(ass_path).read_text(encoding="utf-8")
        # Should contain accent color tag \c&H...&
        assert r"\c&H" in content

    def test_curly_braces_in_transcript_escaped(self, tmp_path):
        gen = SubtitleClipGenerator()
        words = [
            {"word": "{laugh}", "start": 0.0, "end": 0.5},
        ]
        ass_path = str(tmp_path / "test.ass")
        gen._generate_ass_file(words, ass_path, 720, 1280)
        content = Path(ass_path).read_text(encoding="utf-8")
        # Raw { should be escaped as \{ in event text
        # The events section has the text
        lines = content.split("\n")
        event_lines = [line for line in lines if line.startswith("Dialogue:")]
        assert len(event_lines) > 0
        # The transcript { should be escaped
        dialogue_text = " ".join(event_lines)
        assert r"\{" in dialogue_text or "{LAUGH}" not in dialogue_text

    def test_words_grouped_into_cards_of_3(self, tmp_path):
        gen = SubtitleClipGenerator()
        # 4 words -> 2 cards: (3) + (1)
        # Each word in each card becomes its own SSAEvent, so 3+1 + 1 = 4 events total
        # card 1 has 3 words so 3 events, card 2 has 1 word so 1 event = 4 events
        words = [
            {"word": f"w{i}", "start": float(i) * 0.5, "end": float(i) * 0.5 + 0.4}
            for i in range(4)
        ]
        ass_path = str(tmp_path / "test.ass")
        gen._generate_ass_file(words, ass_path, 720, 1280)
        content = Path(ass_path).read_text(encoding="utf-8")
        event_lines = [
            line for line in content.split("\n") if line.startswith("Dialogue:")
        ]
        # 4 words = 4 events (each word highlighted once per card)
        assert len(event_lines) == 4

    def test_surrounding_words_are_white(self, tmp_path):
        gen = SubtitleClipGenerator()
        words = [
            {"word": "one", "start": 0.0, "end": 0.5},
            {"word": "two", "start": 0.5, "end": 1.0},
            {"word": "three", "start": 1.0, "end": 1.5},
        ]
        ass_path = str(tmp_path / "test.ass")
        gen._generate_ass_file(words, ass_path, 720, 1280)
        content = Path(ass_path).read_text(encoding="utf-8")
        # White reset tag should appear after each active word
        assert r"\c&HFFFFFF&" in content


# ---------------------------------------------------------------------------
# 7. TestBuildFfmpegCommand
# ---------------------------------------------------------------------------
class TestBuildFfmpegCommand:
    def test_filter_complex_has_subtitles_filter(self):
        gen = SubtitleClipGenerator()
        cmd = gen._build_ffmpeg_command(
            audio_path="/path/audio.wav",
            ass_path="/path/test.ass",
            output_path="/path/output.mp4",
            width=720,
            height=1280,
        )
        fc_idx = cmd.index("-filter_complex")
        filter_str = cmd[fc_idx + 1]
        assert "subtitles=" in filter_str

    def test_filter_complex_has_fontsdir(self):
        gen = SubtitleClipGenerator()
        cmd = gen._build_ffmpeg_command(
            audio_path="/path/audio.wav",
            ass_path="/path/test.ass",
            output_path="/path/output.mp4",
            width=720,
            height=1280,
        )
        fc_idx = cmd.index("-filter_complex")
        filter_str = cmd[fc_idx + 1]
        assert "fontsdir=" in filter_str

    def test_audio_reencoded_as_aac(self):
        """Audio must be re-encoded to AAC — raw PCM (WAV) cannot be stream-copied
        into an MP4 container. Regression test for commit 5d9ec24.
        """
        gen = SubtitleClipGenerator()
        cmd = gen._build_ffmpeg_command(
            audio_path="/path/audio.wav",
            ass_path="/path/test.ass",
            output_path="/path/output.mp4",
            width=720,
            height=1280,
        )
        assert "-c:a" in cmd
        ca_idx = cmd.index("-c:a")
        assert cmd[ca_idx + 1] == "aac"

    def test_vertical_dimensions_720x1280(self):
        gen = SubtitleClipGenerator()
        cmd = gen._build_ffmpeg_command(
            audio_path="/path/audio.wav",
            ass_path="/path/test.ass",
            output_path="/path/output.mp4",
            width=720,
            height=1280,
        )
        fc_idx = cmd.index("-filter_complex")
        filter_str = cmd[fc_idx + 1]
        assert "720" in filter_str
        assert "1280" in filter_str

    def test_windows_ass_path_colon_escaped(self):
        gen = SubtitleClipGenerator()
        cmd = gen._build_ffmpeg_command(
            audio_path="/path/audio.wav",
            ass_path=r"C:\Users\foo\test.ass",
            output_path="/path/output.mp4",
            width=720,
            height=1280,
        )
        fc_idx = cmd.index("-filter_complex")
        filter_str = cmd[fc_idx + 1]
        # Windows colon should be escaped in filter string
        assert "C\\:" in filter_str


# ---------------------------------------------------------------------------
# 8. TestCreateSubtitleClip
# ---------------------------------------------------------------------------
class TestCreateSubtitleClip:
    @patch("subtitle_clip_generator.subprocess.run")
    @patch("subtitle_clip_generator.Path")
    def test_returns_none_when_audio_missing(self, mock_path_cls, mock_run):
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path_instance.__str__ = MagicMock(return_value="/path/audio.wav")
        mock_path_instance.parent = Path("/path")
        mock_path_instance.stem = "audio"
        mock_path_cls.return_value = mock_path_instance

        gen = SubtitleClipGenerator()
        result = gen.create_subtitle_clip(
            audio_path="/path/audio.wav",
            srt_path=None,
            transcript_data={"words": []},
            clip_info={"start_seconds": 0.0, "end_seconds": 10.0},
            output_path="/path/output.mp4",
            format_type="vertical",
        )
        assert result is None
        mock_run.assert_not_called()

    @patch("subtitle_clip_generator.subprocess.run")
    @patch("subtitle_clip_generator.SubtitleGenerator")
    def test_calls_ffmpeg_and_returns_output_path(
        self, mock_sub_gen_cls, mock_run, tmp_path
    ):
        # Create a real audio file so exists() returns True
        audio_file = tmp_path / "clip.wav"
        audio_file.touch()
        output_file = tmp_path / "clip_subtitle.mp4"

        mock_sub_gen = MagicMock()
        mock_sub_gen.extract_words_for_clip.return_value = [
            {"word": "hello", "start": 0.0, "end": 0.5},
            {"word": "world", "start": 0.5, "end": 1.0},
        ]
        mock_sub_gen_cls.return_value = mock_sub_gen

        mock_run.return_value = MagicMock(returncode=0, stderr="")

        gen = SubtitleClipGenerator()
        result = gen.create_subtitle_clip(
            audio_path=str(audio_file),
            srt_path=None,
            transcript_data={"words": [{"word": "hello", "start": 0.0, "end": 0.5}]},
            clip_info={"start_seconds": 0.0, "end_seconds": 2.0},
            output_path=str(output_file),
            format_type="vertical",
        )
        assert result == str(output_file)
        mock_run.assert_called_once()
        # Verify the FFmpeg args list was passed (not shell=True)
        call_args = mock_run.call_args
        assert call_args[1].get("shell") is not True or call_args[0][0] is not None


# ---------------------------------------------------------------------------
# 9. TestCreateSubtitleClips
# ---------------------------------------------------------------------------
class TestCreateSubtitleClips:
    @patch.object(SubtitleClipGenerator, "create_subtitle_clip")
    def test_batch_calls_create_per_clip(self, mock_create):
        mock_create.side_effect = [
            "/out/clip1_subtitle.mp4",
            "/out/clip2_subtitle.mp4",
        ]
        gen = SubtitleClipGenerator()
        clip_paths = ["/clips/clip1.wav", "/clips/clip2.wav"]
        srt_paths = [None, None]
        transcript_data = {"words": []}
        best_clips = [
            {"start_seconds": 0.0, "end_seconds": 30.0},
            {"start_seconds": 30.0, "end_seconds": 60.0},
        ]
        results = gen.create_subtitle_clips(
            clip_paths=clip_paths,
            srt_paths=srt_paths,
            transcript_data=transcript_data,
            best_clips=best_clips,
            format_type="vertical",
        )
        assert len(results) == 2
        assert mock_create.call_count == 2

    @patch.object(SubtitleClipGenerator, "create_subtitle_clip")
    def test_batch_filters_none_results(self, mock_create):
        mock_create.side_effect = ["/out/clip1_subtitle.mp4", None]
        gen = SubtitleClipGenerator()
        results = gen.create_subtitle_clips(
            clip_paths=["/clips/clip1.wav", "/clips/clip2.wav"],
            srt_paths=[None, None],
            transcript_data={"words": []},
            best_clips=[
                {"start_seconds": 0.0, "end_seconds": 30.0},
                {"start_seconds": 30.0, "end_seconds": 60.0},
            ],
            format_type="vertical",
        )
        assert len(results) == 1
        assert results[0] == "/out/clip1_subtitle.mp4"
