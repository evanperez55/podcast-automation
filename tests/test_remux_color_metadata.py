"""Tests for scripts/remux_color_metadata.py — H.264 color VUI patch."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts import remux_color_metadata as rcm


class TestBuildRemuxCmd:
    """The ffmpeg command must stream-copy and run the bt709 bitstream filter."""

    def test_command_uses_stream_copy(self):
        cmd = rcm.build_remux_cmd(Path("in.mp4"), Path("out.mp4"))
        assert "-c" in cmd
        assert cmd[cmd.index("-c") + 1] == "copy"

    def test_command_applies_h264_metadata_bsf(self):
        cmd = rcm.build_remux_cmd(Path("in.mp4"), Path("out.mp4"))
        assert "-bsf:v" in cmd
        bsf = cmd[cmd.index("-bsf:v") + 1]
        # AVC value 1 == bt709 for all three VUI fields.
        assert "colour_primaries=1" in bsf
        assert "transfer_characteristics=1" in bsf
        assert "matrix_coefficients=1" in bsf

    def test_command_keeps_faststart(self):
        cmd = rcm.build_remux_cmd(Path("in.mp4"), Path("out.mp4"))
        assert "-movflags" in cmd
        assert cmd[cmd.index("-movflags") + 1] == "+faststart"

    def test_command_paths_present(self):
        cmd = rcm.build_remux_cmd(Path("a.mp4"), Path("b.mp4"))
        assert "a.mp4" in cmd
        assert "b.mp4" in cmd


class TestRemuxOne:
    """In-place remux replaces the source on success, leaves it on failure."""

    @patch("scripts.remux_color_metadata.subprocess.run")
    def test_success_replaces_source(self, mock_run, tmp_path):
        src = tmp_path / "clip.mp4"
        src.write_bytes(b"original-bytes")

        # Simulate ffmpeg writing the .colorfix.tmp.mp4 sidecar then exiting 0.
        def fake_run(cmd, **kwargs):
            tmp_dst = Path(cmd[cmd.index("-y") + 1] if False else cmd[-1])
            tmp_dst.write_bytes(b"remuxed-bytes")
            return MagicMock(returncode=0, stderr="")

        mock_run.side_effect = fake_run
        ok = rcm.remux_one(src)

        assert ok is True
        assert src.read_bytes() == b"remuxed-bytes"
        # Tmp sidecar must be cleaned up by the move.
        assert not (tmp_path / "clip.mp4.colorfix.tmp.mp4").exists()

    @patch("scripts.remux_color_metadata.subprocess.run")
    def test_failure_keeps_source_and_cleans_tmp(self, mock_run, tmp_path):
        src = tmp_path / "clip.mp4"
        src.write_bytes(b"original-bytes")

        def fake_run(cmd, **kwargs):
            Path(cmd[-1]).write_bytes(b"partial")
            return MagicMock(returncode=1, stderr="boom")

        mock_run.side_effect = fake_run
        ok = rcm.remux_one(src)

        assert ok is False
        assert src.read_bytes() == b"original-bytes"
        assert not (tmp_path / "clip.mp4.colorfix.tmp.mp4").exists()

    def test_missing_source_returns_false(self, tmp_path):
        ok = rcm.remux_one(tmp_path / "ghost.mp4")
        assert ok is False


class TestExpandInputs:
    """CLI args resolve to a deduplicated list of MP4 paths."""

    def test_literal_paths_passthrough(self, tmp_path):
        a = tmp_path / "a.mp4"
        a.touch()
        out = rcm.expand_inputs([str(a)], all_churches=False)
        assert out == [a]

    def test_non_mp4_skipped(self, tmp_path):
        bad = tmp_path / "thumb.png"
        bad.touch()
        good = tmp_path / "ok.mp4"
        good.touch()
        out = rcm.expand_inputs([str(bad), str(good)], all_churches=False)
        assert out == [good]

    def test_dedupes_by_resolved_path(self, tmp_path):
        a = tmp_path / "a.mp4"
        a.touch()
        out = rcm.expand_inputs([str(a), str(a)], all_churches=False)
        assert len(out) == 1


class TestMain:
    """End-to-end exit-code wiring."""

    @patch("scripts.remux_color_metadata.remux_one", return_value=True)
    def test_exit_zero_on_all_success(self, mock_remux, tmp_path):
        a = tmp_path / "a.mp4"
        a.touch()
        rc = rcm.main([str(a)])
        assert rc == 0

    @patch("scripts.remux_color_metadata.remux_one", return_value=False)
    def test_exit_one_on_any_failure(self, mock_remux, tmp_path):
        a = tmp_path / "a.mp4"
        a.touch()
        rc = rcm.main([str(a)])
        assert rc == 1

    def test_no_targets_errors_out(self, tmp_path):
        # Glob expression that matches nothing → empty target list → argparse error.
        with pytest.raises(SystemExit):
            rcm.main([str(tmp_path / "no-match-*.mp4")])
