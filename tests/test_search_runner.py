"""Tests for pipeline/search_runner.py — search + episode listing commands."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from pipeline import search_runner


class TestRunSearch:
    def test_prints_results(self, capsys):
        fake_index = MagicMock()
        fake_index.search.return_value = [
            {"episode_number": 5, "title": "Lobster Talk", "snippet": "lobsters are..."},
            {"episode_number": 12, "title": "More Lobsters", "snippet": "still lobsters"},
        ]
        with patch.object(search_runner, "EpisodeSearchIndex", return_value=fake_index):
            search_runner.run_search("lobster")

        out = capsys.readouterr().out
        assert 'Searching for: "lobster"' in out
        assert "Episode 5: Lobster Talk" in out
        assert "Episode 12: More Lobsters" in out
        assert "2 result(s) found" in out
        fake_index.search.assert_called_once_with("lobster", limit=10)

    def test_handles_no_results(self, capsys):
        fake_index = MagicMock()
        fake_index.search.return_value = []
        with patch.object(search_runner, "EpisodeSearchIndex", return_value=fake_index):
            search_runner.run_search("unicorn")

        out = capsys.readouterr().out
        assert "No results found" in out


class TestListAvailableEpisodes:
    def _fake_ep(self, name="Episode 1.mp3", size=10 * 1024 * 1024):
        return {
            "name": name,
            "size": size,
            "modified": datetime(2026, 4, 1, 12, 0, 0),
            "path": f"/podcasts/{name}",
        }

    def test_lists_episodes_from_default_dropbox(self, capsys):
        fake_dropbox = MagicMock()
        fake_dropbox.list_episodes.return_value = [
            self._fake_ep("Ep 1.mp3"),
            self._fake_ep("Ep 2.mp3", size=20 * 1024 * 1024),
        ]
        with patch("dropbox_handler.DropboxHandler", return_value=fake_dropbox):
            episodes = search_runner.list_available_episodes()

        assert len(episodes) == 2
        out = capsys.readouterr().out
        assert "Ep 1.mp3" in out
        assert "Ep 2.mp3" in out
        assert "10.0 MB" in out
        assert "20.0 MB" in out

    def test_uses_components_dropbox_when_provided(self):
        """When components dict has dropbox key, use it instead of constructing one."""
        injected = MagicMock()
        injected.list_episodes.return_value = []
        search_runner.list_available_episodes(components={"dropbox": injected})
        injected.list_episodes.assert_called_once()

    def test_handles_no_episodes(self, capsys):
        fake = MagicMock()
        fake.list_episodes.return_value = []
        result = search_runner.list_available_episodes(components={"dropbox": fake})

        assert result == []
        assert "No episodes found" in capsys.readouterr().out


class TestListEpisodesByNumber:
    def test_prints_with_numbers(self, capsys):
        fake = MagicMock()
        fake.list_episodes_with_numbers.return_value = [
            (
                5,
                {
                    "name": "Episode 5.mp3",
                    "size": 15 * 1024 * 1024,
                    "modified": datetime(2026, 4, 1),
                },
            ),
            (
                6,
                {
                    "name": "Episode 6.mp3",
                    "size": 25 * 1024 * 1024,
                    "modified": datetime(2026, 4, 8),
                },
            ),
        ]
        result = search_runner.list_episodes_by_number(
            components={"dropbox": fake}
        )

        assert len(result) == 2
        out = capsys.readouterr().out
        assert "Episode 5:" in out
        assert "Episode 6:" in out

    def test_marks_episodes_without_numbers(self, capsys):
        fake = MagicMock()
        fake.list_episodes_with_numbers.return_value = [
            (
                None,
                {
                    "name": "bonus.mp3",
                    "size": 5 * 1024 * 1024,
                    "modified": datetime(2026, 4, 1),
                },
            ),
        ]
        search_runner.list_episodes_by_number(components={"dropbox": fake})

        out = capsys.readouterr().out
        assert "[No Episode #]" in out
        assert "bonus.mp3" in out

    def test_handles_empty_list(self, capsys):
        fake = MagicMock()
        fake.list_episodes_with_numbers.return_value = []
        result = search_runner.list_episodes_by_number(components={"dropbox": fake})

        assert result == []
        assert "No episodes found" in capsys.readouterr().out

    def test_default_dropbox_constructor_used_when_no_components(self):
        with patch("dropbox_handler.DropboxHandler") as MockDB:
            instance = MockDB.return_value
            instance.list_episodes_with_numbers.return_value = []
            search_runner.list_episodes_by_number()

        MockDB.assert_called_once()
