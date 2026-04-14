"""Tests for scripts/fill_church_pitch.py — Wave C pitch filler."""

from __future__ import annotations

import json
import sys

import pytest

from scripts import fill_church_pitch as fcp


# ---------------------------------------------------------------------------
# Pure formatting helpers
# ---------------------------------------------------------------------------


class TestFormatters:
    def test_fmt_mmss_rounds_to_int_seconds(self):
        assert fcp.fmt_mmss(45) == "0:45"
        assert (
            fcp.fmt_mmss(45.7) == "0:45"
        )  # rounds down to int, no floating formatting

    def test_fmt_mmss_handles_over_one_minute(self):
        assert fcp.fmt_mmss(65) == "1:05"
        assert fcp.fmt_mmss(125) == "2:05"

    def test_fmt_mmss_zero_pads_seconds(self):
        assert fcp.fmt_mmss(61) == "1:01"
        assert fcp.fmt_mmss(60) == "1:00"

    def test_fmt_timestamp_range_strips_leading_hour(self):
        """Short sermons under an hour should display as MM:SS-MM:SS."""
        assert fcp.fmt_timestamp_range("00:05:30", "00:06:15") == "5:30-6:15"

    def test_fmt_timestamp_range_keeps_hour_when_nonzero(self):
        """If clip is 1h+ into the sermon, preserve full H:MM:SS format."""
        assert fcp.fmt_timestamp_range("01:05:30", "01:06:15") == "01:05:30-01:06:15"


# ---------------------------------------------------------------------------
# main() — end-to-end fill
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_prospect(tmp_path, monkeypatch):
    """Set up a fake prospect with output/ and demo/church-vertical/ folders."""
    slug = "test-slug"

    # Episode output + analysis
    ep_dir = tmp_path / "output" / slug / "ep_foo_20260101_120000"
    ep_dir.mkdir(parents=True)
    analysis = {
        "episode_title": "The Test Sermon",
        "hot_take": "Testing is holy.",
        "best_clips": [
            {
                "start": "00:05:00",
                "end": "00:05:30",
                "duration_seconds": 30,
                "suggested_title": "Clip One",
                "hook_caption": "Hook 1",
                "description": "first clip",
                "why_interesting": "because reasons",
            },
            {
                "start": "00:10:00",
                "end": "00:11:30",
                "duration_seconds": 90,
                "suggested_title": "Clip Two",
                "hook_caption": "Hook 2",
                "description": "second clip",
                "why_interesting": "the main point",
            },
        ],
    }
    (ep_dir / "foo_analysis.json").write_text(json.dumps(analysis), encoding="utf-8")

    # Pitch skeleton
    pitch_dir = tmp_path / "demo" / "church-vertical" / slug
    pitch_dir.mkdir(parents=True)
    skeleton = (
        "# Test - Outreach Pitch\n\n"
        '**Episode referenced:** "{{SERMON_TITLE}}" *(processed TBD)*\n'
        "**Drive folder:** Upload from `output/test-slug/{{EP_DIR}}/`\n\n"
        'Subject: Made these from your "{{SERMON_TITLE}}" sermon\n\n'
        'Lead: "{{BEST_CLIP_TITLE}}" ({{CLIP_TIMESTAMP}}). {{WHY_THIS_CLIP_WORKS}}\n\n'
        "Context: {{SPECIFIC_MOMENT_REFERENCE}}\n\n"
        "- {{NUM_CLIPS}} vertical clips\n\n"
        "1. {{CLIP_1_TITLE}} ({{CLIP_1_DURATION}})\n"
        "2. {{CLIP_2_TITLE}} ({{CLIP_2_DURATION}})\n"
        "3. {{CLIP_3_TITLE}} ({{CLIP_3_DURATION}})\n\n"
        "- [ ] Process latest episode: `uv run main.py --client test-slug latest`\n"
    )
    (pitch_dir / "PITCH.md").write_text(skeleton, encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    return {"slug": slug, "tmp": tmp_path, "ep_dir": ep_dir, "pitch_dir": pitch_dir}


class TestMain:
    def test_substitutes_sermon_title(self, fake_prospect, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["fill", fake_prospect["slug"]])
        rc = fcp.main()
        assert rc == 0
        pitch = (fake_prospect["pitch_dir"] / "PITCH.md").read_text(encoding="utf-8")
        assert "The Test Sermon" in pitch
        assert "{{SERMON_TITLE}}" not in pitch

    def test_fills_lead_clip_fields(self, fake_prospect, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["fill", fake_prospect["slug"]])
        fcp.main()
        pitch = (fake_prospect["pitch_dir"] / "PITCH.md").read_text(encoding="utf-8")
        assert "Clip One" in pitch
        assert "5:00-5:30" in pitch

    def test_lead_clip_flag_selects_different_clip(self, fake_prospect, monkeypatch):
        monkeypatch.setattr(
            sys, "argv", ["fill", fake_prospect["slug"], "--lead-clip", "2"]
        )
        fcp.main()
        pitch = (fake_prospect["pitch_dir"] / "PITCH.md").read_text(encoding="utf-8")
        # Clip 2 is the lead now
        assert 'Lead: "Clip Two"' in pitch
        assert "10:00-11:30" in pitch

    def test_invalid_lead_clip_returns_error(self, fake_prospect, monkeypatch, capsys):
        monkeypatch.setattr(
            sys, "argv", ["fill", fake_prospect["slug"], "--lead-clip", "99"]
        )
        rc = fcp.main()
        assert rc == 1
        err = capsys.readouterr().err
        assert "out of range" in err

    def test_missing_output_dir_returns_error(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["fill", "does-not-exist"])
        rc = fcp.main()
        assert rc == 1
        err = capsys.readouterr().err
        assert "No output directory" in err

    def test_missing_analysis_returns_error(self, fake_prospect, monkeypatch, capsys):
        # Remove the analysis file
        for f in fake_prospect["ep_dir"].glob("*_analysis.json"):
            f.unlink()
        monkeypatch.setattr(sys, "argv", ["fill", fake_prospect["slug"]])
        rc = fcp.main()
        assert rc == 1
        err = capsys.readouterr().err
        assert "No analysis.json" in err

    def test_fills_per_clip_durations(self, fake_prospect, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["fill", fake_prospect["slug"]])
        fcp.main()
        pitch = (fake_prospect["pitch_dir"] / "PITCH.md").read_text(encoding="utf-8")
        assert "Clip One (0:30)" in pitch
        assert "Clip Two (1:30)" in pitch

    def test_fills_unused_clip_slots_with_na(self, fake_prospect, monkeypatch):
        """Analysis has 2 clips, template references up to 3 — slot 3 gets '(n/a)'."""
        monkeypatch.setattr(sys, "argv", ["fill", fake_prospect["slug"]])
        fcp.main()
        pitch = (fake_prospect["pitch_dir"] / "PITCH.md").read_text(encoding="utf-8")
        assert "(n/a)" in pitch
        assert "--" in pitch  # placeholder duration

    def test_marks_episode_processed_checkbox(self, fake_prospect, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["fill", fake_prospect["slug"]])
        fcp.main()
        pitch = (fake_prospect["pitch_dir"] / "PITCH.md").read_text(encoding="utf-8")
        assert "[x] Episode processed:" in pitch
        assert "[ ] Process latest episode" not in pitch

    def test_custom_moment_override(self, fake_prospect, monkeypatch):
        monkeypatch.setattr(
            sys,
            "argv",
            ["fill", fake_prospect["slug"], "--moment", "the bit about coffee"],
        )
        fcp.main()
        pitch = (fake_prospect["pitch_dir"] / "PITCH.md").read_text(encoding="utf-8")
        assert "the bit about coffee" in pitch
        # Default hot_take fallback not used
        assert "Testing is holy" not in pitch

    def test_picks_most_recent_episode_dir(self, fake_prospect, monkeypatch):
        """If multiple ep_* dirs exist, pick the most recently modified one."""
        import time

        slug = fake_prospect["slug"]
        older_dir = fake_prospect["tmp"] / "output" / slug / "ep_bar_20260101_000000"
        older_dir.mkdir()
        (older_dir / "bar_analysis.json").write_text(
            json.dumps(
                {
                    "episode_title": "OLDER Sermon",
                    "best_clips": [
                        {
                            "start": "00:00:10",
                            "end": "00:00:20",
                            "duration_seconds": 10,
                            "suggested_title": "Old Clip",
                            "description": "old",
                            "why_interesting": "old",
                            "hook_caption": "old",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        # Make older_dir actually older by touching mtime
        old_time = time.time() - 10000
        import os

        os.utime(older_dir, (old_time, old_time))

        monkeypatch.setattr(sys, "argv", ["fill", slug])
        fcp.main()
        pitch = (fake_prospect["pitch_dir"] / "PITCH.md").read_text(encoding="utf-8")
        assert "The Test Sermon" in pitch
        assert "OLDER Sermon" not in pitch
