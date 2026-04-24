"""Tests for scripts/outreach_verify.py — pre-upload smoke test battery.

Focused on the new checks added 2026-04-23 to prevent re-occurrence of
B023 (Drive transcode hang from bt709 mismatch) and the staging↔PITCH
mismatch that caused two re-upload cycles. Existing checks (filename
hygiene, clip count, duration window, logo bleed) are exercised
end-to-end via outreach_prepare integration tests.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch


from scripts import outreach_verify as ov


# ---------------------------------------------------------------------------
# Color metadata check
# ---------------------------------------------------------------------------


class TestClipColorMetadata:
    """B023: lavfi `color=` source defaults to bt470m transfer; H.264 SPS
    marks bt709 primaries → Drive's transcoder stalls. The check fails any
    clip whose color_transfer/primaries/space isn't bt709."""

    def _ffprobe_response(self, transfer="bt709", primaries="bt709", space="bt709"):
        """Mock ffprobe JSON output shape."""
        return json.dumps(
            {
                "streams": [
                    {
                        "color_transfer": transfer,
                        "color_primaries": primaries,
                        "color_space": space,
                        "color_range": "tv",
                    }
                ]
            }
        )

    @patch("scripts.outreach_verify.subprocess.run")
    def test_passes_when_all_bt709(self, mock_run, tmp_path):
        clip = tmp_path / "clip.mp4"
        clip.write_bytes(b"x")
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=self._ffprobe_response(), stderr=""
        )
        result = ov._check_clip_color_metadata(clip)
        assert result == "OK", f"expected OK, got {result!r}"

    @patch("scripts.outreach_verify.subprocess.run")
    def test_fails_on_bt470m_transfer(self, mock_run, tmp_path):
        """The exact B023 case — primaries=bt709 but transfer=bt470m."""
        clip = tmp_path / "clip.mp4"
        clip.write_bytes(b"x")
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=self._ffprobe_response(transfer="bt470m"),
            stderr="",
        )
        result = ov._check_clip_color_metadata(clip)
        assert result is not None and result != "OK"
        assert "transfer" in result.lower() or "bt470m" in result.lower()

    @patch("scripts.outreach_verify.subprocess.run")
    def test_fails_on_unspecified_metadata(self, mock_run, tmp_path):
        """Metadata fields missing entirely (older encoder runs) → fail."""
        clip = tmp_path / "clip.mp4"
        clip.write_bytes(b"x")
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps({"streams": [{}]}), stderr=""
        )
        result = ov._check_clip_color_metadata(clip)
        assert result is not None and result != "OK"

    @patch("scripts.outreach_verify.subprocess.run")
    def test_returns_none_on_ffprobe_failure(self, mock_run, tmp_path):
        """ffprobe failure → None (skip the check, don't false-fail)."""
        clip = tmp_path / "clip.mp4"
        clip.write_bytes(b"x")
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="ffprobe error"
        )
        result = ov._check_clip_color_metadata(clip)
        assert result is None


# ---------------------------------------------------------------------------
# PITCH ↔ PACKAGE parity check
# ---------------------------------------------------------------------------


class TestPitchParity:
    """The email body lists what's "Inside:" the Drive folder. Each promised
    item must actually exist in the staged content. Caught the missing
    social_captions/chapters/transcript files that bit us 2026-04-23."""

    def test_all_promises_satisfied(self):
        bullets = [
            "5 short vertical clips with burned-in captions",
            "A devotional-style blog post",
            "Social captions written per platform",
            "Chapter markers for the full sermon",
            "A searchable transcript of the whole sermon",
            "Thumbnail and quote cards",
        ]
        staged = {
            "clips/clip_01_topic.mp4",
            "blog_post.md",
            "social_captions.md",
            "chapters.md",
            "transcript.txt",
            "thumbnail.png",
            "quote_card_1.png",
        }
        missing = ov._check_pitch_parity(bullets, staged)
        assert missing == [], f"expected no missing, got {missing}"

    def test_detects_missing_social_captions(self):
        """The exact 2026-04-23 bug — bullet promised but file absent."""
        bullets = ["Social captions written per platform"]
        staged = {"clips/clip_01.mp4", "blog_post.md"}  # no social_captions.md
        missing = ov._check_pitch_parity(bullets, staged)
        assert len(missing) == 1
        assert "social" in missing[0].lower()

    def test_detects_missing_chapters(self):
        bullets = ["Chapter markers for the full sermon"]
        staged = {"blog_post.md"}
        missing = ov._check_pitch_parity(bullets, staged)
        assert len(missing) == 1
        assert "chapter" in missing[0].lower()

    def test_detects_missing_transcript(self):
        bullets = ["A searchable transcript of the whole sermon"]
        staged = {"blog_post.md"}
        missing = ov._check_pitch_parity(bullets, staged)
        assert len(missing) == 1
        assert "transcript" in missing[0].lower()

    def test_unrecognized_bullet_is_skipped_not_flagged(self):
        """If a bullet doesn't match any known artifact pattern, skip it
        rather than mark as missing — pitch wording can vary."""
        bullets = ["Some unrelated marketing prose about our process"]
        staged = {"blog_post.md"}
        missing = ov._check_pitch_parity(bullets, staged)
        assert missing == []

    def test_quote_cards_promise_matches_quote_card_files(self):
        bullets = ["Quote cards"]
        staged = {"quote_card_1.png", "quote_card_2.png"}
        missing = ov._check_pitch_parity(bullets, staged)
        assert missing == []


# ---------------------------------------------------------------------------
# PITCH "Inside:" section parser
# ---------------------------------------------------------------------------


class TestExtractPitchPromises:
    """Pulls bullets from the 'Inside:' section of a PITCH.md."""

    def test_extracts_dash_bullets(self, tmp_path):
        pitch = tmp_path / "PITCH.md"
        pitch.write_text(
            "# Pitch\n\n[GOOGLE DRIVE LINK]\n\nInside:\n"
            "- 5 short vertical clips with burned-in captions\n"
            "- A devotional-style blog post\n"
            "- Social captions written per platform\n"
            "\nThe clip I'd lead with is...\n",
            encoding="utf-8",
        )
        bullets = ov._extract_pitch_promises(pitch)
        assert len(bullets) == 3
        assert any("clips" in b for b in bullets)
        assert any("blog post" in b for b in bullets)
        assert any("Social captions" in b for b in bullets)

    def test_returns_empty_list_when_no_inside_section(self, tmp_path):
        pitch = tmp_path / "PITCH.md"
        pitch.write_text("# Pitch\n\nNo bullet list here.\n", encoding="utf-8")
        assert ov._extract_pitch_promises(pitch) == []

    def test_returns_empty_list_when_pitch_missing(self, tmp_path):
        assert ov._extract_pitch_promises(tmp_path / "nope.md") == []


# ---------------------------------------------------------------------------
# Integration: verify_one wires both checks
# ---------------------------------------------------------------------------


class TestVerifyOneIntegration:
    """Sanity check that verify_one() calls into the new checks. Heavy
    fixture work — just confirms the new findings appear in the output."""

    def _seed(self, tmp_path: Path, slug: str = "redeemer-city-church-tampa") -> Path:
        """Build a minimal output/<slug>/<ep_dir>/ tree under tmp_path."""
        out = tmp_path / "output" / slug
        ep = out / "ep_test_20260423_120000"
        (ep / "clips" / "final").mkdir(parents=True)
        (ep / "clips" / "final" / "clip_01_topic.mp4").write_bytes(b"x")
        (ep / "ep_test_thumbnail.png").write_bytes(b"x")
        (ep / "ep_test_analysis.json").write_text(
            json.dumps(
                {
                    "best_clips": [{"title": "Clip A"}],
                    "social_captions": {"youtube": "x"},
                    "chapters": [{"start_timestamp": "00:00:00", "title": "Intro"}],
                }
            ),
            encoding="utf-8",
        )
        (ep / "ep_test_transcript.json").write_text(
            json.dumps({"segments": [{"start": 0.0, "text": "hello"}]}),
            encoding="utf-8",
        )
        (ep / "ep_test_blog_post.md").write_text("# blog", encoding="utf-8")
        return ep

    @patch("scripts.outreach_verify.activate_client")
    @patch("scripts.outreach_verify._latest_ep_dir")
    @patch("scripts.outreach_verify._check_clip_color_metadata", return_value="OK")
    @patch("scripts.outreach_verify._get_duration", return_value=60.0)
    def test_verify_one_includes_color_check(
        self, mock_dur, mock_color, mock_ep, mock_act, tmp_path
    ):
        ep = self._seed(tmp_path)
        mock_ep.return_value = ep
        findings = ov.verify_one("redeemer-city-church-tampa")
        check_names = [f.check for f in findings]
        assert "clip_color_metadata" in check_names

    @patch("scripts.outreach_verify.activate_client")
    @patch("scripts.outreach_verify._latest_ep_dir")
    @patch("scripts.outreach_verify._check_clip_color_metadata", return_value="OK")
    @patch("scripts.outreach_verify._get_duration", return_value=60.0)
    def test_verify_one_includes_pitch_parity_when_pitch_exists(
        self, mock_dur, mock_color, mock_ep, mock_act, tmp_path, monkeypatch
    ):
        ep = self._seed(tmp_path)
        mock_ep.return_value = ep
        # Drop a PITCH.md under the demo dir so the parity check runs
        pitch_dir = tmp_path / "demo" / "church-vertical" / "redeemer-city-church-tampa"
        pitch_dir.mkdir(parents=True)
        (pitch_dir / "PITCH.md").write_text(
            "# Pitch\n\nInside:\n"
            "- 5 vertical clips\n"
            "- A devotional-style blog post\n"
            "- Social captions written per platform\n"
            "- Chapter markers\n"
            "- A searchable transcript\n"
            "- Thumbnail\n",
            encoding="utf-8",
        )
        # Point the verifier's BASE_DIR at tmp_path so it finds the PITCH
        from config import Config

        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        findings = ov.verify_one("redeemer-city-church-tampa")
        check_names = [f.check for f in findings]
        assert "pitch_parity" in check_names
