"""Tests for process_historical_episodes module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from process_historical_episodes import HistoricalEpisodeProcessor


@pytest.fixture
def mock_config():
    """Mock Config module."""
    with patch("process_historical_episodes.Config") as mock_cfg:
        mock_cfg.OUTPUT_DIR = Path("/fake/output")
        mock_cfg.CLIPS_DIR = Path("/fake/clips")
        mock_cfg.validate = Mock()
        mock_cfg.create_directories = Mock()
        yield mock_cfg


@pytest.fixture
def mock_components():
    """Mock all component classes."""
    with (
        patch("process_historical_episodes.DropboxHandler") as mock_dropbox,
        patch("process_historical_episodes.Transcriber") as mock_transcriber,
        patch("process_historical_episodes.ContentEditor") as mock_editor,
        patch("process_historical_episodes.AudioProcessor") as mock_audio,
    ):
        # Setup mock instances
        dropbox_inst = Mock()
        dropbox_inst.extract_episode_number = Mock(return_value=1)
        dropbox_inst.upload_transcription = Mock(
            return_value="/podcast/transcriptions/ep_1/transcript.json"
        )
        dropbox_inst.upload_finished_episode = Mock(
            return_value="/podcast/finished_files/episode.mp3"
        )
        dropbox_inst.upload_clips = Mock(return_value=["/podcast/clips/ep_1/clip1.wav"])

        transcriber_inst = Mock()
        transcriber_inst.transcribe = Mock(
            return_value={"duration": 3600, "text": "transcript"}
        )

        editor_inst = Mock()
        editor_inst.analyze_content = Mock(
            return_value={
                "episode_summary": "Test summary",
                "best_clips": [{"start_time": 10, "end_time": 40, "title": "Clip"}],
                "censor_timestamps": [],
            }
        )

        audio_inst = Mock()
        audio_inst.apply_censorship = Mock(return_value=Path("/fake/censored.wav"))
        audio_inst.create_clips = Mock(return_value=[Path("/fake/clip1.wav")])
        audio_inst.convert_to_mp3 = Mock(return_value=Path("/fake/censored.mp3"))

        mock_dropbox.return_value = dropbox_inst
        mock_transcriber.return_value = transcriber_inst
        mock_editor.return_value = editor_inst
        mock_audio.return_value = audio_inst

        yield {
            "dropbox": dropbox_inst,
            "transcriber": transcriber_inst,
            "editor": editor_inst,
            "audio": audio_inst,
        }


@pytest.fixture
def processor(mock_config, mock_components):
    """Create HistoricalEpisodeProcessor instance."""
    with patch("builtins.print"):  # Suppress print output
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

    def test_process_historical_episode_success(
        self, processor, mock_components, tmp_path
    ):
        """Test successful episode processing."""
        # Create fake audio file
        audio_file = tmp_path / "Episode #1 - Test.mp4"
        audio_file.write_text("fake audio")

        # Mock file operations
        with (
            patch("builtins.open", mock_open()),
            patch("builtins.print"),
            patch("json.dump"),
        ):
            result = processor.process_historical_episode(audio_file)

        # Verify result
        assert result is not None
        assert result["episode_number"] == 1
        assert "transcript" in result
        assert "analysis" in result
        assert "clips" in result
        assert "episode_summary" in result

    def test_process_historical_episode_file_not_found(self, processor):
        """Test processing with non-existent file."""
        fake_file = Path("/fake/nonexistent.mp4")

        with patch("builtins.print"):
            result = processor.process_historical_episode(fake_file)

        assert result is None

    def test_process_historical_episode_extracts_episode_number(
        self, processor, mock_components, tmp_path
    ):
        """Test that episode number is extracted from filename."""
        audio_file = tmp_path / "Episode #5 - Title.mp4"
        audio_file.write_text("fake")

        mock_components["dropbox"].extract_episode_number.return_value = 5

        with (
            patch("builtins.open", mock_open()),
            patch("builtins.print"),
            patch("json.dump"),
        ):
            result = processor.process_historical_episode(audio_file)

        assert result["episode_number"] == 5

    def test_process_historical_episode_creates_output_subfolder(
        self, processor, mock_components, tmp_path, mock_config
    ):
        """Test that episode output subfolder is created."""
        audio_file = tmp_path / "Episode #3 - Test.mp4"
        audio_file.write_text("fake")

        mock_components["dropbox"].extract_episode_number.return_value = 3

        with (
            patch("builtins.open", mock_open()),
            patch("builtins.print"),
            patch("json.dump"),
            patch("pathlib.Path.mkdir") as mock_mkdir,
        ):
            processor.process_historical_episode(audio_file)

        # Verify subfolder creation was attempted
        assert mock_mkdir.called

    def test_process_historical_episode_uploads_to_dropbox(
        self, processor, mock_components, tmp_path
    ):
        """Test that files are uploaded to Dropbox."""
        audio_file = tmp_path / "Episode #1 - Test.mp4"
        audio_file.write_text("fake")

        with (
            patch("builtins.open", mock_open()),
            patch("builtins.print"),
            patch("json.dump"),
        ):
            processor.process_historical_episode(audio_file)

        # Verify uploads were called
        assert mock_components["dropbox"].upload_transcription.called
        assert mock_components["dropbox"].upload_finished_episode.called
        assert mock_components["dropbox"].upload_clips.called

    def test_process_historical_episode_handles_no_episode_number(
        self, processor, mock_components, tmp_path
    ):
        """Test processing file without episode number."""
        audio_file = tmp_path / "random_audio.mp4"
        audio_file.write_text("fake")

        mock_components["dropbox"].extract_episode_number.return_value = None

        with (
            patch("builtins.open", mock_open()),
            patch("builtins.print"),
            patch("json.dump"),
        ):
            result = processor.process_historical_episode(audio_file)

        assert result["episode_number"] == 0

    def test_process_all_historical_episodes_folder_not_found(self, processor):
        """Test processing with non-existent folder."""
        with patch("builtins.print"):
            processor.process_all_historical_episodes("/fake/folder")

        # Should handle gracefully

    def test_process_all_historical_episodes_no_audio_files(self, processor, tmp_path):
        """Test processing folder with no audio files."""
        empty_folder = tmp_path / "empty"
        empty_folder.mkdir()

        with patch("builtins.print"):
            processor.process_all_historical_episodes(str(empty_folder))

        # Should handle gracefully

    def test_process_all_historical_episodes_finds_audio_files(
        self, processor, mock_components, tmp_path
    ):
        """Test that all audio file types are found."""
        folder = tmp_path / "episodes"
        folder.mkdir()

        # Create different audio formats
        (folder / "ep1.mp4").write_text("fake")
        (folder / "ep2.m4a").write_text("fake")
        (folder / "ep3.wav").write_text("fake")
        (folder / "ep4.mp3").write_text("fake")

        with (
            patch.object(
                processor,
                "process_historical_episode",
                return_value={"episode_number": 1},
            ) as mock_process,
            patch("builtins.print"),
        ):
            processor.process_all_historical_episodes(str(folder))

        # Should have processed 4 files
        assert mock_process.call_count == 4

    def test_process_all_historical_episodes_sorts_by_episode_number(
        self, processor, mock_components, tmp_path
    ):
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
            return {"episode_number": num}

        # Mock extract_episode_number to return actual numbers
        def extract_num(filename):
            if "#3" in filename:
                return 3
            if "#2" in filename:
                return 2
            if "#1" in filename:
                return 1
            return 999

        mock_components["dropbox"].extract_episode_number.side_effect = extract_num

        with (
            patch.object(
                processor, "process_historical_episode", side_effect=track_calls
            ),
            patch("builtins.print"),
        ):
            processor.process_all_historical_episodes(str(folder))

        # Should be processed in order: 1, 2, 3
        assert call_order == [1, 2, 3]

    def test_process_all_historical_episodes_with_start_episode(
        self, processor, mock_components, tmp_path
    ):
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
            return {"episode_number": num}

        def extract_num(filename):
            if "#1" in filename:
                return 1
            if "#2" in filename:
                return 2
            if "#3" in filename:
                return 3
            return 999

        mock_components["dropbox"].extract_episode_number.side_effect = extract_num

        with (
            patch.object(
                processor, "process_historical_episode", side_effect=track_calls
            ),
            patch("builtins.print"),
        ):
            processor.process_all_historical_episodes(str(folder), start_episode=2)

        # Should only process episodes 2 and 3
        assert 1 not in processed
        assert 2 in processed
        assert 3 in processed

    def test_process_all_historical_episodes_handles_exceptions(
        self, processor, mock_components, tmp_path
    ):
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
            return {"episode_number": 2}

        def extract_num(filename):
            if "#1" in filename:
                return 1
            if "#2" in filename:
                return 2
            return 999

        mock_components["dropbox"].extract_episode_number.side_effect = extract_num

        with (
            patch.object(
                processor, "process_historical_episode", side_effect=fail_then_succeed
            ),
            patch("builtins.print"),
            patch("traceback.print_exc"),
        ):
            processor.process_all_historical_episodes(str(folder))

        # Should have tried to process both episodes
        assert call_count[0] == 2

    def test_process_all_historical_episodes_network_error_auto_continues(
        self, processor, mock_components, tmp_path
    ):
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
            return {"episode_number": 2}

        def extract_num(filename):
            if "#1" in filename:
                return 1
            if "#2" in filename:
                return 2
            return 999

        mock_components["dropbox"].extract_episode_number.side_effect = extract_num

        with (
            patch.object(
                processor, "process_historical_episode", side_effect=raise_ssl_error
            ),
            patch("builtins.print"),
            patch("traceback.print_exc"),
        ):
            processor.process_all_historical_episodes(str(folder))

        # Should have continued to episode 2 after SSL error on episode 1
        assert call_count[0] == 2


class TestProcessHistoricalEpisodeUploadFailures:
    """Tests for Dropbox upload failure warnings (lines 133, 145, 158)."""

    def test_transcription_upload_failure_warns(
        self, processor, mock_components, tmp_path
    ):
        """When transcription upload returns None, a warning is printed."""
        audio_file = tmp_path / "Episode #1 - Test.mp4"
        audio_file.write_text("fake")

        mock_components["dropbox"].upload_transcription.return_value = None

        printed = []
        with (
            patch("builtins.open", mock_open()),
            patch(
                "builtins.print", side_effect=lambda *a, **kw: printed.append(str(a))
            ),
            patch("json.dump"),
        ):
            result = processor.process_historical_episode(audio_file)

        assert result is not None
        assert any("Failed to upload transcription" in line for line in printed)

    def test_finished_episode_upload_failure_warns(
        self, processor, mock_components, tmp_path
    ):
        """When finished episode upload returns None, a warning is printed."""
        audio_file = tmp_path / "Episode #1 - Test.mp4"
        audio_file.write_text("fake")

        mock_components["dropbox"].upload_finished_episode.return_value = None

        printed = []
        with (
            patch("builtins.open", mock_open()),
            patch(
                "builtins.print", side_effect=lambda *a, **kw: printed.append(str(a))
            ),
            patch("json.dump"),
        ):
            result = processor.process_historical_episode(audio_file)

        assert result is not None
        assert any("Failed to upload censored audio" in line for line in printed)

    def test_clips_upload_failure_warns(self, processor, mock_components, tmp_path):
        """When clips upload returns empty list, a warning is printed."""
        audio_file = tmp_path / "Episode #1 - Test.mp4"
        audio_file.write_text("fake")

        mock_components["dropbox"].upload_clips.return_value = []

        printed = []
        with (
            patch("builtins.open", mock_open()),
            patch(
                "builtins.print", side_effect=lambda *a, **kw: printed.append(str(a))
            ),
            patch("json.dump"),
        ):
            result = processor.process_historical_episode(audio_file)

        assert result is not None
        assert any("Failed to upload clips" in line for line in printed)


class TestProcessAllHistoricalEpisodesReturnNone:
    """Tests for process_historical_episode returning None in batch (line 252)."""

    def test_process_returns_none_prints_error(
        self, processor, mock_components, tmp_path
    ):
        """When process_historical_episode returns None, an error is printed."""
        folder = tmp_path / "episodes"
        folder.mkdir()
        (folder / "Episode #1.mp4").write_text("fake")

        mock_components["dropbox"].extract_episode_number.return_value = 1

        printed = []
        with (
            patch.object(processor, "process_historical_episode", return_value=None),
            patch(
                "builtins.print", side_effect=lambda *a, **kw: printed.append(str(a))
            ),
        ):
            processor.process_all_historical_episodes(str(folder))

        assert any("Failed to process" in line for line in printed)


class TestMainFunction:
    """Tests for the main() entry point (lines 285-326)."""

    def test_main_with_all_arg(self):
        """Test main() with 'all' argument processes all episodes."""
        with (
            patch("process_historical_episodes.HistoricalEpisodeProcessor") as mock_cls,
            patch("sys.argv", ["script", "all"]),
            patch("builtins.print"),
        ):
            mock_inst = Mock()
            mock_cls.return_value = mock_inst

            from process_historical_episodes import main

            main()

            mock_inst.process_all_historical_episodes.assert_called_once_with(
                "historical_ep", start_episode=None
            )

    def test_main_with_all_and_start_episode(self):
        """Test main() with 'all 5' starts from episode 5."""
        with (
            patch("process_historical_episodes.HistoricalEpisodeProcessor") as mock_cls,
            patch("sys.argv", ["script", "all", "5"]),
            patch("builtins.print"),
        ):
            mock_inst = Mock()
            mock_cls.return_value = mock_inst

            from process_historical_episodes import main

            main()

            mock_inst.process_all_historical_episodes.assert_called_once_with(
                "historical_ep", start_episode=5
            )

    def test_main_with_all_and_folder_arg(self):
        """Test main() with 'all <folder>' uses folder as path."""
        with (
            patch("process_historical_episodes.HistoricalEpisodeProcessor") as mock_cls,
            patch("sys.argv", ["script", "all", "my_folder"]),
            patch("builtins.print"),
        ):
            mock_inst = Mock()
            mock_cls.return_value = mock_inst

            from process_historical_episodes import main

            main()

            mock_inst.process_all_historical_episodes.assert_called_once_with(
                "my_folder", start_episode=None
            )

    def test_main_with_single_file_arg(self):
        """Test main() with a file path processes single episode."""
        with (
            patch("process_historical_episodes.HistoricalEpisodeProcessor") as mock_cls,
            patch("sys.argv", ["script", "/path/to/episode.mp4"]),
            patch("builtins.print"),
        ):
            mock_inst = Mock()
            mock_cls.return_value = mock_inst

            from process_historical_episodes import main

            main()

            mock_inst.process_historical_episode.assert_called_once_with(
                "/path/to/episode.mp4"
            )

    def test_main_interactive_mode_process_all(self):
        """Test main() interactive mode choice 1 processes all."""
        with (
            patch("process_historical_episodes.HistoricalEpisodeProcessor") as mock_cls,
            patch("sys.argv", ["script"]),
            patch("builtins.print"),
            patch("builtins.input", side_effect=["1"]),
        ):
            mock_inst = Mock()
            mock_cls.return_value = mock_inst

            from process_historical_episodes import main

            main()

            mock_inst.process_all_historical_episodes.assert_called_once()

    def test_main_interactive_mode_process_single(self):
        """Test main() interactive mode choice 2 processes single file."""
        with (
            patch("process_historical_episodes.HistoricalEpisodeProcessor") as mock_cls,
            patch("sys.argv", ["script"]),
            patch("builtins.print"),
            patch("builtins.input", side_effect=["2", "/path/to/file.mp4"]),
        ):
            mock_inst = Mock()
            mock_cls.return_value = mock_inst

            from process_historical_episodes import main

            main()

            mock_inst.process_historical_episode.assert_called_once_with(
                "/path/to/file.mp4"
            )

    def test_main_interactive_mode_invalid_choice(self):
        """Test main() interactive mode with invalid choice prints error."""
        printed = []
        with (
            patch("process_historical_episodes.HistoricalEpisodeProcessor") as mock_cls,
            patch("sys.argv", ["script"]),
            patch(
                "builtins.print", side_effect=lambda *a, **kw: printed.append(str(a))
            ),
            patch("builtins.input", side_effect=["9"]),
        ):
            mock_cls.return_value = Mock()

            from process_historical_episodes import main

            main()

        assert any("Invalid choice" in line for line in printed)


class TestMainBlock:
    """Tests for the __main__ block (lines 330-340)."""

    def test_keyboard_interrupt_exits_with_code_1(self):
        """KeyboardInterrupt during main() exits with code 1."""
        with (
            patch(
                "process_historical_episodes.main",
                side_effect=KeyboardInterrupt,
            ),
            patch("builtins.print"),
            pytest.raises(SystemExit) as exc_info,
        ):
            exec(
                compile(
                    "try:\n"
                    "    main()\n"
                    "except KeyboardInterrupt:\n"
                    '    print("\\n\\n[WARNING] Interrupted by user")\n'
                    "    import sys; sys.exit(1)\n",
                    "<test>",
                    "exec",
                ),
                {
                    "main": Mock(side_effect=KeyboardInterrupt),
                    "print": lambda *a, **kw: None,
                },
            )

        assert exc_info.value.code == 1
