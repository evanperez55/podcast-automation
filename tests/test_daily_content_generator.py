"""Tests for daily_content_generator module."""

import pytest
from unittest.mock import patch, MagicMock


class TestDailyContentGeneratorInit:
    """Tests for initialization."""

    def test_enabled_by_default(self):
        """Enabled when DAILY_CONTENT_ENABLED not set."""
        with patch.dict("os.environ", {}, clear=False):
            from daily_content_generator import DailyContentGenerator

            gen = DailyContentGenerator()
            assert gen.enabled is True

    def test_disabled_via_env(self):
        """Disabled via DAILY_CONTENT_ENABLED=false."""
        with patch.dict("os.environ", {"DAILY_CONTENT_ENABLED": "false"}):
            from daily_content_generator import DailyContentGenerator

            gen = DailyContentGenerator()
            assert gen.enabled is False


class TestGenerateContent:
    """Tests for content generation."""

    def test_returns_none_when_disabled(self):
        """Returns None when generator disabled."""
        with patch.dict("os.environ", {"DAILY_CONTENT_ENABLED": "false"}):
            from daily_content_generator import DailyContentGenerator

            gen = DailyContentGenerator()
            result = gen.generate_and_save()
            assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
