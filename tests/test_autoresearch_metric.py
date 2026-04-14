"""Tests for scripts/autoresearch_metric.py — composite test/coverage score."""
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from scripts import autoresearch_metric as arm


class TestMain:
    """main() parses pytest --cov output and prints a composite score."""

    def _fake_pytest(self, stdout: str):
        return MagicMock(stdout=stdout, stderr="")

    def test_parses_passed_count(self, capsys):
        output = "\n".join(
            [
                "......",
                "100 passed in 5s",
                "Name    Stmts    Miss    Cover",
                "TOTAL    1000   200    80%",
            ]
        )
        with patch.object(subprocess, "run", return_value=self._fake_pytest(output)):
            arm.main()

        out = capsys.readouterr().out
        assert "passed=100" in out
        assert "failed=0" in out
        assert "errors=0" in out
        assert "coverage=80.0%" in out
        # Composite: 80 * 0.7 + 100 * 0.3 = 56 + 30 = 86.00
        assert "SCORE: 86.00" in out

    def test_parses_failed_and_error_counts(self, capsys):
        output = "\n".join(
            [
                "95 passed, 3 failed, 2 error in 5s",
                "TOTAL    1000    300    70%",
            ]
        )
        with patch.object(subprocess, "run", return_value=self._fake_pytest(output)):
            arm.main()

        out = capsys.readouterr().out
        assert "passed=95" in out
        assert "failed=3" in out
        assert "errors=2" in out
        # pass_rate = 95 / 100 * 100 = 95
        # score = 70 * 0.7 + 95 * 0.3 = 49 + 28.5 = 77.5
        assert "SCORE: 77.50" in out

    def test_handles_missing_coverage_line(self, capsys):
        """If pytest output has no TOTAL coverage line, coverage is 0."""
        output = "50 passed in 1s\n(no coverage output)"
        with patch.object(subprocess, "run", return_value=self._fake_pytest(output)):
            arm.main()

        out = capsys.readouterr().out
        assert "coverage=0" in out
        # score = 0 * 0.7 + 100 * 0.3 = 30.00
        assert "SCORE: 30.00" in out

    def test_handles_zero_tests(self, capsys):
        """If pytest reports no tests at all, pass_rate is 0 (no div by zero)."""
        output = "no tests ran\nTOTAL    100    100    0%"
        with patch.object(subprocess, "run", return_value=self._fake_pytest(output)):
            arm.main()

        out = capsys.readouterr().out
        # With no passed match, the regex won't match and all counts are 0
        assert "passed=0" in out
        # score = 0 * 0.7 + 0 * 0.3 = 0
        assert "SCORE: 0.00" in out

    def test_reads_from_stderr_too(self, capsys):
        """pytest sometimes puts the summary on stderr — both streams are parsed."""
        with patch.object(
            subprocess,
            "run",
            return_value=MagicMock(
                stdout="TOTAL    1000    0    100%",
                stderr="200 passed in 2s",
            ),
        ):
            arm.main()

        out = capsys.readouterr().out
        assert "passed=200" in out
        assert "coverage=100.0%" in out
        assert "SCORE: 100.00" in out
