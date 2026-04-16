"""Google Drive folder uploader for outreach demo packages.

Creates a per-prospect folder, uploads curated demo assets (clips, blog post,
quote cards, episode video), marks the folder "anyone with link: viewer", and
returns a shareable URL suitable for pasting into an outreach email.

Scope: drive.file — least-privilege. We can only read/write files this app
created. No risk of touching unrelated Drive content.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from config import Config
from logger import logger

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
]

FOLDER_MIMETYPE = "application/vnd.google-apps.folder"


class DriveUploader:
    """Upload folders to Google Drive and return shareable links."""

    TOKEN_PATH = Config.BASE_DIR / "credentials" / "google_outreach_token.json"

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
                logger.info("Drive token refreshed")
            except Exception as e:
                logger.warning("Drive token refresh failed: %s", e)
                creds = None

        if not creds or not creds.valid:
            raise FileNotFoundError(
                f"Drive token not found or invalid: {self.TOKEN_PATH}\n"
                "Run: uv run python setup_google_outreach.py"
            )

        self.service = build("drive", "v3", credentials=creds)

    def create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        body: dict = {"name": name, "mimeType": FOLDER_MIMETYPE}
        if parent_id:
            body["parents"] = [parent_id]
        result = self.service.files().create(body=body, fields="id").execute()
        fid = result["id"]
        logger.info("Drive folder created: %s (%s)", name, fid)
        return fid

    def upload_file(self, local_path: Path, folder_id: str) -> str:
        local_path = Path(local_path)
        if not local_path.exists():
            raise FileNotFoundError(local_path)
        media = MediaFileUpload(str(local_path), resumable=False)
        body = {"name": local_path.name, "parents": [folder_id]}
        result = (
            self.service.files()
            .create(body=body, media_body=media, fields="id")
            .execute()
        )
        fid = result["id"]
        logger.info("Uploaded %s -> %s", local_path.name, fid)
        return fid

    def make_shareable(self, file_or_folder_id: str) -> str:
        """Set 'anyone with link: viewer' and return the webViewLink."""
        self.service.permissions().create(
            fileId=file_or_folder_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()
        result = (
            self.service.files()
            .get(fileId=file_or_folder_id, fields="webViewLink")
            .execute()
        )
        return result["webViewLink"]

    def upload_folder(
        self,
        local_dir: Path,
        folder_name: str,
        parent_id: Optional[str] = None,
    ) -> str:
        """Upload `local_dir` as a Drive folder named `folder_name`.

        Recurses into subfolders. Returns the shareable webViewLink of the
        newly-created top-level folder.
        """
        local_dir = Path(local_dir)
        root_id = self.create_folder(folder_name, parent_id=parent_id)
        self._upload_contents(local_dir, root_id)
        return self.make_shareable(root_id)

    def _upload_contents(self, local_dir: Path, drive_folder_id: str) -> None:
        for entry in sorted(local_dir.iterdir()):
            if entry.is_dir():
                sub_id = self.create_folder(entry.name, parent_id=drive_folder_id)
                self._upload_contents(entry, sub_id)
            elif entry.is_file():
                self.upload_file(entry, folder_id=drive_folder_id)
