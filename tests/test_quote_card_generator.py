"""Tests for quote card generator."""

import pytest
from unittest.mock import patch

from quote_card_generator import QuoteCardGenerator


SAMPLE_ANALYSIS = {
    "best_quotes": [
        {
            "quote": "Lobsters are basically immortal and honestly good for them",
            "timestamp": "00:03:15",
            "speaker_context": "one of the hosts",
        },
        {
            "quote": "I think cancer is going to be just like how bacteria was",
            "timestamp": "00:06:02",
            "speaker_context": "one of the hosts",
        },
        {
            "quote": "We spent twenty minutes on whether horses are lying to us",
            "timestamp": "00:25:30",
            "speaker_context": "one of the hosts",
        },
    ],
}


class TestQuoteCardGeneratorInit:
    """Tests for QuoteCardGenerator initialization."""

    def test_init_default_enabled(self):
        """Default state is enabled."""
        gen = QuoteCardGenerator()
        assert gen.enabled is True
        assert gen.width == 1080
        assert gen.height == 1080

    @patch.dict("os.environ", {"QUOTE_CARD_ENABLED": "false"})
    def test_init_disabled(self):
        """QUOTE_CARD_ENABLED=false disables generation."""
        gen = QuoteCardGenerator()
        assert gen.enabled is False


class TestGenerateQuoteCard:
    """Tests for single quote card generation."""

    def test_generates_png(self, tmp_path):
        """Generates a valid PNG file."""
        gen = QuoteCardGenerator()
        output = tmp_path / "test_quote.png"
        result = gen.generate_quote_card("This is a test quote", 30, str(output))
        assert result is not None
        assert result.exists()
        assert result.suffix == ".png"

    def test_image_dimensions(self, tmp_path):
        """Generated image is 1080x1080."""
        from PIL import Image

        gen = QuoteCardGenerator()
        output = tmp_path / "test_quote.png"
        gen.generate_quote_card("Test quote", 30, str(output))

        img = Image.open(str(output))
        assert img.size == (1080, 1080)

    def test_disabled_returns_none(self, tmp_path):
        """When disabled, returns None without creating file."""
        with patch.dict("os.environ", {"QUOTE_CARD_ENABLED": "false"}):
            gen = QuoteCardGenerator()
            output = tmp_path / "test.png"
            result = gen.generate_quote_card("Test", 30, str(output))
            assert result is None
            assert not output.exists()

    def test_long_quote_wraps(self, tmp_path):
        """Long quotes are word-wrapped without error."""
        gen = QuoteCardGenerator()
        output = tmp_path / "long_quote.png"
        long_quote = "This is a very long quote that should be word wrapped across multiple lines to fit within the card dimensions properly"
        result = gen.generate_quote_card(long_quote, 30, str(output))
        assert result is not None
        assert result.exists()

    def test_creates_parent_dirs(self, tmp_path):
        """Creates parent directories if they don't exist."""
        gen = QuoteCardGenerator()
        output = tmp_path / "nested" / "dir" / "quote.png"
        result = gen.generate_quote_card("Test", 30, str(output))
        assert result is not None
        assert result.exists()


class TestGenerateAllQuoteCards:
    """Tests for batch quote card generation."""

    def test_generates_all_quotes(self, tmp_path):
        """Generates one card per quote."""
        gen = QuoteCardGenerator()
        paths = gen.generate_all_quote_cards(SAMPLE_ANALYSIS, 30, str(tmp_path))
        assert len(paths) == 3
        for p in paths:
            assert p.exists()

    def test_empty_quotes_returns_empty(self, tmp_path):
        """No best_quotes returns empty list."""
        gen = QuoteCardGenerator()
        paths = gen.generate_all_quote_cards({}, 30, str(tmp_path))
        assert paths == []

    def test_disabled_returns_empty(self, tmp_path):
        """When disabled, returns empty list."""
        with patch.dict("os.environ", {"QUOTE_CARD_ENABLED": "false"}):
            gen = QuoteCardGenerator()
            paths = gen.generate_all_quote_cards(SAMPLE_ANALYSIS, 30, str(tmp_path))
            assert paths == []

    def test_caps_at_five(self, tmp_path):
        """Maximum 5 quote cards generated."""
        analysis = {
            "best_quotes": [
                {
                    "quote": f"Quote number {i}",
                    "timestamp": "00:00:00",
                    "speaker_context": "host",
                }
                for i in range(8)
            ]
        }
        gen = QuoteCardGenerator()
        paths = gen.generate_all_quote_cards(analysis, 30, str(tmp_path))
        assert len(paths) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
