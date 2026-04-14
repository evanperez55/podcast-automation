"""Tests for scripts/gen_church_pitches.py — pitch skeleton generator."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from scripts import gen_church_pitches as gcp


# ---------------------------------------------------------------------------
# PROSPECTS / ANGLE_RATIONALES contract
# ---------------------------------------------------------------------------


class TestProspectTable:
    """Every prospect entry must have the fields the template needs."""

    REQUIRED_KEYS = {
        "slug",
        "church_name",
        "pastor_name",
        "first_name",
        "city",
        "contact_hint",
        "ep_count",
        "angle",
        "positioning",
        "tier",
        "flags",
    }

    def test_all_prospects_have_required_keys(self):
        for p in gcp.PROSPECTS:
            missing = self.REQUIRED_KEYS - set(p.keys())
            assert not missing, f"{p.get('slug')} missing: {missing}"

    def test_every_angle_has_rationale(self):
        """Angle value in PROSPECTS must map to a rationale string."""
        for p in gcp.PROSPECTS:
            assert p["angle"] in gcp.ANGLE_RATIONALES, (
                f"{p['slug']} uses unknown angle '{p['angle']}'"
            )

    def test_slugs_are_unique(self):
        slugs = [p["slug"] for p in gcp.PROSPECTS]
        assert len(slugs) == len(set(slugs)), "duplicate slug in PROSPECTS"

    def test_flags_is_list_of_strings(self):
        for p in gcp.PROSPECTS:
            assert isinstance(p["flags"], list)
            for f in p["flags"]:
                assert isinstance(f, str)

    def test_tier_is_1_or_2(self):
        for p in gcp.PROSPECTS:
            assert p["tier"] in (1, 2)


# ---------------------------------------------------------------------------
# main() — writes PITCH.md files
# ---------------------------------------------------------------------------


@pytest.fixture
def run_in_tmp(tmp_path, monkeypatch):
    """Run main() with cwd = tmp_path so files land in tmp."""
    demo_dir = tmp_path / "demo" / "church-vertical"
    for p in gcp.PROSPECTS:
        (demo_dir / p["slug"]).mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestMain:
    def test_writes_one_pitch_per_prospect(self, run_in_tmp):
        gcp.main()
        for p in gcp.PROSPECTS:
            out = run_in_tmp / "demo" / "church-vertical" / p["slug"] / "PITCH.md"
            assert out.exists(), f"{p['slug']} PITCH.md not written"

    def test_pitch_contains_church_name(self, run_in_tmp):
        gcp.main()
        prospect = gcp.PROSPECTS[0]
        out = (
            run_in_tmp
            / "demo"
            / "church-vertical"
            / prospect["slug"]
            / "PITCH.md"
        )
        content = out.read_text(encoding="utf-8")
        assert prospect["church_name"] in content

    def test_pitch_contains_first_name_in_greeting(self, run_in_tmp):
        gcp.main()
        prospect = gcp.PROSPECTS[0]
        out = (
            run_in_tmp
            / "demo"
            / "church-vertical"
            / prospect["slug"]
            / "PITCH.md"
        )
        content = out.read_text(encoding="utf-8")
        assert f"Hey {prospect['first_name']}" in content

    def test_pitch_contains_positioning_paragraph(self, run_in_tmp):
        gcp.main()
        prospect = gcp.PROSPECTS[0]
        out = (
            run_in_tmp
            / "demo"
            / "church-vertical"
            / prospect["slug"]
            / "PITCH.md"
        )
        content = out.read_text(encoding="utf-8")
        # Positioning text is prospect-specific — must show up verbatim
        assert prospect["positioning"][:50] in content

    def test_pitch_contains_flags_block_when_flags_present(self, run_in_tmp):
        """Prospects with flags (e.g. SUBSPLASH_HOST) get a **Flags:** section."""
        gcp.main()
        flagged = [p for p in gcp.PROSPECTS if p["flags"]]
        assert flagged, "test setup requires at least one prospect with flags"
        prospect = flagged[0]
        out = (
            run_in_tmp
            / "demo"
            / "church-vertical"
            / prospect["slug"]
            / "PITCH.md"
        )
        content = out.read_text(encoding="utf-8")
        assert "**Flags:**" in content
        for flag in prospect["flags"]:
            assert flag in content

    def test_pitch_omits_flags_block_when_no_flags(self, run_in_tmp):
        gcp.main()
        unflagged = [p for p in gcp.PROSPECTS if not p["flags"]]
        assert unflagged
        prospect = unflagged[0]
        out = (
            run_in_tmp
            / "demo"
            / "church-vertical"
            / prospect["slug"]
            / "PITCH.md"
        )
        content = out.read_text(encoding="utf-8")
        assert "**Flags:**" not in content

    def test_tier_2_prospects_marked_in_header(self, run_in_tmp):
        gcp.main()
        t2 = [p for p in gcp.PROSPECTS if p["tier"] == 2]
        if not t2:
            pytest.skip("no tier 2 prospects in current table")
        prospect = t2[0]
        out = (
            run_in_tmp
            / "demo"
            / "church-vertical"
            / prospect["slug"]
            / "PITCH.md"
        )
        content = out.read_text(encoding="utf-8")
        assert "*(Tier 2)*" in content

    def test_pitch_leaves_wave_c_placeholders(self, run_in_tmp):
        """The skeleton should keep {{SERMON_TITLE}} etc. so fill_church_pitch
        knows what to replace later."""
        gcp.main()
        prospect = gcp.PROSPECTS[0]
        out = (
            run_in_tmp
            / "demo"
            / "church-vertical"
            / prospect["slug"]
            / "PITCH.md"
        )
        content = out.read_text(encoding="utf-8")
        assert "{{SERMON_TITLE}}" in content
        assert "{{BEST_CLIP_TITLE}}" in content
