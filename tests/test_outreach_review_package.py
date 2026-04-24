"""Tests for scripts/outreach_review_package.py — pre-send package review CLI."""

from __future__ import annotations

from unittest.mock import patch

from scripts import outreach_review_package as rp


class TestReviewPackage:
    """review_package wires verify + stage + open in the right order."""

    def _ok_finding(self):
        from scripts.outreach_verify import Finding

        return Finding("OK", "thumbnail_exists", "ok")

    def _err_finding(self):
        from scripts.outreach_verify import Finding

        return Finding("ERROR", "clip_count_matches_analysis", "mismatch")

    @patch("scripts.outreach_review_package.verify_one")
    @patch("scripts.outreach_review_package._find_latest_ep_dir")
    @patch("scripts.outreach_review_package._stage_assets")
    @patch("scripts.outreach_review_package.webbrowser.open")
    def test_runs_full_flow_when_verify_passes(
        self, mock_browser, mock_stage, mock_ep, mock_verify, tmp_path, capsys
    ):
        mock_verify.return_value = [self._ok_finding()]
        mock_ep.return_value = tmp_path / "ep_1"
        rc = rp.review_package("test-slug", open_in_browser=True, staging_root=tmp_path)
        assert rc == 0
        mock_verify.assert_called_once_with("test-slug")
        mock_stage.assert_called_once()
        mock_browser.assert_called_once()

    @patch("scripts.outreach_review_package.verify_one")
    @patch("scripts.outreach_review_package._stage_assets")
    @patch("scripts.outreach_review_package.webbrowser.open")
    def test_aborts_on_error_findings(
        self, mock_browser, mock_stage, mock_verify, tmp_path
    ):
        mock_verify.return_value = [self._err_finding()]
        rc = rp.review_package("test-slug", open_in_browser=True, staging_root=tmp_path)
        assert rc == 1
        # Staging + browser must NOT happen if verify failed
        mock_stage.assert_not_called()
        mock_browser.assert_not_called()

    @patch("scripts.outreach_review_package.verify_one")
    @patch("scripts.outreach_review_package._find_latest_ep_dir")
    @patch("scripts.outreach_review_package._stage_assets")
    @patch("scripts.outreach_review_package.webbrowser.open")
    def test_no_open_flag_skips_browser(
        self, mock_browser, mock_stage, mock_ep, mock_verify, tmp_path
    ):
        mock_verify.return_value = [self._ok_finding()]
        mock_ep.return_value = tmp_path / "ep_1"
        rp.review_package("test-slug", open_in_browser=False, staging_root=tmp_path)
        mock_browser.assert_not_called()

    @patch("scripts.outreach_review_package.verify_one")
    @patch("scripts.outreach_review_package._find_latest_ep_dir", return_value=None)
    def test_aborts_when_no_ep_dir(self, mock_ep, mock_verify, tmp_path):
        mock_verify.return_value = [self._ok_finding()]
        rc = rp.review_package(
            "ghost-slug", open_in_browser=False, staging_root=tmp_path
        )
        assert rc == 1


class TestMain:
    @patch("scripts.outreach_review_package.review_package", return_value=0)
    def test_main_passes_no_open_flag(self, mock_rp):
        rc = rp.main(["test-slug", "--no-open"])
        assert rc == 0
        mock_rp.assert_called_once_with("test-slug", open_in_browser=False)

    @patch("scripts.outreach_review_package.review_package", return_value=0)
    def test_main_default_opens(self, mock_rp):
        rp.main(["test-slug"])
        mock_rp.assert_called_once_with("test-slug", open_in_browser=True)
