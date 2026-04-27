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


class TestInjectPreviewLink:
    def test_replaces_placeholder_with_url(self):
        body = "Hey,\n\nLook:\n\n[PREVIEW URL]\n\nThanks"
        out = op.inject_preview_link(body, "https://episodespreview.com/x/")
        assert "https://episodespreview.com/x/" in out
        assert "[PREVIEW URL]" not in out

    def test_inserts_above_drive_link_when_no_preview_placeholder(self):
        """No [PREVIEW URL] placeholder but a Drive placeholder exists —
        preview line should land ABOVE the Drive link in the email so the
        polished page is the first thing the prospect clicks."""
        body = "Hey,\n\n[GOOGLE DRIVE LINK]\n\nThanks"
        out = op.inject_preview_link(body, "https://episodespreview.com/x/")
        assert "https://episodespreview.com/x/" in out
        # Preview must appear before the Drive placeholder in the rendered body
        assert out.index("episodespreview.com") < out.index("[GOOGLE DRIVE LINK]")

    def test_prepends_when_no_placeholders_present(self):
        """No placeholders at all — preview is inserted at the top of the body."""
        body = "Hey,\n\nNo placeholders here.\n\nThanks"
        out = op.inject_preview_link(body, "https://episodespreview.com/x/")
        assert out.startswith("Preview")
        assert "https://episodespreview.com/x/" in out


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

        # Stub preview publishing — full preview flow has its own dedicated
        # tests; here we just need it to not be the thing under test.
        monkeypatch.setattr(op, "_publish_preview", lambda slug: None)

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

    def test_preview_url_appears_above_drive_link_in_final_body(
        self, tmp_path, monkeypatch
    ):
        """End-to-end ordering: in the final email body, the preview URL
        must precede the Drive URL — the polished page is the lead, the
        Drive folder is the backup. Regression test for the substitution
        ordering bug where injecting Drive first would erase the only
        anchor inject_preview_link could use to position itself."""
        self._write_pitch(tmp_path)
        self._write_ep(tmp_path)
        monkeypatch.setattr(op, "DEMO_ROOT", tmp_path / "demo" / "church-vertical")
        monkeypatch.setattr(op, "OUTPUT_ROOT", tmp_path / "output")

        fake_drive = MagicMock()
        fake_drive.upload_folder.return_value = (
            "https://drive.google.com/drive/folders/abc"
        )
        fake_gmail = MagicMock()
        fake_gmail.create_draft.return_value = "draft-order"

        monkeypatch.setattr(
            op,
            "_publish_preview",
            lambda slug: f"https://episodespreview.com/{slug}/",
        )

        op.prepare_one(
            "test-slug",
            drive=fake_drive,
            gmail=fake_gmail,
            dry_run=False,
            skip_verify=True,
        )

        body = fake_gmail.create_draft.call_args.kwargs["body"]
        preview_pos = body.index("episodespreview.com")
        drive_pos = body.index("drive.google.com")
        assert preview_pos < drive_pos, (
            "preview URL must appear before Drive URL in the email body"
        )

    def test_publishes_preview_and_injects_url(self, tmp_path, monkeypatch):
        """Default flow: prepare_one renders+pushes the preview page and
        injects the URL into the email body alongside the Drive link."""
        self._write_pitch(tmp_path)
        self._write_ep(tmp_path)
        monkeypatch.setattr(op, "DEMO_ROOT", tmp_path / "demo" / "church-vertical")
        monkeypatch.setattr(op, "OUTPUT_ROOT", tmp_path / "output")

        fake_drive = MagicMock()
        fake_drive.upload_folder.return_value = (
            "https://drive.google.com/drive/folders/abc"
        )
        fake_gmail = MagicMock()
        fake_gmail.create_draft.return_value = "draft-2"

        monkeypatch.setattr(
            op,
            "_publish_preview",
            lambda slug: f"https://episodespreview.com/{slug}/",
        )

        result = op.prepare_one(
            "test-slug",
            drive=fake_drive,
            gmail=fake_gmail,
            dry_run=False,
            skip_verify=True,
        )

        assert result["preview_url"] == "https://episodespreview.com/test-slug/"
        body = fake_gmail.create_draft.call_args.kwargs["body"]
        assert "https://episodespreview.com/test-slug/" in body
        assert "https://drive.google.com/drive/folders/abc" in body

    def test_preview_failure_falls_back_to_drive_only(self, tmp_path, monkeypatch):
        """If preview publish fails (returns None), prepare_one continues
        with a Drive-only package — must not lose the prospect to a
        previews-repo issue."""
        self._write_pitch(tmp_path)
        self._write_ep(tmp_path)
        monkeypatch.setattr(op, "DEMO_ROOT", tmp_path / "demo" / "church-vertical")
        monkeypatch.setattr(op, "OUTPUT_ROOT", tmp_path / "output")

        fake_drive = MagicMock()
        fake_drive.upload_folder.return_value = (
            "https://drive.google.com/drive/folders/abc"
        )
        fake_gmail = MagicMock()
        fake_gmail.create_draft.return_value = "draft-3"

        monkeypatch.setattr(op, "_publish_preview", lambda slug: None)

        result = op.prepare_one(
            "test-slug",
            drive=fake_drive,
            gmail=fake_gmail,
            dry_run=False,
            skip_verify=True,
        )

        assert result["preview_url"] is None
        body = fake_gmail.create_draft.call_args.kwargs["body"]
        assert "https://drive.google.com/drive/folders/abc" in body
        # Still has Drive link; preview line/url must NOT appear
        assert "episodespreview.com" not in body

    def test_publish_preview_disabled_skips_render(self, tmp_path, monkeypatch):
        """publish_preview=False short-circuits — _publish_preview not called."""
        self._write_pitch(tmp_path)
        self._write_ep(tmp_path)
        monkeypatch.setattr(op, "DEMO_ROOT", tmp_path / "demo" / "church-vertical")
        monkeypatch.setattr(op, "OUTPUT_ROOT", tmp_path / "output")

        fake_drive = MagicMock()
        fake_drive.upload_folder.return_value = (
            "https://drive.google.com/drive/folders/abc"
        )
        fake_gmail = MagicMock()
        fake_gmail.create_draft.return_value = "draft-4"

        publish_calls = []
        monkeypatch.setattr(
            op,
            "_publish_preview",
            lambda slug: publish_calls.append(slug) or "should-not-appear",
        )

        result = op.prepare_one(
            "test-slug",
            drive=fake_drive,
            gmail=fake_gmail,
            dry_run=False,
            skip_verify=True,
            publish_preview=False,
        )

        assert publish_calls == [], "preview must not be rendered when disabled"
        assert result["preview_url"] is None

    def test_existing_preview_url_skips_publish(self, tmp_path, monkeypatch):
        """preview_url= recovery: skip render+push, use the provided URL."""
        self._write_pitch(tmp_path)
        self._write_ep(tmp_path)
        monkeypatch.setattr(op, "DEMO_ROOT", tmp_path / "demo" / "church-vertical")
        monkeypatch.setattr(op, "OUTPUT_ROOT", tmp_path / "output")

        fake_drive = MagicMock()
        fake_drive.upload_folder.return_value = (
            "https://drive.google.com/drive/folders/abc"
        )
        fake_gmail = MagicMock()
        fake_gmail.create_draft.return_value = "draft-5"

        publish_calls = []
        monkeypatch.setattr(
            op,
            "_publish_preview",
            lambda slug: publish_calls.append(slug) or "should-not-appear",
        )

        existing = "https://episodespreview.com/test-slug/"
        result = op.prepare_one(
            "test-slug",
            drive=fake_drive,
            gmail=fake_gmail,
            dry_run=False,
            skip_verify=True,
            preview_url=existing,
        )

        assert publish_calls == [], "publish must be skipped when preview_url given"
        assert result["preview_url"] == existing
        body = fake_gmail.create_draft.call_args.kwargs["body"]
        assert existing in body

    def test_dry_run_does_not_publish_preview(self, tmp_path, monkeypatch):
        """Dry-run must not push to the previews repo (no git side effects)."""
        self._write_pitch(tmp_path)
        self._write_ep(tmp_path)
        monkeypatch.setattr(op, "DEMO_ROOT", tmp_path / "demo" / "church-vertical")
        monkeypatch.setattr(op, "OUTPUT_ROOT", tmp_path / "output")

        fake_gmail = MagicMock()
        fake_gmail.create_draft.return_value = "DRY_RUN"

        publish_calls = []
        monkeypatch.setattr(
            op,
            "_publish_preview",
            lambda slug: publish_calls.append(slug) or "should-not-appear",
        )

        op.prepare_one(
            "test-slug",
            drive=MagicMock(),
            gmail=fake_gmail,
            dry_run=True,
        )
        assert publish_calls == [], "dry-run must not touch the previews repo"

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

        # Stub preview publish so this recovery test stays focused on Drive.
        monkeypatch.setattr(op, "_publish_preview", lambda slug: None)

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


class TestAutofillIntegration:
    """prepare_one should auto-fill PITCH.md placeholders from the latest
    analysis.json before parsing. Saves the manual {{SERMON_TITLE}} fill-in
    that previously took 5+ min per prospect at the 30/week cadence."""

    def _write_skeleton_pitch(self, tmp_path: Path) -> Path:
        """Pitch with unfilled placeholders that fill() should populate."""
        pitch_dir = tmp_path / "demo" / "church-vertical" / "test-slug"
        pitch_dir.mkdir(parents=True)
        p = pitch_dir / "PITCH.md"
        p.write_text(
            "# Test - Outreach Pitch\n\n"
            "**Contact:** X / **EMAIL: pastor@x.com**\n"
            '**Episode referenced:** "{{SERMON_TITLE}}"\n'
            "\n---\n\n## Email\n\n"
            '**Subject:** Made these from your "{{SERMON_TITLE}}" sermon\n\n'
            "Hey,\n\n"
            'Lead clip: "{{BEST_CLIP_TITLE}}" ({{CLIP_TIMESTAMP}})\n\n'
            "[GOOGLE DRIVE LINK]\n\n"
            "Evan\n\n---\n\n## Follow-Up\n\nx\n"
        )
        return p

    def _write_ep_with_analysis(self, tmp_path: Path) -> Path:
        ep = tmp_path / "output" / "test-slug" / "ep_xyz_20260101_120000"
        (ep / "clips").mkdir(parents=True)
        (ep / "clips" / "clip_01_subtitle.mp4").write_bytes(b"v")
        (ep / "blog_post.md").write_text("# blog")
        analysis = {
            "episode_title": "How To Find Joy In April",
            "hot_take": "Joy is not a feeling.",
            "best_clips": [
                {
                    "start": "00:12:00",
                    "end": "00:12:45",
                    "duration_seconds": 45,
                    "suggested_title": "Joy Is A Choice",
                    "hook_caption": "Joy is not what you think",
                    "description": "the part about joy",
                    "why_interesting": "redefines joy in 30 seconds",
                }
            ],
        }
        (ep / "xyz_analysis.json").write_text(json.dumps(analysis), encoding="utf-8")
        return ep

    def test_autofill_replaces_placeholders_before_draft(self, tmp_path, monkeypatch):
        """Default autofill=True: sermon title + clip title land in the Gmail body."""
        self._write_skeleton_pitch(tmp_path)
        self._write_ep_with_analysis(tmp_path)

        monkeypatch.setattr(op, "DEMO_ROOT", tmp_path / "demo" / "church-vertical")
        monkeypatch.setattr(op, "OUTPUT_ROOT", tmp_path / "output")
        monkeypatch.chdir(tmp_path)  # fill() resolves paths from cwd
        monkeypatch.setattr(op, "_publish_preview", lambda slug: None)

        fake_drive = MagicMock()
        fake_drive.upload_folder.return_value = (
            "https://drive.google.com/drive/folders/abc"
        )
        fake_gmail = MagicMock()
        fake_gmail.create_draft.return_value = "draft-fill-1"

        op.prepare_one(
            "test-slug",
            drive=fake_drive,
            gmail=fake_gmail,
            dry_run=False,
            skip_verify=True,
        )

        gmail_kwargs = fake_gmail.create_draft.call_args.kwargs
        # The {{SERMON_TITLE}} placeholder should have been replaced before
        # parse_pitch read the body
        assert "How To Find Joy In April" in gmail_kwargs["subject"]
        assert "{{SERMON_TITLE}}" not in gmail_kwargs["body"]
        assert "Joy Is A Choice" in gmail_kwargs["body"]
        assert "12:00-12:45" in gmail_kwargs["body"]

    def test_no_autofill_leaves_placeholders_intact(self, tmp_path, monkeypatch):
        """autofill=False: PITCH.md is parsed as-is. Used when the operator
        has hand-edited a pitch and doesn't want fill() to clobber custom
        moment/why text."""
        self._write_skeleton_pitch(tmp_path)
        self._write_ep_with_analysis(tmp_path)

        monkeypatch.setattr(op, "DEMO_ROOT", tmp_path / "demo" / "church-vertical")
        monkeypatch.setattr(op, "OUTPUT_ROOT", tmp_path / "output")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(op, "_publish_preview", lambda slug: None)

        fake_drive = MagicMock()
        fake_drive.upload_folder.return_value = (
            "https://drive.google.com/drive/folders/abc"
        )
        fake_gmail = MagicMock()
        fake_gmail.create_draft.return_value = "draft-no-fill"

        op.prepare_one(
            "test-slug",
            drive=fake_drive,
            gmail=fake_gmail,
            dry_run=False,
            skip_verify=True,
            autofill=False,
        )

        gmail_kwargs = fake_gmail.create_draft.call_args.kwargs
        # Placeholder-style braces still in the body since fill() was skipped
        assert "{{SERMON_TITLE}}" in gmail_kwargs["subject"]
        assert "{{BEST_CLIP_TITLE}}" in gmail_kwargs["body"]

    def test_autofill_silent_when_no_analysis_yet(self, tmp_path, monkeypatch):
        """If the pipeline hasn't run (no analysis.json), autofill is a no-op
        and the existing PITCH.md is parsed as-is. Manual prep workflow."""
        self._write_skeleton_pitch(tmp_path)
        # Note: NO _write_ep_with_analysis — there's no ep_dir at all.
        # But prepare_one with drive_link= bypasses _find_latest_ep_dir, so
        # we use that path to keep the test focused on the autofill behavior.

        monkeypatch.setattr(op, "DEMO_ROOT", tmp_path / "demo" / "church-vertical")
        monkeypatch.setattr(op, "OUTPUT_ROOT", tmp_path / "output")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(op, "_publish_preview", lambda slug: None)

        fake_gmail = MagicMock()
        fake_gmail.create_draft.return_value = "draft-no-ep"

        # Should not raise — autofill silently skips on missing analysis
        op.prepare_one(
            "test-slug",
            drive=None,
            gmail=fake_gmail,
            dry_run=False,
            drive_link="https://drive.google.com/PRE_EXISTING",
            autofill=True,
        )

        gmail_kwargs = fake_gmail.create_draft.call_args.kwargs
        # Placeholders never got filled because there was no analysis
        assert "{{SERMON_TITLE}}" in gmail_kwargs["subject"]


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


# ---------------------------------------------------------------------------
# Post-upload public-access smoke test
# ---------------------------------------------------------------------------


class TestVerifyDrivePublicAccess:
    """After upload we hit the URL with no auth to catch Workspace-policy or
    permission-race gaps that file-level perms wouldn't surface."""

    def _mock_response(self, status=200, body=""):
        from unittest.mock import MagicMock

        m = MagicMock()
        m.status_code = status
        m.text = body
        return m

    def test_returns_none_on_truly_public_folder(self):
        from unittest.mock import patch

        with patch(
            "requests.get",
            return_value=self._mock_response(200, "<html>file list</html>"),
        ):
            assert (
                op._verify_drive_public_access(
                    "https://drive.google.com/drive/folders/abc"
                )
                is None
            )

    def test_returns_string_on_request_access_page(self):
        from unittest.mock import patch

        body = "<html>You need access. Request access</html>"
        with patch("requests.get", return_value=self._mock_response(200, body)):
            result = op._verify_drive_public_access(
                "https://drive.google.com/drive/folders/locked"
            )
            assert result is not None
            assert "request access" in result.lower()

    def test_returns_string_on_404(self):
        from unittest.mock import patch

        with patch("requests.get", return_value=self._mock_response(404, "")):
            result = op._verify_drive_public_access(
                "https://drive.google.com/drive/folders/gone"
            )
            assert result is not None
            assert "404" in result

    def test_returns_none_on_network_error(self):
        """Transient network failures must NOT false-fail (don't block uploads)."""
        from unittest.mock import patch

        with patch("requests.get", side_effect=ConnectionError("dns")):
            result = op._verify_drive_public_access(
                "https://drive.google.com/drive/folders/x"
            )
            assert result is None

    def test_detects_you_need_permission_marker(self):
        from unittest.mock import patch

        body = "<html>You need permission to access</html>"
        with patch("requests.get", return_value=self._mock_response(200, body)):
            result = op._verify_drive_public_access("https://drive.google.com/x")
            assert result is not None
            assert "permission" in result.lower()


# ---------------------------------------------------------------------------
# --dry-run shows the staged tree
# ---------------------------------------------------------------------------


class TestDryRunPrintsStagedTree:
    """In dry-run mode, prepare_one now stages to tmp + prints the file
    tree so you can eyeball what would actually go to Drive."""

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

    def _write_ep_dir(self, tmp_path: Path) -> Path:
        ep = tmp_path / "output" / "test-slug" / "ep_42_20260423_120000"
        (ep / "clips" / "final").mkdir(parents=True)
        (ep / "clips" / "final" / "clip_01_topic.mp4").write_bytes(b"video")
        (ep / "ep42_blog_post.md").write_text("# blog", encoding="utf-8")
        return ep

    def test_dry_run_prints_package_preview_header(self, tmp_path, monkeypatch, capsys):
        from unittest.mock import MagicMock

        self._write_pitch(tmp_path)
        self._write_ep_dir(tmp_path)
        monkeypatch.setattr(op, "DEMO_ROOT", tmp_path / "demo" / "church-vertical")
        monkeypatch.setattr(op, "OUTPUT_ROOT", tmp_path / "output")

        op.prepare_one(
            "test-slug",
            drive=MagicMock(),
            gmail=MagicMock(),
            dry_run=True,
        )

        out = capsys.readouterr().out
        assert "PACKAGE PREVIEW" in out
        assert "test-slug" in out
        # The clip we staged should show up
        assert "clip_01_topic.mp4" in out
        assert "blog_post.md" in out

    def test_dry_run_still_skips_upload(self, tmp_path, monkeypatch):
        """The new tree-print behavior must not start uploading by mistake."""
        from unittest.mock import MagicMock

        self._write_pitch(tmp_path)
        self._write_ep_dir(tmp_path)
        monkeypatch.setattr(op, "DEMO_ROOT", tmp_path / "demo" / "church-vertical")
        monkeypatch.setattr(op, "OUTPUT_ROOT", tmp_path / "output")

        fake_drive = MagicMock()
        op.prepare_one("test-slug", drive=fake_drive, gmail=MagicMock(), dry_run=True)
        fake_drive.upload_folder.assert_not_called()
