"""Tests for process_historical_episodes module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import json

from process_historical_episodes import HistoricalEpisodeProcessor


@pytest.fixture
def mock_config():
    """Mock Config module."""
    with patch('process_historical_episodes.Config') as mock_cfg:
        mock_cfg.OUTPUT_DIR = Path("/fake/output")
        mock_cfg.CLIPS_DIR = Path("/fake/clips")
        mock_cfg.validate = Mock()
        mock_cfg.create_directories = Mock()
        yield mock_cfg


@pytest.fixture
def mock_components():
    """Mock all component classes."""
    with patch('process_historical_episodes.DropboxHandler') as mock_dropbox, \
         patch('process_historical_episodes.Transcriber') as mock_transcriber, \
         patch('process_historical_episodes.ContentEditor') as mock_editor, \
         patch('process_historical_episodes.AudioProcessor') as mock_audio:

        # Setup mock instances
        dropbox_inst = Mock()
        dropbox_inst.extract_episode_number = Mock(return_value=1)
        dropbox_inst.upload_transcription = Mock(return_value="/podcast/transcriptions/ep_1/transcript.json")
        dropbox_inst.upload_finished_episode = Mock(return_value="/podcast/finished_files/episode.mp3")
        dropbox_inst.upload_clips = Mock(return_value=["/podcast/clips/ep_1/clip1.wav"])

        transcriber_inst = Mock()
        transcriber_inst.transcribe = Mock(return_value={"duration": 3600, "text": "transcript"})

        editor_inst = Mock()
        editor_inst.analyze_content = Mock(return_value={
            "episode_summary": "Test summary",
            "best_clips": [{"start_time": 10, "end_time": 40, "title": "Clip"}],
            "censor_timestamps": []
        })

        audio_inst = Mock()
        audio_inst.apply_censorship = Mock(return_value=Path("/fake/censored.wav"))
        audio_inst.create_clips = Mock(return_value=[Path("/fake/clip1.wav")])
        audio_inst.convert_to_mp3 = Mock(return_value=Path("/fake/censored.mp3"))

        mock_dropbox.return_value = dropbox_inst
        mock_transcriber.return_value = transcriber_inst
        mock_editor.return_value = editor_inst
        mock_audio.return_value = audio_inst

        yield {
            'dropbox': dropbox_inst,
            'transcriber': transcriber_inst,
            'editor': editor_inst,
            'audio': audio_inst
        }


@pytest.fixture
def processor(mock_config, mock_components):
    """Create HistoricalEpisodeProcessor instance."""
    with patch('builtins.print'):  # Suppress print output
        return HistoricalEpisodeProcessor()


class TestHistoricalEpisodeProcessor:
    """Test HistoricalEpisodeProcessor functionality."""

    def test_init(self, processor, mock_config):
        """Test processor initialization."""
        assert processor is not None
        assert processor.dropbox is not None
        assert processor.transcriber is not None
        assert processor.editor is not None
        assert processor.audio_processor is not None

    def test_process_historical_episode_success(self, processor, mock_components, tmp_path):
        """Test successful episode processing."""
        # Create fake audio file
        audio_file = tmp_path / "Episode #1 - Test.mp4"
        audio_file.write_text("fake audio")

        # Mock file operations
        with patch('builtins.open', mock_open()) as mock_file, \
             patch('builtins.print'), \
             patch('json.dump'):

            result = processor.process_historical_episode(audio_file)

        # Verify result
        assert result is not None
        assert result['episode_number'] == 1
        assert 'transcript' in result
        assert 'analysis' in result
        assert 'clips' in result
        assert 'episode_summary' in result

    def test_process_historical_episode_file_not_found(self, processor):
        """Test processing with non-existent file."""
        fake_file = Path("/fake/nonexistent.mp4")

        with patch('builtins.print'):
            result = processor.process_historical_episode(fake_file)

        assert result is None

    def test_process_historical_episode_extracts_episode_number(self, processor, mock_components, tmp_path):
        """Test that episode number is extracted from filename."""
        audio_file = tmp_path / "Episode #5 - Title.mp4"
        audio_file.write_text("fake")

        mock_components['dropbox'].extract_episode_number.return_value = 5

        with patch('builtins.open', mock_open()), \
             patch('builtins.print'), \
             patch('json.dump'):

            result = processor.process_historical_episode(audio_file)

        assert result['episode_number'] == 5

    def test_process_historical_episode_creates_output_subfolder(self, processor, mock_components, tmp_path, mock_config):
        """Test that episode output subfolder is created."""
        audio_file = tmp_path / "Episode #3 - Test.mp4"
        audio_file.write_text("fake")

        mock_components['dropbox'].extract_episode_number.return_value = 3

        with patch('builtins.open', mock_open()), \
             patch('builtins.print'), \
             patch('json.dump'), \
             patch('pathlib.Path.mkdir') as mock_mkdir:

            result = processor.process_historical_episode(audio_file)

        # Verify subfolder creation was attempted
        assert mock_mkdir.called

    def test_process_historical_episode_uploads_to_dropbox(self, processor, mock_components, tmp_path):
        """Test that files are uploaded to Dropbox."""
        audio_file = tmp_path / "Episode #1 - Test.mp4"
        audio_file.write_text("fake")

        with patch('builtins.open', mock_open()), \
             patch('builtins.print'), \
             patch('json.dump'):

            result = processor.process_historical_episode(audio_file)

        # Verify uploads were called
        assert mock_components['dropbox'].upload_transcription.called
        assert mock_components['dropbox'].upload_finished_episode.called
        assert mock_components['dropbox'].upload_clips.called

    def test_process_historical_episode_handles_no_episode_number(self, processor, mock_components, tmp_path):
        """Test processing file without episode number."""
        audio_file = tmp_path / "random_audio.mp4"
        audio_file.write_text("fake")

        mock_components['dropbox'].extract_episode_number.return_value = None

        with patch('builtins.open', mock_open()), \
             patch('builtins.print'), \
             patch('json.dump'):

            result = processor.process_historical_episode(audio_file)

        assert result['episode_number'] == 0

    def test_process_all_historical_episodes_folder_not_found(self, processor):
        """Test processing with non-existent folder."""
        with patch('builtins.print'):
            processor.process_all_historical_episodes("/fake/folder")

        # Should handle gracefully

    def test_process_all_historical_episodes_no_audio_files(self, processor, tmp_path):
        """Test processing folder with no audio files."""
        empty_folder = tmp_path / "empty"
        empty_folder.mkdir()

        with patch('builtins.print'):
            processor.process_all_historical_episodes(str(empty_folder))

        # Should handle gracefully

    def test_process_all_historical_episodes_finds_audio_files(self, processor, mock_components, tmp_path):
        """Test that all audio file types are found."""
        folder = tmp_path / "episodes"
        folder.mkdir()

        # Create different audio formats
        (folder / "ep1.mp4").write_text("fake")
        (folder / "ep2.m4a").write_text("fake")
        (folder / "ep3.wav").write_text("fake")
        (folder / "ep4.mp3").write_text("fake")

        with patch.object(processor, 'process_historical_episode', return_value={'episode_number': 1}) as mock_process, \
             patch('builtins.print'):

            processor.process_all_historical_episodes(str(folder))

        # Should have processed 4 files
        assert mock_process.call_count == 4

    def test_process_all_historical_episodes_sorts_by_episode_number(self, processor, mock_components, tmp_path):
        """Test that episodes are processed in order."""
        folder = tmp_path / "episodes"
        folder.mkdir()

        (folder / "Episode #3.mp4").write_text("fake")
        (folder / "Episode #1.mp4").write_text("fake")
        (folder / "Episode #2.mp4").write_text("fake")

        call_order = []

        def track_calls(audio_file):
            num = processor.dropbox.extract_episode_number(audio_file.name)
            call_order.append(num)
            return {'episode_number': num}

        # Mock extract_episode_number to return actual numbers
        def extract_num(filename):
            if "#3" in filename:
                return 3
            elif "#2" in filename:
                return 2
            elif "#1" in filename:
                return 1
            return 999

        mock_components['dropbox'].extract_episode_number.side_effect = extract_num

        with patch.object(processor, 'process_historical_episode', side_effect=track_calls), \
             patch('builtins.print'):

            processor.process_all_historical_episodes(str(folder))

        # Should be processed in order: 1, 2, 3
        assert call_order == [1, 2, 3]

    def test_process_all_historical_episodes_with_start_episode(self, processor, mock_components, tmp_path):
        """Test processing with start_episode parameter."""
        folder = tmp_path / "episodes"
        folder.mkdir()

        (folder / "Episode #1.mp4").write_text("fake")
        (folder / "Episode #2.mp4").write_text("fake")
        (folder / "Episode #3.mp4").write_text("fake")

        processed = []

        def track_calls(audio_file):
            num = processor.dropbox.extract_episode_number(audio_file.name)
            processed.append(num)
            return {'episode_number': num}

        def extract_num(filename):
            if "#1" in filename: return 1
            if "#2" in filename: return 2
            if "#3" in filename: return 3
            return 999

        mock_components['dropbox'].extract_episode_number.side_effect = extract_num

        with patch.object(processor, 'process_historical_episode', side_effect=track_calls), \
             patch('builtins.print'):

            processor.process_all_historical_episodes(str(folder), start_episode=2)

        # Should only process episodes 2 and 3
        assert 1 not in processed
        assert 2 in processed
        assert 3 in processed

    def test_process_all_historical_episodes_handles_exceptions(self, processor, mock_components, tmp_path):
        """Test that exceptions don't stop batch processing."""
        folder = tmp_path / "episodes"
        folder.mkdir()

        (folder / "Episode #1.mp4").write_text("fake")
        (folder / "Episode #2.mp4").write_text("fake")

        call_count = [0]

        def fail_then_succeed(audio_file):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Network error")
            return {'episode_number': 2}

        def extract_num(filename):
            if "#1" in filename: return 1
            if "#2" in filename: return 2
            return 999

        mock_components['dropbox'].extract_episode_number.side_effect = extract_num

        with patch.object(processor, 'process_historical_episode', side_effect=fail_then_succeed), \
             patch('builtins.print'), \
             patch('traceback.print_exc'):

            processor.process_all_historical_episodes(str(folder))

        # Should have tried to process both episodes
        assert call_count[0] == 2

    def test_process_all_historical_episodes_network_error_auto_continues(self, processor, mock_components, tmp_path):
        """Test that network errors auto-continue to next episode."""
        folder = tmp_path / "episodes"
        folder.mkdir()

        (folder / "Episode #1.mp4").write_text("fake")
        (folder / "Episode #2.mp4").write_text("fake")

        call_count = [0]

        def raise_ssl_error(audio_file):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("SSLError: Max retries exceeded")
            return {'episode_number': 2}

        def extract_num(filename):
            if "#1" in filename: return 1
            if "#2" in filename: return 2
            return 999

        mock_components['dropbox'].extract_episode_number.side_effect = extract_num

        with patch.object(processor, 'process_historical_episode', side_effect=raise_ssl_error), \
             patch('builtins.print'), \
             patch('traceback.print_exc'):

            processor.process_all_historical_episodes(str(folder))

        # Should have continued to episode 2 after SSL error on episode 1
        assert call_count[0] == 2
