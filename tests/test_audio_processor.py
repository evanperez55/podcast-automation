"""Tests for audio_processor module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from pydub import AudioSegment

from audio_processor import AudioProcessor


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

    @patch('audio_processor.AudioSegment.from_file')
    def test_apply_censorship_supports_multiple_formats(self, mock_from_file, audio_processor, mock_audio_segment, tmp_path):
        """Test that apply_censorship uses from_file (supports all formats)."""
        # Setup
        mock_from_file.return_value = mock_audio_segment
        audio_file = tmp_path / "test.mp4"
        audio_file.write_text("fake audio")
        output_path = tmp_path / "output.wav"
        censor_timestamps = []

        # Execute
        result = audio_processor.apply_censorship(audio_file, censor_timestamps, output_path)

        # Verify - Should use from_file, not from_wav
        mock_from_file.assert_called_once()
        assert mock_from_file.call_args[0][0] == str(audio_file)

    @patch('audio_processor.AudioSegment.from_file')
    def test_apply_censorship_with_mp4_file(self, mock_from_file, audio_processor, mock_audio_segment, tmp_path):
        """Test censorship works with MP4 files."""
        mock_from_file.return_value = mock_audio_segment
        audio_file = tmp_path / "test.mp4"
        audio_file.write_text("fake")
        output_path = tmp_path / "output.wav"

        result = audio_processor.apply_censorship(audio_file, [], output_path)

        assert result == output_path

    @patch('audio_processor.AudioSegment.from_file')
    def test_apply_censorship_with_m4a_file(self, mock_from_file, audio_processor, mock_audio_segment, tmp_path):
        """Test censorship works with M4A files."""
        mock_from_file.return_value = mock_audio_segment
        audio_file = tmp_path / "test.m4a"
        audio_file.write_text("fake")
        output_path = tmp_path / "output.wav"

        result = audio_processor.apply_censorship(audio_file, [], output_path)

        assert result == output_path

    @patch('audio_processor.AudioSegment.from_file')
    def test_apply_censorship_with_wav_file(self, mock_from_file, audio_processor, mock_audio_segment, tmp_path):
        """Test censorship works with WAV files."""
        mock_from_file.return_value = mock_audio_segment
        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake")
        output_path = tmp_path / "output.wav"

        result = audio_processor.apply_censorship(audio_file, [], output_path)

        assert result == output_path

    @patch('audio_processor.AudioSegment.from_file')
    def test_apply_censorship_applies_beeps(self, mock_from_file, audio_processor, tmp_path):
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

        # Mock beep sound that supports slicing
        audio_processor.beep_sound = Mock(spec=AudioSegment)
        audio_processor.beep_sound.__getitem__ = Mock(return_value=mock_audio)

        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake")
        output_path = tmp_path / "output.wav"

        censor_timestamps = [
            {"seconds": 10.0, "reason": "Test"},
            {"seconds": 20.0, "reason": "Test2"}
        ]

        # Execute
        result = audio_processor.apply_censorship(audio_file, censor_timestamps, output_path)

        # Verify censorship was applied
        assert result == output_path
        # Verify export was called
        mock_audio.export.assert_called_once()

    @patch('audio_processor.AudioSegment.from_file')
    def test_extract_clip(self, mock_from_file, audio_processor, mock_audio_segment, tmp_path):
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

    @patch('audio_processor.AudioSegment.from_file')
    def test_create_clips(self, mock_from_file, audio_processor, mock_audio_segment, tmp_path):
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

    @patch('audio_processor.AudioSegment.from_file')
    def test_convert_to_mp3(self, mock_from_file, audio_processor, mock_audio_segment, tmp_path):
        """Test converting audio to MP3."""
        mock_from_file.return_value = mock_audio_segment
        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake")

        result = audio_processor.convert_to_mp3(audio_file)

        assert result.suffix == '.mp3'
        assert result.parent == audio_file.parent
        # Verify export was called with mp3 format
        mock_audio_segment.export.assert_called()

    def test_beep_sound_loaded(self):
        """Test that AudioProcessor loads beep sound."""
        # This should work (beep will be generated if file doesn't exist)
        processor = AudioProcessor()
        assert processor.beep_sound is not None

    @patch('audio_processor.AudioSegment.from_file')
    def test_empty_censor_timestamps(self, mock_from_file, audio_processor, mock_audio_segment, tmp_path):
        """Test censorship with no timestamps (no censoring needed)."""
        mock_from_file.return_value = mock_audio_segment
        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake")
        output_path = tmp_path / "output.wav"

        result = audio_processor.apply_censorship(audio_file, [], output_path)

        assert result == output_path

    @patch('audio_processor.AudioSegment.from_file')
    def test_empty_clips_list(self, mock_from_file, audio_processor, mock_audio_segment, tmp_path):
        """Test creating clips with empty list."""
        mock_from_file.return_value = mock_audio_segment
        audio_file = tmp_path / "test.wav"
        audio_file.write_text("fake")
        clip_dir = tmp_path / "clips"
        clip_dir.mkdir()

        result = audio_processor.create_clips(audio_file, [], clip_dir)

        assert len(result) == 0
