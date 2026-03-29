"""Tests for outreach_tracker module."""

import pytest
from pathlib import Path

from outreach_tracker import OutreachTracker, VALID_STATUSES


def _make_tracker(tmp_path):
    """Create an OutreachTracker backed by a temp database."""
    return OutreachTracker(db_path=str(tmp_path / "test_outreach.db"))


class TestOutreachTrackerInit:
    def test_init_creates_db(self, tmp_path):
        """DB file is created on instantiation."""
        tracker = _make_tracker(tmp_path)
        assert Path(tracker.db_path).exists()

    def test_valid_statuses_exported(self):
        """VALID_STATUSES tuple is exported at module level."""
        assert "identified" in VALID_STATUSES
        assert "contacted" in VALID_STATUSES
        assert "interested" in VALID_STATUSES
        assert "demo_sent" in VALID_STATUSES
        assert "converted" in VALID_STATUSES
        assert "declined" in VALID_STATUSES


class TestAddProspect:
    def test_add_prospect_returns_true(self, tmp_path):
        """add_prospect returns True for a new slug."""
        tracker = _make_tracker(tmp_path)
        result = tracker.add_prospect("test-show", {"show_name": "Test Show"})
        assert result is True

    def test_add_prospect_idempotent(self, tmp_path):
        """Second add_prospect with same slug returns False and preserves original data."""
        tracker = _make_tracker(tmp_path)
        tracker.add_prospect("test-show", {"show_name": "Test Show"})
        result = tracker.add_prospect("test-show", {"show_name": "Duplicate Name"})
        assert result is False
        p = tracker.get_prospect("test-show")
        assert p["show_name"] == "Test Show"

    def test_add_prospect_default_status_identified(self, tmp_path):
        """Prospect added without explicit status defaults to 'identified'."""
        tracker = _make_tracker(tmp_path)
        tracker.add_prospect("my-show", {"show_name": "My Show"})
        p = tracker.get_prospect("my-show")
        assert p["status"] == "identified"


class TestGetProspect:
    def test_get_prospect_existing(self, tmp_path):
        """get_prospect returns dict with all expected fields."""
        tracker = _make_tracker(tmp_path)
        tracker.add_prospect(
            "the-show", {"show_name": "The Show", "contact_email": "host@example.com"}
        )
        p = tracker.get_prospect("the-show")
        assert p is not None
        assert p["slug"] == "the-show"
        assert p["show_name"] == "The Show"
        assert p["contact_email"] == "host@example.com"
        assert "status" in p
        assert "created_at" in p
        assert "updated_at" in p

    def test_get_prospect_missing(self, tmp_path):
        """get_prospect returns None for a nonexistent slug."""
        tracker = _make_tracker(tmp_path)
        result = tracker.get_prospect("nonexistent")
        assert result is None


class TestUpdateStatus:
    def test_update_status_valid(self, tmp_path):
        """update_status returns True and updates status, updated_at, last_contact_date."""
        tracker = _make_tracker(tmp_path)
        tracker.add_prospect("pod-a", {"show_name": "Pod A"})
        result = tracker.update_status("pod-a", "contacted")
        assert result is True
        p = tracker.get_prospect("pod-a")
        assert p["status"] == "contacted"
        assert p["updated_at"] is not None
        assert p["last_contact_date"] is not None

    def test_update_status_invalid_raises(self, tmp_path):
        """update_status raises ValueError for an invalid status."""
        tracker = _make_tracker(tmp_path)
        tracker.add_prospect("pod-b", {"show_name": "Pod B"})
        with pytest.raises(ValueError, match="Invalid status"):
            tracker.update_status("pod-b", "bogus")

    def test_update_status_missing_slug(self, tmp_path):
        """update_status returns False when slug does not exist."""
        tracker = _make_tracker(tmp_path)
        result = tracker.update_status("nonexistent", "contacted")
        assert result is False

    def test_update_status_all_lifecycle_stages(self, tmp_path):
        """All valid statuses can be set without error."""
        tracker = _make_tracker(tmp_path)
        tracker.add_prospect("lifecycle-pod", {"show_name": "Lifecycle Pod"})
        for status in VALID_STATUSES:
            result = tracker.update_status("lifecycle-pod", status)
            assert result is True
            p = tracker.get_prospect("lifecycle-pod")
            assert p["status"] == status


class TestListProspects:
    def test_list_prospects_empty(self, tmp_path):
        """list_prospects returns empty list when no prospects exist."""
        tracker = _make_tracker(tmp_path)
        result = tracker.list_prospects()
        assert result == []

    def test_list_prospects_multiple(self, tmp_path):
        """list_prospects returns all prospects with required keys."""
        tracker = _make_tracker(tmp_path)
        tracker.add_prospect("show-a", {"show_name": "Show A"})
        tracker.add_prospect("show-b", {"show_name": "Show B"})
        tracker.add_prospect("show-c", {"show_name": "Show C"})
        results = tracker.list_prospects()
        assert len(results) == 3
        for p in results:
            assert "slug" in p
            assert "show_name" in p
            assert "status" in p
            assert "last_contact_date" in p

    def test_list_prospects_ordered_by_created_at_desc(self, tmp_path):
        """list_prospects returns most recently added prospects first."""
        tracker = _make_tracker(tmp_path)
        tracker.add_prospect("first-show", {"show_name": "First Show"})
        tracker.add_prospect("second-show", {"show_name": "Second Show"})
        results = tracker.list_prospects()
        assert len(results) == 2
        # Most recent should be first
        assert results[0]["slug"] == "second-show"
        assert results[1]["slug"] == "first-show"


class TestSocialLinksRoundtrip:
    def test_social_links_roundtrip(self, tmp_path):
        """add_prospect with social_links dict; get_prospect returns same dict."""
        tracker = _make_tracker(tmp_path)
        social = {"twitter": "@testpod", "instagram": "@testpod_ig"}
        tracker.add_prospect(
            "social-pod", {"show_name": "Social Pod", "social_links": social}
        )
        p = tracker.get_prospect("social-pod")
        assert p is not None
        # social_links should be deserialized back to a dict
        assert isinstance(p["social_links"], dict)
        assert p["social_links"]["twitter"] == "@testpod"
        assert p["social_links"]["instagram"] == "@testpod_ig"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
