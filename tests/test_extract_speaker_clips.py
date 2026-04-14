"""Tests for extract_speaker_clips.py — speaker clip extraction from diarized transcripts."""

import json
from unittest.mock import patch

import pytest

from extract_speaker_clips import (
    _merge_segments,
    _fmt_time,
    identify_speakers,
    extract_clips,
    load_transcript,
)


SAMPLE_DATA = {
    "audio_file": "downloads/ep_27_raw.WAV",
    "speakers": {
        "SPEAKER_00": {"speaking_time": 120.0, "segment_count": 10},
        "SPEAKER_01": {"speaking_time": 80.0, "segment_count": 8},
    },
    "segments": [
        {"start": 0, "end": 15, "text": "Hello and welcome", "speaker": "SPEAKER_00"},
        {
            "start": 16,
            "end": 30,
            "text": "Thanks for having me",
            "speaker": "SPEAKER_01",
        },
        {
            "start": 31,
            "end": 50,
            "text": "Let us talk about stuff",
            "speaker": "SPEAKER_00",
        },
        {"start": 51, "end": 55, "text": "Sure thing", "speaker": "SPEAKER_01"},
    ],
}


class TestMergeSegments:
    """Tests for _merge_segments helper."""

    def test_empty_segments_returns_empty(self):
        """Empty input returns empty list."""
        assert _merge_segments([], max_gap=2.0) == []

    def test_single_segment_becomes_single_turn(self):
        """Single segment produces one turn with correct duration."""
        segs = [{"start": 10, "end": 25, "text": "Hello"}]
        turns = _merge_segments(segs, max_gap=2.0)
        assert len(turns) == 1
        assert turns[0]["duration"] == 15
        assert turns[0]["text"] == "Hello"

    def test_consecutive_segments_merge_within_gap(self):
        """Segments within max_gap are merged into one turn."""
        segs = [
            {"start": 0, "end": 10, "text": "First part"},
            {"start": 11, "end": 20, "text": "Second part"},
        ]
        turns = _merge_segments(segs, max_gap=2.0)
        assert len(turns) == 1
        assert turns[0]["text"] == "First part Second part"
        assert turns[0]["segment_count"] == 2
        assert turns[0]["duration"] == 20

    def test_segments_split_when_gap_exceeds_threshold(self):
        """Segments with gap > max_gap become separate turns."""
        segs = [
            {"start": 0, "end": 10, "text": "First"},
            {"start": 20, "end": 30, "text": "Second"},
        ]
        turns = _merge_segments(segs, max_gap=2.0)
        assert len(turns) == 2
        assert turns[0]["text"] == "First"
        assert turns[1]["text"] == "Second"

    def test_unsorted_segments_are_sorted_by_start(self):
        """Segments are sorted by start time before merging."""
        segs = [
            {"start": 20, "end": 30, "text": "Later"},
            {"start": 0, "end": 10, "text": "Earlier"},
        ]
        turns = _merge_segments(segs, max_gap=2.0)
        assert turns[0]["text"] == "Earlier"
        assert turns[1]["text"] == "Later"


class TestFmtTime:
    """Tests for _fmt_time helper."""

    def test_zero_seconds(self):
        """Zero seconds formats as 00:00."""
        assert _fmt_time(0) == "00:00"

    def test_minutes_and_seconds(self):
        """125 seconds formats as 02:05."""
        assert _fmt_time(125) == "02:05"


class TestIdentifySpeakers:
    """Tests for identify_speakers output."""

    def test_prints_all_speakers(self, capsys):
        """Prints information for each speaker in the data."""
        identify_speakers(SAMPLE_DATA)
        output = capsys.readouterr().out
        assert "SPEAKER_00" in output
        assert "SPEAKER_01" in output
        assert "Hello and welcome" in output


class TestLoadTranscript:
    """Tests for load_transcript function."""

    def test_load_valid_json(self, tmp_path):
        """Loads and returns parsed JSON from a valid file."""
        transcript_file = tmp_path / "test_diarized.json"
        transcript_file.write_text(json.dumps(SAMPLE_DATA))
        result = load_transcript(str(transcript_file))
        assert result["audio_file"] == "downloads/ep_27_raw.WAV"

    def test_load_missing_file_exits(self):
        """Exits when transcript file does not exist."""
        with pytest.raises(SystemExit):
            load_transcript("nonexistent_file.json")


class TestExtractClips:
    """Tests for extract_clips function."""

    @patch("extract_speaker_clips.AudioProcessor")
    def test_extract_clips_happy_path(self, mock_processor_cls, tmp_path):
        """Extracts clips for a valid speaker and returns clip paths."""
        mock_processor = mock_processor_cls.return_value
        mock_processor.extract_clip.return_value = tmp_path / "clip.wav"

        audio_file = tmp_path / "audio.wav"
        audio_file.write_text("fake audio")
        output_dir = tmp_path / "clips"

        result = extract_clips(
            SAMPLE_DATA,
            "SPEAKER_00",
            str(audio_file),
            str(output_dir),
            min_duration=5.0,
            merge_gap=2.0,
        )

        assert len(result) > 0
        mock_processor.extract_clip.assert_called()

    @patch("extract_speaker_clips.AudioProcessor")
    def test_extract_clips_no_long_turns(self, mock_processor_cls, tmp_path):
        """Returns empty list when no turns meet minimum duration."""
        audio_file = tmp_path / "audio.wav"
        audio_file.write_text("fake")

        # All segments are short (< 100s min_duration)
        result = extract_clips(
            SAMPLE_DATA,
            "SPEAKER_01",
            str(audio_file),
            str(tmp_path / "out"),
            min_duration=100.0,
            merge_gap=2.0,
        )

        assert result == []
        mock_processor_cls.return_value.extract_clip.assert_not_called()

    def test_extract_clips_missing_audio_exits(self, tmp_path):
        """Exits when audio file does not exist."""
        with pytest.raises(SystemExit):
            extract_clips(
                SAMPLE_DATA, "SPEAKER_00", str(tmp_path / "nope.wav"), str(tmp_path)
            )

    def test_extract_clips_invalid_speaker_exits(self, tmp_path):
        """Exits when speaker ID is not in the transcript."""
        audio_file = tmp_path / "audio.wav"
        audio_file.write_text("fake")

        with pytest.raises(SystemExit):
            extract_clips(SAMPLE_DATA, "SPEAKER_99", str(audio_file), str(tmp_path))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
