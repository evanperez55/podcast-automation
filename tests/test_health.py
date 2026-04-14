"""Tests for pipeline/health.py — credential health-check CLI command."""

from __future__ import annotations

import pickle

import pytest

from pipeline.health import health_check


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeCreds:
    """Stand-in for a Google OAuth creds object."""

    def __init__(self, expired=False, refresh_token=None):
        self.expired = expired
        self.refresh_token = refresh_token


@pytest.fixture
def empty_config(monkeypatch):
    """Strip all credential fields off Config so tests start clean."""
    from config import Config

    for attr in [
        "TWITTER_API_KEY",
        "TWITTER_API_SECRET",
        "TWITTER_ACCESS_TOKEN",
        "TWITTER_ACCESS_SECRET",
        "BLUESKY_HANDLE",
        "BLUESKY_APP_PASSWORD",
        "DISCORD_WEBHOOK_URL",
        "DROPBOX_REFRESH_TOKEN",
        "OPENAI_API_KEY",
    ]:
        monkeypatch.setattr(Config, attr, None, raising=False)
    return Config


@pytest.fixture
def fake_yt_token(tmp_path, monkeypatch):
    """Point Config.BASE_DIR at tmp_path and write a YouTube pickle token."""
    from config import Config

    monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
    creds_dir = tmp_path / "credentials"
    creds_dir.mkdir()
    return creds_dir / "youtube_token.pickle"


# ---------------------------------------------------------------------------
# YouTube token handling
# ---------------------------------------------------------------------------


class TestYouTubeToken:
    def test_missing_token_file(self, empty_config, fake_yt_token, capsys):
        """No youtube_token.pickle → MISSING status."""
        assert not fake_yt_token.exists()
        health_check()
        out = capsys.readouterr().out
        assert "YouTube" in out
        assert "MISSING" in out

    def test_valid_token(self, empty_config, fake_yt_token, capsys):
        """Valid, non-expired pickle → OK."""
        with fake_yt_token.open("wb") as f:
            pickle.dump(_FakeCreds(expired=False), f)
        health_check()
        out = capsys.readouterr().out
        assert "Token loaded successfully" in out

    def test_expired_token_with_refresh_token(
        self, empty_config, fake_yt_token, capsys
    ):
        """Expired but has refresh_token → OK (can refresh)."""
        with fake_yt_token.open("wb") as f:
            pickle.dump(_FakeCreds(expired=True, refresh_token="xyz"), f)
        health_check()
        out = capsys.readouterr().out
        assert "refresh token available" in out

    def test_expired_token_without_refresh_token(
        self, empty_config, fake_yt_token, capsys
    ):
        """Expired with no refresh_token → ERROR."""
        with fake_yt_token.open("wb") as f:
            pickle.dump(_FakeCreds(expired=True, refresh_token=None), f)
        health_check()
        out = capsys.readouterr().out
        assert "ERROR" in out
        assert "no refresh token" in out

    def test_corrupt_token_file(self, empty_config, fake_yt_token, capsys):
        """Corrupt pickle → ERROR with 'Cannot load token' message."""
        fake_yt_token.write_bytes(b"not a valid pickle")
        health_check()
        out = capsys.readouterr().out
        assert "Cannot load token" in out


# ---------------------------------------------------------------------------
# Credential env vars — Twitter, Bluesky, Discord, Dropbox, OpenAI
# ---------------------------------------------------------------------------


class TestTwitterCredentials:
    def test_all_four_keys_present(self, empty_config, capsys, monkeypatch):
        for k in [
            "TWITTER_API_KEY",
            "TWITTER_API_SECRET",
            "TWITTER_ACCESS_TOKEN",
            "TWITTER_ACCESS_SECRET",
        ]:
            monkeypatch.setattr(empty_config, k, "value")
        health_check()
        out = capsys.readouterr().out
        # Twitter row should show OK
        for line in out.splitlines():
            if line.startswith("Twitter"):
                assert "OK" in line

    def test_partial_twitter_keys(self, empty_config, capsys, monkeypatch):
        monkeypatch.setattr(empty_config, "TWITTER_API_KEY", "value")
        # Leave the other 3 None
        health_check()
        out = capsys.readouterr().out
        for line in out.splitlines():
            if line.startswith("Twitter"):
                assert "MISSING" in line
                # The 3 missing keys should be listed
                assert "TWITTER_API_SECRET" in line
                assert "TWITTER_ACCESS_TOKEN" in line
                assert "TWITTER_ACCESS_SECRET" in line


class TestOtherCredentials:
    def test_bluesky_both_present(self, empty_config, capsys, monkeypatch):
        monkeypatch.setattr(empty_config, "BLUESKY_HANDLE", "handle")
        monkeypatch.setattr(empty_config, "BLUESKY_APP_PASSWORD", "pw")
        health_check()
        out = capsys.readouterr().out
        for line in out.splitlines():
            if line.startswith("Bluesky"):
                assert "OK" in line

    def test_bluesky_missing_password(self, empty_config, capsys, monkeypatch):
        monkeypatch.setattr(empty_config, "BLUESKY_HANDLE", "handle")
        health_check()
        out = capsys.readouterr().out
        for line in out.splitlines():
            if line.startswith("Bluesky"):
                assert "MISSING" in line
                assert "BLUESKY_APP_PASSWORD" in line

    def test_discord_configured(self, empty_config, capsys, monkeypatch):
        monkeypatch.setattr(empty_config, "DISCORD_WEBHOOK_URL", "https://...")
        health_check()
        out = capsys.readouterr().out
        for line in out.splitlines():
            if line.startswith("Discord"):
                assert "OK" in line

    def test_discord_missing(self, empty_config, capsys):
        health_check()
        out = capsys.readouterr().out
        for line in out.splitlines():
            if line.startswith("Discord"):
                assert "MISSING" in line

    def test_dropbox_configured(self, empty_config, capsys, monkeypatch):
        monkeypatch.setattr(empty_config, "DROPBOX_REFRESH_TOKEN", "token")
        health_check()
        out = capsys.readouterr().out
        for line in out.splitlines():
            if line.startswith("Dropbox"):
                assert "OK" in line

    def test_openai_configured(self, empty_config, capsys, monkeypatch):
        monkeypatch.setattr(empty_config, "OPENAI_API_KEY", "sk-xxx")
        health_check()
        out = capsys.readouterr().out
        for line in out.splitlines():
            if line.startswith("OpenAI"):
                assert "OK" in line


# ---------------------------------------------------------------------------
# Output format
# ---------------------------------------------------------------------------


class TestOutputFormat:
    def test_prints_table_header(self, empty_config, capsys):
        health_check()
        out = capsys.readouterr().out
        assert "Platform" in out
        assert "Status" in out
        assert "Details" in out

    def test_all_platforms_appear_in_output(self, empty_config, capsys):
        health_check()
        out = capsys.readouterr().out
        for platform in [
            "YouTube",
            "Twitter",
            "Bluesky",
            "Discord",
            "Dropbox",
            "OpenAI",
        ]:
            assert platform in out, f"{platform} row missing from output"
