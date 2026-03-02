"""Tests for the ClipPreviewer class."""

from unittest.mock import patch

from clip_previewer import ClipPreviewer

CLIP_PATHS = ["/path/clip1.wav", "/path/clip2.wav", "/path/clip3.wav"]
CLIP_INFO = [
    {
        "duration_seconds": 20,
        "suggested_title": "Clip 1",
        "description": "First clip description",
    },
    {
        "duration_seconds": 25,
        "suggested_title": "Clip 2",
        "description": "Second clip description",
    },
    {
        "duration_seconds": 18,
        "suggested_title": "Clip 3",
        "description": "Third clip description",
    },
]


class TestAutoApprove:
    def test_auto_approve_all(self):
        """auto_approve=True returns all indices without prompting."""
        previewer = ClipPreviewer(auto_approve=True)
        result = previewer.preview_clips(CLIP_PATHS, CLIP_INFO)
        assert result == [0, 1, 2]


class TestInteractivePreview:
    @patch("builtins.input", return_value="A")
    def test_approve_all_interactive(self, mock_input):
        """Typing 'A' approves all clips."""
        previewer = ClipPreviewer(auto_approve=False)
        result = previewer.preview_clips(CLIP_PATHS, CLIP_INFO)
        assert result == [0, 1, 2]

    @patch("builtins.input", return_value="Q")
    def test_quit_returns_empty(self, mock_input):
        """Typing 'Q' quits and returns an empty list."""
        previewer = ClipPreviewer(auto_approve=False)
        result = previewer.preview_clips(CLIP_PATHS, CLIP_INFO)
        assert result == []

    @patch("builtins.input", side_effect=["S2", "A"])
    def test_skip_and_approve(self, mock_input):
        """Skipping clip 2 then approving returns [0, 2]."""
        previewer = ClipPreviewer(auto_approve=False)
        result = previewer.preview_clips(CLIP_PATHS, CLIP_INFO)
        assert result == [0, 2]

    @patch("builtins.input", side_effect=["P1", "A"])
    @patch("clip_previewer.subprocess.Popen")
    def test_play_then_approve(self, mock_popen, mock_input):
        """Playing clip 1 then approving returns all indices."""
        previewer = ClipPreviewer(auto_approve=False)
        result = previewer.preview_clips(CLIP_PATHS, CLIP_INFO)
        assert result == [0, 1, 2]
        mock_popen.assert_called_once()


class TestParseIndex:
    def test_parse_index_valid(self):
        """'S2' with total=3 returns 1 (0-based index)."""
        previewer = ClipPreviewer()
        assert previewer._parse_index("S2", total=3) == 1

    def test_parse_index_out_of_bounds(self):
        """'S5' with total=3 returns None."""
        previewer = ClipPreviewer()
        assert previewer._parse_index("S5", total=3) is None

    def test_parse_index_invalid(self):
        """'Sxyz' returns None (non-numeric suffix)."""
        previewer = ClipPreviewer()
        assert previewer._parse_index("Sxyz", total=3) is None


class TestFilterClips:
    def test_filter_clips(self):
        """Filtering with approved=[0, 2] returns the correct subset."""
        previewer = ClipPreviewer()
        paths, info = previewer.filter_clips(CLIP_PATHS, CLIP_INFO, [0, 2])
        assert paths == ["/path/clip1.wav", "/path/clip3.wav"]
        assert info == [CLIP_INFO[0], CLIP_INFO[2]]

    def test_filter_clips_empty(self):
        """Filtering with approved=[] returns empty lists."""
        previewer = ClipPreviewer()
        paths, info = previewer.filter_clips(CLIP_PATHS, CLIP_INFO, [])
        assert paths == []
        assert info == []


class TestPlayClip:
    @patch("clip_previewer.subprocess.Popen")
    @patch("clip_previewer.os.name", "nt")
    def test_play_clip_called(self, mock_popen):
        """_play_clip opens the file via subprocess.Popen on Windows."""
        previewer = ClipPreviewer()
        previewer._play_clip("/path/clip1.wav")
        mock_popen.assert_called_once_with(["start", "", "/path/clip1.wav"], shell=True)
