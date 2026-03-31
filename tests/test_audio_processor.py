"""Tests for audio_processor module."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch
from pydub import AudioSegment

from audio_processor import AudioProcessor
from config import Config
from pipeline.context import PipelineContext
from pipeline.steps.audio import run_audio


@pytest.fixture
def audio_processor():
    """Create an AudioProcessor instance."""
    return AudioProcessor()


@pytest.fixture
def mock_audio_segment():
    """Create a mock AudioSegment."""
    audio = Mock(spec=AudioSegment)
    audio.duration_seconds = 100.0
    audio.__len__ = Mock(return_value=100000)  # milliseconds
    audio.__getitem__ = Mock(return_value=audio)
    audio.overlay = Mock(return_value=audio)
    audio.export = Mock()
    return audio


class TestAudioProcessor:
    """Test AudioProcessor functionality."""

    def test_init(self, audio_processor):
        """Test AudioProcessor initialization."""
        assert audio_processor is not None
        assert audio_processor.beep_sound is not None

    @patch("audio_processor.AudioSegment.from_file")
    def test_apply_censorship_supports_multiple_formats(
        self, mock_from_file, audio_processor, mock_audio_segment, tmp_path
    ):
        """Test that apply_censorship uses from_file (supports all formats)."""
        # Setup
        mock_from_file.return_value = mock_audio_segment
        audio_file = tmp_path / "test.mp4"
        audio_file.write_text("fake audio")
        output_path = tmp_path / "output.wav"
        censor_timestamps = []

        # Execute
        audio_processor.apply_censorship(audio_file, censor_timestamps, output_path)

        # Verify - Should use from_file, not from_wav
        mock_from_file.assert_called_once()
        assert mock_from_file.call_args[0][0] == str(audio_file)

    @patch("audio_processor.AudioSegment.from_file")
    def test_apply_censorship_with_mp4_file(
        self, mock_from_file, audio_processor, mock_audio_segment, tmp_path
    ):
        """Test censorship works with MP4 files."""
        mock_from_file.return_value = mock_audio_segment
        audio_file = tmp_path / "test.mp4"
        audio_file.write_text("fake")
        output_path = tmp_path / "output.wav"

        result = audio_processor.apply_censorship(audio_file, [], output_path)

        assert result == output_path

    @patch("audio_processor.AudioSegment.from_file")
    def test_apply_censorship_with_m4a_file(
        self, mock_from_file, audio_processor, mock_audio_segment, tmp_path
    ):
        """Test censorship works with M4A files."""
        mock_from_file.return_value = mock_audio_segment
        audio_file = tmp_path / "test.m4a"
        audio_file.write_text("fake")
        output_path = tmp_path / "output.wav"

        result = audio_processor.apply_censorship(audio_file, [], output_path)

        assert result == output_path

    @patch("audio_processor.AudioSegment.from_file")
    def test_apply_censorship_with_wav_file(
        self, mock_from_file, audio_processor, mock_audio_segment, tmp_path
    ):
        """Test censorship works with WAV files."""
        mock_from_file.return_value = mock_audio_segment
        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake")
        output_path = tmp_path / "output.wav"

        result = audio_processor.apply_censorship(audio_file, [], output_path)

        assert result == output_path

    @patch("audio_processor.AudioSegment.from_file")
    def test_apply_censorship_applies_beeps(
        self, mock_from_file, audio_processor, tmp_path
    ):
        """Test that censorship applies beep sounds at correct timestamps."""
        # Setup - Create a mock that maintains its identity through concatenation
        mock_audio = Mock(spec=AudioSegment)
        mock_audio.__len__ = Mock(return_value=100000)  # 100 seconds in ms

        # Mock slicing and concatenation to return the same mock
        # This simulates audio = audio[:start] + beep + audio[end:]
        mock_audio.__getitem__ = Mock(return_value=mock_audio)
        mock_audio.__add__ = Mock(return_value=mock_audio)
        mock_audio.export = Mock()

        mock_from_file.return_value = mock_audio

        # Mock beep sound that supports slicing and length
        audio_processor.beep_sound = Mock(spec=AudioSegment)
        audio_processor.beep_sound.__len__ = Mock(return_value=1000)  # 1 second beep
        audio_processor.beep_sound.__getitem__ = Mock(return_value=mock_audio)

        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake")
        output_path = tmp_path / "output.wav"

        censor_timestamps = [
            {"seconds": 10.0, "reason": "Test"},
            {"seconds": 20.0, "reason": "Test2"},
        ]

        # Execute
        result = audio_processor.apply_censorship(
            audio_file, censor_timestamps, output_path
        )

        # Verify censorship was applied
        assert result == output_path
        # Verify export was called
        mock_audio.export.assert_called_once()

    @patch("audio_processor.AudioSegment.from_file")
    def test_extract_clip(
        self, mock_from_file, audio_processor, mock_audio_segment, tmp_path
    ):
        """Test extracting audio clip."""
        # Setup mock with fade support
        mock_clip = Mock(spec=AudioSegment)
        mock_clip.fade_in = Mock(return_value=mock_clip)
        mock_clip.fade_out = Mock(return_value=mock_clip)
        mock_clip.export = Mock()

        mock_audio_segment.__getitem__ = Mock(return_value=mock_clip)
        mock_from_file.return_value = mock_audio_segment

        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake")
        output_path = tmp_path / "clip.wav"

        # Use correct function signature: start_seconds, end_seconds, output_path
        result = audio_processor.extract_clip(audio_file, 10.0, 40.0, output_path)

        assert result == output_path
        # Verify slicing happened
        mock_audio_segment.__getitem__.assert_called()

    @patch("audio_processor.AudioSegment.from_file")
    def test_create_clips(
        self, mock_from_file, audio_processor, mock_audio_segment, tmp_path
    ):
        """Test creating multiple clips."""
        # Setup mock with fade support
        mock_clip = Mock(spec=AudioSegment)
        mock_clip.fade_in = Mock(return_value=mock_clip)
        mock_clip.fade_out = Mock(return_value=mock_clip)
        mock_clip.export = Mock()

        mock_audio_segment.__getitem__ = Mock(return_value=mock_clip)
        mock_from_file.return_value = mock_audio_segment

        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake")
        clip_dir = tmp_path / "clips"
        clip_dir.mkdir()

        # Use correct key names: 'start_seconds', 'end_seconds', 'description'
        best_clips = [
            {"start_seconds": 10.0, "end_seconds": 40.0, "description": "Clip 1"},
            {"start_seconds": 50.0, "end_seconds": 80.0, "description": "Clip 2"},
        ]

        result = audio_processor.create_clips(audio_file, best_clips, clip_dir)

        assert len(result) == 2
        assert all(path.parent == clip_dir for path in result)

    @patch("audio_processor.subprocess.run")
    def test_convert_to_mp3(self, mock_run, audio_processor, tmp_path):
        """Test converting audio to MP3 via direct FFmpeg call."""
        mock_run.return_value = MagicMock(returncode=0)
        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake")

        result = audio_processor.convert_to_mp3(audio_file)

        assert result.suffix == ".mp3"
        assert result.parent == audio_file.parent
        # Verify FFmpeg was called with libmp3lame
        cmd = mock_run.call_args[0][0]
        assert "libmp3lame" in cmd

    def test_beep_sound_loaded(self):
        """Test that AudioProcessor loads beep sound."""
        # This should work (beep will be generated if file doesn't exist)
        processor = AudioProcessor()
        assert processor.beep_sound is not None

    @patch("audio_processor.AudioSegment.from_file")
    def test_empty_censor_timestamps(
        self, mock_from_file, audio_processor, mock_audio_segment, tmp_path
    ):
        """Test censorship with no timestamps (no censoring needed)."""
        mock_from_file.return_value = mock_audio_segment
        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake")
        output_path = tmp_path / "output.wav"

        result = audio_processor.apply_censorship(audio_file, [], output_path)

        assert result == output_path

    @patch("audio_processor.AudioSegment.from_file")
    def test_empty_clips_list(
        self, mock_from_file, audio_processor, mock_audio_segment, tmp_path
    ):
        """Test creating clips with empty list."""
        mock_from_file.return_value = mock_audio_segment
        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake")
        clip_dir = tmp_path / "clips"
        clip_dir.mkdir()

        result = audio_processor.create_clips(audio_file, [], clip_dir)

        assert len(result) == 0


class TestCensoringTimestampAccuracy:
    """Tests for accurate word-level censoring timestamps."""

    @patch("audio_processor.AudioSegment.from_file")
    def test_censorship_uses_word_boundaries(
        self, mock_from_file, audio_processor, tmp_path
    ):
        """Test that censorship uses start_seconds/end_seconds when available."""
        # Setup - Create a mock audio
        mock_audio = Mock(spec=AudioSegment)
        mock_audio.__len__ = Mock(return_value=100000)  # 100 seconds in ms
        mock_audio.__getitem__ = Mock(return_value=mock_audio)
        mock_audio.__add__ = Mock(return_value=mock_audio)
        mock_audio.export = Mock()
        mock_from_file.return_value = mock_audio

        # Mock beep sound
        audio_processor.beep_sound = Mock(spec=AudioSegment)
        audio_processor.beep_sound.__len__ = Mock(return_value=1000)
        audio_processor.beep_sound.__getitem__ = Mock(return_value=mock_audio)
        audio_processor.beep_sound.__mul__ = Mock(return_value=mock_audio)

        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake")
        output_path = tmp_path / "output.wav"

        # Use word-level timestamps (the fix)
        censor_timestamps = [
            {
                "seconds": 10.0,  # Segment timestamp (old behavior would use this)
                "start_seconds": 10.234,  # Actual word start
                "end_seconds": 10.567,  # Actual word end
                "reason": "Name: Joey",
            }
        ]

        # Execute
        result = audio_processor.apply_censorship(
            audio_file, censor_timestamps, output_path
        )

        # Verify - the slicing should use word boundaries (10.234-0.05 to 10.567+0.05)
        # This means ~10184ms to ~10617ms
        assert result == output_path
        mock_audio.export.assert_called_once()

    @patch("audio_processor.AudioSegment.from_file")
    def test_censorship_falls_back_to_seconds(
        self, mock_from_file, audio_processor, tmp_path
    ):
        """Test that censorship falls back to 'seconds' when word boundaries not available."""
        mock_audio = Mock(spec=AudioSegment)
        mock_audio.__len__ = Mock(return_value=100000)
        mock_audio.__getitem__ = Mock(return_value=mock_audio)
        mock_audio.__add__ = Mock(return_value=mock_audio)
        mock_audio.export = Mock()
        mock_from_file.return_value = mock_audio

        audio_processor.beep_sound = Mock(spec=AudioSegment)
        audio_processor.beep_sound.__len__ = Mock(return_value=1000)
        audio_processor.beep_sound.__getitem__ = Mock(return_value=mock_audio)

        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake")
        output_path = tmp_path / "output.wav"

        # Old format without word boundaries
        censor_timestamps = [{"seconds": 10.0, "reason": "Name: Joey"}]

        result = audio_processor.apply_censorship(
            audio_file, censor_timestamps, output_path
        )

        assert result == output_path

    @patch("audio_processor.AudioSegment.from_file")
    def test_censorship_sorting_uses_start_seconds(
        self, mock_from_file, audio_processor, tmp_path
    ):
        """Test that censorship sorts by start_seconds when available."""
        mock_audio = Mock(spec=AudioSegment)
        mock_audio.__len__ = Mock(return_value=100000)
        mock_audio.__getitem__ = Mock(return_value=mock_audio)
        mock_audio.__add__ = Mock(return_value=mock_audio)
        mock_audio.export = Mock()
        mock_from_file.return_value = mock_audio

        audio_processor.beep_sound = Mock(spec=AudioSegment)
        audio_processor.beep_sound.__len__ = Mock(return_value=1000)
        audio_processor.beep_sound.__getitem__ = Mock(return_value=mock_audio)
        audio_processor.beep_sound.__mul__ = Mock(return_value=mock_audio)

        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake")
        output_path = tmp_path / "output.wav"

        # Timestamps out of order by segment time, but in order by start_seconds
        censor_timestamps = [
            {
                "seconds": 20.0,
                "start_seconds": 5.0,
                "end_seconds": 5.5,
                "reason": "First",
            },
            {
                "seconds": 10.0,
                "start_seconds": 15.0,
                "end_seconds": 15.5,
                "reason": "Second",
            },
        ]

        result = audio_processor.apply_censorship(
            audio_file, censor_timestamps, output_path
        )

        assert result == output_path

    @patch("audio_processor.AudioSegment.from_file")
    def test_censorship_handles_short_words(
        self, mock_from_file, audio_processor, tmp_path
    ):
        """Test censorship handles very short word durations correctly."""
        mock_audio = Mock(spec=AudioSegment)
        mock_audio.__len__ = Mock(return_value=100000)
        mock_audio.__getitem__ = Mock(return_value=mock_audio)
        mock_audio.__add__ = Mock(return_value=mock_audio)
        mock_audio.export = Mock()
        mock_from_file.return_value = mock_audio

        audio_processor.beep_sound = Mock(spec=AudioSegment)
        audio_processor.beep_sound.__len__ = Mock(return_value=1000)
        audio_processor.beep_sound.__getitem__ = Mock(return_value=mock_audio)

        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake")
        output_path = tmp_path / "output.wav"

        # Very short word (100ms)
        censor_timestamps = [
            {"start_seconds": 10.0, "end_seconds": 10.1, "reason": "Short word"}
        ]

        result = audio_processor.apply_censorship(
            audio_file, censor_timestamps, output_path
        )

        assert result == output_path

    @patch("audio_processor.AudioSegment.from_file")
    def test_censorship_handles_long_words(
        self, mock_from_file, audio_processor, tmp_path
    ):
        """Test censorship handles long word durations using duck (no beep repetition needed)."""
        # MagicMock required so __getitem__, __add__ work as dunder operators
        mock_audio = MagicMock(spec=AudioSegment)
        mock_audio.__len__ = Mock(return_value=100000)
        mock_segment = MagicMock(spec=AudioSegment)
        mock_segment.apply_gain = Mock(return_value=mock_segment)
        mock_segment.fade_in = Mock(return_value=mock_segment)
        mock_segment.fade_out = Mock(return_value=mock_segment)
        mock_segment.__add__ = Mock(return_value=mock_audio)
        mock_audio.__getitem__ = Mock(return_value=mock_segment)
        mock_audio.__add__ = Mock(return_value=mock_audio)
        mock_audio.export = Mock()
        mock_from_file.return_value = mock_audio

        audio_processor.beep_sound = Mock(spec=AudioSegment)

        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake")
        output_path = tmp_path / "output.wav"

        # Long word/phrase (2 seconds)
        censor_timestamps = [
            {"start_seconds": 10.0, "end_seconds": 12.0, "reason": "Long slur"}
        ]

        result = audio_processor.apply_censorship(
            audio_file, censor_timestamps, output_path
        )

        # Ducking applies gain reduction — no beep repetition needed for long words
        assert result == output_path
        mock_segment.apply_gain.assert_called_once()


class TestAudioDucking:
    """Tests for audio ducking behavior (AUDIO-01).

    These tests verify that apply_censorship uses smooth volume ducking
    (gain reduction + fade in/out) instead of beep-tone replacement.
    All tests are RED — implementation not yet written.
    """

    @patch("audio_processor.AudioSegment.from_file")
    def test_duck_no_beep_sound_used(self, mock_from_file, audio_processor, tmp_path):
        """Ducking must NOT use self.beep_sound — no __getitem__ or __mul__ on beep."""
        mock_audio = Mock(spec=AudioSegment)
        mock_audio.__len__ = Mock(return_value=100000)
        mock_audio.__getitem__ = Mock(return_value=mock_audio)
        mock_audio.__add__ = Mock(return_value=mock_audio)
        mock_audio.apply_gain = Mock(return_value=mock_audio)
        mock_audio.fade_in = Mock(return_value=mock_audio)
        mock_audio.fade_out = Mock(return_value=mock_audio)
        mock_audio.export = Mock()
        mock_from_file.return_value = mock_audio

        # Assign a mock beep so we can detect if it's accessed
        # MagicMock required to track magic method calls (__getitem__, __mul__)
        mock_beep = MagicMock(spec=AudioSegment)
        audio_processor.beep_sound = mock_beep

        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake audio")
        output_path = tmp_path / "output.wav"

        censor_timestamps = [
            {"start_seconds": 10.0, "end_seconds": 10.5, "reason": "Test"}
        ]
        audio_processor.apply_censorship(audio_file, censor_timestamps, output_path)

        # Ducking must not use the beep sound at all
        mock_beep.__getitem__.assert_not_called()
        mock_beep.__mul__.assert_not_called()

    @patch("audio_processor.AudioSegment.from_file")
    def test_duck_applies_gain_reduction(
        self, mock_from_file, audio_processor, tmp_path
    ):
        """The ducked segment must have apply_gain called with a negative value (<= -30 dB)."""
        # MagicMock required so __getitem__, __add__ work as dunder operators
        mock_audio = MagicMock(spec=AudioSegment)
        mock_audio.__len__ = Mock(return_value=100000)
        mock_segment = MagicMock(spec=AudioSegment)
        mock_segment.apply_gain = Mock(return_value=mock_segment)
        mock_segment.fade_in = Mock(return_value=mock_segment)
        mock_segment.fade_out = Mock(return_value=mock_segment)
        mock_segment.__add__ = Mock(return_value=mock_audio)
        mock_audio.__getitem__ = Mock(return_value=mock_segment)
        mock_audio.__add__ = Mock(return_value=mock_audio)
        mock_audio.export = Mock()
        mock_from_file.return_value = mock_audio

        audio_processor.beep_sound = Mock(spec=AudioSegment)

        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake audio")
        output_path = tmp_path / "output.wav"

        censor_timestamps = [
            {"start_seconds": 10.0, "end_seconds": 10.5, "reason": "Test"}
        ]
        audio_processor.apply_censorship(audio_file, censor_timestamps, output_path)

        # apply_gain must be called with a strongly negative dB value (<= -30)
        mock_segment.apply_gain.assert_called_once()
        gain_arg = mock_segment.apply_gain.call_args[0][0]
        assert gain_arg <= -30, f"Expected gain <= -30 dB for ducking, got {gain_arg}"

    @patch("audio_processor.AudioSegment.from_file")
    def test_duck_applies_fade_in_and_out(
        self, mock_from_file, audio_processor, tmp_path
    ):
        """Ducked segment must have both fade_in() and fade_out() called for smooth edges."""
        # MagicMock required so __getitem__, __add__ work as dunder operators
        mock_audio = MagicMock(spec=AudioSegment)
        mock_audio.__len__ = Mock(return_value=100000)
        mock_segment = MagicMock(spec=AudioSegment)
        mock_segment.apply_gain = Mock(return_value=mock_segment)
        mock_segment.fade_in = Mock(return_value=mock_segment)
        mock_segment.fade_out = Mock(return_value=mock_segment)
        mock_segment.__add__ = Mock(return_value=mock_audio)
        mock_audio.__getitem__ = Mock(return_value=mock_segment)
        mock_audio.__add__ = Mock(return_value=mock_audio)
        mock_audio.export = Mock()
        mock_from_file.return_value = mock_audio

        audio_processor.beep_sound = Mock(spec=AudioSegment)

        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake audio")
        output_path = tmp_path / "output.wav"

        censor_timestamps = [
            {"start_seconds": 10.0, "end_seconds": 10.5, "reason": "Test"}
        ]
        audio_processor.apply_censorship(audio_file, censor_timestamps, output_path)

        # Both fade_in and fade_out must be called on the ducked segment
        mock_segment.fade_in.assert_called_once()
        mock_segment.fade_out.assert_called_once()

    @patch("audio_processor.AudioSegment.from_file")
    def test_duck_short_segment_no_fade_overrun(
        self, mock_from_file, audio_processor, tmp_path
    ):
        """For a 100ms segment, fade_in and fade_out must still be called (pydub handles gracefully)."""
        # MagicMock required so __getitem__, __add__ work as dunder operators
        mock_audio = MagicMock(spec=AudioSegment)
        mock_audio.__len__ = Mock(return_value=100000)
        mock_segment = MagicMock(spec=AudioSegment)
        mock_segment.apply_gain = Mock(return_value=mock_segment)
        mock_segment.fade_in = Mock(return_value=mock_segment)
        mock_segment.fade_out = Mock(return_value=mock_segment)
        mock_segment.__add__ = Mock(return_value=mock_audio)
        mock_audio.__getitem__ = Mock(return_value=mock_segment)
        mock_audio.__add__ = Mock(return_value=mock_audio)
        mock_audio.export = Mock()
        mock_from_file.return_value = mock_audio

        audio_processor.beep_sound = Mock(spec=AudioSegment)

        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake audio")
        output_path = tmp_path / "output.wav"

        # Very short segment: 100ms
        censor_timestamps = [
            {"start_seconds": 10.0, "end_seconds": 10.1, "reason": "Short word"}
        ]
        audio_processor.apply_censorship(audio_file, censor_timestamps, output_path)

        # Fades must still be applied even for short segments
        mock_segment.fade_in.assert_called_once()
        mock_segment.fade_out.assert_called_once()

    @patch("audio_processor.AudioSegment.from_file")
    def test_duck_preserves_audio_before_and_after(
        self, mock_from_file, audio_processor, tmp_path
    ):
        """Final audio must be built from audio[:start_ms] + ducked + audio[end_ms:] — verify splice calls."""
        # MagicMock required so __getitem__, __add__ work as dunder operators.
        # audio[start:end] returns mock_segment (the extracted piece).
        # The splice is: audio[:start] + ducked + audio[end:]
        # audio[:start] returns mock_segment → mock_segment.__add__(ducked) is called (1st +)
        # result + audio[end:] → returned object's __add__ is called (2nd +)
        mock_audio = MagicMock(spec=AudioSegment)
        mock_audio.__len__ = Mock(return_value=100000)
        mock_segment = MagicMock(spec=AudioSegment)
        mock_segment.apply_gain = Mock(return_value=mock_segment)
        mock_segment.fade_in = Mock(return_value=mock_segment)
        mock_segment.fade_out = Mock(return_value=mock_segment)
        # mock_segment + ducked returns mock_audio so the second + is on mock_audio
        mock_segment.__add__ = Mock(return_value=mock_audio)
        mock_audio.__getitem__ = Mock(return_value=mock_segment)
        mock_audio.__add__ = Mock(return_value=mock_audio)
        mock_audio.export = Mock()
        mock_from_file.return_value = mock_audio

        audio_processor.beep_sound = Mock(spec=AudioSegment)

        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake audio")
        output_path = tmp_path / "output.wav"

        censor_timestamps = [
            {"start_seconds": 10.0, "end_seconds": 10.5, "reason": "Test"}
        ]
        audio_processor.apply_censorship(audio_file, censor_timestamps, output_path)

        # The splice pattern audio[:start] + ducked + audio[end:] requires exactly 2 add calls total:
        # 1st: mock_segment.__add__(ducked), 2nd: mock_audio.__add__(audio[end:])
        assert mock_segment.__add__.call_count == 1, (
            f"Expected 1 __add__ call on prefix segment, got {mock_segment.__add__.call_count}"
        )
        assert mock_audio.__add__.call_count == 1, (
            f"Expected 1 __add__ call on (prefix+ducked) result, got {mock_audio.__add__.call_count}"
        )


class TestNormalizeAudio:
    """Tests for two-pass FFmpeg LUFS normalization (AUDIO-02, AUDIO-03).

    All tests are RED — implementation rewrites normalize_audio() to use
    subprocess FFmpeg calls instead of pydub dBFS adjustment.
    """

    # Sample JSON from FFmpeg loudnorm first-pass (measurement pass)
    FIRST_PASS_JSON = """{
        "input_i" : "-23.45",
        "input_tp" : "-6.23",
        "input_lra" : "8.10",
        "input_thresh" : "-33.90",
        "target_offset" : "0.39",
        "normalization_type" : "linear",
        "output_i" : "-16.00",
        "output_tp" : "-1.10",
        "output_lra" : "8.10",
        "output_thresh" : "-26.45"
    }"""

    # Second-pass JSON from FFmpeg loudnorm output measurements
    SECOND_PASS_JSON = """{
        "input_i" : "-23.45",
        "input_tp" : "-6.23",
        "input_lra" : "8.10",
        "input_thresh" : "-33.90",
        "target_offset" : "0.39",
        "normalization_type" : "linear",
        "output_i" : "-16.00",
        "output_tp" : "-1.10",
        "output_lra" : "8.10",
        "output_thresh" : "-26.45"
    }"""

    AGC_FALLBACK_JSON = """{
        "input_i" : "-14.0",
        "input_tp" : "-1.0",
        "input_lra" : "5.0",
        "input_thresh" : "-24.0",
        "target_offset" : "0.0",
        "normalization_type" : "dynamic",
        "output_i" : "-16.00",
        "output_tp" : "-1.50",
        "output_lra" : "5.00",
        "output_thresh" : "-24.00"
    }"""

    def test_normalize_raises_on_missing_file(self, audio_processor, tmp_path):
        """FileNotFoundError is raised when input path does not exist (no subprocess involvement)."""
        missing_file = tmp_path / "nonexistent.wav"

        with pytest.raises(FileNotFoundError):
            audio_processor.normalize_audio(missing_file)

    @patch("audio_processor.subprocess.run")
    def test_normalize_calls_ffmpeg_twice(self, mock_run, audio_processor, tmp_path):
        """subprocess.run must be called exactly twice: one measurement pass, one normalize pass."""
        mock_run.return_value = Mock(
            returncode=0, stderr=f"FFmpeg output\n{self.FIRST_PASS_JSON}\n"
        )

        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake wav content")
        output_file = tmp_path / "normalized.wav"

        audio_processor.normalize_audio(audio_file, output_path=output_file)

        assert mock_run.call_count == 2, (
            f"Expected 2 subprocess.run calls, got {mock_run.call_count}"
        )

        # First call: measurement pass with print_format=json
        first_call_args = mock_run.call_args_list[0][0][0]
        first_call_str = " ".join(str(a) for a in first_call_args)
        assert "loudnorm" in first_call_str
        assert "I=-16" in first_call_str or "I=" in first_call_str
        assert "print_format=json" in first_call_str

        # Second call: normalization pass with linear=true and measured_I
        second_call_args = mock_run.call_args_list[1][0][0]
        second_call_str = " ".join(str(a) for a in second_call_args)
        assert "linear=true" in second_call_str
        assert "measured_I" in second_call_str

    @patch.object(Config, "LUFS_TARGET", -16)
    @patch("audio_processor.subprocess.run")
    def test_normalize_uses_lufs_target_from_config(
        self, mock_run, audio_processor, tmp_path
    ):
        """FFmpeg loudnorm filter in first pass must use Config.LUFS_TARGET value."""
        mock_run.return_value = Mock(
            returncode=0, stderr=f"FFmpeg output\n{self.FIRST_PASS_JSON}\n"
        )

        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake wav content")
        output_file = tmp_path / "normalized.wav"

        audio_processor.normalize_audio(audio_file, output_path=output_file)

        first_call_args = mock_run.call_args_list[0][0][0]
        first_call_str = " ".join(str(a) for a in first_call_args)
        # LUFS target must appear in the loudnorm filter string
        assert "I=-16" in first_call_str, (
            f"Expected 'I=-16' (LUFS target) in first-pass command, got: {first_call_str}"
        )

    @patch("audio_processor.AudioProcessor._parse_loudnorm_json")
    @patch("audio_processor.subprocess.run")
    def test_normalize_warns_on_agc_fallback(
        self, mock_run, mock_parse, audio_processor, tmp_path, caplog
    ):
        """WARNING log is emitted (not exception) when normalization_type is 'dynamic'."""
        import logging

        mock_parse.return_value = {
            "normalization_type": "dynamic",
            "input_i": "-14.0",
            "input_tp": "-1.0",
            "input_lra": "5.0",
            "input_thresh": "-24.0",
            "target_offset": "0.0",
            "output_i": "-16.0",
            "output_lra": "5.0",
        }
        mock_run.return_value = Mock(returncode=0, stderr="")

        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake wav content")
        output_file = tmp_path / "normalized.wav"

        with caplog.at_level(logging.WARNING):
            # Should NOT raise — warning only
            audio_processor.normalize_audio(audio_file, output_path=output_file)

        warning_messages = [
            r.message for r in caplog.records if r.levelno == logging.WARNING
        ]
        assert any(
            "dynamic" in msg.lower()
            or "agc" in msg.lower()
            or "fallback" in msg.lower()
            for msg in warning_messages
        ), f"Expected WARNING about AGC/dynamic fallback, got: {warning_messages}"

    @patch("audio_processor.subprocess.run")
    def test_normalize_logs_input_output_gain_lra(
        self, mock_run, audio_processor, tmp_path, caplog
    ):
        """INFO log must contain input LUFS, output LUFS, gain applied, and LRA when normalization completes."""
        import logging

        first_stderr = f"FFmpeg measurement output\n{self.FIRST_PASS_JSON}\n"
        second_stderr = f"FFmpeg normalize output\n{self.SECOND_PASS_JSON}\n"
        mock_run.side_effect = [
            Mock(returncode=0, stderr=first_stderr),
            Mock(returncode=0, stderr=second_stderr),
        ]

        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake wav content")
        output_file = tmp_path / "normalized.wav"

        with caplog.at_level(logging.INFO):
            audio_processor.normalize_audio(audio_file, output_path=output_file)

        info_messages = " ".join(
            r.message for r in caplog.records if r.levelno == logging.INFO
        )
        # Must log the measured input LUFS value
        assert "-23" in info_messages or "-23.45" in info_messages, (
            f"Expected input LUFS in log, got: {info_messages}"
        )
        # Must log the output LUFS value
        assert "-16" in info_messages, (
            f"Expected output LUFS in log, got: {info_messages}"
        )

    @patch("audio_processor.subprocess.run")
    def test_normalize_returns_output_path(self, mock_run, audio_processor, tmp_path):
        """normalize_audio(audio_path, output_path) must return output_path."""
        mock_run.return_value = Mock(
            returncode=0, stderr=f"FFmpeg output\n{self.FIRST_PASS_JSON}\n"
        )

        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake wav content")
        output_file = tmp_path / "normalized.wav"

        result = audio_processor.normalize_audio(audio_file, output_path=output_file)

        assert result == output_file

    @patch("audio_processor.subprocess.run")
    def test_normalize_passes_devnull_to_subprocess(
        self, mock_run, audio_processor, tmp_path
    ):
        """subprocess.run must be called with stdin=subprocess.DEVNULL to prevent stdin hang."""
        import subprocess

        mock_run.return_value = Mock(
            returncode=0, stderr=f"FFmpeg output\n{self.FIRST_PASS_JSON}\n"
        )

        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake wav content")
        output_file = tmp_path / "normalized.wav"

        audio_processor.normalize_audio(audio_file, output_path=output_file)

        for call in mock_run.call_args_list:
            kwargs = call[1]
            assert kwargs.get("stdin") == subprocess.DEVNULL, (
                f"Expected stdin=subprocess.DEVNULL in subprocess.run, got: {kwargs.get('stdin')}"
            )


class TestClipDurationValidation:
    """Tests for clip duration validation in create_clips."""

    @patch("audio_processor.AudioSegment.from_file")
    def test_short_clip_extended_to_minimum(
        self, mock_from_file, audio_processor, tmp_path
    ):
        """Test that clips shorter than CLIP_MIN_DURATION are extended."""
        mock_audio = Mock(spec=AudioSegment)
        mock_audio.__len__ = Mock(return_value=300000)  # 300 seconds
        mock_clip = Mock(spec=AudioSegment)
        mock_clip.fade_in = Mock(return_value=mock_clip)
        mock_clip.fade_out = Mock(return_value=mock_clip)
        mock_clip.export = Mock()
        mock_audio.__getitem__ = Mock(return_value=mock_clip)
        mock_from_file.return_value = mock_audio

        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake")
        clip_dir = tmp_path / "clips"
        clip_dir.mkdir()

        # Clip that's only 3 seconds (below CLIP_MIN_DURATION which is typically 10)
        best_clips = [
            {"start_seconds": 10.0, "end_seconds": 13.0, "description": "Short clip"}
        ]

        result = audio_processor.create_clips(audio_file, best_clips, clip_dir)

        assert len(result) == 1
        # Verify the slice used extended end time
        call_args = mock_audio.__getitem__.call_args
        sliced_range = call_args[0][0]
        # The end should be start + CLIP_MIN_DURATION (in ms)
        expected_end_ms = int((10.0 + Config.CLIP_MIN_DURATION) * 1000)
        assert sliced_range.stop == expected_end_ms

    @patch("audio_processor.AudioSegment.from_file")
    def test_long_clip_trimmed_to_maximum(
        self, mock_from_file, audio_processor, tmp_path
    ):
        """Test that clips longer than CLIP_MAX_DURATION are trimmed."""
        mock_audio = Mock(spec=AudioSegment)
        mock_audio.__len__ = Mock(return_value=600000)  # 600 seconds
        mock_clip = Mock(spec=AudioSegment)
        mock_clip.fade_in = Mock(return_value=mock_clip)
        mock_clip.fade_out = Mock(return_value=mock_clip)
        mock_clip.export = Mock()
        mock_audio.__getitem__ = Mock(return_value=mock_clip)
        mock_from_file.return_value = mock_audio

        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake")
        clip_dir = tmp_path / "clips"
        clip_dir.mkdir()

        # Clip that's 120 seconds (above CLIP_MAX_DURATION which is typically 60)
        best_clips = [
            {"start_seconds": 10.0, "end_seconds": 130.0, "description": "Long clip"}
        ]

        result = audio_processor.create_clips(audio_file, best_clips, clip_dir)

        assert len(result) == 1
        # Verify the slice used trimmed end time
        call_args = mock_audio.__getitem__.call_args
        sliced_range = call_args[0][0]
        expected_end_ms = int((10.0 + Config.CLIP_MAX_DURATION) * 1000)
        assert sliced_range.stop == expected_end_ms

    @patch("audio_processor.AudioSegment.from_file")
    def test_valid_duration_clip_unchanged(
        self, mock_from_file, audio_processor, tmp_path
    ):
        """Test that clips within valid duration range are not modified."""
        mock_audio = Mock(spec=AudioSegment)
        mock_audio.__len__ = Mock(return_value=300000)
        mock_clip = Mock(spec=AudioSegment)
        mock_clip.fade_in = Mock(return_value=mock_clip)
        mock_clip.fade_out = Mock(return_value=mock_clip)
        mock_clip.export = Mock()
        mock_audio.__getitem__ = Mock(return_value=mock_clip)
        mock_from_file.return_value = mock_audio

        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake")
        clip_dir = tmp_path / "clips"
        clip_dir.mkdir()

        # Clip that's 25 seconds (within valid range)
        best_clips = [
            {"start_seconds": 10.0, "end_seconds": 35.0, "description": "Normal clip"}
        ]

        result = audio_processor.create_clips(audio_file, best_clips, clip_dir)

        assert len(result) == 1
        # Verify original timestamps used
        call_args = mock_audio.__getitem__.call_args
        sliced_range = call_args[0][0]
        assert sliced_range.start == 10000  # 10s in ms
        assert sliced_range.stop == 35000  # 35s in ms


class TestAudioCaching:
    """Tests for audio caching optimizations — load once, reuse across operations."""

    @patch("audio_processor.AudioSegment.from_file")
    def test_create_clips_loads_audio_once(
        self, mock_from_file, audio_processor, tmp_path
    ):
        """create_clips loads audio once and passes to extract_clip, not N times."""
        mock_audio = Mock(spec=AudioSegment)
        mock_audio.__len__ = Mock(return_value=300000)
        mock_clip = Mock(spec=AudioSegment)
        mock_clip.fade_in = Mock(return_value=mock_clip)
        mock_clip.fade_out = Mock(return_value=mock_clip)
        mock_clip.export = Mock()
        mock_audio.__getitem__ = Mock(return_value=mock_clip)
        mock_from_file.return_value = mock_audio

        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake")
        clip_dir = tmp_path / "clips"
        clip_dir.mkdir()

        best_clips = [
            {"start_seconds": 10.0, "end_seconds": 40.0, "description": "Clip 1"},
            {"start_seconds": 50.0, "end_seconds": 80.0, "description": "Clip 2"},
            {"start_seconds": 90.0, "end_seconds": 120.0, "description": "Clip 3"},
        ]

        result = audio_processor.create_clips(audio_file, best_clips, clip_dir)

        assert len(result) == 3
        # Audio loaded exactly once (in create_clips), not 3 times (once per clip)
        mock_from_file.assert_called_once()

    @patch("audio_processor.AudioSegment.from_file")
    def test_extract_clip_with_preloaded_audio_skips_load(
        self, mock_from_file, audio_processor, tmp_path
    ):
        """extract_clip with _audio param skips AudioSegment.from_file."""
        pre_loaded = Mock(spec=AudioSegment)
        mock_clip = Mock(spec=AudioSegment)
        mock_clip.fade_in = Mock(return_value=mock_clip)
        mock_clip.fade_out = Mock(return_value=mock_clip)
        mock_clip.export = Mock()
        pre_loaded.__getitem__ = Mock(return_value=mock_clip)

        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake")
        output_path = tmp_path / "clip.wav"

        audio_processor.extract_clip(
            audio_file, 10.0, 40.0, output_path, _audio=pre_loaded
        )

        # from_file should NOT be called since pre-loaded audio was provided
        mock_from_file.assert_not_called()
        # But the clip should still be extracted from the pre-loaded audio
        pre_loaded.__getitem__.assert_called_once()

    @patch("audio_processor.AudioSegment.from_file")
    def test_convert_to_mp3_with_preloaded_audio_skips_load(
        self, mock_from_file, audio_processor, tmp_path
    ):
        """convert_to_mp3 with _audio param skips AudioSegment.from_file."""
        pre_loaded = Mock(spec=AudioSegment)
        pre_loaded.export = Mock()

        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake")

        audio_processor.convert_to_mp3(audio_file, _audio=pre_loaded)

        mock_from_file.assert_not_called()
        pre_loaded.export.assert_called_once()


class TestRawSnapshot:
    """Tests for raw audio snapshot before censorship (DEMO-02).

    Verifies that run_audio() captures a 60-second WAV segment via FFmpeg
    before the censorship step, stores the path in censor checkpoint outputs,
    and skips snapshot creation on pipeline resume.
    """

    def _make_ctx(self, tmp_path, analysis=None):
        """Build a minimal PipelineContext for run_audio testing."""
        return PipelineContext(
            episode_folder="ep01",
            episode_number=1,
            episode_output_dir=tmp_path,
            timestamp="20260328",
            audio_file=tmp_path / "ep01.wav",
            analysis=analysis or {},
        )

    def _make_components(self):
        """Build a minimal components dict with mocked transcriber and audio_processor."""
        transcriber = Mock()
        transcriber.transcribe.return_value = {"segments": [], "words": []}
        audio_proc = Mock()
        audio_proc.apply_censorship.return_value = Path("/fake/censored.wav")
        audio_proc.normalize_audio.return_value = Path("/fake/normalized.wav")
        audio_proc.convert_to_mp3.return_value = Path("/fake/episode.mp3")
        return {
            "transcriber": transcriber,
            "audio_processor": audio_proc,
            "chapter_generator": None,
        }

    @patch("pipeline.steps.audio.subprocess.run")
    def test_snapshot_calls_ffmpeg_before_censor(self, mock_run, tmp_path):
        """run_audio calls subprocess.run (FFmpeg) to create 60-second snapshot before censorship."""
        # Setup
        mock_run.return_value = Mock(returncode=0)
        audio_file = tmp_path / "ep01.wav"
        audio_file.write_bytes(b"fake")
        ctx = self._make_ctx(tmp_path)
        ctx.audio_file = audio_file
        components = self._make_components()

        # Execute
        run_audio(ctx, components, state=None)

        # Verify FFmpeg was called
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert str(audio_file) in cmd
        assert "_raw_snapshot.wav" in cmd[-1]

    @patch("pipeline.steps.audio.subprocess.run")
    def test_snapshot_start_from_best_clip(self, mock_run, tmp_path):
        """Snapshot start time uses best_clips[0].start_seconds when available."""
        mock_run.return_value = Mock(returncode=0)
        audio_file = tmp_path / "ep01.wav"
        audio_file.write_bytes(b"fake")
        analysis = {
            "best_clips": [
                {
                    "start_seconds": 120.0,
                    "end_seconds": 180.0,
                    "description": "Good bit",
                }
            ]
        }
        ctx = self._make_ctx(tmp_path, analysis=analysis)
        ctx.audio_file = audio_file
        components = self._make_components()

        run_audio(ctx, components, state=None)

        cmd = mock_run.call_args[0][0]
        ss_index = cmd.index("-ss")
        assert cmd[ss_index + 1] == "120.0"

    @patch("pipeline.steps.audio.subprocess.run")
    def test_snapshot_default_start_when_no_clips(self, mock_run, tmp_path):
        """Snapshot start defaults to 60.0 when analysis has no best_clips."""
        mock_run.return_value = Mock(returncode=0)
        audio_file = tmp_path / "ep01.wav"
        audio_file.write_bytes(b"fake")
        ctx = self._make_ctx(tmp_path, analysis={})
        ctx.audio_file = audio_file
        components = self._make_components()

        run_audio(ctx, components, state=None)

        cmd = mock_run.call_args[0][0]
        ss_index = cmd.index("-ss")
        assert cmd[ss_index + 1] == "60.0"

    @patch("pipeline.steps.audio.subprocess.run")
    def test_snapshot_path_naming_convention(self, mock_run, tmp_path):
        """Snapshot path follows {stem}_{timestamp}_raw_snapshot.wav in episode_output_dir."""
        mock_run.return_value = Mock(returncode=0)
        audio_file = tmp_path / "ep01.wav"
        audio_file.write_bytes(b"fake")
        ctx = self._make_ctx(tmp_path)
        ctx.audio_file = audio_file
        components = self._make_components()

        run_audio(ctx, components, state=None)

        cmd = mock_run.call_args[0][0]
        snapshot_path = Path(cmd[-1])
        assert snapshot_path.parent == tmp_path
        assert snapshot_path.name == "ep01_20260328_raw_snapshot.wav"

    @patch("pipeline.steps.audio.subprocess.run")
    def test_snapshot_skipped_on_resume(self, mock_run, tmp_path):
        """When censor step is already completed (resume), FFmpeg snapshot is NOT called."""
        mock_run.return_value = Mock(returncode=0)
        audio_file = tmp_path / "ep01.wav"
        audio_file.write_bytes(b"fake")
        ctx = self._make_ctx(tmp_path)
        ctx.audio_file = audio_file
        components = self._make_components()

        # State says censor is already done
        state = Mock()
        state.is_step_completed.side_effect = lambda step: step == "censor"
        state.get_step_outputs.return_value = {
            "censored_audio": str(tmp_path / "ep01_censored.wav"),
            "raw_snapshot_path": str(tmp_path / "ep01_20260328_raw_snapshot.wav"),
        }

        run_audio(ctx, components, state=state)

        # FFmpeg must NOT be called for snapshot on resume
        mock_run.assert_not_called()

    @patch("pipeline.steps.audio.subprocess.run")
    def test_snapshot_path_stored_in_censor_checkpoint(self, mock_run, tmp_path):
        """raw_snapshot_path is stored in the censor checkpoint outputs dict."""
        mock_run.return_value = Mock(returncode=0)
        audio_file = tmp_path / "ep01.wav"
        audio_file.write_bytes(b"fake")
        ctx = self._make_ctx(tmp_path)
        ctx.audio_file = audio_file
        components = self._make_components()

        state = Mock()
        state.is_step_completed.return_value = False

        run_audio(ctx, components, state=state)

        # Find the complete_step call for "censor"
        censor_calls = [
            c for c in state.complete_step.call_args_list if c[0][0] == "censor"
        ]
        assert len(censor_calls) == 1
        outputs = censor_calls[0][0][1]
        assert "raw_snapshot_path" in outputs

    @patch("pipeline.steps.audio.subprocess.run")
    def test_ctx_raw_snapshot_path_set_after_creation(self, mock_run, tmp_path):
        """ctx.raw_snapshot_path is populated with the snapshot Path after FFmpeg runs."""
        mock_run.return_value = Mock(returncode=0)
        audio_file = tmp_path / "ep01.wav"
        audio_file.write_bytes(b"fake")
        ctx = self._make_ctx(tmp_path)
        ctx.audio_file = audio_file
        components = self._make_components()

        run_audio(ctx, components, state=None)

        assert ctx.raw_snapshot_path is not None
        assert ctx.raw_snapshot_path.name == "ep01_20260328_raw_snapshot.wav"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
