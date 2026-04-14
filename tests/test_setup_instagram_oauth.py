"""Tests for scripts/setup_instagram_oauth.py — OAuth helper functions.

The main() flow is interactive (user pastes a browser callback URL) and
not fully testable without a real OAuth dance, but the pure token-exchange
helpers and the URL-argument parsing are testable in isolation.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from scripts import setup_instagram_oauth as sio


@pytest.fixture
def fake_creds(monkeypatch):
    """Set fake INSTAGRAM_APP_ID / INSTAGRAM_APP_SECRET at module level."""
    monkeypatch.setattr(sio, "INSTAGRAM_APP_ID", "fake_app_id")
    monkeypatch.setattr(sio, "INSTAGRAM_APP_SECRET", "fake_app_secret")


class TestExchangeCodeForToken:
    def test_returns_token_on_success(self, fake_creds):
        fake_resp = MagicMock(
            status_code=200,
            json=MagicMock(return_value={"access_token": "short_abc", "user_id": 123}),
        )
        with patch("requests.post", return_value=fake_resp) as mock_post:
            token = sio.exchange_code_for_token("auth_code_xyz")

        assert token == "short_abc"
        call_data = mock_post.call_args.kwargs["data"]
        assert call_data["client_id"] == "fake_app_id"
        assert call_data["client_secret"] == "fake_app_secret"
        assert call_data["grant_type"] == "authorization_code"
        assert call_data["code"] == "auth_code_xyz"

    def test_returns_none_on_http_error(self, fake_creds, capsys):
        fake_resp = MagicMock(status_code=400, text="Bad Request: invalid code")
        with patch("requests.post", return_value=fake_resp):
            token = sio.exchange_code_for_token("bad_code")

        assert token is None
        assert "Error" in capsys.readouterr().out


class TestExchangeForLongLivedToken:
    def test_returns_long_lived_token(self, fake_creds):
        fake_resp = MagicMock(
            status_code=200,
            json=MagicMock(
                return_value={"access_token": "long_xyz", "expires_in": 5184000}
            ),
        )
        with patch("requests.get", return_value=fake_resp) as mock_get:
            token = sio.exchange_for_long_lived_token("short_abc")

        assert token == "long_xyz"
        params = mock_get.call_args.kwargs["params"]
        assert params["grant_type"] == "ig_exchange_token"
        assert params["client_secret"] == "fake_app_secret"
        assert params["access_token"] == "short_abc"

    def test_prints_expiry_in_days(self, fake_creds, capsys):
        fake_resp = MagicMock(
            status_code=200,
            json=MagicMock(
                return_value={"access_token": "t", "expires_in": 60 * 86400}
            ),
        )
        with patch("requests.get", return_value=fake_resp):
            sio.exchange_for_long_lived_token("s")

        assert "60 days" in capsys.readouterr().out

    def test_returns_none_on_error(self, fake_creds, capsys):
        fake_resp = MagicMock(status_code=500, text="Server down")
        with patch("requests.get", return_value=fake_resp):
            token = sio.exchange_for_long_lived_token("short")

        assert token is None


class TestMainArgumentParsing:
    """main() accepts either a raw code or a full callback URL as argv[1]."""

    def test_missing_credentials_exits(self, monkeypatch, capsys):
        monkeypatch.setattr(sio, "INSTAGRAM_APP_ID", "")
        monkeypatch.setattr(sio, "INSTAGRAM_APP_SECRET", "")
        monkeypatch.setattr(sys, "argv", ["setup"])
        with pytest.raises(SystemExit) as exc:
            sio.main()
        assert exc.value.code == 1
        assert "INSTAGRAM_APP_ID" in capsys.readouterr().out

    def test_extracts_code_from_callback_url(self, fake_creds, monkeypatch):
        """Passing the raw browser callback URL should parse the ?code= param."""
        monkeypatch.setattr(
            sys,
            "argv",
            ["setup", "https://localhost:8888/callback?code=AUTHCODE123"],
        )
        with patch.object(sio, "exchange_code_for_token", return_value=None) as ex:
            with pytest.raises(SystemExit):  # sys.exit after token exchange fails
                sio.main()
        ex.assert_called_once_with("AUTHCODE123")

    def test_strips_trailing_hash_underscore_instagram_adds(
        self, fake_creds, monkeypatch
    ):
        """Instagram appends '#_' to the code — strip before exchanging."""
        monkeypatch.setattr(sys, "argv", ["setup", "AUTHCODE123#_"])
        with patch.object(sio, "exchange_code_for_token", return_value=None) as ex:
            with pytest.raises(SystemExit):
                sio.main()
        ex.assert_called_once_with("AUTHCODE123")

    def test_raw_code_argument_accepted(self, fake_creds, monkeypatch):
        """A bare auth code (no URL scheme) is used as-is."""
        monkeypatch.setattr(sys, "argv", ["setup", "BAREAUTHCODE"])
        with patch.object(sio, "exchange_code_for_token", return_value=None) as ex:
            with pytest.raises(SystemExit):
                sio.main()
        ex.assert_called_once_with("BAREAUTHCODE")
