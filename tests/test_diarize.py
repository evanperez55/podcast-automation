"""Tests for diarize.py — speaker diarization using WhisperX + pyannote."""

import json
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock, mock_open

import pytest


class TestGetDevice:
    """Tests for get_device function."""

    @patch("diarize.torch")
    def test_returns_cuda_when_available(self, mock_torch):
        """Returns 'cuda' when CUDA GPU is available."""
        from diarize import get_device

        mock_torch.cuda.is_available.return_value = True
        assert get_device() == "cuda"

    @patch("diarize.torch")
    def test_returns_cpu_when_no_cuda(self, mock_torch):
        """Returns 'cpu' when CUDA is not available."""
        from diarize import get_device

        mock_torch.cuda.is_available.return_value = False
        assert get_device() == "cpu"


class TestDiarize:
    """Tests for the main diarize function."""

    @patch("diarize.whisperx")
    @patch("diarize.DiarizationPipeline")
    @patch("diarize.torch")
    @patch("diarize.gc.collect")
    @patch.object(Path, "exists", return_value=True)
    @patch.object(Path, "mkdir")
    @patch("builtins.open", new_callable=MagicMock)
    @patch("diarize.json.dump")
    @patch("diarize.Config")
    def test_diarize_happy_path_cpu(
        self, mock_config, mock_json_dump, mock_open_fn, mock_mkdir,
        mock_exists, mock_gc, mock_torch, mock_diarize_pipeline, mock_whisperx
    ):
        """Full diarization pipeline runs on CPU and produces output file."""
        from diarize import diarize

        mock_config.HF_TOKEN = "hf_test_token"
        mock_torch.cuda.is_available.return_value = False

        # Whisper transcription
        mock_model = MagicMock()
        mock_whisperx.load_model.return_value = mock_model
        mock_whisperx.load_audio.return_value = "audio_array"
        mock_model.transcribe.return_value = {
            "segments": [
                {"start": 0, "end": 5, "text": "Hello", "words": [{"word": "Hello"}]},
                {"start": 5, "end": 10, "text": "World", "words": [{"word": "World"}]},
            ],
            "language": "en",
        }

        # Alignment
        mock_align_model = MagicMock()
        mock_whisperx.load_align_model.return_value = (mock_align_model, {})
        mock_whisperx.align.return_value = {
            "segments": [
                {"start": 0, "end": 5, "text": "Hello", "words": [{"word": "Hello"}], "speaker": "SPEAKER_00"},
                {"start": 5, "end": 10, "text": "World", "words": [{"word": "World"}], "speaker": "SPEAKER_01"},
            ]
        }

        # Diarization
        mock_pipeline_instance = MagicMock()
        mock_diarize_pipeline.return_value = mock_pipeline_instance
        mock_pipeline_instance.return_value = "diarize_segments"

        # Speaker assignment
        mock_whisperx.assign_word_speakers.return_value = {
            "language": "en",
            "segments": [
                {"start": 0, "end": 5, "text": "Hello", "speaker": "SPEAKER_00"},
                {"start": 5, "end": 10, "text": "World", "speaker": "SPEAKER_01"},
            ],
        }

        result = diarize("test_audio.wav", num_speakers=2, model_size="tiny")

        assert result == Path("test_audio_diarized.json")
        mock_whisperx.load_model.assert_called_once_with("tiny", "cpu", compute_type="int8")
        mock_json_dump.assert_called_once()
        output_data = mock_json_dump.call_args[0][0]
        assert output_data["num_speakers"] == 2

    @patch("diarize.torch")
    @patch.object(Path, "exists", return_value=True)
    @patch("diarize.Config")
    def test_diarize_missing_hf_token_exits(self, mock_config, mock_exists, mock_torch):
        """Exits with error when HF_TOKEN is not set."""
        from diarize import diarize

        mock_config.HF_TOKEN = None

        with pytest.raises(SystemExit):
            diarize("test_audio.wav")

    @patch("diarize.torch")
    @patch("diarize.Config")
    def test_diarize_missing_audio_file_exits(self, mock_config, mock_torch):
        """Exits with error when audio file does not exist."""
        from diarize import diarize

        with patch.object(Path, "exists", return_value=False):
            with pytest.raises(SystemExit):
                diarize("nonexistent.wav")

    @patch("diarize.whisperx")
    @patch("diarize.DiarizationPipeline")
    @patch("diarize.torch")
    @patch("diarize.gc.collect")
    @patch.object(Path, "exists", return_value=True)
    @patch.object(Path, "mkdir")
    @patch("builtins.open", new_callable=MagicMock)
    @patch("diarize.json.dump")
    @patch("diarize.Config")
    def test_diarize_custom_output_path(
        self, mock_config, mock_json_dump, mock_open_fn, mock_mkdir,
        mock_exists, mock_gc, mock_torch, mock_diarize_pipeline, mock_whisperx
    ):
        """Custom output_path is used instead of default."""
        from diarize import diarize

        mock_config.HF_TOKEN = "hf_test"
        mock_torch.cuda.is_available.return_value = False

        mock_model = MagicMock()
        mock_whisperx.load_model.return_value = mock_model
        mock_whisperx.load_audio.return_value = "audio"
        mock_model.transcribe.return_value = {"segments": [], "language": "en"}
        mock_whisperx.load_align_model.return_value = (MagicMock(), {})
        mock_whisperx.align.return_value = {"segments": []}
        mock_diarize_pipeline.return_value.return_value = "segs"
        mock_whisperx.assign_word_speakers.return_value = {"segments": []}

        result = diarize("test.wav", output_path="custom/output.json")

        assert result == Path("custom/output.json")

    @patch("diarize.whisperx")
    @patch("diarize.DiarizationPipeline")
    @patch("diarize.torch")
    @patch("diarize.gc.collect")
    @patch.object(Path, "exists", return_value=True)
    @patch.object(Path, "mkdir")
    @patch("builtins.open", new_callable=MagicMock)
    @patch("diarize.json.dump")
    @patch("diarize.Config")
    def test_diarize_unknown_speaker_handled(
        self, mock_config, mock_json_dump, mock_open_fn, mock_mkdir,
        mock_exists, mock_gc, mock_torch, mock_diarize_pipeline, mock_whisperx
    ):
        """Segments without speaker label are grouped under UNKNOWN."""
        from diarize import diarize

        mock_config.HF_TOKEN = "hf_test"
        mock_torch.cuda.is_available.return_value = False

        mock_model = MagicMock()
        mock_whisperx.load_model.return_value = mock_model
        mock_whisperx.load_audio.return_value = "audio"
        mock_model.transcribe.return_value = {"segments": [{"text": "hi"}], "language": "en"}
        mock_whisperx.load_align_model.return_value = (MagicMock(), {})
        mock_whisperx.align.return_value = {"segments": [{"start": 0, "end": 5, "text": "hi"}]}
        mock_diarize_pipeline.return_value.return_value = "segs"
        mock_whisperx.assign_word_speakers.return_value = {
            "segments": [{"start": 0, "end": 5, "text": "hi"}]  # no "speaker" key
        }

        diarize("test.wav")

        output_data = mock_json_dump.call_args[0][0]
        assert "UNKNOWN" in output_data["speakers"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
