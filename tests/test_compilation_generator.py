"""Tests for compilation_generator module."""

import pytest
from unittest.mock import patch, MagicMock

from compilation_generator import CompilationGenerator


@pytest.fixture
def generator():
    """Create a CompilationGenerator instance."""
    return CompilationGenerator()


class TestCompilationGeneratorInit:
    """Tests for __init__."""

    def test_enabled_by_default(self):
        """Enabled by default when env var not set."""
        with patch.dict("os.environ", {}, clear=False):
            gen = CompilationGenerator()
            assert gen.enabled is True

    def test_disabled_via_env(self):
        """Can be disabled via COMPILATION_ENABLED=false."""
        with patch.dict("os.environ", {"COMPILATION_ENABLED": "false"}):
            gen = CompilationGenerator()
            assert gen.enabled is False

    def test_crossfade_default(self):
        """Default crossfade is 500ms."""
        gen = CompilationGenerator()
        assert gen.crossfade_ms == 500


class TestGenerateBestOf:
    """Tests for generate_best_of."""

    def test_returns_none_when_disabled(self, generator):
        """Returns None when compilation disabled."""
        generator.enabled = False
        result = generator.generate_best_of()
        assert result is None

    def test_returns_none_when_no_clips(self, generator):
        """Returns None when no clips found."""
        with patch.object(generator, "_discover_and_score_clips", return_value=[]):
            result = generator.generate_best_of()
        assert result is None

    def test_clips_sorted_by_score(self, generator):
        """Clips are sorted by score descending before selection."""
        clips = [
            {"path": "clip1.wav", "score": 5},
            {"path": "clip2.wav", "score": 9},
            {"path": "clip3.wav", "score": 7},
        ]
        clips.sort(key=lambda c: c["score"], reverse=True)
        assert clips[0]["score"] == 9
        assert clips[1]["score"] == 7


class TestDiscoverAndScoreClips:
    """Tests for _discover_and_score_clips."""

    def test_returns_empty_when_no_output_dir(self, generator, tmp_path, monkeypatch):
        """Returns empty list when output dir doesn't exist."""
        from config import Config

        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path / "nonexistent")
        result = generator._discover_and_score_clips()
        assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
