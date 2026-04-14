"""Regression tests for cli_commands — focus on cross-platform console safety."""

from __future__ import annotations

import io
import sys
from unittest.mock import MagicMock, patch

import cli_commands


def _cp1252_stdout() -> io.TextIOWrapper:
    """Build a strict cp1252 stdout that mirrors a default Windows console."""
    return io.TextIOWrapper(
        io.BytesIO(), encoding="cp1252", errors="strict", newline=""
    )


class TestOutreachListEncoding:
    def test_list_does_not_crash_on_cp1252_console_with_unicode_show_name(
        self, monkeypatch
    ):
        """Regression: show names containing non-cp1252 chars (e.g. Chinese,
        curly quotes) must not raise UnicodeEncodeError when `outreach list`
        prints to a default Windows console. See prior bug: cp1252 strict
        stdout raised 'charmap codec can't encode' on list output."""
        fake_stdout = _cp1252_stdout()
        monkeypatch.setattr(sys, "stdout", fake_stdout)
        monkeypatch.setattr(sys, "argv", ["main.py", "outreach", "list"])

        mock_tracker = MagicMock()
        mock_tracker.list_prospects.return_value = [
            {
                "slug": "abc",
                "show_name": "投资ABC｜掌握投资中那些绕不开的知识",
                "status": "new",
                "last_contact_date": None,
            },
            {
                "slug": "fr",
                "show_name": "L'Éducation Financière Pour Tous",
                "status": "new",
                "last_contact_date": "2026-04-10",
            },
        ]

        with patch("outreach_tracker.OutreachTracker", return_value=mock_tracker):
            handled = cli_commands.handle_client_command(
                "outreach", {"client_name": None}
            )

        assert handled is True
        fake_stdout.flush()

    def test_list_with_empty_prospects_does_not_crash(self, monkeypatch):
        fake_stdout = _cp1252_stdout()
        monkeypatch.setattr(sys, "stdout", fake_stdout)
        monkeypatch.setattr(sys, "argv", ["main.py", "outreach", "list"])

        mock_tracker = MagicMock()
        mock_tracker.list_prospects.return_value = []

        with patch("outreach_tracker.OutreachTracker", return_value=mock_tracker):
            handled = cli_commands.handle_client_command(
                "outreach", {"client_name": None}
            )

        assert handled is True

    def test_add_prospect_with_unicode_show_name_does_not_crash(self, monkeypatch):
        fake_stdout = _cp1252_stdout()
        monkeypatch.setattr(sys, "stdout", fake_stdout)
        monkeypatch.setattr(
            sys,
            "argv",
            ["main.py", "outreach", "add", "abc", "投资ABC｜掌握投资"],
        )

        mock_tracker = MagicMock()
        mock_tracker.add_prospect.return_value = True

        with patch("outreach_tracker.OutreachTracker", return_value=mock_tracker):
            handled = cli_commands.handle_client_command(
                "outreach", {"client_name": None}
            )

        assert handled is True

    def test_status_prints_unicode_field_values_without_crashing(self, monkeypatch):
        fake_stdout = _cp1252_stdout()
        monkeypatch.setattr(sys, "stdout", fake_stdout)
        monkeypatch.setattr(sys, "argv", ["main.py", "outreach", "status", "abc"])

        mock_tracker = MagicMock()
        mock_tracker.get_prospect.return_value = {
            "slug": "abc",
            "show_name": "投资ABC",
            "host_name": "Zhang Wěi",
            "status": "new",
        }

        with patch("outreach_tracker.OutreachTracker", return_value=mock_tracker):
            handled = cli_commands.handle_client_command(
                "outreach", {"client_name": None}
            )

        assert handled is True
