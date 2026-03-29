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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
