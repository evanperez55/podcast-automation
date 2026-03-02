"""Tests for subtitle_generator module."""

import pytest
from subtitle_generator import SubtitleGenerator


@pytest.fixture
def gen():
    return SubtitleGenerator()


@pytest.fixture
def sample_transcript():
    return {
        "words": [
            {"word": "Hello", "start": 10.0, "end": 10.3},
            {"word": "world", "start": 10.4, "end": 10.7},
            {"word": "this", "start": 10.8, "end": 11.0},
            {"word": "is", "start": 11.1, "end": 11.2},
            {"word": "a", "start": 11.3, "end": 11.4},
            {"word": "test.", "start": 11.5, "end": 11.8},
            {"word": "Another", "start": 12.0, "end": 12.3},
            {"word": "sentence", "start": 12.4, "end": 12.8},
        ]
    }


class TestExtractWordsForClip:
    def test_extracts_words_in_range(self, gen, sample_transcript):
        words = gen.extract_words_for_clip(sample_transcript, 10.0, 11.0)
        assert len(words) == 5  # Hello, world, this, is, a (with 0.5s tolerance)
        assert words[0]["word"] == "Hello"

    def test_offsets_to_clip_relative(self, gen, sample_transcript):
        words = gen.extract_words_for_clip(sample_transcript, 10.0, 12.0)
        assert words[0]["start"] == 0.0
        assert words[0]["end"] == pytest.approx(0.3)

    def test_empty_when_no_words_in_range(self, gen, sample_transcript):
        words = gen.extract_words_for_clip(sample_transcript, 50.0, 60.0)
        assert words == []


class TestGroupWordsIntoLines:
    def test_breaks_at_punctuation(self, gen):
        words = [
            {"word": "Hello", "start": 0.0, "end": 0.3},
            {"word": "world.", "start": 0.4, "end": 0.7},
            {"word": "Next", "start": 0.8, "end": 1.0},
        ]
        lines = gen.group_words_into_lines(words)
        assert len(lines) == 2
        assert lines[0]["text"] == "Hello world."
        assert lines[1]["text"] == "Next"

    def test_breaks_at_max_words(self, gen):
        words = [
            {"word": f"w{i}", "start": i * 0.3, "end": i * 0.3 + 0.2} for i in range(8)
        ]
        lines = gen.group_words_into_lines(words)
        assert len(lines) == 2
        assert len(lines[0]["text"].split()) == 5

    def test_empty_input(self, gen):
        assert gen.group_words_into_lines([]) == []


class TestGenerateSrt:
    def test_srt_format(self, gen):
        lines = [
            {"text": "Hello world", "start": 0.0, "end": 1.5},
            {"text": "Second line", "start": 1.6, "end": 3.0},
        ]
        srt = gen.generate_srt(lines)
        assert "1\n00:00:00,000 --> 00:00:01,500\nHello world" in srt
        assert "2\n00:00:01,600 --> 00:00:03,000\nSecond line" in srt

    def test_time_formatting(self):
        assert SubtitleGenerator._seconds_to_srt_time(0.0) == "00:00:00,000"
        assert SubtitleGenerator._seconds_to_srt_time(65.5) == "00:01:05,500"
        assert SubtitleGenerator._seconds_to_srt_time(3661.123) == "01:01:01,123"


class TestGenerateClipSrt:
    def test_end_to_end(self, gen, sample_transcript, tmp_path):
        out = str(tmp_path / "clip.srt")
        result = gen.generate_clip_srt(sample_transcript, 10.0, 12.0, out)
        assert result == out
        content = open(out).read()
        assert "-->" in content

    def test_returns_none_no_words(self, gen, tmp_path):
        out = str(tmp_path / "empty.srt")
        result = gen.generate_clip_srt({"words": []}, 0, 10, out)
        assert result is None
