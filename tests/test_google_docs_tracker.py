"""Tests for google_docs_tracker credential path configuration."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

from config import Config

# Ensure google_docs_tracker is imported fresh (no stale module cache)
if "google_docs_tracker" in sys.modules:
    del sys.modules["google_docs_tracker"]

import google_docs_tracker  # noqa: E402
from google_docs_tracker import GoogleDocsTopicTracker  # noqa: E402


class TestCredentialPaths:
    """Verify credential paths resolve to the credentials/ directory."""

    def test_creds_path_in_credentials_dir(self):
        """creds_path must be anchored under Config.BASE_DIR / credentials/."""
        expected = Config.BASE_DIR / "credentials" / "google_docs_credentials.json"

        mock_flow = MagicMock()
        mock_flow.run_local_server.return_value = MagicMock(to_json=lambda: "{}")

        original_exists = Path.exists

        def fake_exists(self_path):
            if self_path.name == "google_docs_token.json":
                return False
            if self_path.name == "google_docs_credentials.json":
                return True
            return original_exists(self_path)

        with (
            patch.object(google_docs_tracker, "Credentials") as mock_creds_cls,
            patch.object(google_docs_tracker, "InstalledAppFlow") as mock_flow_cls,
            patch.object(google_docs_tracker, "build") as mock_build,
            patch.object(google_docs_tracker, "Ollama"),
            patch("builtins.open", mock_open()),
            patch.object(Path, "exists", fake_exists),
        ):
            # Token path does not exist — force the creds_path branch
            mock_creds_cls.from_authorized_user_file.side_effect = FileNotFoundError
            mock_flow_cls.from_client_secrets_file.return_value = mock_flow
            mock_build.return_value = MagicMock()

            tracker = GoogleDocsTopicTracker.__new__(GoogleDocsTopicTracker)
            tracker.creds = None
            tracker.service = None
            tracker.ollama_client = MagicMock()
            tracker.doc_id = "test-doc-id"
            tracker._authenticate()

        # Verify InstalledAppFlow.from_client_secrets_file received credentials/ path
        call_args = mock_flow_cls.from_client_secrets_file.call_args
        actual_path = Path(call_args[0][0])
        assert actual_path == expected, (
            f"creds_path should be {expected}, got {actual_path}"
        )

    def test_token_path_in_credentials_dir(self):
        """token_path must be anchored under Config.BASE_DIR / credentials/."""
        expected_token = Config.BASE_DIR / "credentials" / "google_docs_token.json"

        original_exists = Path.exists

        def fake_exists_token(self_path):
            if self_path.name == "google_docs_token.json":
                return True
            return original_exists(self_path)

        with (
            patch.object(google_docs_tracker, "Credentials") as mock_creds_cls,
            patch.object(google_docs_tracker, "InstalledAppFlow"),
            patch.object(google_docs_tracker, "build") as mock_build,
            patch.object(google_docs_tracker, "Ollama"),
            patch.object(Path, "exists", fake_exists_token),
        ):
            # Token file exists and creds are valid
            mock_creds_cls.from_authorized_user_file.return_value = MagicMock(
                valid=True, expired=False
            )
            mock_build.return_value = MagicMock()

            tracker = GoogleDocsTopicTracker.__new__(GoogleDocsTopicTracker)
            tracker.creds = None
            tracker.service = None
            tracker.ollama_client = MagicMock()
            tracker.doc_id = "test-doc-id"
            tracker._authenticate()

        # Verify Credentials.from_authorized_user_file received credentials/ token path
        call_args = mock_creds_cls.from_authorized_user_file.call_args
        actual_path = Path(call_args[0][0])
        assert actual_path == expected_token, (
            f"token_path should be {expected_token}, got {actual_path}"
        )
