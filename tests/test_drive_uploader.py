"""Tests for drive_uploader.py — Google Drive folder uploader for demo packages.

Uploads curated outreach assets (clips, blog post, quote cards, episode video)
to a per-prospect Drive folder and returns a shareable link suitable for
pasting into an outreach email.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestDriveUploaderInit:
    """Token/credential handling mirrors GmailSender's pattern."""

    def test_missing_token_raises_with_setup_hint(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "drive_uploader.DriveUploader.TOKEN_PATH", tmp_path / "nope.json"
        )
        from drive_uploader import DriveUploader

        with pytest.raises(FileNotFoundError, match="setup_google_outreach"):
            DriveUploader()


@pytest.fixture
def uploader(tmp_path, monkeypatch):
    """DriveUploader with auth + service fully mocked."""
    token_path = tmp_path / "token.json"
    token_path.write_text("{}")
    monkeypatch.setattr("drive_uploader.DriveUploader.TOKEN_PATH", token_path)

    fake_creds = MagicMock(valid=True, expired=False)
    with (
        patch(
            "drive_uploader.Credentials.from_authorized_user_file",
            return_value=fake_creds,
        ),
        patch("drive_uploader.build"),
    ):
        from drive_uploader import DriveUploader

        u = DriveUploader()
    u.service = MagicMock()
    return u


class TestCreateFolder:
    def test_creates_top_level_folder(self, uploader):
        uploader.service.files().create().execute.return_value = {"id": "fld-1"}

        fid = uploader.create_folder("Redeemer City Church - Demo")

        assert fid == "fld-1"
        call_kwargs = uploader.service.files().create.call_args_list[-1].kwargs
        assert call_kwargs["body"]["mimeType"] == "application/vnd.google-apps.folder"
        assert call_kwargs["body"]["name"] == "Redeemer City Church - Demo"
        # No parent → no "parents" key
        assert "parents" not in call_kwargs["body"]

    def test_creates_nested_folder(self, uploader):
        uploader.service.files().create().execute.return_value = {"id": "fld-2"}

        uploader.create_folder("Clips", parent_id="parent-fld")

        call_kwargs = uploader.service.files().create.call_args_list[-1].kwargs
        assert call_kwargs["body"]["parents"] == ["parent-fld"]


class TestUploadFile:
    def test_uploads_single_file_to_folder(self, uploader, tmp_path):
        f = tmp_path / "clip.mp4"
        f.write_bytes(b"fake mp4")

        uploader.service.files().create().execute.return_value = {"id": "f-1"}

        with patch("drive_uploader.MediaFileUpload") as mock_media:
            fid = uploader.upload_file(f, folder_id="fld-abc")

        assert fid == "f-1"
        mock_media.assert_called_once()
        call_kwargs = uploader.service.files().create.call_args_list[-1].kwargs
        assert call_kwargs["body"]["name"] == "clip.mp4"
        assert call_kwargs["body"]["parents"] == ["fld-abc"]

    def test_missing_local_file_raises(self, uploader, tmp_path):
        with pytest.raises(FileNotFoundError):
            uploader.upload_file(tmp_path / "does-not-exist.mp4", folder_id="x")


class TestMakeShareable:
    def test_makes_anyone_with_link_viewer_and_returns_url(self, uploader):
        uploader.service.files().get().execute.return_value = {
            "webViewLink": "https://drive.google.com/drive/folders/xyz"
        }

        url = uploader.make_shareable("fld-xyz")

        # Must set the "anyone with link" permission (the whole point of
        # pasting this into a cold email is that the prospect can open it).
        perm_calls = uploader.service.permissions().create.call_args_list
        assert len(perm_calls) >= 1
        body = perm_calls[-1].kwargs["body"]
        assert body["type"] == "anyone"
        assert body["role"] == "reader"
        assert url == "https://drive.google.com/drive/folders/xyz"


class TestUploadFolder:
    """End-to-end: one call uploads a local dir and returns a shareable link."""

    def test_uploads_all_files_and_returns_link(self, uploader, tmp_path):
        # Set up a local directory with a few assets
        src = tmp_path / "demo"
        src.mkdir()
        (src / "clip_01.mp4").write_bytes(b"a")
        (src / "blog.md").write_text("hello")
        subdir = src / "quote_cards"
        subdir.mkdir()
        (subdir / "card1.png").write_bytes(b"img")

        # Each service call returns a new fake id — use a counter
        id_counter = iter(["fld-root", "file-1", "file-2", "fld-sub", "file-3"])
        uploader.service.files().create().execute.side_effect = lambda: {
            "id": next(id_counter)
        }
        uploader.service.files().get().execute.return_value = {
            "webViewLink": "https://drive.google.com/drive/folders/fld-root"
        }

        with patch("drive_uploader.MediaFileUpload"):
            link = uploader.upload_folder(src, folder_name="Demo - Prospect X")

        assert link == "https://drive.google.com/drive/folders/fld-root"
        # 2 folders created (root + quote_cards) + 3 files = 5 create calls
        assert uploader.service.files().create.call_count >= 5

    def test_empty_folder_still_creates_and_returns_link(self, uploader, tmp_path):
        src = tmp_path / "empty"
        src.mkdir()
        uploader.service.files().create().execute.return_value = {"id": "fld-e"}
        uploader.service.files().get().execute.return_value = {
            "webViewLink": "https://drive.google.com/drive/folders/fld-e"
        }

        link = uploader.upload_folder(src, folder_name="Empty Demo")
        assert link.endswith("fld-e")
