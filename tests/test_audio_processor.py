"""Tests for audio_processor module."""

import pytest
from unittest.mock import Mock, patch
from pydub import AudioSegment

from audio_processor import AudioProcessor
from config import Config


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

    @patch("audio_processor.AudioSegment.from_file")
    def test_convert_to_mp3(
        self, mock_from_file, audio_processor, mock_audio_segment, tmp_path
    ):
        """Test converting audio to MP3."""
        mock_from_file.return_value = mock_audio_segment
        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake")

        result = audio_processor.convert_to_mp3(audio_file)

        assert result.suffix == ".mp3"
        assert result.parent == audio_file.parent
        # Verify export was called with mp3 format
        mock_audio_segment.export.assert_called()

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
        """Test censorship handles long word durations (longer than beep sound)."""
        mock_audio = Mock(spec=AudioSegment)
        mock_audio.__len__ = Mock(return_value=100000)
        mock_audio.__getitem__ = Mock(return_value=mock_audio)
        mock_audio.__add__ = Mock(return_value=mock_audio)
        mock_audio.export = Mock()
        mock_from_file.return_value = mock_audio

        # Short beep sound (500ms)
        audio_processor.beep_sound = Mock(spec=AudioSegment)
        audio_processor.beep_sound.__len__ = Mock(return_value=500)
        audio_processor.beep_sound.__getitem__ = Mock(return_value=mock_audio)
        audio_processor.beep_sound.__mul__ = Mock(return_value=mock_audio)

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

        # Should have repeated the beep to cover 2 seconds
        assert result == output_path
        audio_processor.beep_sound.__mul__.assert_called()


class TestNormalizeAudio:
    """Tests for audio normalization."""

    @patch("audio_processor.AudioSegment.from_file")
    def test_normalize_applies_gain_when_needed(
        self, mock_from_file, audio_processor, tmp_path
    ):
        """Test that normalize adjusts gain when audio is far from target."""
        mock_audio = Mock(spec=AudioSegment)
        mock_audio.dBFS = -25.0  # Below target
        mock_normalized = Mock(spec=AudioSegment)
        mock_audio.apply_gain = Mock(return_value=mock_normalized)
        mock_normalized.export = Mock()
        mock_from_file.return_value = mock_audio

        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake")

        result = audio_processor.normalize_audio(audio_file)

        # Should apply gain adjustment (target is LUFS_TARGET, typically -16)
        mock_audio.apply_gain.assert_called_once()
        gain_arg = mock_audio.apply_gain.call_args[0][0]
        assert gain_arg == Config.LUFS_TARGET - (-25.0)
        assert result == audio_file

    @patch("audio_processor.AudioSegment.from_file")
    def test_normalize_skips_when_near_target(
        self, mock_from_file, audio_processor, tmp_path
    ):
        """Test that normalize skips when audio is already near target level."""
        mock_audio = Mock(spec=AudioSegment)
        mock_audio.dBFS = Config.LUFS_TARGET + 0.2  # Very close to target
        mock_from_file.return_value = mock_audio

        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake")

        result = audio_processor.normalize_audio(audio_file)

        # Should NOT apply gain since difference < 0.5 dB
        mock_audio.apply_gain.assert_not_called()
        assert result == audio_file

    @patch("audio_processor.AudioSegment.from_file")
    def test_normalize_outputs_to_separate_path(
        self, mock_from_file, audio_processor, tmp_path
    ):
        """Test normalization writing to a different output path."""
        mock_audio = Mock(spec=AudioSegment)
        mock_audio.dBFS = -25.0
        mock_normalized = Mock(spec=AudioSegment)
        mock_audio.apply_gain = Mock(return_value=mock_normalized)
        mock_normalized.export = Mock()
        mock_from_file.return_value = mock_audio

        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake")
        output_file = tmp_path / "normalized.wav"

        result = audio_processor.normalize_audio(audio_file, output_path=output_file)

        assert result == output_file
        mock_normalized.export.assert_called_once_with(str(output_file), format="wav")

    def test_normalize_raises_on_missing_file(self, audio_processor, tmp_path):
        """Test that normalize raises FileNotFoundError for missing input."""
        missing_file = tmp_path / "nonexistent.wav"

        with pytest.raises(FileNotFoundError):
            audio_processor.normalize_audio(missing_file)


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
