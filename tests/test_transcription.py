"""Tests for transcription module."""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from config import Config
from transcription import Transcriber


class TestTranscriberInit:
    """Tests for Transcriber initialization."""

    @patch("faster_whisper.WhisperModel")
    def test_init_cuda(self, mock_model_cls):
        """Uses CUDA when available."""
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True

        with patch.dict(sys.modules, {"torch": mock_torch}):
            t = Transcriber("base")

        assert t.device == "cuda"
        assert t.compute_type == "float16"
        mock_model_cls.assert_called_once_with(
            "base", device="cuda", compute_type="float16"
        )

    @patch("faster_whisper.WhisperModel")
    def test_init_cpu_fallback(self, mock_model_cls):
        """Falls back to CPU int8 when no CUDA."""
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False

        with patch.dict(sys.modules, {"torch": mock_torch}):
            t = Transcriber("tiny")

        assert t.device == "cpu"
        assert t.compute_type == "int8"

    @patch("faster_whisper.WhisperModel")
    def test_init_default_model_size(self, mock_model_cls):
        """Uses Config.WHISPER_MODEL as default."""
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False

        with (
            patch.dict(sys.modules, {"torch": mock_torch}),
            patch.object(Config, "WHISPER_MODEL", "large-v3"),
        ):
            Transcriber()

        mock_model_cls.assert_called_once_with(
            "large-v3", device="cpu", compute_type="int8"
        )


@pytest.fixture
def transcriber():
    """Create a Transcriber with mocked model."""
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = False

    with (
        patch("faster_whisper.WhisperModel"),
        patch.dict(sys.modules, {"torch": mock_torch}),
    ):
        t = Transcriber("tiny")
    return t


class TestTranscribe:
    """Tests for Transcriber.transcribe."""

    def test_file_not_found(self, transcriber):
        """Raises FileNotFoundError for missing audio file."""
        with pytest.raises(FileNotFoundError, match="Audio file not found"):
            transcriber.transcribe("/nonexistent/audio.wav")

    def test_transcribe_success(self, transcriber, tmp_path):
        """Produces transcript data with expected fields."""
        audio = tmp_path / "test.wav"
        audio.write_bytes(b"fake audio data")

        mock_word = MagicMock()
        mock_word.word = " hello "
        mock_word.start = 0.0
        mock_word.end = 0.5

        mock_segment = MagicMock()
        mock_segment.start = 0.0
        mock_segment.end = 1.0
        mock_segment.text = "hello world"
        mock_segment.words = [mock_word]

        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.language_probability = 0.99

        transcriber.model.transcribe.return_value = ([mock_segment], mock_info)

        result = transcriber.transcribe(str(audio))

        assert result["text"] == "hello world"
        assert result["language"] == "en"
        assert len(result["segments"]) == 1
        assert len(result["words"]) == 1
        assert result["words"][0]["word"] == "hello"
        assert result["duration"] == 1.0

    def test_transcribe_saves_json(self, transcriber, tmp_path):
        """Saves transcript JSON when output_path provided."""
        audio = tmp_path / "test.wav"
        audio.write_bytes(b"fake audio")
        output = tmp_path / "transcript.json"

        mock_segment = MagicMock()
        mock_segment.start = 0.0
        mock_segment.end = 1.0
        mock_segment.text = "test"
        mock_segment.words = []

        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.language_probability = 0.95

        transcriber.model.transcribe.return_value = ([mock_segment], mock_info)

        transcriber.transcribe(str(audio), output_path=str(output))

        assert output.exists()
        data = json.loads(output.read_text())
        assert data["text"] == "test"

    def test_transcribe_error_propagates(self, transcriber, tmp_path):
        """Transcription errors are re-raised."""
        audio = tmp_path / "test.wav"
        audio.write_bytes(b"fake")

        transcriber.model.transcribe.side_effect = RuntimeError("model error")

        with pytest.raises(RuntimeError, match="model error"):
            transcriber.transcribe(str(audio))


class TestHelperMethods:
    """Tests for transcript utility methods."""

    def test_get_transcript_text(self, transcriber):
        """Extracts full text from transcript data."""
        data = {"text": "hello world", "words": []}
        assert transcriber.get_transcript_text(data) == "hello world"

    def test_get_words_with_timestamps(self, transcriber):
        """Returns words list from transcript data."""
        words = [{"word": "hello", "start": 0.0, "end": 0.5}]
        data = {"text": "hello", "words": words}
        assert transcriber.get_words_with_timestamps(data) == words

    def test_find_word_timestamps(self, transcriber):
        """Finds all matching word occurrences."""
        data = {
            "words": [
                {"word": "hello", "start": 0.0, "end": 0.5},
                {"word": "world", "start": 0.5, "end": 1.0},
                {"word": "Hello!", "start": 2.0, "end": 2.5},
            ]
        }
        matches = transcriber.find_word_timestamps(data, "hello")
        assert len(matches) == 2

    def test_find_word_timestamps_no_match(self, transcriber):
        """Returns empty list when no matches."""
        data = {"words": [{"word": "hello", "start": 0.0, "end": 0.5}]}
        matches = transcriber.find_word_timestamps(data, "goodbye")
        assert matches == []


class TestTranscriberInitPath:
    """Tests for FFmpeg PATH setup during Transcriber init."""

    @patch("faster_whisper.WhisperModel")
    def test_adds_ffmpeg_to_path(self, mock_model_cls):
        """Adds FFmpeg directory to PATH if not already present."""
        import os

        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False

        with (
            patch.dict(sys.modules, {"torch": mock_torch}),
            patch.object(Config, "FFMPEG_PATH", "/custom/ffmpeg/bin/ffmpeg"),
            patch.dict("os.environ", {"PATH": "/usr/bin"}),
        ):
            Transcriber("tiny")
            assert "/custom/ffmpeg/bin" in os.environ["PATH"]

    @patch("faster_whisper.WhisperModel")
    def test_skips_adding_ffmpeg_if_already_in_path(self, mock_model_cls):
        """Does not duplicate FFmpeg dir if already in PATH."""
        import os

        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False

        ffmpeg_dir = "/custom/ffmpeg/bin"
        with (
            patch.dict(sys.modules, {"torch": mock_torch}),
            patch.object(Config, "FFMPEG_PATH", f"{ffmpeg_dir}/ffmpeg"),
            patch.dict("os.environ", {"PATH": f"{ffmpeg_dir}{os.pathsep}/usr/bin"}),
        ):
            Transcriber("tiny")
            count = os.environ["PATH"].split(os.pathsep).count(ffmpeg_dir)
            assert count == 1


class TestTranscribeGpuOomFallback:
    """Tests for GPU out-of-memory fallback in transcribe."""

    def test_gpu_oom_retries_on_cpu(self, tmp_path):
        """GPU OOM error triggers CPU fallback transcription."""
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.empty_cache = MagicMock()

        mock_model = MagicMock()
        mock_cpu_model = MagicMock()

        mock_segment = MagicMock()
        mock_segment.start = 0.0
        mock_segment.end = 1.0
        mock_segment.text = "hello"
        mock_segment.words = []

        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.language_probability = 0.99

        # First call (GPU) raises OOM, second call (CPU) succeeds
        mock_model.transcribe.side_effect = RuntimeError(
            "CUDA out of memory. Tried to allocate..."
        )
        mock_cpu_model.transcribe.return_value = ([mock_segment], mock_info)

        with (
            patch(
                "faster_whisper.WhisperModel", side_effect=[mock_model, mock_cpu_model]
            ),
            patch.dict(sys.modules, {"torch": mock_torch}),
        ):
            t = Transcriber("base")

        # The model is the original GPU model
        assert t.device == "cuda"

        audio = tmp_path / "test.wav"
        audio.write_bytes(b"fake audio")

        # Patch WhisperModel for the CPU fallback inside transcribe
        with (
            patch("faster_whisper.WhisperModel", return_value=mock_cpu_model),
            patch.dict(sys.modules, {"torch": mock_torch}),
        ):
            result = t.transcribe(str(audio))

        assert result is not None
        assert result["text"] == "hello"
        assert t.device == "cpu"
        mock_torch.cuda.empty_cache.assert_called_once()

    def test_non_oom_runtime_error_propagates(self, transcriber, tmp_path):
        """Non-OOM RuntimeError is re-raised, not caught."""
        audio = tmp_path / "test.wav"
        audio.write_bytes(b"fake")

        transcriber.model.transcribe.side_effect = RuntimeError("driver error")

        with pytest.raises(RuntimeError, match="driver error"):
            transcriber.transcribe(str(audio))

    def test_gpu_oom_on_cpu_device_propagates(self, tmp_path):
        """OOM error on CPU device is re-raised (no fallback)."""
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False

        with (
            patch("faster_whisper.WhisperModel"),
            patch.dict(sys.modules, {"torch": mock_torch}),
        ):
            t = Transcriber("tiny")

        audio = tmp_path / "test.wav"
        audio.write_bytes(b"fake")

        t.model.transcribe.side_effect = RuntimeError("out of memory")
        # On CPU, device != "cuda", so OOM is re-raised
        with pytest.raises(RuntimeError, match="out of memory"):
            t.transcribe(str(audio))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
