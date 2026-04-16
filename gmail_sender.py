"""Gmail draft creator for outreach emails.

Intentionally NEVER sends — only drafts. The user reviews each draft in the
Gmail UI and hits send manually. This is the safety boundary for cold
outreach: a bad merge-field caught in 1 draft is fine, caught in 10 sent
emails is a reputation hit.
"""

from __future__ import annotations

import base64
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import Config
from logger import logger

SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
]


class GmailSender:
    """Create Gmail drafts via the Gmail API. Drafts only — never sends."""

    TOKEN_PATH = Config.BASE_DIR / "credentials" / "google_outreach_token.json"
    CREDENTIALS_PATH = (
        Config.BASE_DIR / "credentials" / "google_docs_credentials.json"
    )

    def __init__(self) -> None:
        self.service = None
        self._authenticate()

    def _authenticate(self) -> None:
        creds: Optional[Credentials] = None

        if self.TOKEN_PATH.exists():
            creds = Credentials.from_authorized_user_file(str(self.TOKEN_PATH), SCOPES)

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("Gmail token refreshed")
            except Exception as e:
                logger.warning("Gmail token refresh failed: %s", e)
                creds = None

        if not creds or not creds.valid:
            raise FileNotFoundError(
                f"Gmail/Drive outreach token not found or invalid: {self.TOKEN_PATH}\n"
                "Run: uv run python setup_google_outreach.py"
            )

        self.service = build("gmail", "v1", credentials=creds)

    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        dry_run: bool = False,
    ) -> Optional[str]:
        """Create a Gmail draft and return its id. `dry_run` skips the API call."""
        if dry_run:
            logger.info("[DRY RUN] Would create Gmail draft to %s: %s", to, subject)
            return "DRY_RUN"

        message = MIMEText(body, "plain", "utf-8")
        message["To"] = to
        message["Subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        try:
            result = (
                self.service.users()
                .drafts()
                .create(userId="me", body={"message": {"raw": raw}})
                .execute()
            )
            draft_id = result.get("id")
            logger.info("Created Gmail draft %s to %s", draft_id, to)
            return draft_id
        except HttpError as e:
            logger.error("Gmail draft creation failed for %s: %s", to, e)
            return None
