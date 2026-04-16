"""Tests for scripts/process_church_batch.py — sequential pipeline runner."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from scripts import process_church_batch as pcb


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def batch_in_tmp(tmp_path, monkeypatch):
    """Point the module's BATCH_DIR/LOG_DIR/STATUS_PATH at a tmp_path."""
    batch = tmp_path / "church_batch"
    monkeypatch.setattr(pcb, "BATCH_DIR", batch)
    monkeypatch.setattr(pcb, "LOG_DIR", batch / "logs")
    monkeypatch.setattr(pcb, "STATUS_PATH", batch / "status.json")
    return batch


# ---------------------------------------------------------------------------
# run_one()
# ---------------------------------------------------------------------------


class TestRunOne:
    """run_one wraps a single pipeline invocation with logging + error isolation."""

    def test_returns_success_shape_on_rc_zero(self, batch_in_tmp):
        """Successful subprocess call produces status=success dict."""
        fake_proc = MagicMock(returncode=0)
        with patch.object(subprocess, "run", return_value=fake_proc):
            result = pcb.run_one("test-slug")

        assert result["slug"] == "test-slug"
        assert result["status"] == "success"
        assert result["return_code"] == 0
        assert result["error"] is None
        assert "started_at" in result
        assert "finished_at" in result
        assert result["duration_sec"] >= 0
        assert "test-slug" in result["log_path"]

    def test_returns_failed_shape_on_rc_nonzero(self, batch_in_tmp):
        """Non-zero exit code is reported as status=failed with the rc surfaced."""
        fake_proc = MagicMock(returncode=2)
        with patch.object(subprocess, "run", return_value=fake_proc):
            result = pcb.run_one("test-slug")

        assert result["status"] == "failed"
        assert result["return_code"] == 2
        assert result["error"] == "exit code 2"

    def test_returns_timeout_shape(self, batch_in_tmp):
        """Timeout from subprocess.TimeoutExpired is categorized separately."""
        exc = subprocess.TimeoutExpired(cmd=["uv"], timeout=10)
        with patch.object(subprocess, "run", side_effect=exc):
            result = pcb.run_one("test-slug")

        assert result["status"] == "timeout"
        assert result["return_code"] == -1
        assert "timed out" in result["error"]

    def test_returns_error_shape_on_unexpected_exception(self, batch_in_tmp):
        """Arbitrary exceptions don't kill the batch — they become status=error."""
        with patch.object(subprocess, "run", side_effect=OSError("boom")):
            result = pcb.run_one("test-slug")

        assert result["status"] == "error"
        assert result["return_code"] == -2
        assert "OSError" in result["error"] or "boom" in result["error"]

    def test_writes_per_prospect_log_file(self, batch_in_tmp):
        """Each run_one call produces a log file at LOG_DIR/{slug}.log."""
        fake_proc = MagicMock(returncode=0)
        with patch.object(subprocess, "run", return_value=fake_proc):
            pcb.run_one("my-prospect")

        log_path = batch_in_tmp / "logs" / "my-prospect.log"
        assert log_path.exists()
        log_content = log_path.read_text(encoding="utf-8")
        assert "my-prospect" in log_content
        assert "CMD:" in log_content

    def test_invokes_correct_uv_command(self, batch_in_tmp):
        """Subprocess is called with the expected 'uv run main.py --client ...' form."""
        fake_proc = MagicMock(returncode=0)
        with patch.object(subprocess, "run", return_value=fake_proc) as mock_run:
            pcb.run_one("foo-church")

        cmd = mock_run.call_args.args[0]
        assert cmd == [
            "uv",
            "run",
            "main.py",
            "--client",
            "foo-church",
            "latest",
            "--auto-approve",
        ]
        # Must enforce a timeout so hung pipelines don't stall the batch forever
        assert mock_run.call_args.kwargs["timeout"] == pcb.PER_PROSPECT_TIMEOUT_SEC

    def test_forces_pythonunbuffered_so_crash_tracebacks_reach_log(self, batch_in_tmp):
        """B011 diagnostic: subprocess stderr is redirected to a log file, which
        block-buffers Python log output. If the pipeline crashes natively
        (STATUS_STACK_BUFFER_OVERRUN), any faulthandler traceback must reach the
        log file — that requires PYTHONUNBUFFERED=1 in the child env."""
        fake_proc = MagicMock(returncode=0)
        with patch.object(subprocess, "run", return_value=fake_proc) as mock_run:
            pcb.run_one("foo-church")

        env = mock_run.call_args.kwargs.get("env")
        assert env is not None, (
            "run_one must pass an explicit env so PYTHONUNBUFFERED sticks"
        )
        assert env.get("PYTHONUNBUFFERED") == "1"


# ---------------------------------------------------------------------------
# write_status()
# ---------------------------------------------------------------------------


class TestWriteStatus:
    """Status file is the contract between the batch runner and external pollers."""

    def test_writes_valid_json(self, batch_in_tmp):
        state = {"prospects_total": 10, "prospects_done": 3, "results": []}
        pcb.write_status(state)

        status = json.loads(pcb.STATUS_PATH.read_text(encoding="utf-8"))
        assert status == state

    def test_creates_batch_dir_if_missing(self, batch_in_tmp):
        """First write should create the directory, not crash."""
        assert not batch_in_tmp.exists()
        pcb.write_status({"x": 1})
        assert batch_in_tmp.exists()
        assert pcb.STATUS_PATH.exists()

    def test_overwrites_previous_status(self, batch_in_tmp):
        """Status file is overwritten each call — external pollers see latest only."""
        pcb.write_status({"prospects_done": 1})
        pcb.write_status({"prospects_done": 5})

        status = json.loads(pcb.STATUS_PATH.read_text(encoding="utf-8"))
        assert status == {"prospects_done": 5}


# ---------------------------------------------------------------------------
# main() — batch orchestration
# ---------------------------------------------------------------------------


class TestBatchMain:
    """End-to-end batch driver behavior."""

    def test_all_success_returns_zero(self, batch_in_tmp, monkeypatch):
        """Exit 0 when every prospect succeeds."""
        monkeypatch.setattr(pcb, "PROSPECTS", ["a", "b"])
        fake_proc = MagicMock(returncode=0)
        with patch.object(subprocess, "run", return_value=fake_proc):
            rc = pcb.main()

        assert rc == 0
        status = json.loads(pcb.STATUS_PATH.read_text(encoding="utf-8"))
        assert status["prospects_done"] == 2
        assert all(r["status"] == "success" for r in status["results"])

    def test_partial_failure_returns_nonzero(self, batch_in_tmp, monkeypatch):
        """Exit nonzero if any prospect fails, but batch still completes the rest."""
        monkeypatch.setattr(pcb, "PROSPECTS", ["ok-1", "fails", "ok-2"])

        def fake_run(cmd, **kwargs):
            slug = cmd[4]  # --client <slug>
            return MagicMock(returncode=5 if slug == "fails" else 0)

        with patch.object(subprocess, "run", side_effect=fake_run):
            rc = pcb.main()

        assert rc == 1
        status = json.loads(pcb.STATUS_PATH.read_text(encoding="utf-8"))
        slugs_to_status = {r["slug"]: r["status"] for r in status["results"]}
        assert slugs_to_status == {
            "ok-1": "success",
            "fails": "failed",
            "ok-2": "success",
        }

    def test_status_file_updated_between_prospects(self, batch_in_tmp, monkeypatch):
        """Status JSON is written after each prospect, not only at the end — so
        external pollers can track progress live (Wave C depends on this)."""
        monkeypatch.setattr(pcb, "PROSPECTS", ["one", "two", "three"])

        writes_seen = []
        original_write = pcb.write_status

        def capture(state):
            # Capture a snapshot at each write point
            writes_seen.append(state.copy())
            return original_write(state)

        monkeypatch.setattr(pcb, "write_status", capture)

        fake_proc = MagicMock(returncode=0)
        with patch.object(subprocess, "run", return_value=fake_proc):
            pcb.main()

        # Expect writes interleaved with each prospect's start + finish —
        # so prospects_done values should be observable as 0, 1, 2, 3 somewhere.
        done_values = sorted({w.get("prospects_done", 0) for w in writes_seen})
        assert 0 in done_values
        assert 3 in done_values
        # At least 4 writes total (initial + one after each of 3 prospects + marker)
        assert len(writes_seen) >= 4

    def test_exception_in_one_prospect_does_not_abort_batch(
        self, batch_in_tmp, monkeypatch
    ):
        """A subprocess exception on prospect 2 should not stop prospect 3."""
        monkeypatch.setattr(pcb, "PROSPECTS", ["first", "bad", "third"])

        def fake_run(cmd, **kwargs):
            slug = cmd[4]
            if slug == "bad":
                raise RuntimeError("whisper died")
            return MagicMock(returncode=0)

        with patch.object(subprocess, "run", side_effect=fake_run):
            pcb.main()

        status = json.loads(pcb.STATUS_PATH.read_text(encoding="utf-8"))
        slugs = [r["slug"] for r in status["results"]]
        assert slugs == ["first", "bad", "third"]
        assert status["results"][1]["status"] == "error"
