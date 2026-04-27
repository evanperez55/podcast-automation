"""Tests for scripts/draft_reply.py — reply scenario template renderer.

Covers:
- All six template files load and render without unfilled placeholders
- Scenario lookup is case-insensitive and surfaces a helpful error on unknowns
- first_name + church_name + preview_url substitutions land correctly
- PITCH.md-derived first_name strips honorifics and skips placeholder names
- Missing PITCH.md falls back to safe defaults — never raises
"""

from __future__ import annotations

import pytest

from outreach_tracker import OutreachTracker
from scripts import draft_reply as dr


# ---------------------------------------------------------------------------
# Template inventory — every scenario file must exist and be renderable
# ---------------------------------------------------------------------------


class TestTemplateInventory:
    """Catches accidental template deletions or scenarios added to the docstring
    without a matching file."""

    EXPECTED_SCENARIOS = {
        "interested",
        "pricing",
        "decline",
        "already_have_someone",
        "call_request",
        "forward_to_team",
    }

    def test_all_documented_scenarios_have_template_files(self):
        actual = set(dr.list_scenarios())
        missing = self.EXPECTED_SCENARIOS - actual
        assert not missing, f"Documented scenarios missing template files: {missing}"

    def test_no_orphan_template_files(self):
        """A template file with no documentation hint that it exists is dead code."""
        actual = set(dr.list_scenarios())
        orphans = actual - self.EXPECTED_SCENARIOS
        assert not orphans, (
            f"Templates exist but aren't in EXPECTED_SCENARIOS: {orphans} "
            f"— add them to the docstring or delete the file"
        )


# ---------------------------------------------------------------------------
# Render — every scenario must accept the full context without KeyError
# ---------------------------------------------------------------------------


class TestRender:
    BASE_CONTEXT = {
        "slug": "test-slug",
        "church_name": "Test Church",
        "first_name": "Pat",
        "preview_url": "https://episodespreview.com/test-slug/",
    }

    @pytest.mark.parametrize(
        "scenario", sorted(TestTemplateInventory.EXPECTED_SCENARIOS)
    )
    def test_each_scenario_renders_without_unfilled_braces(self, scenario):
        """Catches the case where a template adds a new {placeholder} that
        build_context doesn't supply."""
        rendered = dr.render(scenario, self.BASE_CONTEXT)
        assert "{first_name}" not in rendered
        assert "{church_name}" not in rendered
        assert "{preview_url}" not in rendered
        # The rendered text should always greet by first_name
        assert "Pat" in rendered

    def test_interested_includes_preview_url(self):
        """The interested template MUST surface the preview URL — that's the
        whole point of this scenario."""
        rendered = dr.render("interested", self.BASE_CONTEXT)
        assert self.BASE_CONTEXT["preview_url"] in rendered

    def test_pricing_includes_all_three_tiers(self):
        rendered = dr.render("pricing", self.BASE_CONTEXT)
        assert "$49" in rendered
        assert "$99" in rendered
        assert "$199" in rendered

    def test_decline_uses_church_name(self):
        """Decline message should mention removing the church from follow-ups
        — using their name keeps it personal, not boilerplate."""
        rendered = dr.render("decline", self.BASE_CONTEXT)
        assert "Test Church" in rendered

    def test_unknown_scenario_raises_with_helpful_message(self):
        with pytest.raises(FileNotFoundError, match="Unknown scenario"):
            dr.render("nonexistent-scenario", self.BASE_CONTEXT)

    def test_scenario_lookup_is_case_insensitive(self):
        """User shouldn't have to remember casing. INTERESTED == interested."""
        a = dr.render("interested", self.BASE_CONTEXT)
        b = dr.render("INTERESTED", self.BASE_CONTEXT)
        assert a == b


# ---------------------------------------------------------------------------
# derive_first_name — strip honorifics and dodge placeholder names
# ---------------------------------------------------------------------------


class TestDeriveFirstName:
    def test_extracts_simple_first_name(self):
        text = "**Contact:** Mitch Kuhn / **EMAIL: x@y.com**"
        assert dr.derive_first_name(text) == "Mitch"

    def test_strips_dr_honorific(self):
        """A pitch addressed to 'Dr. Steve Ball' should reply to 'Steve' —
        first-name-basis matches the existing PITCH voice."""
        text = "**Contact:** Dr. Steve Ball / **EMAIL: x@y.com**"
        assert dr.derive_first_name(text) == "Steve"

    def test_strips_pastor_honorific(self):
        text = "**Contact:** Pastor Tony Merida / **EMAIL: x@y.com**"
        assert dr.derive_first_name(text) == "Tony"

    def test_falls_back_when_name_is_pastor_placeholder(self):
        """If the contact line is just 'Pastor' (no real name was found), the
        skeleton fallback 'there' should win — addressing a stranger by
        'Pastor' in a reply reads weird."""
        text = "**Contact:** Pastor / **EMAIL: info@x.com**"
        assert dr.derive_first_name(text, fallback="there") == "there"

    def test_falls_back_when_no_contact_line(self):
        assert dr.derive_first_name("# Pitch with no contact line", fallback="x") == "x"


# ---------------------------------------------------------------------------
# derive_preview_url — surfaces the rendered URL or returns None
# ---------------------------------------------------------------------------


class TestDerivePreviewUrl:
    def test_finds_episodespreview_url_after_outreach_prepare_ran(self):
        text = "Body: see https://episodespreview.com/redeemer-city/abc/ for details"
        assert (
            dr.derive_preview_url(text)
            == "https://episodespreview.com/redeemer-city/abc/"
        )

    def test_returns_none_when_only_placeholder_present(self):
        """If outreach_prepare hasn't substituted the [PREVIEW URL] placeholder,
        we should NOT match the literal placeholder text."""
        text = "Body: [PREVIEW URL] — outreach_prepare will fill this"
        assert dr.derive_preview_url(text) is None


# ---------------------------------------------------------------------------
# build_context — integration: tracker + PITCH.md combined
# ---------------------------------------------------------------------------


class TestBuildContext:
    def test_pulls_church_name_from_tracker(self, tmp_path, monkeypatch):
        tracker = OutreachTracker(db_path=str(tmp_path / "outreach.db"))
        tracker.add_prospect(
            "a", {"show_name": "Alpha Church", "contact_email": "a@x.com"}
        )

        # No PITCH.md → first_name + preview_url use fallbacks
        monkeypatch.setattr(dr, "DEMO_ROOT", tmp_path / "demo" / "church-vertical")
        ctx = dr.build_context("a", tracker)

        assert ctx["church_name"] == "Alpha Church"
        assert ctx["first_name"] == "there"
        assert "PREVIEW URL" in ctx["preview_url"]

    def test_pulls_first_name_from_pitch_when_present(self, tmp_path, monkeypatch):
        tracker = OutreachTracker(db_path=str(tmp_path / "outreach.db"))
        tracker.add_prospect(
            "b", {"show_name": "Beta Church", "contact_email": "b@x.com"}
        )

        pitch_dir = tmp_path / "demo" / "church-vertical" / "b"
        pitch_dir.mkdir(parents=True)
        (pitch_dir / "PITCH.md").write_text(
            "**Contact:** Mitch Kuhn / **EMAIL: b@x.com**\n"
            "Preview at https://episodespreview.com/b/abc/\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(dr, "DEMO_ROOT", tmp_path / "demo" / "church-vertical")

        ctx = dr.build_context("b", tracker)
        assert ctx["first_name"] == "Mitch"
        assert ctx["preview_url"] == "https://episodespreview.com/b/abc/"

    def test_unknown_slug_falls_back_to_slug_as_church_name(
        self, tmp_path, monkeypatch
    ):
        """If the slug isn't in the tracker yet, render still works — just
        with degraded data so the operator can hand-edit before sending."""
        tracker = OutreachTracker(db_path=str(tmp_path / "outreach.db"))
        monkeypatch.setattr(dr, "DEMO_ROOT", tmp_path / "demo" / "church-vertical")

        ctx = dr.build_context("never-added", tracker)
        assert ctx["church_name"] == "never-added"
        assert ctx["first_name"] == "there"
