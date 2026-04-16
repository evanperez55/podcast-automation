"""Tests for gmail_sender.py — OAuth-backed Gmail draft creator.

The sender only creates DRAFTS, never sends automatically. The user reviews
drafts in Gmail and hits send themselves. This is the safety boundary for
cold outreach — one bad merge-field would otherwise go out to 10 prospects.
"""

from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestGmailSenderInit:
    """Initialization covers auth failure modes and token loading."""

    def test_missing_token_raises(self, tmp_path, monkeypatch):
        """No token file → clear error pointing at setup script."""
        monkeypatch.setattr(
            "gmail_sender.GmailSender.TOKEN_PATH", tmp_path / "nope.json"
        )
        monkeypatch.setattr(
            "gmail_sender.GmailSender.CREDENTIALS_PATH", tmp_path / "also-nope.json"
        )
        from gmail_sender import GmailSender

        with pytest.raises(FileNotFoundError, match="setup_google_outreach"):
            GmailSender()

    def test_valid_token_builds_service(self, tmp_path, monkeypatch):
        """Existing valid token → no OAuth flow, service is built."""
        token_path = tmp_path / "token.json"
        token_path.write_text("{}")  # content doesn't matter, Credentials is mocked
        monkeypatch.setattr("gmail_sender.GmailSender.TOKEN_PATH", token_path)

        fake_creds = MagicMock(valid=True, expired=False)
        fake_service = MagicMock()

        with (
            patch(
                "gmail_sender.Credentials.from_authorized_user_file",
                return_value=fake_creds,
            ),
            patch("gmail_sender.build", return_value=fake_service) as mock_build,
        ):
            from gmail_sender import GmailSender

            sender = GmailSender()

        mock_build.assert_called_once_with("gmail", "v1", credentials=fake_creds)
        assert sender.service is fake_service

    def test_expired_token_is_refreshed(self, tmp_path, monkeypatch):
        """Expired token with refresh_token → refresh, don't force re-auth."""
        token_path = tmp_path / "token.json"
        token_path.write_text("{}")
        monkeypatch.setattr("gmail_sender.GmailSender.TOKEN_PATH", token_path)

        fake_creds = MagicMock(
            valid=False, expired=True, refresh_token="refresh-abc"
        )
        # After refresh, treat as valid
        def refresh_side_effect(_request):
            fake_creds.valid = True
            fake_creds.expired = False

        fake_creds.refresh.side_effect = refresh_side_effect

        with (
            patch(
                "gmail_sender.Credentials.from_authorized_user_file",
                return_value=fake_creds,
            ),
            patch("gmail_sender.build", return_value=MagicMock()),
        ):
            from gmail_sender import GmailSender

            GmailSender()

        fake_creds.refresh.assert_called_once()


class TestCreateDraft:
    """create_draft() is the only public API. Everything else is plumbing."""

    @pytest.fixture
    def sender(self, tmp_path, monkeypatch):
        """Build a GmailSender with service mocked out, no real auth."""
        token_path = tmp_path / "token.json"
        token_path.write_text("{}")
        monkeypatch.setattr("gmail_sender.GmailSender.TOKEN_PATH", token_path)

        fake_creds = MagicMock(valid=True, expired=False)
        with (
            patch(
                "gmail_sender.Credentials.from_authorized_user_file",
                return_value=fake_creds,
            ),
            patch("gmail_sender.build"),
        ):
            from gmail_sender import GmailSender

            s = GmailSender()
        # Replace service with a controllable mock
        s.service = MagicMock()
        return s

    def test_creates_draft_with_given_fields(self, sender):
        """Subject, body, recipient all land in the draft payload."""
        sender.service.users().drafts().create().execute.return_value = {
            "id": "draft-123"
        }

        result = sender.create_draft(
            to="pastor@example.com",
            subject="Made these from your sermon",
            body="Hey pastor,\n\nHere is the demo.\n\n- Evan",
        )

        assert result == "draft-123"
        # The Gmail API expects a base64url-encoded RFC 2822 message. Decode the
        # outer envelope and parse the inner MIME so we see the actual body
        # (MIMEText with charset=utf-8 base64-encodes the payload by default).
        import email as _email_lib

        call_kwargs = sender.service.users().drafts().create.call_args_list[-1].kwargs
        raw = call_kwargs["body"]["message"]["raw"]
        decoded = base64.urlsafe_b64decode(raw).decode("utf-8")
        assert "To: pastor@example.com" in decoded
        assert "Subject: Made these from your sermon" in decoded
        parsed = _email_lib.message_from_string(decoded)
        body_text = parsed.get_payload(decode=True).decode("utf-8")
        assert "Here is the demo." in body_text

    def test_returns_none_on_api_error(self, sender):
        """HttpError from Gmail → log + return None, do not crash caller."""
        from googleapiclient.errors import HttpError

        resp = MagicMock(status=500, reason="Server Error")
        sender.service.users().drafts().create().execute.side_effect = HttpError(
            resp=resp, content=b'{"error": {"message": "boom"}}'
        )

        result = sender.create_draft(
            to="pastor@example.com", subject="Test", body="Hi"
        )
        assert result is None

    def test_dry_run_skips_api_call(self, sender):
        """dry_run=True logs intent but does not call the Gmail API."""
        result = sender.create_draft(
            to="pastor@example.com",
            subject="Test",
            body="Hi",
            dry_run=True,
        )
        assert result == "DRY_RUN"
        # None of the drafts chain should have been called with dry_run path
        sender.service.users().drafts().create().execute.assert_not_called()

    def test_plaintext_body_preserves_newlines(self, sender):
        """Email body newlines must survive encoding — pitches are multi-paragraph."""
        import email as _email_lib

        sender.service.users().drafts().create().execute.return_value = {
            "id": "draft-xyz"
        }

        body = "Paragraph one.\n\nParagraph two.\n\n- bullet 1\n- bullet 2"
        sender.create_draft(
            to="x@example.com", subject="Test", body=body
        )

        call_kwargs = sender.service.users().drafts().create.call_args_list[-1].kwargs
        raw = call_kwargs["body"]["message"]["raw"]
        decoded = base64.urlsafe_b64decode(raw).decode("utf-8")
        parsed = _email_lib.message_from_string(decoded)
        body_text = parsed.get_payload(decode=True).decode("utf-8")
        assert "Paragraph one." in body_text
        assert "Paragraph two." in body_text
        assert "- bullet 1" in body_text
        assert "\n\n" in body_text  # paragraph breaks survive
