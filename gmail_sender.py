"""Gmail draft creator for outreach emails.

Intentionally NEVER sends — only drafts. The user reviews each draft in the
Gmail UI and hits send manually. This is the safety boundary for cold
outreach: a bad merge-field caught in 1 draft is fine, caught in 10 sent
emails is a reputation hit.
"""

from __future__ import annotations

import base64
import html as html_lib
import re
from email.mime.text import MIMEText
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import Config
from logger import logger

SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    # Needed to fetch the user's real Gmail signature via sendAs.list() so
    # API-created drafts don't lose it (Gmail UI only auto-inserts on compose,
    # not on drafts built via the API).
    "https://www.googleapis.com/auth/gmail.settings.basic",
]


def _html_to_plain(s: str) -> str:
    """Flatten a Gmail signature's HTML into plain text.

    Gmail stores signatures as HTML even if the user never opened the
    HTML editor. Drafts here are plain-text MIMEText, so we strip tags,
    convert <br> to newlines, and unescape entities.
    """
    if not s:
        return ""
    # Collapse raw whitespace (including newlines from HTML source formatting)
    # BEFORE we introduce our own newlines — otherwise leading-whitespace in
    # indented HTML leaks through and the output fragments lines that were
    # meant to flow inline inside a <td>.
    s = re.sub(r"\s+", " ", s)
    # Row-level + paragraph tags → newline (each starts a new visual line)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.IGNORECASE)
    s = re.sub(
        r"</?(p|div|tr|table|li|ul|ol|h[1-6])[^>]*>",
        "\n",
        s,
        flags=re.IGNORECASE,
    )
    # Cells on the same row should flow inline — signatures often use
    # <tr><td>neurovai.org</td><td>|</td><td>LinkedIn</td></tr> layouts.
    s = re.sub(r"</?td[^>]*>", " ", s, flags=re.IGNORECASE)
    # Drop all remaining tags, then decode entities
    s = re.sub(r"<[^>]+>", "", s)
    s = html_lib.unescape(s)
    # Final per-line cleanup
    lines = [re.sub(r" +", " ", ln).strip() for ln in s.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)


class GmailSender:
    """Create Gmail drafts via the Gmail API. Drafts only — never sends."""

    TOKEN_PATH = Config.BASE_DIR / "credentials" / "google_outreach_token.json"
    CREDENTIALS_PATH = Config.BASE_DIR / "credentials" / "google_docs_credentials.json"

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

    def get_signature(self) -> str:
        """Return the user's default Gmail signature as plain text.

        Returns empty string (not None) on any failure — missing scope,
        missing signature, no default alias — so callers can treat it as
        optional without None-checks.
        """
        try:
            result = (
                self.service.users().settings().sendAs().list(userId="me").execute()
            )
        except HttpError as e:
            logger.warning("Could not fetch Gmail signature: %s", e)
            return ""

        aliases = result.get("sendAs", [])
        default = next((a for a in aliases if a.get("isDefault")), None)
        if not default:
            return ""
        return _html_to_plain(default.get("signature", ""))

    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        dry_run: bool = False,
        include_signature: bool = False,
    ) -> Optional[str]:
        """Create a Gmail draft and return its id. `dry_run` skips the API call.

        If `include_signature` is True, the user's default Gmail signature is
        fetched and appended to the body (separated by a blank line).
        """
        if dry_run:
            logger.info("[DRY RUN] Would create Gmail draft to %s: %s", to, subject)
            return "DRY_RUN"

        if include_signature:
            sig = self.get_signature()
            if sig:
                body = f"{body.rstrip()}\n\n{sig}"

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
