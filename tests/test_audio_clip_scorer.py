"""Tests for audio_clip_scorer module - AudioClipScorer class."""

from unittest.mock import patch, MagicMock

# This import will fail until audio_clip_scorer.py is created (RED phase):
from audio_clip_scorer import AudioClipScorer

SAMPLE_SEGMENTS = [
    {"start": 0.0, "end": 5.0, "text": "hello there"},
    {"start": 5.0, "end": 10.0, "text": "this is funny"},
]


class TestAudioClipScorer:
    """Tests for AudioClipScorer basic scoring behavior."""

    @patch("audio_clip_scorer.AudioSegment")
    def test_score_segments_returns_list(self, mock_audio_segment):
        """score_segments must return a list."""
        mock_audio = MagicMock()
        mock_audio.__len__ = MagicMock(return_value=10000)  # 10 seconds in ms
        chunk_mock = MagicMock()
        chunk_mock.rms = 500
        mock_audio.__getitem__ = MagicMock(return_value=chunk_mock)
        mock_audio_segment.from_file.return_value = mock_audio

        scorer = AudioClipScorer()
        segments = [{"start": 0.0, "end": 5.0, "text": "hello"}]
        result = scorer.score_segments("fake.wav", segments)

        assert isinstance(result, list)

    @patch("audio_clip_scorer.AudioSegment")
    def test_score_segments_adds_audio_energy_score_field(self, mock_audio_segment):
        """Each returned segment dict must contain 'audio_energy_score' key."""
        mock_audio = MagicMock()
        mock_audio.__len__ = MagicMock(return_value=10000)
        chunk_mock = MagicMock()
        chunk_mock.rms = 500
        mock_audio.__getitem__ = MagicMock(return_value=chunk_mock)
        mock_audio_segment.from_file.return_value = mock_audio

        scorer = AudioClipScorer()
        segments = [{"start": 0.0, "end": 5.0, "text": "hello"}]
        result = scorer.score_segments("fake.wav", segments)

        assert len(result) == 1
        assert "audio_energy_score" in result[0], (
            "Each segment must have an 'audio_energy_score' field"
        )

    @patch("audio_clip_scorer.AudioSegment")
    def test_audio_energy_score_is_float_between_0_and_1(self, mock_audio_segment):
        """audio_energy_score must be a float in range [0.0, 1.0]."""
        mock_audio = MagicMock()
        mock_audio.__len__ = MagicMock(return_value=10000)
        chunk_mock = MagicMock()
        chunk_mock.rms = 500
        mock_audio.__getitem__ = MagicMock(return_value=chunk_mock)
        mock_audio_segment.from_file.return_value = mock_audio

        scorer = AudioClipScorer()
        segments = [{"start": 0.0, "end": 5.0, "text": "hello"}]
        result = scorer.score_segments("fake.wav", segments)

        score = result[0]["audio_energy_score"]
        assert isinstance(score, float), (
            f"audio_energy_score must be float, got {type(score)}"
        )
        assert 0.0 <= score <= 1.0, (
            f"audio_energy_score must be in [0.0, 1.0], got {score}"
        )

    @patch("audio_clip_scorer.AudioSegment")
    def test_missing_audio_file_returns_segments_unchanged(self, mock_audio_segment):
        """When AudioSegment.from_file raises FileNotFoundError, return input segments unchanged."""
        mock_audio_segment.from_file.side_effect = FileNotFoundError("no such file")

        scorer = AudioClipScorer()
        segments = [{"start": 0.0, "end": 5.0, "text": "hello"}]
        result = scorer.score_segments("missing.wav", segments)

        assert result == segments, (
            "When audio file missing, segments must be returned unchanged"
        )

    @patch("audio_clip_scorer.AudioSegment")
    def test_empty_segments_returns_empty_list(self, mock_audio_segment):
        """score_segments with empty list must return empty list."""
        mock_audio = MagicMock()
        mock_audio.__len__ = MagicMock(return_value=10000)
        mock_audio_segment.from_file.return_value = mock_audio

        scorer = AudioClipScorer()
        result = scorer.score_segments("fake.wav", [])

        assert result == [], "Empty segments input must return empty list"


class TestEnergyScoring:
    """Tests for the energy scoring algorithm correctness."""

    @patch("audio_clip_scorer.AudioSegment")
    def test_higher_rms_window_gets_higher_score(self, mock_audio_segment):
        """Segment with higher average RMS must get a higher audio_energy_score."""
        mock_audio = MagicMock()
        mock_audio.__len__ = MagicMock(return_value=20000)  # 20 seconds

        low_rms_chunk = MagicMock()
        low_rms_chunk.rms = 100

        high_rms_chunk = MagicMock()
        high_rms_chunk.rms = 5000

        def getitem_side_effect(key):
            """Return low RMS for first segment window, high RMS for second."""
            start_ms = key.start or 0
            if start_ms < 5000:
                return low_rms_chunk
            return high_rms_chunk

        mock_audio.__getitem__ = MagicMock(side_effect=getitem_side_effect)
        mock_audio_segment.from_file.return_value = mock_audio

        scorer = AudioClipScorer()
        segments = [
            {"start": 0.0, "end": 5.0, "text": "quiet bit"},
            {"start": 5.0, "end": 10.0, "text": "loud funny bit"},
        ]
        result = scorer.score_segments("fake.wav", segments)

        assert len(result) == 2
        quiet_score = result[0]["audio_energy_score"]
        loud_score = result[1]["audio_energy_score"]
        assert loud_score > quiet_score, (
            f"Higher RMS segment must have higher score: loud={loud_score}, quiet={quiet_score}"
        )

    @patch("audio_clip_scorer.AudioSegment")
    def test_score_segments_graceful_on_load_exception(self, mock_audio_segment):
        """When AudioSegment.from_file raises any Exception, return segments unchanged."""
        mock_audio_segment.from_file.side_effect = Exception("unexpected error")

        scorer = AudioClipScorer()
        segments = [
            {"start": 0.0, "end": 5.0, "text": "segment one"},
            {"start": 5.0, "end": 10.0, "text": "segment two"},
        ]
        result = scorer.score_segments("broken.wav", segments)

        assert result == segments, (
            "On any load exception, segments must be returned unchanged"
        )
