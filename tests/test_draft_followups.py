"""Tests for scripts/draft_followups.py — automated follow-up drafter.

Covers:
- parse_followup: extracts the SECOND email (follow-up) section from PITCH.md
- select_prospects: filters by status='contacted' and last_contact_date age
- is_recently_followed_up: idempotency marker check
- mark_followed_up: writes the marker into the tracker `notes` column
- draft_one: end-to-end happy path + error handling

The original primary-email parser lives in outreach_prepare; the follow-up
parser MUST use the second `## Follow-Up` section so we don't accidentally
re-send the original pitch as a follow-up.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from outreach_tracker import OutreachTracker
from scripts import draft_followups as df


# ---------------------------------------------------------------------------
# parse_followup
# ---------------------------------------------------------------------------


class TestParseFollowup:
    """The follow-up parser must walk past the primary email and extract
    Subject + Body from the SECOND email section, terminated by the next
    `---` divider (or EOF)."""

    PITCH_TEMPLATE = (
        "# Test - Outreach Pitch\n\n"
        "**Contact:** X / **EMAIL: pastor@x.com**\n\n"
        "---\n\n## Email\n\n"
        "**Subject:** Primary subject — should NOT match\n\n"
        "Primary body, ignored by the follow-up parser.\n\n"
        "---\n\n## Follow-Up Email (send 4-5 days later if no response)\n\n"
        '**Subject:** Re: Made these from your "Joy" sermon\n\n'
        "Hey Mitch,\n\n"
        "Quick follow-up - here are the clips in case they got buried:\n\n"
        "1. Joy is a choice (1:00): [direct link]\n\n"
        "Evan\n\n"
        "---\n\n## Pre-Send Checklist\n- [x] processed\n"
    )

    def _write(self, tmp_path: Path, content: str = None) -> Path:
        p = tmp_path / "PITCH.md"
        p.write_text(content or self.PITCH_TEMPLATE, encoding="utf-8")
        return p

    def test_extracts_followup_subject_not_primary(self, tmp_path):
        p = self._write(tmp_path)
        result = df.parse_followup(p)
        assert result["subject"].startswith("Re: Made these")
        assert "Primary subject" not in result["subject"]

    def test_extracts_followup_body_from_section_only(self, tmp_path):
        p = self._write(tmp_path)
        result = df.parse_followup(p)
        body = result["body"]
        assert body.startswith("Hey Mitch,")
        assert "Joy is a choice" in body
        assert "Evan" in body
        # Pre-Send Checklist is past the next `---` and must NOT leak in
        assert "Pre-Send Checklist" not in body
        # Primary body must NOT leak in
        assert "Primary body" not in body

    def test_handles_followup_at_eof_no_trailing_divider(self, tmp_path):
        """Some PITCH.md files end at the follow-up section (no Pre-Send
        Checklist). Body must still be extracted up to EOF."""
        content = (
            "# T\n\n**Contact:** X / **EMAIL: x@x.com**\n\n"
            "## Follow-Up\n\n"
            "**Subject:** sub\n\n"
            "Body line 1\nBody line 2\n"
        )
        p = self._write(tmp_path, content)
        result = df.parse_followup(p)
        assert result["subject"] == "sub"
        assert "Body line 1" in result["body"]
        assert "Body line 2" in result["body"]

    def test_missing_followup_section_raises(self, tmp_path):
        p = self._write(tmp_path, "# T\n\n## Email\n**Subject:** x\nbody\n")
        with pytest.raises(ValueError, match="Follow-Up"):
            df.parse_followup(p)

    def test_missing_subject_in_followup_raises(self, tmp_path):
        content = "## Follow-Up\n\nBody but no subject line.\n"
        p = self._write(tmp_path, content)
        with pytest.raises(ValueError, match="Subject"):
            df.parse_followup(p)


# ---------------------------------------------------------------------------
# is_recently_followed_up — idempotency marker
# ---------------------------------------------------------------------------


class TestIsRecentlyFollowedUp:
    def test_returns_true_when_marker_matches_today(self):
        notes = "FOLLOWED_UP=2026-04-27"
        assert df.is_recently_followed_up(notes, "2026-04-27") is True

    def test_returns_false_when_marker_is_yesterday(self):
        """A marker from a previous date must NOT block re-drafting today.
        The whole point of the marker is to dedupe SAME-DAY re-runs."""
        notes = "FOLLOWED_UP=2026-04-26"
        assert df.is_recently_followed_up(notes, "2026-04-27") is False

    def test_returns_false_when_no_marker(self):
        assert df.is_recently_followed_up("some other notes", "2026-04-27") is False
        assert df.is_recently_followed_up(None, "2026-04-27") is False
        assert df.is_recently_followed_up("", "2026-04-27") is False

    def test_finds_marker_among_other_notes(self):
        notes = "elder-led congregation\nFOLLOWED_UP=2026-04-27\nstale_feed: yes"
        assert df.is_recently_followed_up(notes, "2026-04-27") is True


# ---------------------------------------------------------------------------
# select_prospects — tracker filter
# ---------------------------------------------------------------------------


@pytest.fixture
def tracker(tmp_path):
    return OutreachTracker(db_path=str(tmp_path / "outreach.db"))


def _set_last_contact(tracker, slug: str, iso: str) -> None:
    """Helper: directly stamp last_contact_date so we can simulate aged contacts."""
    import sqlite3

    conn = sqlite3.connect(tracker.db_path)
    try:
        conn.execute(
            "UPDATE prospects SET last_contact_date = ? WHERE slug = ?",
            (iso, slug),
        )
        conn.commit()
    finally:
        conn.close()


class TestSelectProspects:
    def test_includes_contacted_aged_past_window(self, tracker):
        tracker.add_prospect("a", {"show_name": "A", "contact_email": "a@x.com"})
        tracker.update_status("a", "contacted")
        # Stamp last_contact 10 days ago
        old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        _set_last_contact(tracker, "a", old)

        eligible = df.select_prospects(tracker, days=5)
        assert len(eligible) == 1
        assert eligible[0]["slug"] == "a"

    def test_excludes_contacted_within_window(self, tracker):
        """Contacted yesterday — too recent for a 5-day follow-up."""
        tracker.add_prospect("b", {"show_name": "B", "contact_email": "b@x.com"})
        tracker.update_status("b", "contacted")
        recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        _set_last_contact(tracker, "b", recent)

        assert df.select_prospects(tracker, days=5) == []

    def test_excludes_other_statuses(self, tracker):
        """A prospect in 'interested' or 'demo_sent' or 'declined' must NEVER
        get a follow-up draft — they've already replied."""
        for slug, status in [
            ("c-int", "interested"),
            ("c-demo", "demo_sent"),
            ("c-decl", "declined"),
            ("c-conv", "converted"),
        ]:
            tracker.add_prospect(
                slug, {"show_name": slug, "contact_email": f"{slug}@x.com"}
            )
            tracker.update_status(slug, status)
            old = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
            _set_last_contact(tracker, slug, old)

        assert df.select_prospects(tracker, days=5) == []

    def test_excludes_already_followed_up_today(self, tracker):
        tracker.add_prospect(
            "d",
            {
                "show_name": "D",
                "contact_email": "d@x.com",
                "notes": "FOLLOWED_UP=2026-04-27",
            },
        )
        tracker.update_status("d", "contacted")
        old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        _set_last_contact(tracker, "d", old)

        # Pin "today" to match the marker so the dedup hits
        today = datetime(2026, 4, 27, tzinfo=timezone.utc)
        assert df.select_prospects(tracker, days=5, today=today) == []

    def test_force_overrides_today_marker(self, tracker):
        tracker.add_prospect(
            "e",
            {
                "show_name": "E",
                "contact_email": "e@x.com",
                "notes": "FOLLOWED_UP=2026-04-27",
            },
        )
        tracker.update_status("e", "contacted")
        old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        _set_last_contact(tracker, "e", old)

        today = datetime(2026, 4, 27, tzinfo=timezone.utc)
        eligible = df.select_prospects(tracker, days=5, today=today, force=True)
        assert len(eligible) == 1

    def test_only_slug_filter(self, tracker):
        for s in ["wanted", "skipped"]:
            tracker.add_prospect(s, {"show_name": s, "contact_email": f"{s}@x.com"})
            tracker.update_status(s, "contacted")
            old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
            _set_last_contact(tracker, s, old)

        eligible = df.select_prospects(tracker, days=5, only_slug="wanted")
        assert len(eligible) == 1
        assert eligible[0]["slug"] == "wanted"


# ---------------------------------------------------------------------------
# mark_followed_up — writes the marker to the notes column
# ---------------------------------------------------------------------------


class TestMarkFollowedUp:
    def test_appends_marker_when_no_existing_notes(self, tracker):
        tracker.add_prospect("a", {"show_name": "A", "contact_email": "a@x.com"})
        df.mark_followed_up(tracker, "a", "2026-04-27")
        prospect = tracker.get_prospect("a")
        assert "FOLLOWED_UP=2026-04-27" in prospect["notes"]

    def test_appends_marker_to_existing_notes(self, tracker):
        tracker.add_prospect(
            "b",
            {"show_name": "B", "contact_email": "b@x.com", "notes": "stale_feed: yes"},
        )
        df.mark_followed_up(tracker, "b", "2026-04-27")
        prospect = tracker.get_prospect("b")
        assert "stale_feed: yes" in prospect["notes"]
        assert "FOLLOWED_UP=2026-04-27" in prospect["notes"]

    def test_replaces_old_marker_in_place(self, tracker):
        """Re-running on a different day shouldn't accumulate stale markers."""
        tracker.add_prospect(
            "c",
            {
                "show_name": "C",
                "contact_email": "c@x.com",
                "notes": "FOLLOWED_UP=2026-04-20",
            },
        )
        df.mark_followed_up(tracker, "c", "2026-04-27")
        prospect = tracker.get_prospect("c")
        assert "FOLLOWED_UP=2026-04-27" in prospect["notes"]
        assert "2026-04-20" not in prospect["notes"]


# ---------------------------------------------------------------------------
# draft_one — end-to-end with mocked Gmail
# ---------------------------------------------------------------------------


class TestDraftOne:
    def _setup_pitch(self, tmp_path: Path, slug: str, monkeypatch) -> Path:
        pitch_dir = tmp_path / "demo" / "church-vertical" / slug
        pitch_dir.mkdir(parents=True)
        (pitch_dir / "PITCH.md").write_text(
            TestParseFollowup.PITCH_TEMPLATE, encoding="utf-8"
        )
        monkeypatch.setattr(df, "DEMO_ROOT", tmp_path / "demo" / "church-vertical")
        return pitch_dir / "PITCH.md"

    def test_creates_draft_and_marks_tracker(self, tmp_path, tracker, monkeypatch):
        slug = "test-slug"
        self._setup_pitch(tmp_path, slug, monkeypatch)
        tracker.add_prospect(slug, {"show_name": "T", "contact_email": "pastor@x.com"})

        fake_gmail = MagicMock()
        fake_gmail.create_draft.return_value = "draft-99"

        result = df.draft_one(
            tracker.get_prospect(slug),
            gmail=fake_gmail,
            today_iso="2026-04-27",
            tracker=tracker,
        )

        assert result["status"] == "drafted"
        assert result["draft_id"] == "draft-99"
        assert result["to"] == "pastor@x.com"

        # Tracker got a FOLLOWED_UP marker
        marker = tracker.get_prospect(slug)["notes"]
        assert "FOLLOWED_UP=2026-04-27" in marker

        # Gmail was called with the follow-up subject + body, not the primary
        kwargs = fake_gmail.create_draft.call_args.kwargs
        assert kwargs["to"] == "pastor@x.com"
        assert "Re: Made these" in kwargs["subject"]
        assert "Quick follow-up" in kwargs["body"]
        assert "Primary body" not in kwargs["body"]

    def test_dry_run_does_not_mark_tracker(self, tmp_path, tracker, monkeypatch):
        slug = "dry-slug"
        self._setup_pitch(tmp_path, slug, monkeypatch)
        tracker.add_prospect(slug, {"show_name": "Dry", "contact_email": "d@x.com"})

        fake_gmail = MagicMock()
        fake_gmail.create_draft.return_value = "DRY_RUN"

        df.draft_one(
            tracker.get_prospect(slug),
            gmail=fake_gmail,
            today_iso="2026-04-27",
            tracker=tracker,
            dry_run=True,
        )

        # Marker NOT written when dry_run=True
        notes = tracker.get_prospect(slug)["notes"] or ""
        assert "FOLLOWED_UP" not in notes

    def test_missing_pitch_returns_error(self, tmp_path, tracker, monkeypatch):
        monkeypatch.setattr(df, "DEMO_ROOT", tmp_path / "demo" / "church-vertical")
        tracker.add_prospect("nope", {"show_name": "N", "contact_email": "n@x.com"})

        result = df.draft_one(
            tracker.get_prospect("nope"),
            gmail=MagicMock(),
            today_iso="2026-04-27",
        )
        assert result["status"] == "error"
        assert "PITCH.md missing" in result["err"]

    def test_no_email_returns_error(self, tmp_path, tracker, monkeypatch):
        slug = "no-email"
        self._setup_pitch(tmp_path, slug, monkeypatch)
        # contact_email left unset
        tracker.add_prospect(slug, {"show_name": "N"})

        result = df.draft_one(
            tracker.get_prospect(slug),
            gmail=MagicMock(),
            today_iso="2026-04-27",
        )
        assert result["status"] == "error"
        assert "contact_email" in result["err"]
