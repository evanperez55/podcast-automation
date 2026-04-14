"""Tests for scripts/organize_output.py — episode file organizer."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import organize_output as oo


@pytest.fixture
def output_tree(tmp_path, monkeypatch):
    """Build a scratch output/ directory with mixed files and cd into it."""
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "output"
    out.mkdir()
    return out


def touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")


class TestOrganizeOutputFolder:
    def test_missing_output_dir_is_graceful(self, tmp_path, monkeypatch, capsys):
        """If output/ doesn't exist, the script logs an error and returns, no crash."""
        monkeypatch.chdir(tmp_path)
        oo.organize_output_folder()
        assert "Output directory not found" in capsys.readouterr().out

    def test_groups_files_by_episode_hash_pattern(self, output_tree):
        touch(output_tree / "Episode #25 - Intro.mp3")
        touch(output_tree / "Episode #25 - Intro.srt")
        touch(output_tree / "Episode #26 - Other.mp3")

        oo.organize_output_folder()

        assert (output_tree / "ep_25" / "Episode #25 - Intro.mp3").exists()
        assert (output_tree / "ep_25" / "Episode #25 - Intro.srt").exists()
        assert (output_tree / "ep_26" / "Episode #26 - Other.mp3").exists()
        # Originals moved out of root
        assert not (output_tree / "Episode #25 - Intro.mp3").exists()

    def test_groups_files_by_ep_raw_pattern(self, output_tree):
        """Files named 'ep_<n>_raw_...' should route to the same episode folder."""
        touch(output_tree / "ep_7_raw_audio.wav")
        touch(output_tree / "ep_7_raw_metadata.json")

        oo.organize_output_folder()

        assert (output_tree / "ep_7" / "ep_7_raw_audio.wav").exists()
        assert (output_tree / "ep_7" / "ep_7_raw_metadata.json").exists()

    def test_rss_and_metadata_files_stay_in_root(self, output_tree):
        """podcast_feed.xml, test_podcast_feed.xml, podcast_metadata.json
        are explicitly kept at root (they're not episode-scoped)."""
        touch(output_tree / "podcast_feed.xml")
        touch(output_tree / "test_podcast_feed.xml")
        touch(output_tree / "podcast_metadata.json")
        touch(output_tree / "Episode #1 - Foo.mp3")

        oo.organize_output_folder()

        assert (output_tree / "podcast_feed.xml").exists()
        assert (output_tree / "test_podcast_feed.xml").exists()
        assert (output_tree / "podcast_metadata.json").exists()
        assert (output_tree / "ep_1" / "Episode #1 - Foo.mp3").exists()

    def test_unmatched_files_stay_in_root(self, output_tree):
        """Files that match neither pattern should not be moved."""
        touch(output_tree / "random_notes.txt")
        touch(output_tree / "some_thumbnail.png")

        oo.organize_output_folder()

        assert (output_tree / "random_notes.txt").exists()
        assert (output_tree / "some_thumbnail.png").exists()

    def test_skip_when_destination_already_exists(self, output_tree, capsys):
        """If ep_N/<file> already exists, the source file is left in root —
        the script does not overwrite."""
        touch(output_tree / "Episode #5 - Test.mp3")
        # Pre-seed the destination
        (output_tree / "ep_5").mkdir()
        touch(output_tree / "ep_5" / "Episode #5 - Test.mp3")

        oo.organize_output_folder()

        # Source NOT moved (still in root)
        assert (output_tree / "Episode #5 - Test.mp3").exists()
        # Existing destination preserved
        assert (output_tree / "ep_5" / "Episode #5 - Test.mp3").exists()
        assert "SKIP" in capsys.readouterr().out

    def test_empty_output_dir_noop(self, output_tree, capsys):
        oo.organize_output_folder()
        out = capsys.readouterr().out
        assert "Found 0 episodes" in out

    def test_subdirectories_are_ignored(self, output_tree):
        """Only top-level files get organized — existing subdirs shouldn't be touched."""
        (output_tree / "ep_existing").mkdir()
        touch(output_tree / "ep_existing" / "already_there.txt")
        touch(output_tree / "Episode #9 - New.mp3")

        oo.organize_output_folder()

        assert (output_tree / "ep_9" / "Episode #9 - New.mp3").exists()
        # Untouched pre-existing subdir
        assert (output_tree / "ep_existing" / "already_there.txt").exists()
