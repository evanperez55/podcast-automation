"""Tests for ChapterGenerator — RED phase (chapter_generator.py does not exist yet)."""

import pytest  # noqa: F401
from unittest.mock import MagicMock, patch

from chapter_generator import ChapterGenerator  # noqa: F401  # ImportError expected (RED)

SAMPLE_CHAPTERS = [
    {"start_seconds": 0.0, "title": "Intro"},
    {"start_seconds": 330.0, "title": "We Talk About Lobsters"},
    {"start_seconds": 1200.0, "title": "Wrap Up"},
]


class TestEmbedID3Chapters:
    """Tests for ChapterGenerator.embed_id3_chapters writing CHAP+CTOC frames."""

    def test_writes_ctoc_and_chap_frames(self):
        """embed_id3_chapters adds 1 CTOC + 3 CHAP frames and calls save()."""
        cg = ChapterGenerator()
        with (
            patch("chapter_generator.mutagen.id3.ID3") as mock_id3_cls,
            patch("chapter_generator.mutagen.mp3.MP3") as mock_mp3_cls,
            patch("chapter_generator.mutagen.id3.CTOC") as mock_ctoc,  # noqa: F841
            patch("chapter_generator.mutagen.id3.CHAP") as mock_chap,  # noqa: F841
            patch("chapter_generator.mutagen.id3.TIT2") as mock_tit2,  # noqa: F841
            patch("chapter_generator.mutagen.id3.CTOCFlags") as mock_flags,  # noqa: F841
        ):
            mock_audio = MagicMock()
            mock_id3_cls.return_value = mock_audio
            mock_mp3 = MagicMock()
            mock_mp3.info.length = 2000.0
            mock_mp3_cls.return_value = mock_mp3

            cg.embed_id3_chapters("/fake/ep.mp3", SAMPLE_CHAPTERS)

            # 1 CTOC + 3 CHAP = 4 add() calls
            assert mock_audio.add.call_count == 4
            assert mock_audio.save.called

    def test_last_chapter_end_time_equals_total_duration(self):
        """Last CHAP frame end_time equals int(mp3_info.info.length * 1000)."""
        cg = ChapterGenerator()
        chap_calls = []

        with (
            patch("chapter_generator.mutagen.id3.ID3") as mock_id3_cls,
            patch("chapter_generator.mutagen.mp3.MP3") as mock_mp3_cls,
            patch("chapter_generator.mutagen.id3.CTOC"),
            patch("chapter_generator.mutagen.id3.CHAP") as mock_chap_cls,
            patch("chapter_generator.mutagen.id3.TIT2"),
            patch("chapter_generator.mutagen.id3.CTOCFlags"),
        ):
            mock_audio = MagicMock()
            mock_id3_cls.return_value = mock_audio
            mock_mp3 = MagicMock()
            mock_mp3.info.length = 2000.0
            mock_mp3_cls.return_value = mock_mp3

            def capture_chap(**kwargs):
                chap_calls.append(kwargs)
                return MagicMock()

            mock_chap_cls.side_effect = capture_chap

            cg.embed_id3_chapters("/fake/ep.mp3", SAMPLE_CHAPTERS)

        # Last CHAP's end_time should be 2000 * 1000 = 2000000
        assert len(chap_calls) == 3
        last_chap = chap_calls[-1]
        assert last_chap["end_time"] == 2000000

    def test_returns_true_on_success(self):
        """embed_id3_chapters returns True when chapters list is non-empty."""
        cg = ChapterGenerator()
        with (
            patch("chapter_generator.mutagen.id3.ID3") as mock_id3_cls,
            patch("chapter_generator.mutagen.mp3.MP3") as mock_mp3_cls,
            patch("chapter_generator.mutagen.id3.CTOC"),
            patch("chapter_generator.mutagen.id3.CHAP"),
            patch("chapter_generator.mutagen.id3.TIT2"),
            patch("chapter_generator.mutagen.id3.CTOCFlags"),
        ):
            mock_audio = MagicMock()
            mock_id3_cls.return_value = mock_audio
            mock_mp3 = MagicMock()
            mock_mp3.info.length = 1500.0
            mock_mp3_cls.return_value = mock_mp3

            result = cg.embed_id3_chapters("/fake/ep.mp3", SAMPLE_CHAPTERS)

        assert result is True


class TestEmbedID3ChaptersEdgeCases:
    """Edge case tests for ChapterGenerator.embed_id3_chapters."""

    def test_returns_false_for_empty_chapters(self):
        """embed_id3_chapters(mp3_path, []) returns False without calling ID3."""
        cg = ChapterGenerator()
        with patch("chapter_generator.mutagen.id3.ID3") as mock_id3_cls:
            result = cg.embed_id3_chapters("/fake/ep.mp3", [])

        assert result is False
        mock_id3_cls.assert_not_called()

    def test_no_existing_id3_header(self):
        """When ID3(mp3_path) raises ID3NoHeaderError, function creates new ID3 and continues."""
        cg = ChapterGenerator()
        with (
            patch("chapter_generator.mutagen.id3.ID3") as mock_id3_cls,
            patch("chapter_generator.mutagen.id3.ID3NoHeaderError", Exception),
            patch("chapter_generator.mutagen.mp3.MP3") as mock_mp3_cls,
            patch("chapter_generator.mutagen.id3.CTOC"),
            patch("chapter_generator.mutagen.id3.CHAP"),
            patch("chapter_generator.mutagen.id3.TIT2"),
            patch("chapter_generator.mutagen.id3.CTOCFlags"),
        ):
            # First call raises ID3NoHeaderError, subsequent calls return a mock
            new_audio = MagicMock()
            mock_id3_cls.side_effect = [
                Exception("/fake/ep.mp3 has no ID3 header"),
                new_audio,
                new_audio,
            ]
            mock_mp3 = MagicMock()
            mock_mp3.info.length = 1000.0
            mock_mp3_cls.return_value = mock_mp3

            cg.embed_id3_chapters("/fake/ep.mp3", SAMPLE_CHAPTERS)

        # Should still save (chapters still embedded)
        assert new_audio.save.called

    def test_title_truncated_to_45_chars(self):
        """Chapter title of 60 chars is sliced to 45 before writing to CHAP sub_frames."""
        cg = ChapterGenerator()
        long_title = "A" * 60
        chapters = [{"start_seconds": 0.0, "title": long_title}]
        tit2_texts = []

        with (
            patch("chapter_generator.mutagen.id3.ID3") as mock_id3_cls,
            patch("chapter_generator.mutagen.mp3.MP3") as mock_mp3_cls,
            patch("chapter_generator.mutagen.id3.CTOC"),
            patch("chapter_generator.mutagen.id3.CHAP"),
            patch("chapter_generator.mutagen.id3.TIT2") as mock_tit2_cls,
            patch("chapter_generator.mutagen.id3.CTOCFlags"),
        ):
            mock_audio = MagicMock()
            mock_id3_cls.return_value = mock_audio
            mock_mp3 = MagicMock()
            mock_mp3.info.length = 500.0
            mock_mp3_cls.return_value = mock_mp3

            def capture_tit2(encoding=3, text=""):
                tit2_texts.append(text)
                return MagicMock()

            mock_tit2_cls.side_effect = capture_tit2

            cg.embed_id3_chapters("/fake/ep.mp3", chapters)

        assert len(tit2_texts) == 1
        assert len(tit2_texts[0]) == 45

    def test_deletes_existing_chap_ctoc(self):
        """audio.delall('CHAP') and audio.delall('CTOC') called before any audio.add."""
        cg = ChapterGenerator()
        call_order = []

        with (
            patch("chapter_generator.mutagen.id3.ID3") as mock_id3_cls,
            patch("chapter_generator.mutagen.mp3.MP3") as mock_mp3_cls,
            patch("chapter_generator.mutagen.id3.CTOC"),
            patch("chapter_generator.mutagen.id3.CHAP"),
            patch("chapter_generator.mutagen.id3.TIT2"),
            patch("chapter_generator.mutagen.id3.CTOCFlags"),
        ):
            mock_audio = MagicMock()

            def track_delall(tag):
                call_order.append(f"delall:{tag}")

            def track_add(frame):
                call_order.append("add")

            mock_audio.delall.side_effect = track_delall
            mock_audio.add.side_effect = track_add
            mock_id3_cls.return_value = mock_audio
            mock_mp3 = MagicMock()
            mock_mp3.info.length = 1000.0
            mock_mp3_cls.return_value = mock_mp3

            cg.embed_id3_chapters("/fake/ep.mp3", SAMPLE_CHAPTERS)

        # delall calls must precede any add calls
        first_add_idx = next((i for i, c in enumerate(call_order) if c == "add"), None)
        chap_delall_idx = next(
            (i for i, c in enumerate(call_order) if c == "delall:CHAP"), None
        )
        ctoc_delall_idx = next(
            (i for i, c in enumerate(call_order) if c == "delall:CTOC"), None
        )
        assert chap_delall_idx is not None, "delall('CHAP') never called"
        assert ctoc_delall_idx is not None, "delall('CTOC') never called"
        assert chap_delall_idx < first_add_idx, "delall('CHAP') must precede add()"
        assert ctoc_delall_idx < first_add_idx, "delall('CTOC') must precede add()"


class TestGenerateChaptersJson:
    """Tests for ChapterGenerator.generate_chapters_json writing Podcasting 2.0 JSON."""

    def test_writes_podcasting20_json(self, tmp_path):
        """Output JSON has version '1.2.0' and chapters array with startTime and title."""
        import json

        cg = ChapterGenerator()
        output_path = str(tmp_path / "test_chapters.json")
        cg.generate_chapters_json(SAMPLE_CHAPTERS, output_path)

        with open(output_path) as f:
            payload = json.load(f)

        assert payload["version"] == "1.2.0"
        assert len(payload["chapters"]) == 3
        assert payload["chapters"][0]["startTime"] == 0.0
        assert payload["chapters"][0]["title"] == "Intro"

    def test_returns_output_path(self, tmp_path):
        """generate_chapters_json returns the output_path string passed in."""
        cg = ChapterGenerator()
        output_path = str(tmp_path / "out.json")
        result = cg.generate_chapters_json(SAMPLE_CHAPTERS, output_path)
        assert result == output_path

    def test_returns_none_for_empty_chapters(self, tmp_path):
        """generate_chapters_json with empty list returns None, file not written."""
        import os

        cg = ChapterGenerator()
        output_path = str(tmp_path / "should_not_exist.json")
        result = cg.generate_chapters_json([], output_path)

        assert result is None
        assert not os.path.exists(output_path)
