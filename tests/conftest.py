"""Shared test fixtures for podcast-automation.

Centralizes common fixtures used across multiple test files.
Import these by name in test files — pytest discovers them automatically.
"""

import pytest
from unittest.mock import Mock

from audio_processor import AudioProcessor
from config import Config
from pydub import AudioSegment


# ---------------------------------------------------------------------------
# Audio fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def audio_processor():
    """Create an AudioProcessor instance."""
    return AudioProcessor()


@pytest.fixture
def mock_audio_segment():
    """Create a mock AudioSegment with standard duration."""
    audio = Mock(spec=AudioSegment)
    audio.duration_seconds = 100.0
    audio.__len__ = Mock(return_value=100000)
    audio.__getitem__ = Mock(return_value=audio)
    audio.overlay = Mock(return_value=audio)
    audio.export = Mock()
    return audio


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------


SAMPLE_ANALYSIS = {
    "episode_title": "Test Episode",
    "episode_summary": "A test episode about testing.",
    "chapters": [
        {"start_timestamp": "00:00:00", "title": "Intro", "start_seconds": 0},
        {"start_timestamp": "00:05:00", "title": "Main Topic", "start_seconds": 300},
    ],
    "best_clips": [
        {
            "start": "00:05:00",
            "end": "00:05:25",
            "description": "Great moment",
            "suggested_title": "Test Clip",
        }
    ],
    "show_notes": "Show notes content here.",
    "social_captions": {"youtube": "YT caption"},
}

SAMPLE_TRANSCRIPT = {
    "segments": [{"text": "Hello world"}, {"text": "This is a test"}],
    "words": [],
    "duration": 600,
}

SAMPLE_SEGMENTS = [
    {"start": 0.0, "end": 5.0, "text": "hello there"},
    {"start": 5.0, "end": 10.0, "text": "this is funny"},
]

SAMPLE_CHAPTERS = [
    {"start_seconds": 0.0, "title": "Intro"},
    {"start_seconds": 330.0, "title": "We Talk About Lobsters"},
    {"start_seconds": 1200.0, "title": "Wrap Up"},
]


# ---------------------------------------------------------------------------
# Config fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_output_dir(tmp_path, monkeypatch):
    """Point Config.OUTPUT_DIR to a temp directory."""
    monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path)
    return tmp_path
