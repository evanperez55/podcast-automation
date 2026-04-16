"""One-time OAuth setup for Gmail + Drive outreach automation.

Reuses the existing Google Cloud OAuth client from credentials/google_docs_
credentials.json but requests broader scopes (gmail.compose + drive.file)
and saves the resulting token at credentials/google_outreach_token.json.

Run this ONCE per machine. Token auto-refreshes indefinitely so long as
the OAuth app is Published in Cloud Console (see B010 in MEMORY.md).

Usage:
    uv run python setup_google_outreach.py
"""

from __future__ import annotations

import sys

from google_auth_oauthlib.flow import InstalledAppFlow

from config import Config

SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/drive.file",
]

CREDENTIALS_PATH = Config.BASE_DIR / "credentials" / "google_docs_credentials.json"
TOKEN_PATH = Config.BASE_DIR / "credentials" / "google_outreach_token.json"


def main() -> int:
    if not CREDENTIALS_PATH.exists():
        print(f"[ERROR] OAuth client file not found: {CREDENTIALS_PATH}")
        print()
        print("Create or reuse an OAuth 2.0 Desktop client in Google Cloud Console,")
        print(f"download it, and save as {CREDENTIALS_PATH}")
        return 1

    print("=" * 60)
    print("OUTREACH OAUTH SETUP — Gmail compose + Drive file scopes")
    print("=" * 60)
    print()
    print("Required Google Cloud Console prerequisites:")
    print("  1. Gmail API enabled in the same project")
    print("  2. Google Drive API enabled in the same project")
    print("  3. OAuth consent screen status: Published (not Testing)")
    print()
    print("A browser window will open. Authorize the requested scopes:")
    for s in SCOPES:
        print(f"  - {s}")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(port=0)

    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

    print()
    print(f"[OK] Token saved: {TOKEN_PATH}")
    print()
    print("Smoke test your setup:")
    print("  uv run python -c \"from gmail_sender import GmailSender; GmailSender()\"")
    print("  uv run python -c \"from drive_uploader import DriveUploader; DriveUploader()\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
