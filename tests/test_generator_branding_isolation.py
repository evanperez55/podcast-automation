"""Contract test: every content-baking generator must hard-fail for a
non-default client that hasn't configured CLIENT_LOGO_PATH.

This is the regression guard for B021 (2026-04-22): five generators
silently fell back to the bundled Fake Problems logo when CLIENT_LOGO_PATH
was None, leaking FP branding into every non-default client's thumbnail
and clip backgrounds. The fix routed all five through
client_config.resolve_client_logo_or_raise.

If someone adds a new generator, forgets to use the helper, and ships a
new client logo-bearing module, THIS test fails. The list of expected
generators is maintained here — adding a new one requires touching this
file, which is the point.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# PIL gets pre-injected into sys.modules for environments without Pillow
# so the imports below resolve. (Same pattern as test_thumbnail_generator.)
try:
    import PIL  # noqa: F401
except ImportError:
    _pil_mock = MagicMock()
    sys.modules.setdefault("PIL", _pil_mock)
    sys.modules.setdefault("PIL.Image", _pil_mock.Image)
    sys.modules.setdefault("PIL.ImageDraw", _pil_mock.ImageDraw)
    sys.modules.setdefault("PIL.ImageFont", _pil_mock.ImageFont)

from config import Config  # noqa: E402

# (module_name, class_name) pairs for every generator that bakes a logo.
# Adding a new logo-bearing module? It MUST go in this list + MUST route
# through client_config.resolve_client_logo_or_raise.
LOGO_BEARING_GENERATORS = [
    ("thumbnail_generator", "ThumbnailGenerator"),
    ("subtitle_clip_generator", "SubtitleClipGenerator"),
    ("quote_card_generator", "QuoteCardGenerator"),
    ("audiogram_generator", "AudiogramGenerator"),
    # VideoConverter has a separate signature (accepts logo_path kwarg)
    # so it's covered by a dedicated test below rather than the generic
    # parametrize.
]


@pytest.fixture(autouse=True)
def _reset_client_flags(monkeypatch):
    """Always start each test with the default-client flag True so tests
    that don't set it explicitly don't inherit leakage from a prior test."""
    monkeypatch.setattr(Config, "IS_DEFAULT_CLIENT", True)
    monkeypatch.setattr(Config, "CLIENT_LOGO_PATH", None)


@pytest.mark.parametrize("module_name,class_name", LOGO_BEARING_GENERATORS)
def test_generator_raises_for_non_default_client_without_logo(
    module_name, class_name, monkeypatch
):
    """Non-default client + no CLIENT_LOGO_PATH => ValueError at init.

    This is the exact scenario that shipped FP branding to 10 church
    prospects on 2026-04-22.
    """
    monkeypatch.setattr(Config, "IS_DEFAULT_CLIENT", False)
    monkeypatch.setattr(Config, "CLIENT_LOGO_PATH", None)
    monkeypatch.setattr(Config, "PODCAST_NAME", "Some Church Podcast")

    module = importlib.import_module(module_name)
    cls = getattr(module, class_name)

    with pytest.raises(ValueError, match="CLIENT_LOGO_PATH"):
        cls()


@pytest.mark.parametrize("module_name,class_name", LOGO_BEARING_GENERATORS)
def test_generator_raises_for_non_default_client_with_nonexistent_logo(
    module_name, class_name, monkeypatch, tmp_path
):
    """Non-default client + CLIENT_LOGO_PATH pointing at a missing file
    must raise — otherwise a stale or typo'd YAML path silently falls back."""
    monkeypatch.setattr(Config, "IS_DEFAULT_CLIENT", False)
    monkeypatch.setattr(Config, "CLIENT_LOGO_PATH", str(tmp_path / "nope.png"))
    monkeypatch.setattr(Config, "PODCAST_NAME", "Some Church Podcast")

    module = importlib.import_module(module_name)
    cls = getattr(module, class_name)

    with pytest.raises(ValueError, match="CLIENT_LOGO_PATH"):
        cls()


@pytest.mark.parametrize("module_name,class_name", LOGO_BEARING_GENERATORS)
def test_generator_uses_client_logo_when_configured(
    module_name, class_name, monkeypatch, tmp_path
):
    """Non-default client with a valid CLIENT_LOGO_PATH initializes fine
    and uses that path (not the bundled Fake Problems asset)."""
    logo = tmp_path / "client_logo.png"
    logo.write_bytes(b"\x89PNG\r\n\x1a\n")
    monkeypatch.setattr(Config, "IS_DEFAULT_CLIENT", False)
    monkeypatch.setattr(Config, "CLIENT_LOGO_PATH", str(logo))
    monkeypatch.setattr(Config, "PODCAST_NAME", "Some Church Podcast")

    module = importlib.import_module(module_name)
    cls = getattr(module, class_name)

    # Must instantiate without raising
    gen = cls()
    assert Path(gen.logo_path) == logo


def test_video_converter_raises_for_non_default_client_without_logo(monkeypatch):
    """VideoConverter has a separate signature (logo_path kwarg, jpg default)
    but must honor the same contract: non-default + no config => raise."""
    monkeypatch.setattr(Config, "IS_DEFAULT_CLIENT", False)
    monkeypatch.setattr(Config, "CLIENT_LOGO_PATH", None)
    monkeypatch.setattr(Config, "PODCAST_NAME", "Some Church Podcast")

    from video_converter import VideoConverter

    with pytest.raises(ValueError, match="CLIENT_LOGO_PATH"):
        VideoConverter()


def test_default_client_falls_back_to_bundled_logo(monkeypatch, tmp_path):
    """Default client (Fake Problems) with no CLIENT_LOGO_PATH override
    resolves to the bundled assets/podcast_logo.png — the intended behavior."""
    # Set up a fake bundled logo so the check `exists()` inside
    # resolve_client_logo_or_raise passes without touching the real asset.
    fake_assets = tmp_path / "assets"
    fake_assets.mkdir()
    bundled = fake_assets / "podcast_logo.png"
    bundled.write_bytes(b"\x89PNG\r\n\x1a\n")
    monkeypatch.setattr(Config, "ASSETS_DIR", fake_assets)
    monkeypatch.setattr(Config, "IS_DEFAULT_CLIENT", True)
    monkeypatch.setattr(Config, "CLIENT_LOGO_PATH", None)

    from thumbnail_generator import ThumbnailGenerator

    gen = ThumbnailGenerator()
    assert Path(gen.logo_path) == bundled


def test_generator_list_covers_every_consumer_of_helper():
    """Meta-check: every module calling resolve_client_logo_or_raise outside
    of tests must appear in LOGO_BEARING_GENERATORS (or be the VideoConverter
    which is covered separately). This is the single point that forces
    contributors to update the registry when adding a new generator."""
    project_root = Path(__file__).resolve().parent.parent
    helper_callers = set()
    for py in project_root.glob("*.py"):
        if py.name.startswith("test_"):
            continue
        text = py.read_text(encoding="utf-8")
        # Client-config itself defines the helper — exclude.
        if py.name == "client_config.py":
            continue
        if "resolve_client_logo_or_raise" in text:
            helper_callers.add(py.stem)

    registered_modules = {m for m, _ in LOGO_BEARING_GENERATORS}
    registered_modules.add("video_converter")  # covered by dedicated test
    missing = helper_callers - registered_modules
    assert not missing, (
        f"Modules {missing} call resolve_client_logo_or_raise but aren't in "
        f"LOGO_BEARING_GENERATORS or covered by the dedicated VideoConverter "
        f"test. Add them to tests/test_generator_branding_isolation.py."
    )
