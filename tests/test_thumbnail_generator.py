"""Tests for thumbnail_generator module."""

import sys
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# PIL may not be installed in the test environment.  We pre-inject mocks for
# all PIL sub-modules so that ``thumbnail_generator`` can be imported even
# when Pillow is absent.
# ---------------------------------------------------------------------------
try:
    import PIL  # noqa: F401
except ImportError:
    _pil_mock = MagicMock()
    sys.modules.setdefault("PIL", _pil_mock)
    sys.modules.setdefault("PIL.Image", _pil_mock.Image)
    sys.modules.setdefault("PIL.ImageDraw", _pil_mock.ImageDraw)
    sys.modules.setdefault("PIL.ImageFont", _pil_mock.ImageFont)

from thumbnail_generator import ThumbnailGenerator  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Remove thumbnail-related env vars so each test starts from defaults."""
    for key in (
        "THUMBNAIL_FONT",
        "THUMBNAIL_BG_COLOR",
        "THUMBNAIL_TEXT_COLOR",
        "THUMBNAIL_BADGE_COLOR",
    ):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def pil_mocks():
    """Provide fresh PIL mocks for each test.

    ``from PIL import Image`` inside the production code resolves to
    ``sys.modules["PIL"].Image``.  We temporarily replace those
    attributes with fresh MagicMock objects so that each test gets
    isolated mocks.

    When the full suite runs with --cov, the real PIL may already be in
    sys.modules without ImageDraw/ImageFont as direct attributes.  We
    use getattr with a sentinel so we can safely restore the original
    state afterward.
    """
    mock_image_mod = MagicMock()
    mock_draw_mod = MagicMock()
    mock_font_mod = MagicMock()

    pil = sys.modules["PIL"]
    _sentinel = object()
    orig_image = getattr(pil, "Image", _sentinel)
    orig_draw = getattr(pil, "ImageDraw", _sentinel)
    orig_font = getattr(pil, "ImageFont", _sentinel)

    pil.Image = mock_image_mod
    pil.ImageDraw = mock_draw_mod
    pil.ImageFont = mock_font_mod

    yield {
        "Image": mock_image_mod,
        "ImageDraw": mock_draw_mod,
        "ImageFont": mock_font_mod,
    }

    for attr, orig in [
        ("Image", orig_image),
        ("ImageDraw", orig_draw),
        ("ImageFont", orig_font),
    ]:
        if orig is _sentinel:
            delattr(pil, attr)
        else:
            setattr(pil, attr, orig)


# ---------------------------------------------------------------------------
# 1. test_init_defaults
# ---------------------------------------------------------------------------
class TestInitDefaults:
    def test_default_colors_and_dimensions(self):
        gen = ThumbnailGenerator()
        assert gen.bg_color == "#1a1a2e"
        assert gen.text_color == "#ffffff"
        assert gen.badge_color == "#e94560"
        assert gen.width == 1280
        assert gen.height == 720
        assert gen.font_path is None
        assert gen.logo_path.name == "podcast_logo.png"


# ---------------------------------------------------------------------------
# 2. test_init_custom_env
# ---------------------------------------------------------------------------
class TestInitCustomEnv:
    def test_env_overrides(self, monkeypatch):
        monkeypatch.setenv("THUMBNAIL_FONT", "/usr/share/fonts/custom.ttf")
        monkeypatch.setenv("THUMBNAIL_BG_COLOR", "#000000")
        monkeypatch.setenv("THUMBNAIL_TEXT_COLOR", "#ff0000")
        monkeypatch.setenv("THUMBNAIL_BADGE_COLOR", "#00ff00")

        gen = ThumbnailGenerator()
        assert gen.font_path == "/usr/share/fonts/custom.ttf"
        assert gen.bg_color == "#000000"
        assert gen.text_color == "#ff0000"
        assert gen.badge_color == "#00ff00"


# ---------------------------------------------------------------------------
# 3. test_generate_thumbnail_success
# ---------------------------------------------------------------------------
class TestGenerateThumbnailSuccess:
    @patch.object(ThumbnailGenerator, "_add_episode_badge")
    @patch.object(ThumbnailGenerator, "_overlay_title_text")
    @patch.object(ThumbnailGenerator, "_create_background")
    def test_returns_output_path(self, mock_bg, mock_text, mock_badge, tmp_path):
        mock_image = MagicMock()
        mock_bg.return_value = mock_image
        mock_text.return_value = mock_image
        mock_badge.return_value = mock_image

        out = tmp_path / "thumb.png"
        gen = ThumbnailGenerator()
        result = gen.generate_thumbnail("Test Title", 25, str(out))

        assert result == out
        mock_bg.assert_called_once_with(1280, 720)
        mock_text.assert_called_once_with(mock_image, "Test Title")
        mock_badge.assert_called_once_with(mock_image, 25)
        mock_image.save.assert_called_once_with(str(out), "PNG")


# ---------------------------------------------------------------------------
# 4. test_generate_thumbnail_returns_none_on_error
# ---------------------------------------------------------------------------
class TestGenerateThumbnailError:
    @patch.object(
        ThumbnailGenerator, "_create_background", side_effect=RuntimeError("boom")
    )
    def test_returns_none_on_error(self, _mock_bg, tmp_path):
        gen = ThumbnailGenerator()
        result = gen.generate_thumbnail("Title", 1, str(tmp_path / "fail.png"))
        assert result is None


# ---------------------------------------------------------------------------
# 5. test_create_background_with_logo
# ---------------------------------------------------------------------------
class TestCreateBackgroundWithLogo:
    def test_loads_and_resizes_logo(self, tmp_path, pil_mocks):
        gen = ThumbnailGenerator()
        gen.logo_path = tmp_path / "podcast_logo.png"
        gen.logo_path.write_bytes(b"\x89PNG")  # minimal placeholder

        MockImage = pil_mocks["Image"]
        mock_logo = MagicMock()
        mock_resized = MagicMock()
        mock_logo.resize.return_value = mock_resized
        mock_converted = MagicMock()
        mock_resized.convert.return_value = mock_converted
        MockImage.open.return_value = mock_logo

        result = gen._create_background(1280, 720)

        MockImage.open.assert_called_once_with(str(gen.logo_path))
        mock_logo.resize.assert_called_once_with((1280, 720))
        mock_resized.convert.assert_called_once_with("RGBA")
        assert result is mock_converted


# ---------------------------------------------------------------------------
# 6. test_create_background_fallback_no_logo
# ---------------------------------------------------------------------------
class TestCreateBackgroundFallback:
    def test_solid_color_when_logo_missing(self, tmp_path, pil_mocks):
        gen = ThumbnailGenerator()
        gen.logo_path = tmp_path / "nonexistent.png"  # does not exist

        MockImage = pil_mocks["Image"]
        mock_image = MagicMock()
        MockImage.new.return_value = mock_image

        result = gen._create_background(1280, 720)

        MockImage.new.assert_called_once_with("RGBA", (1280, 720), gen.bg_color)
        assert result is mock_image


# ---------------------------------------------------------------------------
# 7. test_overlay_title_text_called
# ---------------------------------------------------------------------------
class TestOverlayTitleText:
    def test_draw_text_called(self, pil_mocks):
        gen = ThumbnailGenerator()

        mock_image = MagicMock()
        mock_image.width = 1280
        mock_image.height = 720

        mock_draw = MagicMock()
        # textbbox returns (left, top, right, bottom)
        mock_draw.textbbox.return_value = (0, 0, 200, 40)

        mock_font = MagicMock()

        pil_mocks["ImageDraw"].Draw.return_value = mock_draw
        pil_mocks["ImageFont"].load_default.return_value = mock_font

        result = gen._overlay_title_text(mock_image, "Short Title")

        pil_mocks["ImageDraw"].Draw.assert_called_once_with(mock_image)
        # At least the shadow + main text for a single line
        assert mock_draw.text.call_count >= 2
        assert result is mock_image


# ---------------------------------------------------------------------------
# 8. test_add_episode_badge
# ---------------------------------------------------------------------------
class TestAddEpisodeBadge:
    def test_badge_contains_episode_number(self, pil_mocks):
        gen = ThumbnailGenerator()

        mock_image = MagicMock()
        mock_image.width = 1280
        mock_image.height = 720

        mock_draw = MagicMock()
        mock_draw.textbbox.return_value = (0, 0, 80, 30)

        mock_font = MagicMock()

        pil_mocks["ImageDraw"].Draw.return_value = mock_draw
        pil_mocks["ImageFont"].load_default.return_value = mock_font

        result = gen._add_episode_badge(mock_image, 42)

        # The badge text should include "EP 42"
        text_calls = mock_draw.text.call_args_list
        badge_texts = [c for c in text_calls if "EP 42" in str(c)]
        assert len(badge_texts) >= 1
        assert result is mock_image


# ---------------------------------------------------------------------------
# 9. test_generate_thumbnail_dimensions
# ---------------------------------------------------------------------------
class TestGenerateThumbnailDimensions:
    @patch.object(ThumbnailGenerator, "_add_episode_badge")
    @patch.object(ThumbnailGenerator, "_overlay_title_text")
    @patch.object(ThumbnailGenerator, "_create_background")
    def test_creates_1280x720(self, mock_bg, mock_text, mock_badge, tmp_path):
        mock_image = MagicMock()
        mock_bg.return_value = mock_image
        mock_text.return_value = mock_image
        mock_badge.return_value = mock_image

        gen = ThumbnailGenerator()
        gen.generate_thumbnail("Title", 1, str(tmp_path / "t.png"))

        mock_bg.assert_called_once_with(1280, 720)


# ---------------------------------------------------------------------------
# 10. test_word_wrap_long_title
# ---------------------------------------------------------------------------
class TestWordWrapLongTitle:
    def test_long_title_produces_multiple_lines(self, pil_mocks):
        gen = ThumbnailGenerator()

        mock_image = MagicMock()
        mock_image.width = 1280
        mock_image.height = 720

        mock_draw = MagicMock()
        mock_font = MagicMock()

        # Simulate textbbox so that every word has width 200 and the max
        # wrapping width is 1280 - 160 = 1120.  Six words at 200px each
        # (1200) exceed 1120, so the title MUST wrap across multiple lines.
        def fake_textbbox(_pos, text, font=None):
            word_count = len(text.split())
            width = word_count * 200
            return (0, 0, width, 40)

        mock_draw.textbbox.side_effect = fake_textbbox

        pil_mocks["ImageDraw"].Draw.return_value = mock_draw
        pil_mocks["ImageFont"].load_default.return_value = mock_font

        title = "One Two Three Four Five Six Seven Eight"
        gen._overlay_title_text(mock_image, title)

        # Each draw.text call writes one line twice (shadow + main text),
        # so total calls = 2 * number_of_lines.  With 8 words at 200px each
        # and max_width 1120, we expect at least 2 lines => >= 4 draw.text calls.
        assert mock_draw.text.call_count >= 4
