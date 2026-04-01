"""Tests for DemoPackager — demo folder assembly from existing pipeline output."""

import json
import shutil
from unittest.mock import MagicMock, patch

import pytest

from config import Config

# ---------------------------------------------------------------------------
# Sample data constants
# ---------------------------------------------------------------------------

SAMPLE_ANALYSIS = {
    "episode_title": "Test Crime Episode",
    "episode_summary": "A gripping episode about a mysterious case.",
    "best_clips": [
        {
            "start_seconds": 120.0,
            "end_seconds": 180.0,
            "description": "Key witness testimony",
            "suggested_title": "The Witness Speaks",
            "hook_caption": "You won't believe what she said",
            "clip_hashtags": ["#truecrime", "#podcast"],
        },
        {
            "start_seconds": 300.0,
            "end_seconds": 360.0,
            "description": "Detective's theory",
            "suggested_title": "The Detective's Theory",
            "hook_caption": "The detective had a wild idea",
            "clip_hashtags": ["#truecrime"],
        },
    ],
    "social_captions": {
        "youtube": "YouTube caption for episode",
        "instagram": "Instagram caption #truecrime",
        "twitter": "Twitter caption — short and punchy",
        "tiktok": "TikTok caption with hooks",
    },
    "show_notes": "Show notes for the episode.\n\nKey takeaways:\n- Point 1\n- Point 2",
    "chapters": [
        {"start_timestamp": "00:00:00", "title": "Introduction", "start_seconds": 0},
        {"start_timestamp": "00:02:00", "title": "The Case", "start_seconds": 120},
    ],
    "censor_timestamps": [
        {"start": 45.0, "end": 46.0},
        {"start": 200.0, "end": 201.5},
    ],
}

SAMPLE_COMPLIANCE = {
    "episode_number": 399,
    "checked_at": "2026-03-28T18:00:00",
    "critical": False,
    "flagged": [
        {
            "start_seconds": 45.0,
            "end_seconds": 46.0,
            "text": "some flagged text",
            "category": "profanity",
            "severity": "low",
            "reason": "Mild language",
        }
    ],
    "warnings": [],
}

SAMPLE_LUFS_STATS = {
    "input_i": "-18.5",
    "input_tp": "-2.1",
    "input_lra": "9.0",
    "input_thresh": "-28.5",
    "output_i": "-16.0",
    "output_tp": "-1.5",
    "target_offset": "0.0",
    "normalization_type": "dynamic",
}


# ---------------------------------------------------------------------------
# Helper: create a populated fake episode output directory
# ---------------------------------------------------------------------------


def _make_episode_dir(tmp_path, client="truecrime", ep="ep01"):
    """Create a fake episode output structure under tmp_path."""
    ep_dir = tmp_path / "output" / client / ep
    ep_dir.mkdir(parents=True)

    # Analysis JSON
    analysis_path = ep_dir / "audio_20260328_analysis.json"
    analysis_path.write_text(json.dumps(SAMPLE_ANALYSIS), encoding="utf-8")

    # Processed WAV
    wav_path = ep_dir / "audio_20260328_censored.wav"
    wav_path.write_bytes(b"FAKE_WAV_DATA")

    # Processed MP3
    mp3_path = ep_dir / "audio_20260328_censored.mp3"
    mp3_path.write_bytes(b"FAKE_MP3_DATA")

    # Thumbnail
    thumb_path = ep_dir / "audio_20260328_thumbnail.png"
    thumb_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    # Compliance JSON
    compliance_path = ep_dir / "compliance_report_399_20260328.json"
    compliance_path.write_text(json.dumps(SAMPLE_COMPLIANCE), encoding="utf-8")

    # Clips directory
    clips_dir = tmp_path / "clips" / client / ep
    clips_dir.mkdir(parents=True)
    for i in range(1, 4):
        clip = clips_dir / f"audio_censored_clip_0{i}_subtitle.mp4"
        clip.write_bytes(b"FAKE_MP4_DATA")

    return ep_dir, analysis_path, wav_path, mp3_path, thumb_path, clips_dir


# ---------------------------------------------------------------------------
# TestDemoPackager — core package_demo() tests
# ---------------------------------------------------------------------------


class TestDemoPackager:
    """Tests for DemoPackager.package_demo() core behavior."""

    def test_package_creates_expected_structure(self, tmp_path, monkeypatch):
        """package_demo creates demo/<client>/<ep_id>/ with expected files."""
        from demo_packager import DemoPackager

        ep_dir, analysis_path, wav_path, mp3_path, thumb_path, clips_dir = (
            _make_episode_dir(tmp_path)
        )
        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path / "output" / "truecrime")
        monkeypatch.setattr(Config, "CLIPS_DIR", tmp_path / "clips")
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)

        with (
            patch("demo_packager.PipelineState") as mock_state_cls,
            patch(
                "demo_packager.DemoPackager._measure_lufs",
                return_value=SAMPLE_LUFS_STATS,
            ),
        ):
            mock_state = MagicMock()
            mock_state.is_step_completed.return_value = False
            mock_state_cls.return_value = mock_state

            packager = DemoPackager()
            demo_path = packager.package_demo("truecrime", "ep01")

        assert demo_path.exists()
        assert (demo_path / "DEMO.md").exists()
        assert (demo_path / "summary.html").exists()
        assert (demo_path / "processed_audio.mp3").exists()
        assert (demo_path / "thumbnail.png").exists()
        assert (demo_path / "show_notes.txt").exists()
        assert (demo_path / "captions.txt").exists()
        assert (demo_path / "compliance_report.json").exists()
        assert (demo_path / "clips").is_dir()

    def test_reads_analysis_json_correctly(self, tmp_path, monkeypatch):
        """Analysis JSON fields are read and used in show_notes.txt output."""
        from demo_packager import DemoPackager

        ep_dir, analysis_path, wav_path, mp3_path, thumb_path, clips_dir = (
            _make_episode_dir(tmp_path)
        )
        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path / "output" / "truecrime")
        monkeypatch.setattr(Config, "CLIPS_DIR", tmp_path / "clips")
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)

        with (
            patch("demo_packager.PipelineState") as mock_state_cls,
            patch(
                "demo_packager.DemoPackager._measure_lufs",
                return_value=SAMPLE_LUFS_STATS,
            ),
        ):
            mock_state = MagicMock()
            mock_state.is_step_completed.return_value = False
            mock_state_cls.return_value = mock_state

            packager = DemoPackager()
            demo_path = packager.package_demo("truecrime", "ep01")

        show_notes = (demo_path / "show_notes.txt").read_text(encoding="utf-8")
        assert "Show notes for the episode." in show_notes

    def test_missing_thumbnail_logs_warning_and_continues(
        self, tmp_path, monkeypatch, caplog
    ):
        """Missing thumbnail logs a warning but does not raise."""
        import logging
        from demo_packager import DemoPackager

        ep_dir, analysis_path, wav_path, mp3_path, thumb_path, clips_dir = (
            _make_episode_dir(tmp_path)
        )
        # Remove the thumbnail
        thumb_path.unlink()

        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path / "output" / "truecrime")
        monkeypatch.setattr(Config, "CLIPS_DIR", tmp_path / "clips")
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)

        with (
            patch("demo_packager.PipelineState") as mock_state_cls,
            patch(
                "demo_packager.DemoPackager._measure_lufs",
                return_value=SAMPLE_LUFS_STATS,
            ),
            caplog.at_level(logging.WARNING),
        ):
            mock_state = MagicMock()
            mock_state.is_step_completed.return_value = False
            mock_state_cls.return_value = mock_state

            packager = DemoPackager()
            # Should not raise
            demo_path = packager.package_demo("truecrime", "ep01")

        assert not (demo_path / "thumbnail.png").exists()
        assert any("thumbnail" in msg.lower() for msg in caplog.messages)

    def test_missing_clips_logs_warning_and_continues(
        self, tmp_path, monkeypatch, caplog
    ):
        """Missing clip videos logs a warning but does not raise."""
        import logging
        from demo_packager import DemoPackager

        ep_dir, analysis_path, wav_path, mp3_path, thumb_path, clips_dir = (
            _make_episode_dir(tmp_path)
        )
        # Remove all clips
        shutil.rmtree(clips_dir)

        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path / "output" / "truecrime")
        monkeypatch.setattr(Config, "CLIPS_DIR", tmp_path / "clips")
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)

        with (
            patch("demo_packager.PipelineState") as mock_state_cls,
            patch(
                "demo_packager.DemoPackager._measure_lufs",
                return_value=SAMPLE_LUFS_STATS,
            ),
            caplog.at_level(logging.WARNING),
        ):
            mock_state = MagicMock()
            mock_state.is_step_completed.return_value = False
            mock_state_cls.return_value = mock_state

            packager = DemoPackager()
            demo_path = packager.package_demo("truecrime", "ep01")

        # clips/ directory exists but is empty
        assert (demo_path / "clips").is_dir()
        assert list((demo_path / "clips").iterdir()) == []

    def test_captions_txt_contains_all_platforms(self, tmp_path, monkeypatch):
        """captions.txt contains all four platform captions with labels."""
        from demo_packager import DemoPackager

        ep_dir, analysis_path, wav_path, mp3_path, thumb_path, clips_dir = (
            _make_episode_dir(tmp_path)
        )
        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path / "output" / "truecrime")
        monkeypatch.setattr(Config, "CLIPS_DIR", tmp_path / "clips")
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)

        with (
            patch("demo_packager.PipelineState") as mock_state_cls,
            patch(
                "demo_packager.DemoPackager._measure_lufs",
                return_value=SAMPLE_LUFS_STATS,
            ),
        ):
            mock_state = MagicMock()
            mock_state.is_step_completed.return_value = False
            mock_state_cls.return_value = mock_state

            packager = DemoPackager()
            demo_path = packager.package_demo("truecrime", "ep01")

        captions = (demo_path / "captions.txt").read_text(encoding="utf-8")
        assert "YouTube caption for episode" in captions
        assert "Instagram caption" in captions
        assert "Twitter caption" in captions
        assert "TikTok caption" in captions
        # Should have platform headers
        assert "YOUTUBE" in captions.upper() or "youtube" in captions.lower()
        assert "INSTAGRAM" in captions.upper() or "instagram" in captions.lower()

    def test_glob_fallback_when_pipeline_state_absent(self, tmp_path, monkeypatch):
        """package_demo works via glob fallback when pipeline state has no steps completed."""
        from demo_packager import DemoPackager

        ep_dir, analysis_path, wav_path, mp3_path, thumb_path, clips_dir = (
            _make_episode_dir(tmp_path)
        )
        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path / "output" / "truecrime")
        monkeypatch.setattr(Config, "CLIPS_DIR", tmp_path / "clips")
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)

        with (
            patch("demo_packager.PipelineState") as mock_state_cls,
            patch(
                "demo_packager.DemoPackager._measure_lufs",
                return_value=SAMPLE_LUFS_STATS,
            ),
        ):
            # State returns no completed steps — forces glob fallback
            mock_state = MagicMock()
            mock_state.is_step_completed.return_value = False
            mock_state.get_step_outputs.return_value = {}
            mock_state_cls.return_value = mock_state

            packager = DemoPackager()
            demo_path = packager.package_demo("truecrime", "ep01")

        assert (demo_path / "DEMO.md").exists()
        assert (demo_path / "summary.html").exists()


# ---------------------------------------------------------------------------
# TestSummaryHtml — HTML summary generation tests
# ---------------------------------------------------------------------------


class TestSummaryHtml:
    """Tests for summary.html generation."""

    def test_html_contains_base64_thumbnail(self, tmp_path, monkeypatch):
        """summary.html contains base64-encoded thumbnail when thumbnail exists."""
        from demo_packager import DemoPackager

        ep_dir, analysis_path, wav_path, mp3_path, thumb_path, clips_dir = (
            _make_episode_dir(tmp_path)
        )
        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path / "output" / "truecrime")
        monkeypatch.setattr(Config, "CLIPS_DIR", tmp_path / "clips")
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)

        with (
            patch("demo_packager.PipelineState") as mock_state_cls,
            patch(
                "demo_packager.DemoPackager._measure_lufs",
                return_value=SAMPLE_LUFS_STATS,
            ),
        ):
            mock_state = MagicMock()
            mock_state.is_step_completed.return_value = False
            mock_state_cls.return_value = mock_state

            packager = DemoPackager()
            demo_path = packager.package_demo("truecrime", "ep01")

        html = (demo_path / "summary.html").read_text(encoding="utf-8")
        assert "data:image/png;base64," in html

    def test_html_without_thumbnail_uses_empty_placeholder(self, tmp_path, monkeypatch):
        """summary.html renders without error when thumbnail is absent."""
        from demo_packager import DemoPackager

        ep_dir, analysis_path, wav_path, mp3_path, thumb_path, clips_dir = (
            _make_episode_dir(tmp_path)
        )
        thumb_path.unlink()

        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path / "output" / "truecrime")
        monkeypatch.setattr(Config, "CLIPS_DIR", tmp_path / "clips")
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)

        with (
            patch("demo_packager.PipelineState") as mock_state_cls,
            patch(
                "demo_packager.DemoPackager._measure_lufs",
                return_value=SAMPLE_LUFS_STATS,
            ),
        ):
            mock_state = MagicMock()
            mock_state.is_step_completed.return_value = False
            mock_state_cls.return_value = mock_state

            packager = DemoPackager()
            demo_path = packager.package_demo("truecrime", "ep01")

        html = (demo_path / "summary.html").read_text(encoding="utf-8")
        assert "<html" in html
        assert "Test Crime Episode" in html


# ---------------------------------------------------------------------------
# TestBeforeAfter — before/after audio clip tests
# ---------------------------------------------------------------------------


class TestBeforeAfter:
    """Tests for before_after/ folder creation."""

    def test_before_after_created_when_snapshot_exists(self, tmp_path, monkeypatch):
        """before_after/ folder contains both WAV files when raw snapshot exists."""
        from demo_packager import DemoPackager

        ep_dir, analysis_path, wav_path, mp3_path, thumb_path, clips_dir = (
            _make_episode_dir(tmp_path)
        )

        # Create a raw snapshot file
        raw_snapshot = ep_dir / "audio_20260328_raw_snapshot.wav"
        raw_snapshot.write_bytes(b"FAKE_RAW_WAV")

        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path / "output" / "truecrime")
        monkeypatch.setattr(Config, "CLIPS_DIR", tmp_path / "clips")
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)

        with (
            patch("demo_packager.PipelineState") as mock_state_cls,
            patch(
                "demo_packager.DemoPackager._measure_lufs",
                return_value=SAMPLE_LUFS_STATS,
            ),
            patch("demo_packager.subprocess.run") as mock_subproc,
        ):
            mock_state = MagicMock()
            mock_state.is_step_completed.side_effect = lambda step: step == "censor"
            mock_state.get_step_outputs.side_effect = lambda step: (
                {
                    "raw_snapshot_path": str(raw_snapshot),
                    "censored_audio": str(wav_path),
                }
                if step == "censor"
                else {}
            )
            mock_state_cls.return_value = mock_state
            mock_subproc.return_value = MagicMock(returncode=0)

            packager = DemoPackager()
            demo_path = packager.package_demo("truecrime", "ep01")

        before_after = demo_path / "before_after"
        assert before_after.is_dir()
        assert (before_after / "raw_60s.wav").exists()

    def test_before_after_skipped_when_no_snapshot(self, tmp_path, monkeypatch):
        """before_after/ folder is not created when raw snapshot does not exist."""
        from demo_packager import DemoPackager

        ep_dir, analysis_path, wav_path, mp3_path, thumb_path, clips_dir = (
            _make_episode_dir(tmp_path)
        )
        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path / "output" / "truecrime")
        monkeypatch.setattr(Config, "CLIPS_DIR", tmp_path / "clips")
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)

        with (
            patch("demo_packager.PipelineState") as mock_state_cls,
            patch(
                "demo_packager.DemoPackager._measure_lufs",
                return_value=SAMPLE_LUFS_STATS,
            ),
        ):
            mock_state = MagicMock()
            mock_state.is_step_completed.return_value = False
            mock_state.get_step_outputs.return_value = {}
            mock_state_cls.return_value = mock_state

            packager = DemoPackager()
            demo_path = packager.package_demo("truecrime", "ep01")

        # No before_after folder or it is empty
        before_after = demo_path / "before_after"
        assert not before_after.exists() or not list(before_after.iterdir())


# ---------------------------------------------------------------------------
# TestDemoMd — DEMO.md content tests
# ---------------------------------------------------------------------------


class TestDemoMd:
    """Tests for DEMO.md narrative generation."""

    def test_demo_md_contains_episode_title(self, tmp_path, monkeypatch):
        """DEMO.md contains the episode title from analysis JSON."""
        from demo_packager import DemoPackager

        ep_dir, analysis_path, wav_path, mp3_path, thumb_path, clips_dir = (
            _make_episode_dir(tmp_path)
        )
        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path / "output" / "truecrime")
        monkeypatch.setattr(Config, "CLIPS_DIR", tmp_path / "clips")
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)

        with (
            patch("demo_packager.PipelineState") as mock_state_cls,
            patch(
                "demo_packager.DemoPackager._measure_lufs",
                return_value=SAMPLE_LUFS_STATS,
            ),
        ):
            mock_state = MagicMock()
            mock_state.is_step_completed.return_value = False
            mock_state_cls.return_value = mock_state

            packager = DemoPackager()
            demo_path = packager.package_demo("truecrime", "ep01")

        demo_md = (demo_path / "DEMO.md").read_text(encoding="utf-8")
        assert "Test Crime Episode" in demo_md

    def test_demo_md_contains_lufs_metrics(self, tmp_path, monkeypatch):
        """DEMO.md contains LUFS input/output metrics."""
        from demo_packager import DemoPackager

        ep_dir, analysis_path, wav_path, mp3_path, thumb_path, clips_dir = (
            _make_episode_dir(tmp_path)
        )
        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path / "output" / "truecrime")
        monkeypatch.setattr(Config, "CLIPS_DIR", tmp_path / "clips")
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)

        with (
            patch("demo_packager.PipelineState") as mock_state_cls,
            patch(
                "demo_packager.DemoPackager._measure_lufs",
                return_value=SAMPLE_LUFS_STATS,
            ),
        ):
            mock_state = MagicMock()
            mock_state.is_step_completed.return_value = False
            mock_state_cls.return_value = mock_state

            packager = DemoPackager()
            demo_path = packager.package_demo("truecrime", "ep01")

        demo_md = (demo_path / "DEMO.md").read_text(encoding="utf-8")
        assert "-18.5" in demo_md
        assert "-16.0" in demo_md

    def test_demo_md_contains_clip_count(self, tmp_path, monkeypatch):
        """DEMO.md contains the number of clips copied."""
        from demo_packager import DemoPackager

        ep_dir, analysis_path, wav_path, mp3_path, thumb_path, clips_dir = (
            _make_episode_dir(tmp_path)
        )
        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path / "output" / "truecrime")
        monkeypatch.setattr(Config, "CLIPS_DIR", tmp_path / "clips")
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)

        with (
            patch("demo_packager.PipelineState") as mock_state_cls,
            patch(
                "demo_packager.DemoPackager._measure_lufs",
                return_value=SAMPLE_LUFS_STATS,
            ),
        ):
            mock_state = MagicMock()
            mock_state.is_step_completed.return_value = False
            mock_state_cls.return_value = mock_state

            packager = DemoPackager()
            demo_path = packager.package_demo("truecrime", "ep01")

        demo_md = (demo_path / "DEMO.md").read_text(encoding="utf-8")
        # 3 clips were created in the test fixture
        assert "3" in demo_md

    def test_demo_md_contains_censor_count(self, tmp_path, monkeypatch):
        """DEMO.md contains the number of censored segments."""
        from demo_packager import DemoPackager

        ep_dir, analysis_path, wav_path, mp3_path, thumb_path, clips_dir = (
            _make_episode_dir(tmp_path)
        )
        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path / "output" / "truecrime")
        monkeypatch.setattr(Config, "CLIPS_DIR", tmp_path / "clips")
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)

        with (
            patch("demo_packager.PipelineState") as mock_state_cls,
            patch(
                "demo_packager.DemoPackager._measure_lufs",
                return_value=SAMPLE_LUFS_STATS,
            ),
        ):
            mock_state = MagicMock()
            mock_state.is_step_completed.return_value = False
            mock_state_cls.return_value = mock_state

            packager = DemoPackager()
            demo_path = packager.package_demo("truecrime", "ep01")

        demo_md = (demo_path / "DEMO.md").read_text(encoding="utf-8")
        # SAMPLE_ANALYSIS has 2 censor_timestamps
        assert "2" in demo_md


# ---------------------------------------------------------------------------
# TestLufsMeasurement — _measure_lufs() helper tests
# ---------------------------------------------------------------------------


class TestLufsMeasurement:
    """Tests for DemoPackager._measure_lufs() method."""

    def test_measure_lufs_returns_dict_with_input_i(self, tmp_path):
        """_measure_lufs returns dict containing input_i key from FFmpeg output."""
        from demo_packager import DemoPackager

        fake_stderr = (
            "some ffmpeg output\n"
            '{"input_i": "-18.5", "input_tp": "-2.1", "input_lra": "9.0", '
            '"input_thresh": "-28.5", "output_i": "-16.0", "output_tp": "-1.5", '
            '"target_offset": "0.0", "normalization_type": "dynamic"}\n'
            "more output\n"
        )

        audio_path = tmp_path / "test.wav"
        audio_path.write_bytes(b"FAKE")

        with patch("demo_packager.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr=fake_stderr)
            packager = DemoPackager()
            result = packager._measure_lufs(audio_path)

        assert "input_i" in result
        assert result["input_i"] == "-18.5"

    def test_measure_lufs_returns_empty_dict_on_failure(self, tmp_path):
        """_measure_lufs returns empty dict when FFmpeg fails."""
        from demo_packager import DemoPackager

        audio_path = tmp_path / "test.wav"
        audio_path.write_bytes(b"FAKE")

        with patch("demo_packager.subprocess.run") as mock_run:
            mock_run.side_effect = Exception("FFmpeg not found")
            packager = DemoPackager()
            result = packager._measure_lufs(audio_path)

        assert result == {}


# ---------------------------------------------------------------------------
# TestDemoWorkflow — run_demo_workflow() orchestration tests
# ---------------------------------------------------------------------------


class TestDemoWorkflow:
    """Tests for run_demo_workflow() consent-gated orchestration function."""

    def _make_mock_tracker(self, found=True):
        """Create a mock OutreachTracker with a canned prospect."""
        mock_tracker = MagicMock()
        if found:
            mock_tracker.get_prospect.return_value = {
                "slug": "test-podcast",
                "show_name": "Test Podcast Show",
                "status": "contacted",
                "contact_email": "host@example.com",
            }
        else:
            mock_tracker.get_prospect.return_value = None
        mock_tracker.update_status.return_value = True
        return mock_tracker

    def test_no_consent_returns_none_no_pipeline(self):
        """run_demo_workflow returns None without calling pipeline when consent is denied."""
        from demo_packager import run_demo_workflow

        mock_tracker = self._make_mock_tracker()

        with (
            patch("demo_packager.OutreachTracker", return_value=mock_tracker),
            patch("demo_packager.activate_client") as mock_activate,
            patch("demo_packager.run_with_notification") as mock_pipeline,
            patch("demo_packager.DemoPackager") as mock_packager_cls,
            patch("demo_packager.PitchGenerator") as mock_pitch_cls,
        ):
            result = run_demo_workflow(
                "test-podcast",
                "ep01",
                {},
                consent_fn=lambda _: "no",
            )

        assert result is None
        mock_pipeline.assert_not_called()
        mock_activate.assert_not_called()
        mock_packager_cls.assert_not_called()
        mock_pitch_cls.assert_not_called()

    def test_empty_consent_returns_none_no_pipeline(self):
        """run_demo_workflow returns None without calling pipeline when consent is empty string."""
        from demo_packager import run_demo_workflow

        mock_tracker = self._make_mock_tracker()

        with (
            patch("demo_packager.OutreachTracker", return_value=mock_tracker),
            patch("demo_packager.activate_client"),
            patch("demo_packager.run_with_notification") as mock_pipeline,
            patch("demo_packager.DemoPackager"),
            patch("demo_packager.PitchGenerator"),
        ):
            result = run_demo_workflow(
                "test-podcast",
                "ep01",
                {},
                consent_fn=lambda _: "",
            )

        assert result is None
        mock_pipeline.assert_not_called()

    def test_yes_consent_runs_full_chain(self):
        """run_demo_workflow calls pipeline, package_demo, gen-pitch, and updates tracker when consent given."""
        from demo_packager import run_demo_workflow
        from pathlib import Path

        mock_tracker = self._make_mock_tracker()
        mock_demo_path = Path("/tmp/demo/test-podcast/ep01")
        mock_packager = MagicMock()
        mock_packager.package_demo.return_value = mock_demo_path
        mock_pitch = MagicMock()
        mock_pitch.generate_demo_pitch.return_value = {
            "subject": "Test Subject",
            "email": "Test email body",
        }

        with (
            patch("demo_packager.OutreachTracker", return_value=mock_tracker),
            patch("demo_packager.activate_client") as mock_activate,
            patch("demo_packager.run_with_notification") as mock_pipeline,
            patch("demo_packager.DemoPackager", return_value=mock_packager),
            patch("demo_packager.PitchGenerator", return_value=mock_pitch),
        ):
            result = run_demo_workflow(
                "test-podcast",
                "ep01",
                {},
                consent_fn=lambda _: "yes",
            )

        assert result == mock_demo_path
        mock_activate.assert_called_once_with("test-podcast")
        mock_pipeline.assert_called_once()
        mock_packager.package_demo.assert_called_once_with("test-podcast", "ep01")
        mock_pitch.generate_demo_pitch.assert_called_once_with("test-podcast", "ep01")
        # Tracker should be updated to demo_sent
        update_calls = [str(c) for c in mock_tracker.update_status.call_args_list]
        assert any("demo_sent" in c for c in update_calls)

    def test_prospect_not_found_raises_value_error(self):
        """run_demo_workflow raises ValueError if prospect not found in tracker."""
        from demo_packager import run_demo_workflow

        mock_tracker = self._make_mock_tracker(found=False)

        with (
            patch("demo_packager.OutreachTracker", return_value=mock_tracker),
        ):
            with pytest.raises(ValueError, match="not found in tracker"):
                run_demo_workflow(
                    "unknown-slug",
                    "ep01",
                    {},
                    consent_fn=lambda _: "yes",
                )

    def test_tracker_updated_to_interested_before_processing(self):
        """run_demo_workflow updates tracker to 'interested' before pipeline runs."""
        from demo_packager import run_demo_workflow
        from pathlib import Path

        mock_tracker = self._make_mock_tracker()
        call_order = []

        def track_status_call(slug, status):
            call_order.append(("update_status", status))
            return True

        def track_pipeline_call(*args, **kwargs):
            call_order.append(("pipeline",))

        mock_tracker.update_status.side_effect = track_status_call
        mock_packager = MagicMock()
        mock_packager.package_demo.return_value = Path("/tmp/demo/test-podcast/ep01")
        mock_pitch = MagicMock()
        mock_pitch.generate_demo_pitch.return_value = None

        with (
            patch("demo_packager.OutreachTracker", return_value=mock_tracker),
            patch("demo_packager.activate_client"),
            patch(
                "demo_packager.run_with_notification", side_effect=track_pipeline_call
            ),
            patch("demo_packager.DemoPackager", return_value=mock_packager),
            patch("demo_packager.PitchGenerator", return_value=mock_pitch),
        ):
            run_demo_workflow(
                "test-podcast",
                "ep01",
                {},
                consent_fn=lambda _: "yes",
            )

        # interested must come before pipeline
        interested_idx = next(
            (
                i
                for i, x in enumerate(call_order)
                if x == ("update_status", "interested")
            ),
            None,
        )
        pipeline_idx = next(
            (i for i, x in enumerate(call_order) if x == ("pipeline",)),
            None,
        )
        assert interested_idx is not None, (
            "update_status('interested') was never called"
        )
        assert pipeline_idx is not None, "pipeline was never called"
        assert interested_idx < pipeline_idx, (
            "interested must be set before pipeline runs"
        )

    def test_pitch_failure_does_not_abort(self):
        """run_demo_workflow returns demo path even if gen-pitch raises an exception."""
        from demo_packager import run_demo_workflow
        from pathlib import Path

        mock_tracker = self._make_mock_tracker()
        mock_demo_path = Path("/tmp/demo/test-podcast/ep01")
        mock_packager = MagicMock()
        mock_packager.package_demo.return_value = mock_demo_path
        mock_pitch = MagicMock()
        mock_pitch.generate_demo_pitch.side_effect = Exception("OpenAI error")

        with (
            patch("demo_packager.OutreachTracker", return_value=mock_tracker),
            patch("demo_packager.activate_client"),
            patch("demo_packager.run_with_notification"),
            patch("demo_packager.DemoPackager", return_value=mock_packager),
            patch("demo_packager.PitchGenerator", return_value=mock_pitch),
        ):
            # Should not raise
            result = run_demo_workflow(
                "test-podcast",
                "ep01",
                {},
                consent_fn=lambda _: "yes",
            )

        assert result == mock_demo_path


# ---------------------------------------------------------------------------
# TestFindAnalysis — _find_analysis() artifact discovery
# ---------------------------------------------------------------------------


class TestFindAnalysis:
    """Tests for DemoPackager._find_analysis() helper."""

    def test_find_analysis_via_pipeline_state(self, tmp_path):
        """_find_analysis returns analysis from pipeline state path when step is completed."""
        from demo_packager import DemoPackager

        ep_dir = tmp_path / "output" / "ep01"
        ep_dir.mkdir(parents=True)
        analysis_path = ep_dir / "state_analysis.json"
        analysis_path.write_text(json.dumps(SAMPLE_ANALYSIS), encoding="utf-8")

        mock_state = MagicMock()
        mock_state.is_step_completed.return_value = True
        mock_state.get_step_outputs.return_value = {"analysis_path": str(analysis_path)}

        packager = DemoPackager()
        result, path = packager._find_analysis(ep_dir, mock_state)

        assert result is not None
        assert result["episode_title"] == "Test Crime Episode"
        assert path == analysis_path

    def test_find_analysis_state_path_missing_falls_back_to_glob(self, tmp_path):
        """_find_analysis falls back to glob when state path does not exist on disk."""
        from demo_packager import DemoPackager

        ep_dir = tmp_path / "output" / "ep01"
        ep_dir.mkdir(parents=True)
        # State points to nonexistent file
        mock_state = MagicMock()
        mock_state.is_step_completed.return_value = True
        mock_state.get_step_outputs.return_value = {
            "analysis_path": str(ep_dir / "gone.json")
        }

        # But glob file exists
        glob_path = ep_dir / "audio_analysis.json"
        glob_path.write_text(json.dumps(SAMPLE_ANALYSIS), encoding="utf-8")

        packager = DemoPackager()
        result, path = packager._find_analysis(ep_dir, mock_state)

        assert result is not None
        assert path == glob_path

    def test_find_analysis_returns_none_when_nothing_found(self, tmp_path):
        """_find_analysis returns (None, None) when no analysis JSON exists anywhere."""
        from demo_packager import DemoPackager

        ep_dir = tmp_path / "output" / "ep01"
        ep_dir.mkdir(parents=True)

        mock_state = MagicMock()
        mock_state.is_step_completed.return_value = False

        packager = DemoPackager()
        result, path = packager._find_analysis(ep_dir, mock_state)

        assert result is None
        assert path is None

    def test_find_analysis_returns_none_on_json_parse_error(self, tmp_path):
        """_find_analysis returns (None, None) when analysis file contains invalid JSON."""
        from demo_packager import DemoPackager

        ep_dir = tmp_path / "output" / "ep01"
        ep_dir.mkdir(parents=True)
        bad_json = ep_dir / "audio_analysis.json"
        bad_json.write_text("{invalid json!!!", encoding="utf-8")

        mock_state = MagicMock()
        mock_state.is_step_completed.return_value = False

        packager = DemoPackager()
        result, path = packager._find_analysis(ep_dir, mock_state)

        assert result is None
        assert path is None


# ---------------------------------------------------------------------------
# TestFindWav — _find_wav() / _find_mp3() artifact discovery
# ---------------------------------------------------------------------------


class TestFindWavAndMp3:
    """Tests for _find_wav() and _find_mp3() pipeline state paths."""

    def test_find_wav_via_normalize_state(self, tmp_path):
        """_find_wav returns path from normalize step outputs when completed."""
        from demo_packager import DemoPackager

        ep_dir = tmp_path / "output" / "ep01"
        ep_dir.mkdir(parents=True)
        wav_path = ep_dir / "normalized.wav"
        wav_path.write_bytes(b"FAKE")

        mock_state = MagicMock()
        mock_state.is_step_completed.side_effect = lambda s: s == "normalize"
        mock_state.get_step_outputs.return_value = {"normalized_audio": str(wav_path)}

        packager = DemoPackager()
        result = packager._find_wav(ep_dir, mock_state)

        assert result == wav_path

    def test_find_mp3_via_convert_mp3_state(self, tmp_path):
        """_find_mp3 returns path from convert_mp3 step outputs when completed."""
        from demo_packager import DemoPackager

        ep_dir = tmp_path / "output" / "ep01"
        ep_dir.mkdir(parents=True)
        mp3_path = ep_dir / "final.mp3"
        mp3_path.write_bytes(b"FAKE")

        mock_state = MagicMock()
        mock_state.is_step_completed.side_effect = lambda s: s == "convert_mp3"
        mock_state.get_step_outputs.return_value = {"mp3_path": str(mp3_path)}

        packager = DemoPackager()
        result = packager._find_mp3(ep_dir, mock_state)

        assert result == mp3_path


# ---------------------------------------------------------------------------
# TestFindClips — _find_clips() artifact discovery
# ---------------------------------------------------------------------------


class TestFindClips:
    """Tests for _find_clips() pipeline state path."""

    def test_find_clips_via_convert_videos_state(self, tmp_path):
        """_find_clips returns paths from convert_videos step when completed."""
        from demo_packager import DemoPackager

        clips_dir = tmp_path / "clips" / "client" / "ep01"
        clips_dir.mkdir(parents=True)
        clip1 = clips_dir / "clip_01.mp4"
        clip2 = clips_dir / "clip_02.mp4"
        clip1.write_bytes(b"FAKE")
        clip2.write_bytes(b"FAKE")

        mock_state = MagicMock()
        mock_state.is_step_completed.side_effect = lambda s: s == "convert_videos"
        mock_state.get_step_outputs.return_value = {
            "video_clip_paths": [str(clip1), str(clip2)]
        }

        packager = DemoPackager()
        result = packager._find_clips(clips_dir, mock_state)

        assert len(result) == 2
        assert clip1 in result
        assert clip2 in result


# ---------------------------------------------------------------------------
# TestFindCompliance — _find_compliance() edge cases
# ---------------------------------------------------------------------------


class TestFindCompliance:
    """Tests for _find_compliance() edge cases."""

    def test_find_compliance_returns_none_when_no_files(self, tmp_path):
        """_find_compliance returns (None, None) when no compliance JSON exists."""
        from demo_packager import DemoPackager

        ep_dir = tmp_path / "output" / "ep01"
        ep_dir.mkdir(parents=True)

        packager = DemoPackager()
        result, path = packager._find_compliance(ep_dir)

        assert result is None
        assert path is None

    def test_find_compliance_returns_none_on_json_error(self, tmp_path):
        """_find_compliance returns (None, None) when JSON is malformed."""
        from demo_packager import DemoPackager

        ep_dir = tmp_path / "output" / "ep01"
        ep_dir.mkdir(parents=True)
        bad_json = ep_dir / "compliance_report_001_20260328.json"
        bad_json.write_text("NOT VALID JSON", encoding="utf-8")

        packager = DemoPackager()
        result, path = packager._find_compliance(ep_dir)

        assert result is None
        assert path is None


# ---------------------------------------------------------------------------
# TestExtractAudioSegment — _extract_audio_segment() failure path
# ---------------------------------------------------------------------------


class TestExtractAudioSegment:
    """Tests for _extract_audio_segment() error handling."""

    def test_extract_audio_segment_logs_warning_on_failure(self, tmp_path, caplog):
        """_extract_audio_segment logs warning when FFmpeg subprocess fails."""
        import logging
        from demo_packager import DemoPackager

        src = tmp_path / "source.wav"
        src.write_bytes(b"FAKE")
        dest = tmp_path / "output.wav"

        with (
            patch("demo_packager.subprocess.run", side_effect=Exception("ffmpeg boom")),
            caplog.at_level(logging.WARNING),
        ):
            packager = DemoPackager()
            packager._extract_audio_segment(src, 0.0, 60.0, dest)

        assert any("Failed to extract" in msg for msg in caplog.messages)


# ---------------------------------------------------------------------------
# TestFormatHelpers — _format_clip_list() and _format_compliance_summary()
# ---------------------------------------------------------------------------


class TestFormatHelpers:
    """Tests for _format_clip_list() and _format_compliance_summary()."""

    def test_format_clip_list_empty(self):
        """_format_clip_list returns fallback text for empty list."""
        from demo_packager import DemoPackager

        packager = DemoPackager()
        result = packager._format_clip_list([])

        assert result == "No clips available."

    def test_format_compliance_summary_none(self):
        """_format_compliance_summary returns fallback text when data is None."""
        from demo_packager import DemoPackager

        packager = DemoPackager()
        result = packager._format_compliance_summary(None, False, 0)

        assert result == "No compliance report available."


# ---------------------------------------------------------------------------
# TestPackageDemoEdgeCases — additional package_demo() coverage
# ---------------------------------------------------------------------------


class TestPackageDemoEdgeCases:
    """Tests for edge cases in package_demo()."""

    def test_no_analysis_raises_file_not_found(self, tmp_path, monkeypatch):
        """package_demo raises FileNotFoundError when no analysis JSON exists."""
        from demo_packager import DemoPackager

        ep_dir = tmp_path / "output" / "truecrime" / "ep01"
        ep_dir.mkdir(parents=True)

        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path / "output" / "truecrime")
        monkeypatch.setattr(Config, "CLIPS_DIR", tmp_path / "clips")
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)

        with patch("demo_packager.PipelineState") as mock_state_cls:
            mock_state = MagicMock()
            mock_state.is_step_completed.return_value = False
            mock_state_cls.return_value = mock_state

            packager = DemoPackager()
            with pytest.raises(FileNotFoundError, match="No analysis JSON"):
                packager.package_demo("truecrime", "ep01")

    def test_missing_mp3_skips_processed_audio(self, tmp_path, monkeypatch):
        """package_demo skips processed_audio.mp3 when no MP3 is found."""
        from demo_packager import DemoPackager

        ep_dir, analysis_path, wav_path, mp3_path, thumb_path, clips_dir = (
            _make_episode_dir(tmp_path)
        )
        # Remove MP3
        mp3_path.unlink()

        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path / "output" / "truecrime")
        monkeypatch.setattr(Config, "CLIPS_DIR", tmp_path / "clips")
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)

        with (
            patch("demo_packager.PipelineState") as mock_state_cls,
            patch(
                "demo_packager.DemoPackager._measure_lufs",
                return_value=SAMPLE_LUFS_STATS,
            ),
        ):
            mock_state = MagicMock()
            mock_state.is_step_completed.return_value = False
            mock_state_cls.return_value = mock_state

            packager = DemoPackager()
            demo_path = packager.package_demo("truecrime", "ep01")

        assert not (demo_path / "processed_audio.mp3").exists()

    def test_before_after_sets_flag_when_processed_exists(self, tmp_path, monkeypatch):
        """DEMO.md contains before/after section when raw+processed snapshots exist."""
        from demo_packager import DemoPackager

        ep_dir, analysis_path, wav_path, mp3_path, thumb_path, clips_dir = (
            _make_episode_dir(tmp_path)
        )

        # Create raw snapshot
        raw_snapshot = ep_dir / "audio_20260328_raw_snapshot.wav"
        raw_snapshot.write_bytes(b"FAKE_RAW")

        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path / "output" / "truecrime")
        monkeypatch.setattr(Config, "CLIPS_DIR", tmp_path / "clips")
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)

        def fake_extract(src, start, end, dest):
            """Create the output file to simulate successful extraction."""
            dest.write_bytes(b"EXTRACTED")

        with (
            patch("demo_packager.PipelineState") as mock_state_cls,
            patch(
                "demo_packager.DemoPackager._measure_lufs",
                return_value=SAMPLE_LUFS_STATS,
            ),
            patch.object(
                DemoPackager,
                "_extract_audio_segment",
                side_effect=fake_extract,
            ),
        ):
            mock_state = MagicMock()
            mock_state.is_step_completed.return_value = False
            mock_state_cls.return_value = mock_state

            packager = DemoPackager()
            demo_path = packager.package_demo("truecrime", "ep01")

        demo_md = (demo_path / "DEMO.md").read_text(encoding="utf-8")
        assert "before_after/" in demo_md
        assert "raw_60s.wav" in demo_md


# ---------------------------------------------------------------------------
# TestRunDemoWorkflowCli — run_demo_workflow_cli() function
# ---------------------------------------------------------------------------


class TestRunDemoWorkflowCli:
    """Tests for run_demo_workflow_cli() CLI handler."""

    def test_cli_missing_args_prints_usage(self, capsys):
        """run_demo_workflow_cli prints usage when slug or ep_id is missing."""
        from demo_packager import run_demo_workflow_cli

        run_demo_workflow_cli(["main.py", "demo-workflow"], {})

        captured = capsys.readouterr()
        assert "Usage:" in captured.out

    def test_cli_missing_ep_id_prints_usage(self, capsys):
        """run_demo_workflow_cli prints usage when only slug is provided."""
        from demo_packager import run_demo_workflow_cli

        run_demo_workflow_cli(["main.py", "demo-workflow", "my-slug"], {})

        captured = capsys.readouterr()
        assert "Usage:" in captured.out

    def test_cli_value_error_prints_error(self, capsys):
        """run_demo_workflow_cli catches ValueError and prints error message."""
        from demo_packager import run_demo_workflow_cli

        with patch(
            "demo_packager.run_demo_workflow",
            side_effect=ValueError("not found"),
        ):
            run_demo_workflow_cli(["main.py", "demo-workflow", "slug", "ep01"], {})

        captured = capsys.readouterr()
        assert "Error: not found" in captured.out

    def test_cli_generic_exception_prints_error(self, capsys):
        """run_demo_workflow_cli catches generic exceptions and prints error."""
        from demo_packager import run_demo_workflow_cli

        with patch(
            "demo_packager.run_demo_workflow",
            side_effect=RuntimeError("something broke"),
        ):
            run_demo_workflow_cli(["main.py", "demo-workflow", "slug", "ep01"], {})

        captured = capsys.readouterr()
        assert "Error during demo workflow: something broke" in captured.out

    def test_cli_calls_run_demo_workflow_with_correct_args(self):
        """run_demo_workflow_cli passes slug and ep_id to run_demo_workflow."""
        from demo_packager import run_demo_workflow_cli

        with patch("demo_packager.run_demo_workflow") as mock_run:
            mock_run.return_value = None
            run_demo_workflow_cli(
                ["main.py", "demo-workflow", "my-slug", "ep05"],
                {"test_mode": True},
            )

        mock_run.assert_called_once_with("my-slug", "ep05", {"test_mode": True})


# ---------------------------------------------------------------------------
# TestRunDemoWorkflowInputFallback — input() fallback
# ---------------------------------------------------------------------------


class TestRunDemoWorkflowInputFallback:
    """Tests for run_demo_workflow() input() fallback when consent_fn is None."""

    def test_uses_builtin_input_when_no_consent_fn(self):
        """run_demo_workflow falls back to input() when consent_fn is None."""
        from demo_packager import run_demo_workflow
        from pathlib import Path

        mock_tracker = MagicMock()
        mock_tracker.get_prospect.return_value = {
            "slug": "test",
            "show_name": "Test Show",
            "status": "new",
            "contact_email": "",
        }
        mock_tracker.update_status.return_value = True

        mock_packager = MagicMock()
        mock_packager.package_demo.return_value = Path("/tmp/demo")
        mock_pitch = MagicMock()
        mock_pitch.generate_demo_pitch.return_value = None

        with (
            patch("demo_packager.OutreachTracker", return_value=mock_tracker),
            patch("demo_packager.activate_client"),
            patch("demo_packager.run_with_notification"),
            patch("demo_packager.DemoPackager", return_value=mock_packager),
            patch("demo_packager.PitchGenerator", return_value=mock_pitch),
            patch("builtins.input", return_value="yes") as mock_input,
        ):
            result = run_demo_workflow("test", "ep01", {}, consent_fn=None)

        mock_input.assert_called_once()
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
