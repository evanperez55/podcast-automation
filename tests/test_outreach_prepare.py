"""Tests for scripts/outreach_prepare.py — per-prospect outreach orchestrator.

Given a prospect slug, this script:
  1. Finds the latest processed episode output
  2. Curates the user-facing demo assets (clips + blog + thumbnail + quote cards)
  3. Uploads them to a Drive folder, sets 'anyone with link' viewer
  4. Parses the prospect's PITCH.md to extract email address, subject, body
  5. Substitutes the Drive link into the email body
  6. Creates a Gmail DRAFT (never sends) addressed to the prospect
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from scripts import outreach_prepare as op


# ---------------------------------------------------------------------------
# PITCH.md parsing
# ---------------------------------------------------------------------------


class TestParsePitch:
    """The parser must be resilient to the hand-edited PITCH.md variants in
    demo/church-vertical/ — contact line format varies by prospect."""

    def _minimal_pitch(self, email: str = "office@ex.com") -> str:
        return (
            f"# Test Prospect - Outreach Pitch\n\n"
            f"**Prospect:** Test\n"
            f"**Contact:** Office / **EMAIL: {email}**\n"
            f"\n---\n\n## Email\n\n"
            f"**Subject:** Made these from your sermon\n\n"
            f"Hey pastor,\n\n"
            f"I listened this week. Here it is:\n\n"
            f"[GOOGLE DRIVE LINK]\n\n"
            f"Inside you'll find clips.\n\n"
            f"Evan\n\n---\n\n## Follow-Up Email\n\nunused\n"
        )

    def test_extracts_email_address(self, tmp_path):
        p = tmp_path / "PITCH.md"
        p.write_text(self._minimal_pitch("pastor@example.com"))

        parsed = op.parse_pitch(p)
        assert parsed["email"] == "pastor@example.com"

    def test_extracts_subject(self, tmp_path):
        p = tmp_path / "PITCH.md"
        p.write_text(self._minimal_pitch())

        parsed = op.parse_pitch(p)
        assert parsed["subject"] == "Made these from your sermon"

    def test_body_spans_from_greeting_to_signature(self, tmp_path):
        p = tmp_path / "PITCH.md"
        p.write_text(self._minimal_pitch())

        parsed = op.parse_pitch(p)
        body = parsed["body"]
        assert body.startswith("Hey pastor,")
        assert "[GOOGLE DRIVE LINK]" in body
        assert "Evan" in body
        # Follow-up section must NOT leak into primary body
        assert "Follow-Up" not in body
        assert "## " not in body

    def test_missing_email_raises(self, tmp_path):
        p = tmp_path / "PITCH.md"
        p.write_text("# No email here\n\n**Contact:** Unknown\n")
        with pytest.raises(ValueError, match="email"):
            op.parse_pitch(p)


# ---------------------------------------------------------------------------
# Drive-link substitution
# ---------------------------------------------------------------------------


class TestInjectDriveLink:
    def test_replaces_placeholder_with_url(self):
        body = "Hey,\n\nCheck it:\n\n[GOOGLE DRIVE LINK]\n\nThanks"
        out = op.inject_drive_link(body, "https://drive.google.com/xyz")
        assert "https://drive.google.com/xyz" in out
        assert "[GOOGLE DRIVE LINK]" not in out

    def test_appends_link_if_no_placeholder(self):
        """Some pitches may not have the placeholder — append link near the
        top of the body so the prospect sees it without scrolling."""
        body = "Hey,\n\nI made a demo.\n\nThanks"
        out = op.inject_drive_link(body, "https://drive.google.com/xyz")
        assert "https://drive.google.com/xyz" in out


# ---------------------------------------------------------------------------
# Demo asset curation
# ---------------------------------------------------------------------------


class TestCollectDemoAssets:
    """Selects user-facing artifacts from the episode output dir — excludes
    internal JSON (transcripts, analysis, compliance reports)."""

    def _make_ep_dir(self, tmp_path: Path) -> Path:
        ep = tmp_path / "ep_123"
        clips = ep / "clips"
        clips.mkdir(parents=True)

        # User-facing files we WANT
        (clips / "foo_clip_01_subtitle.mp4").write_bytes(b"v")
        (clips / "foo_clip_02_subtitle.mp4").write_bytes(b"v")
        (ep / "ep123_20260413_blog_post.md").write_text("# Blog")
        (ep / "foo_20260413_thumbnail.png").write_bytes(b"img")
        (ep / "quote_card_1.png").write_bytes(b"img")
        (ep / "quote_card_2.png").write_bytes(b"img")
        (ep / "foo_20260413_episode.mp4").write_bytes(b"vid")

        # Internal files we DON'T want
        (ep / "foo_20260413_transcript.json").write_text("{}")
        (ep / "foo_20260413_analysis.json").write_text("{}")
        (ep / "foo_20260413_censored.wav").write_bytes(b"wav")
        (ep / "foo_20260413_censored.mp3").write_bytes(b"mp3")
        (ep / "compliance_report_123_20260413.json").write_text("{}")
        (clips / "foo_clip_01.wav").write_bytes(b"raw")  # pre-video raw clip
        return ep

    def test_includes_subtitle_clips(self, tmp_path):
        ep = self._make_ep_dir(tmp_path)
        assets = op.collect_demo_assets(ep)
        names = {a.name for a in assets}
        assert "foo_clip_01_subtitle.mp4" in names
        assert "foo_clip_02_subtitle.mp4" in names

    def test_excludes_internal_json(self, tmp_path):
        ep = self._make_ep_dir(tmp_path)
        assets = op.collect_demo_assets(ep)
        names = {a.name for a in assets}
        for bad in [
            "foo_20260413_transcript.json",
            "foo_20260413_analysis.json",
            "compliance_report_123_20260413.json",
        ]:
            assert bad not in names, f"{bad} must not ship to prospects"

    def test_includes_blog_thumbnail_quotes(self, tmp_path):
        ep = self._make_ep_dir(tmp_path)
        assets = op.collect_demo_assets(ep)
        names = {a.name for a in assets}
        assert "ep123_20260413_blog_post.md" in names
        assert "foo_20260413_thumbnail.png" in names
        assert "quote_card_1.png" in names

    def test_excludes_full_episode_video_by_default(self, tmp_path):
        """Full episode MP4 is 200+ MB and the prospect already has the audio
        on their platform — skip it to keep Drive uploads snappy."""
        ep = self._make_ep_dir(tmp_path)
        assets = op.collect_demo_assets(ep)
        names = {a.name for a in assets}
        assert "foo_20260413_episode.mp4" not in names

    def test_excludes_raw_audio(self, tmp_path):
        """Prospects get the finished episode MP4, not the WAV/MP3 intermediates."""
        ep = self._make_ep_dir(tmp_path)
        assets = op.collect_demo_assets(ep)
        names = {a.name for a in assets}
        assert "foo_20260413_censored.wav" not in names
        assert "foo_20260413_censored.mp3" not in names
        assert "foo_clip_01.wav" not in names

    def test_keeps_only_latest_run_when_multiple_timestamps_present(self, tmp_path):
        """Some ep_dirs accumulate outputs from multiple processing runs (e.g.
        B011 reruns left 4 copies of everything in one directory). Prospects
        must see only the latest run — otherwise they get 10 clips instead of 5."""
        ep = tmp_path / "ep_multi"
        clips = ep / "clips"
        clips.mkdir(parents=True)

        # OLD run (20260413_195245) + NEW run (20260413_220958) side by side
        (clips / "foo_20260413_195245_censored_clip_01_subtitle.mp4").write_bytes(
            b"old"
        )
        (clips / "foo_20260413_195245_censored_clip_02_subtitle.mp4").write_bytes(
            b"old"
        )
        (clips / "foo_20260413_220958_censored_clip_01_subtitle.mp4").write_bytes(
            b"new"
        )
        (clips / "foo_20260413_220958_censored_clip_02_subtitle.mp4").write_bytes(
            b"new"
        )
        (ep / "ep18933019_20260413_195245_blog_post.md").write_text("old blog")
        (ep / "ep18933019_20260413_220958_blog_post.md").write_text("new blog")
        (ep / "foo_20260413_195245_thumbnail.png").write_bytes(b"old")
        (ep / "foo_20260413_220958_thumbnail.png").write_bytes(b"new")
        # Quote cards have no timestamp — last write wins, only one set exists
        (ep / "quote_card_1.png").write_bytes(b"img")
        (ep / "quote_card_2.png").write_bytes(b"img")

        assets = op.collect_demo_assets(ep)
        names = {a.name for a in assets}

        # OLD timestamp files must be filtered out
        assert "foo_20260413_195245_censored_clip_01_subtitle.mp4" not in names
        assert "ep18933019_20260413_195245_blog_post.md" not in names
        assert "foo_20260413_195245_thumbnail.png" not in names

        # NEW timestamp files are kept
        assert "foo_20260413_220958_censored_clip_01_subtitle.mp4" in names
        assert "ep18933019_20260413_220958_blog_post.md" in names
        assert "foo_20260413_220958_thumbnail.png" in names

        # Timestamp-free files (quote cards) are always kept
        assert "quote_card_1.png" in names
        assert "quote_card_2.png" in names


# ---------------------------------------------------------------------------
# End-to-end orchestration
# ---------------------------------------------------------------------------


class TestPrepareOne:
    """prepare_one() wires the pieces. Drive + Gmail are both mocked."""

    def _write_pitch(self, tmp_path: Path) -> Path:
        pitch_dir = tmp_path / "demo" / "church-vertical" / "test-slug"
        pitch_dir.mkdir(parents=True)
        p = pitch_dir / "PITCH.md"
        p.write_text(
            "# Test - Outreach Pitch\n\n"
            "**Contact:** X / **EMAIL: pastor@x.com**\n"
            "\n---\n\n## Email\n\n"
            "**Subject:** Subject here\n\n"
            "Hey,\n\n[GOOGLE DRIVE LINK]\n\nEvan\n\n---\n\n## Follow-Up\n\nx\n"
        )
        return p

    def _write_ep(self, tmp_path: Path) -> Path:
        ep = tmp_path / "output" / "test-slug" / "ep_1"
        (ep / "clips").mkdir(parents=True)
        (ep / "clips" / "clip_01_subtitle.mp4").write_bytes(b"v")
        (ep / "blog_post.md").write_text("# blog")
        return ep

    def test_full_flow_creates_draft_with_drive_link(self, tmp_path, monkeypatch):
        """prepare_one → Drive folder created, uploaded, link injected, Gmail draft made."""
        self._write_pitch(tmp_path)
        self._write_ep(tmp_path)

        # Point the orchestrator's filesystem lookups at tmp_path
        monkeypatch.setattr(op, "DEMO_ROOT", tmp_path / "demo" / "church-vertical")
        monkeypatch.setattr(op, "OUTPUT_ROOT", tmp_path / "output")

        fake_drive = MagicMock()
        fake_drive.upload_folder.return_value = (
            "https://drive.google.com/drive/folders/abc"
        )
        fake_gmail = MagicMock()
        fake_gmail.create_draft.return_value = "draft-1"

        result = op.prepare_one(
            "test-slug",
            drive=fake_drive,
            gmail=fake_gmail,
            dry_run=False,
            skip_verify=True,  # test fixture doesn't include real clip assets
        )

        assert result["draft_id"] == "draft-1"
        assert result["drive_link"].endswith("abc")

        # Drive upload happened with the ep_dir contents
        fake_drive.upload_folder.assert_called_once()
        upload_args = fake_drive.upload_folder.call_args
        assert upload_args.kwargs.get("folder_name") or upload_args.args[1]

        # Gmail draft was created with the recipient, subject, and drive link
        # substituted into the body
        fake_gmail.create_draft.assert_called_once()
        gmail_kwargs = fake_gmail.create_draft.call_args.kwargs
        assert gmail_kwargs["to"] == "pastor@x.com"
        assert gmail_kwargs["subject"] == "Subject here"
        assert "https://drive.google.com/drive/folders/abc" in gmail_kwargs["body"]
        assert "[GOOGLE DRIVE LINK]" not in gmail_kwargs["body"]

    def test_dry_run_skips_both_network_calls(self, tmp_path, monkeypatch):
        self._write_pitch(tmp_path)
        self._write_ep(tmp_path)

        monkeypatch.setattr(op, "DEMO_ROOT", tmp_path / "demo" / "church-vertical")
        monkeypatch.setattr(op, "OUTPUT_ROOT", tmp_path / "output")

        fake_drive = MagicMock()
        fake_gmail = MagicMock()
        fake_gmail.create_draft.return_value = "DRY_RUN"

        result = op.prepare_one(
            "test-slug", drive=fake_drive, gmail=fake_gmail, dry_run=True
        )

        fake_drive.upload_folder.assert_not_called()
        # Gmail create_draft is still called but with dry_run=True so it
        # does not hit the network.
        assert fake_gmail.create_draft.call_args.kwargs["dry_run"] is True
        assert result["draft_id"] == "DRY_RUN"

    def test_missing_pitch_raises(self, tmp_path, monkeypatch):
        monkeypatch.setattr(op, "DEMO_ROOT", tmp_path / "demo" / "church-vertical")
        monkeypatch.setattr(op, "OUTPUT_ROOT", tmp_path / "output")

        with pytest.raises(FileNotFoundError, match="PITCH"):
            op.prepare_one(
                "nonexistent", drive=MagicMock(), gmail=MagicMock(), dry_run=True
            )

    def test_existing_drive_link_skips_upload(self, tmp_path, monkeypatch):
        """Recovery path: if the Drive upload already happened on a prior run,
        pass drive_link= to skip re-upload and only create the Gmail draft."""
        self._write_pitch(tmp_path)
        self._write_ep(tmp_path)
        monkeypatch.setattr(op, "DEMO_ROOT", tmp_path / "demo" / "church-vertical")
        monkeypatch.setattr(op, "OUTPUT_ROOT", tmp_path / "output")

        fake_drive = MagicMock()
        fake_gmail = MagicMock()
        fake_gmail.create_draft.return_value = "draft-99"

        existing_link = "https://drive.google.com/drive/folders/PRE_EXISTING"
        result = op.prepare_one(
            "test-slug",
            drive=fake_drive,
            gmail=fake_gmail,
            dry_run=False,
            drive_link=existing_link,
        )

        # Upload MUST be skipped — the whole point of the flag is recovery
        fake_drive.upload_folder.assert_not_called()
        assert result["drive_link"] == existing_link
        # Draft was created with the pre-existing link injected into the body
        gmail_kwargs = fake_gmail.create_draft.call_args.kwargs
        assert existing_link in gmail_kwargs["body"]


# ---------------------------------------------------------------------------
# Staging writers — promised-but-missing artifacts (social/chapters/transcript)
# ---------------------------------------------------------------------------


class TestSocialCaptionsWriter:
    """The PITCH.md email promises 'social captions written per platform' — the
    data already lives in analysis.json["social_captions"]. The staging writer
    surfaces it as a clean markdown file so the prospect can copy/paste."""

    def test_writes_one_section_per_platform(self, tmp_path):
        analysis = {
            "social_captions": {
                "youtube": "YT body",
                "instagram": "IG body",
                "twitter": "TW body",
                "tiktok": "TT body",
            }
        }
        out = tmp_path / "social_captions.md"
        op._write_social_captions_md(analysis, out)
        text = out.read_text(encoding="utf-8")
        assert "YouTube" in text
        assert "YT body" in text
        assert "Instagram" in text
        assert "IG body" in text
        assert "Twitter" in text or "X" in text
        assert "TW body" in text
        assert "TikTok" in text
        assert "TT body" in text

    def test_skips_missing_or_empty_platforms(self, tmp_path):
        analysis = {"social_captions": {"youtube": "YT only"}}
        out = tmp_path / "social_captions.md"
        op._write_social_captions_md(analysis, out)
        text = out.read_text(encoding="utf-8")
        assert "YT only" in text
        # Headers for absent platforms must not appear (would imply empty content)
        assert "TikTok" not in text
        assert "Instagram" not in text

    def test_no_file_when_no_captions(self, tmp_path):
        out = tmp_path / "social_captions.md"
        op._write_social_captions_md({}, out)
        assert not out.exists(), "skip silently if no captions to write"


class TestChaptersWriter:
    """Chapters live in analysis.json['chapters'] as
    {start_timestamp, title, start_seconds}. Output is a timestamped TOC
    so the recipient can drop it into YouTube / show notes / podcast app."""

    def test_writes_timestamp_and_title_per_chapter(self, tmp_path):
        analysis = {
            "chapters": [
                {"start_timestamp": "00:00:00", "title": "Intro", "start_seconds": 0.0},
                {
                    "start_timestamp": "00:05:30",
                    "title": "Acts 1 setup",
                    "start_seconds": 330.0,
                },
                {
                    "start_timestamp": "00:42:11",
                    "title": "Closing prayer",
                    "start_seconds": 2531.0,
                },
            ]
        }
        out = tmp_path / "chapters.md"
        op._write_chapters_md(analysis, out)
        text = out.read_text(encoding="utf-8")
        assert "00:00:00" in text
        assert "Intro" in text
        assert "00:42:11" in text
        assert "Closing prayer" in text

    def test_no_file_when_no_chapters(self, tmp_path):
        out = tmp_path / "chapters.md"
        op._write_chapters_md({"chapters": []}, out)
        assert not out.exists()


class TestTranscriptWriter:
    """transcript.json is whisper output (segments with start/end/text). The
    PITCH email promises a 'searchable transcript of the whole sermon' — ship
    it as a readable .txt with [HH:MM:SS] segment timestamps."""

    def test_writes_timestamped_segments(self, tmp_path):
        transcript = {
            "segments": [
                {"start": 0.0, "end": 5.2, "text": " Welcome to Redeemer."},
                {"start": 5.2, "end": 12.8, "text": " Today we're in Acts 1."},
                {"start": 330.0, "end": 335.0, "text": " Let's read together."},
            ]
        }
        out = tmp_path / "transcript.txt"
        op._write_transcript_txt(transcript, out)
        text = out.read_text(encoding="utf-8")
        # 0s → 00:00:00; 330s → 00:05:30
        assert "[00:00:00]" in text
        assert "[00:05:30]" in text
        assert "Welcome to Redeemer." in text
        assert "Let's read together." in text

    def test_strips_blank_segments(self, tmp_path):
        transcript = {
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "  "},
                {"start": 1.0, "end": 2.0, "text": " real text "},
            ]
        }
        out = tmp_path / "transcript.txt"
        op._write_transcript_txt(transcript, out)
        text = out.read_text(encoding="utf-8")
        assert "real text" in text
        # No empty bracket lines
        assert "[00:00:00] \n" not in text

    def test_no_file_when_no_segments(self, tmp_path):
        out = tmp_path / "transcript.txt"
        op._write_transcript_txt({"segments": []}, out)
        assert not out.exists()


class TestStageAssetsIncludesNewFiles:
    """End-to-end: _stage_assets reads analysis.json + transcript.json from
    ep_dir and writes the three derived files into staging. This is the
    contract the email body promises."""

    def _make_ep_dir_with_data(self, tmp_path: Path) -> Path:
        ep = tmp_path / "ep_42"
        (ep / "clips").mkdir(parents=True)
        # One clip + blog so the existing staging logic has something to copy
        (ep / "clips" / "clip_01_subtitle.mp4").write_bytes(b"v")
        (ep / "epX_20260423_blog_post.md").write_text("# blog", encoding="utf-8")
        # Data sources for the new writers
        (ep / "epX_20260423_analysis.json").write_text(
            json.dumps(
                {
                    "social_captions": {
                        "youtube": "YT desc",
                        "twitter": "TW post",
                    },
                    "chapters": [
                        {
                            "start_timestamp": "00:00:00",
                            "title": "Intro",
                            "start_seconds": 0.0,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (ep / "epX_20260423_transcript.json").write_text(
            json.dumps(
                {"segments": [{"start": 0.0, "end": 1.5, "text": "hello world"}]}
            ),
            encoding="utf-8",
        )
        return ep

    def test_staging_writes_social_chapters_transcript(self, tmp_path):
        ep = self._make_ep_dir_with_data(tmp_path)
        staging = tmp_path / "staging"
        op._stage_assets(ep, staging)

        assert (staging / "social_captions.md").exists(), (
            "social_captions.md must be in Drive folder — promised in email"
        )
        assert (staging / "chapters.md").exists(), (
            "chapters.md must be in Drive folder — promised in email"
        )
        assert (staging / "transcript.txt").exists(), (
            "transcript.txt must be in Drive folder — promised in email"
        )

        # Contents are sane
        assert "YT desc" in (staging / "social_captions.md").read_text(encoding="utf-8")
        assert "Intro" in (staging / "chapters.md").read_text(encoding="utf-8")
        assert "hello world" in (staging / "transcript.txt").read_text(encoding="utf-8")

    def test_staging_skips_missing_data_sources_gracefully(self, tmp_path):
        """If analysis.json / transcript.json are missing (older episode),
        staging must not crash — just skip the derived files."""
        ep = tmp_path / "ep_43"
        (ep / "clips").mkdir(parents=True)
        (ep / "clips" / "clip_01_subtitle.mp4").write_bytes(b"v")
        (ep / "epY_blog_post.md").write_text("# blog", encoding="utf-8")
        # Intentionally NO analysis.json / transcript.json

        staging = tmp_path / "staging"
        op._stage_assets(ep, staging)  # must not raise

        assert not (staging / "social_captions.md").exists()
        assert not (staging / "chapters.md").exists()
        assert not (staging / "transcript.txt").exists()
