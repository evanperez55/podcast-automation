"""Tests for google_docs_tracker credential path configuration."""

from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

from config import Config


class TestCredentialPaths:
    """Verify credential paths resolve to the credentials/ directory."""

    def test_creds_path_in_credentials_dir(self):
        """creds_path must be anchored under Config.BASE_DIR / credentials/."""
        expected = Config.BASE_DIR / "credentials" / "google_docs_credentials.json"

        with (
            patch("google_docs_tracker.Credentials") as mock_creds_cls,
            patch("google_docs_tracker.InstalledAppFlow") as mock_flow_cls,
            patch("google_docs_tracker.build") as mock_build,
            patch("google_docs_tracker.Ollama") as mock_ollama,
            patch("builtins.open", mock_open()),
        ):
            # Make the token file "not exist" so we go down the creds_path branch
            mock_creds_cls.from_authorized_user_file.side_effect = FileNotFoundError

            # Make the creds_path "not exist" — we just want to capture what path is used
            # We'll patch Path.exists to return False for token and True for creds_path
            # so the flow reaches InstalledAppFlow.from_client_secrets_file
            with patch("google_docs_tracker.Config") as mock_cfg:
                mock_cfg.GOOGLE_DOC_ID = "test-doc-id"
                mock_cfg.BASE_DIR = Config.BASE_DIR

                # Patch Path.exists: token_path returns False, creds_path returns True
                original_exists = Path.exists

                def fake_exists(self_path):
                    if self_path.name == "google_docs_token.json":
                        return False
                    if self_path.name == "google_docs_credentials.json":
                        return True
                    return original_exists(self_path)

                mock_flow = MagicMock()
                mock_flow.run_local_server.return_value = MagicMock(
                    to_json=lambda: "{}"
                )
                mock_flow_cls.from_client_secrets_file.return_value = mock_flow
                mock_build.return_value = MagicMock()
                mock_ollama.return_value = MagicMock()

                with patch.object(Path, "exists", fake_exists):
                    from google_docs_tracker import GoogleDocsTopicTracker

                    tracker = GoogleDocsTopicTracker.__new__(GoogleDocsTopicTracker)
                    # Call _authenticate to trigger path construction
                    # We patch Config inside the module to use our controlled BASE_DIR
                    tracker.creds = None
                    tracker.service = None
                    tracker.ollama_client = MagicMock()
                    tracker.doc_id = "test-doc-id"
                    tracker._authenticate()

        # Verify InstalledAppFlow.from_client_secrets_file was called with the credentials/ path
        call_args = mock_flow_cls.from_client_secrets_file.call_args
        actual_path = Path(call_args[0][0])
        assert actual_path == expected, (
            f"creds_path should be {expected}, got {actual_path}"
        )

    def test_token_path_in_credentials_dir(self):
        """token_path must be anchored under Config.BASE_DIR / credentials/."""
        expected_token = Config.BASE_DIR / "credentials" / "google_docs_token.json"

        with (
            patch("google_docs_tracker.Credentials") as mock_creds_cls,
            patch("google_docs_tracker.InstalledAppFlow"),
            patch("google_docs_tracker.build") as mock_build,
            patch("google_docs_tracker.Ollama") as mock_ollama,
        ):
            # Make token file "exist" so we load it
            mock_creds_cls.from_authorized_user_file.return_value = MagicMock(
                valid=True, expired=False
            )
            mock_build.return_value = MagicMock()
            mock_ollama.return_value = MagicMock()

            with patch("google_docs_tracker.Config") as mock_cfg:
                mock_cfg.GOOGLE_DOC_ID = "test-doc-id"
                mock_cfg.BASE_DIR = Config.BASE_DIR

                original_exists = Path.exists

                def fake_exists_token(self_path):
                    if self_path.name == "google_docs_token.json":
                        return True
                    return original_exists(self_path)

                with patch.object(Path, "exists", fake_exists_token):
                    from google_docs_tracker import GoogleDocsTopicTracker

                    tracker = GoogleDocsTopicTracker.__new__(GoogleDocsTopicTracker)
                    tracker.creds = None
                    tracker.service = None
                    tracker.ollama_client = MagicMock()
                    tracker.doc_id = "test-doc-id"
                    tracker._authenticate()

        # Verify Credentials.from_authorized_user_file was called with the credentials/ token path
        call_args = mock_creds_cls.from_authorized_user_file.call_args
        actual_path = Path(call_args[0][0])
        assert actual_path == expected_token, (
            f"token_path should be {expected_token}, got {actual_path}"
        )
