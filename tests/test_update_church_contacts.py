"""Tests for scripts/update_church_contacts.py — email injection into pitch files + tracker."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from scripts import update_church_contacts as ucc


# ---------------------------------------------------------------------------
# CONTACTS table shape
# ---------------------------------------------------------------------------


class TestContactsTable:
    def test_every_contact_has_email_person_note(self):
        for slug, contact in ucc.CONTACTS.items():
            assert "email" in contact
            assert "contact_person" in contact
            assert "note" in contact

    def test_all_emails_look_like_emails(self):
        for slug, contact in ucc.CONTACTS.items():
            email = contact["email"]
            assert "@" in email, f"{slug}: {email!r} is not an email"
            assert "." in email.split("@")[-1], f"{slug}: bad domain in {email!r}"


# ---------------------------------------------------------------------------
# update_pitch_file
# ---------------------------------------------------------------------------


class TestUpdatePitchFile:
    @pytest.fixture
    def pitch_skeleton(self, tmp_path, monkeypatch):
        """Set up a fake demo/church-vertical/<slug>/PITCH.md and cd into tmp."""
        monkeypatch.chdir(tmp_path)
        slug = "fake-church"
        pitch_dir = tmp_path / "demo" / "church-vertical" / slug
        pitch_dir.mkdir(parents=True)
        skeleton = (
            "# Fake Church - Outreach Pitch\n\n"
            "**Contact:** Pastor Bob / **EMAIL: TBD** - check: the website\n"
            "**Episode:** TBD\n\n"
            "- [ ] Find Pastor Bob contact email (check the website)\n"
        )
        (pitch_dir / "PITCH.md").write_text(skeleton, encoding="utf-8")
        return {"slug": slug, "path": pitch_dir / "PITCH.md"}

    def test_substitutes_email_into_contact_line(self, pitch_skeleton):
        contact = {
            "email": "bob@fakechurch.org",
            "contact_person": "Pastor Bob",
            "note": "Direct pastor email",
        }
        ucc.update_pitch_file(pitch_skeleton["slug"], contact)

        text = pitch_skeleton["path"].read_text(encoding="utf-8")
        assert "bob@fakechurch.org" in text
        assert "EMAIL: TBD" not in text

    def test_inserts_contact_notes_block(self, pitch_skeleton):
        contact = {
            "email": "bob@fakechurch.org",
            "contact_person": "Pastor Bob",
            "note": "Verify this is the real pastor",
        }
        ucc.update_pitch_file(pitch_skeleton["slug"], contact)

        text = pitch_skeleton["path"].read_text(encoding="utf-8")
        assert "**Contact notes:** Verify this is the real pastor" in text

    def test_marks_find_email_checkbox_as_resolved(self, pitch_skeleton):
        contact = {
            "email": "bob@fakechurch.org",
            "contact_person": "Pastor Bob",
            "note": "n/a",
        }
        ucc.update_pitch_file(pitch_skeleton["slug"], contact)

        text = pitch_skeleton["path"].read_text(encoding="utf-8")
        assert "[x] Contact email resolved: bob@fakechurch.org" in text
        assert "[ ] Find Pastor Bob contact email" not in text

    def test_no_op_when_pitch_missing(self, tmp_path, monkeypatch, capsys):
        """If PITCH.md doesn't exist, skip gracefully — don't crash the batch."""
        monkeypatch.chdir(tmp_path)
        contact = {
            "email": "bob@fakechurch.org",
            "contact_person": "Pastor Bob",
            "note": "n/a",
        }
        ucc.update_pitch_file("nonexistent-slug", contact)
        assert "SKIP" in capsys.readouterr().out

    def test_does_not_duplicate_contact_notes_on_rerun(self, pitch_skeleton):
        contact = {
            "email": "bob@fakechurch.org",
            "contact_person": "Pastor Bob",
            "note": "First note",
        }
        ucc.update_pitch_file(pitch_skeleton["slug"], contact)
        ucc.update_pitch_file(pitch_skeleton["slug"], contact)

        text = pitch_skeleton["path"].read_text(encoding="utf-8")
        # "**Contact notes:**" should appear exactly once
        assert text.count("**Contact notes:**") == 1


# ---------------------------------------------------------------------------
# update_tracker
# ---------------------------------------------------------------------------


class TestUpdateTracker:
    def test_shells_out_to_outreach_update(self):
        """The current CLI doesn't accept contact_email, so this invocation
        is expected to print a 'Valid statuses: ...' error — that's the
        behavior documented by the script. This test locks in that we're
        at least issuing the command with the right shape."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="Error: Invalid status 'contact_email=x'",
                stderr="",
            )
            ucc.update_tracker("test-slug", "test@example.com")

        cmd = mock_run.call_args.args[0]
        assert cmd[0:4] == ["uv", "run", "main.py", "outreach"]
        assert cmd[4] == "update"
        assert cmd[5] == "test-slug"
        assert cmd[6] == "contact_email=test@example.com"
