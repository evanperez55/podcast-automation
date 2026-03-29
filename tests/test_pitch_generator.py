"""Tests for pitch_generator.py — PitchGenerator class (intro and demo pitch modes)."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from pitch_generator import PitchGenerator, run_gen_pitch_cli

# ---------------------------------------------------------------------------
# Sample test data
# ---------------------------------------------------------------------------

SAMPLE_PROSPECT_YAML = """
podcast_name: The Comedy Pod
prospect:
  itunes_id: 123456
  genre: comedy
  episode_count: 150
  host_email: host@example.com
  social_links:
    twitter: "@comedypod"
"""

SAMPLE_ANALYSIS = {
    "episode_title": "Test Episode Title",
    "episode_summary": "A great episode about testing and comedy.",
    "show_notes": "Check out our sponsors. This episode covers...",
    "chapters": [{"time": "0:00", "title": "Intro"}],
    "social_captions": {"youtube": "YT caption"},
    "best_clips": [
        {"start": 10.0, "end": 70.0, "description": "Funny bit about testing"},
    ],
}

SAMPLE_GPT_RESPONSE = """### SUBJECT
Your podcast could save 6+ hours per episode

### EMAIL
Hey Comedy Pod team,

Just listened to a few episodes — your timing is sharp. We automate the
production side: transcription, audio mastering, clip extraction, captions,
thumbnails, and show notes from one command.

Typically saves hosts 6-11 hours per episode at $1-2 in AI costs.

Worth a quick chat?

### DM
Hey! Big fan of Comedy Pod. We automate podcast production (transcripts, clips,
captions). Saves ~8hrs/episode. Want to see a free demo?"""

SAMPLE_DEMO_MD = """# Demo: Test Episode Title

**Client:** comedy-pod
**Episode:** ep25
**Processed:** 2026-03-28

## What Was Automated

| Step | Tool | What Happened |
|------|------|---------------|
| Audio Mastering | FFmpeg loudnorm EBU R128 | -22.3 LUFS -> -16.0 LUFS (target: -16 LUFS) |
| Clip Extraction | pydub + FFmpeg | 3 clips selected by energy scoring |
"""


# ---------------------------------------------------------------------------
# TestPitchGeneratorInit
# ---------------------------------------------------------------------------


class TestPitchGeneratorInit:
    """Tests for PitchGenerator.__init__."""

    def test_enabled_when_api_key_set(self):
        """enabled=True when OPENAI_API_KEY is present."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test123"}):
            with patch("pitch_generator.openai.OpenAI"):
                gen = PitchGenerator()
        assert gen.enabled is True

    def test_disabled_when_api_key_missing(self):
        """enabled=False when OPENAI_API_KEY is not set."""
        with patch("pitch_generator.Config") as mock_cfg:
            mock_cfg.OPENAI_API_KEY = None
            mock_cfg.BASE_DIR = Path(".")
            mock_cfg.OUTPUT_DIR = Path("output")
            gen = PitchGenerator()
        assert gen.enabled is False

    def test_client_not_created_when_disabled(self):
        """OpenAI client is not instantiated when disabled."""
        with patch("pitch_generator.Config") as mock_cfg:
            mock_cfg.OPENAI_API_KEY = None
            mock_cfg.BASE_DIR = Path(".")
            mock_cfg.OUTPUT_DIR = Path("output")
            gen = PitchGenerator()
        assert not hasattr(gen, "client")


# ---------------------------------------------------------------------------
# TestGenerateIntroPitch
# ---------------------------------------------------------------------------


class TestGenerateIntroPitch:
    """Tests for PitchGenerator.generate_intro_pitch."""

    def _make_gen(self):
        with patch("pitch_generator.Config") as mock_cfg:
            mock_cfg.OPENAI_API_KEY = "sk-test"
            mock_cfg.BASE_DIR = Path(".")
            mock_cfg.OUTPUT_DIR = Path("output")
            with patch("pitch_generator.openai.OpenAI"):
                gen = PitchGenerator()
        gen.enabled = True
        gen.client = MagicMock()
        return gen

    def test_returns_none_when_disabled(self):
        """Returns None immediately if disabled — no file I/O."""
        with patch("pitch_generator.Config") as mock_cfg:
            mock_cfg.OPENAI_API_KEY = None
            mock_cfg.BASE_DIR = Path(".")
            mock_cfg.OUTPUT_DIR = Path("output")
            gen = PitchGenerator()
        result = gen.generate_intro_pitch("comedy-pod")
        assert result is None

    def test_raises_on_missing_yaml(self, tmp_path):
        """FileNotFoundError raised when client YAML does not exist."""
        gen = self._make_gen()
        with patch("pitch_generator.Config") as mock_cfg:
            mock_cfg.BASE_DIR = tmp_path
            mock_cfg.OUTPUT_DIR = tmp_path / "output"
            with pytest.raises(FileNotFoundError):
                gen.generate_intro_pitch("nonexistent-client")

    def test_reads_prospect_yaml_and_calls_gpt(self, tmp_path):
        """Reads YAML prospect: block, calls GPT-4o, returns dict with expected keys."""
        gen = self._make_gen()

        # Create client YAML
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "comedy-pod.yaml").write_text(
            SAMPLE_PROSPECT_YAML, encoding="utf-8"
        )

        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = SAMPLE_GPT_RESPONSE
        gen.client.chat.completions.create.return_value = mock_response

        with patch("pitch_generator.Config") as mock_cfg:
            mock_cfg.BASE_DIR = tmp_path
            mock_cfg.OUTPUT_DIR = tmp_path / "output"
            result = gen.generate_intro_pitch("comedy-pod")

        assert result is not None
        assert "subject" in result
        assert "email" in result
        assert "dm" in result
        assert "path" in result

    def test_writes_pitch_md_to_correct_path(self, tmp_path):
        """PITCH.md written to demo/<slug>/PITCH.md."""
        gen = self._make_gen()

        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "comedy-pod.yaml").write_text(
            SAMPLE_PROSPECT_YAML, encoding="utf-8"
        )

        mock_response = MagicMock()
        mock_response.choices[0].message.content = SAMPLE_GPT_RESPONSE
        gen.client.chat.completions.create.return_value = mock_response

        with patch("pitch_generator.Config") as mock_cfg:
            mock_cfg.BASE_DIR = tmp_path
            mock_cfg.OUTPUT_DIR = tmp_path / "output"
            result = gen.generate_intro_pitch("comedy-pod")

        expected_path = tmp_path / "demo" / "comedy-pod" / "PITCH.md"
        assert expected_path.exists()
        assert result["path"] == expected_path

    def test_pitch_md_contains_sections(self, tmp_path):
        """Written PITCH.md contains Subject Line, Email Body, and DM Variant sections."""
        gen = self._make_gen()

        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "comedy-pod.yaml").write_text(
            SAMPLE_PROSPECT_YAML, encoding="utf-8"
        )

        mock_response = MagicMock()
        mock_response.choices[0].message.content = SAMPLE_GPT_RESPONSE
        gen.client.chat.completions.create.return_value = mock_response

        with patch("pitch_generator.Config") as mock_cfg:
            mock_cfg.BASE_DIR = tmp_path
            mock_cfg.OUTPUT_DIR = tmp_path / "output"
            gen.generate_intro_pitch("comedy-pod")

        pitch_md = (tmp_path / "demo" / "comedy-pod" / "PITCH.md").read_text()
        assert "## Subject Line" in pitch_md
        assert "## Email Body" in pitch_md
        assert "## DM Variant" in pitch_md


# ---------------------------------------------------------------------------
# TestGenerateDemoPitch
# ---------------------------------------------------------------------------


class TestGenerateDemoPitch:
    """Tests for PitchGenerator.generate_demo_pitch."""

    def _make_gen(self):
        with patch("pitch_generator.Config") as mock_cfg:
            mock_cfg.OPENAI_API_KEY = "sk-test"
            mock_cfg.BASE_DIR = Path(".")
            mock_cfg.OUTPUT_DIR = Path("output")
            with patch("pitch_generator.openai.OpenAI"):
                gen = PitchGenerator()
        gen.enabled = True
        gen.client = MagicMock()
        return gen

    def test_returns_none_when_disabled(self):
        """Returns None immediately if disabled."""
        with patch("pitch_generator.Config") as mock_cfg:
            mock_cfg.OPENAI_API_KEY = None
            mock_cfg.BASE_DIR = Path(".")
            mock_cfg.OUTPUT_DIR = Path("output")
            gen = PitchGenerator()
        result = gen.generate_demo_pitch("comedy-pod", "ep25")
        assert result is None

    def test_returns_none_when_demo_md_missing(self, tmp_path):
        """Returns None and logs warning when DEMO.md not found."""
        gen = self._make_gen()

        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "comedy-pod.yaml").write_text(
            SAMPLE_PROSPECT_YAML, encoding="utf-8"
        )
        # No DEMO.md created

        with patch("pitch_generator.Config") as mock_cfg:
            mock_cfg.BASE_DIR = tmp_path
            mock_cfg.OUTPUT_DIR = tmp_path / "output"
            result = gen.generate_demo_pitch("comedy-pod", "ep25")

        assert result is None

    def test_returns_none_when_analysis_missing(self, tmp_path):
        """Returns None and logs warning when analysis JSON not found."""
        gen = self._make_gen()

        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "comedy-pod.yaml").write_text(
            SAMPLE_PROSPECT_YAML, encoding="utf-8"
        )

        # Create DEMO.md but no analysis JSON
        demo_dir = tmp_path / "demo" / "comedy-pod" / "ep25"
        demo_dir.mkdir(parents=True)
        (demo_dir / "DEMO.md").write_text(SAMPLE_DEMO_MD, encoding="utf-8")

        with patch("pitch_generator.Config") as mock_cfg:
            mock_cfg.BASE_DIR = tmp_path
            mock_cfg.OUTPUT_DIR = tmp_path / "output"
            result = gen.generate_demo_pitch("comedy-pod", "ep25")

        assert result is None

    def test_returns_dict_on_success(self, tmp_path):
        """Returns dict with subject/email/dm/path on success."""
        gen = self._make_gen()

        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "comedy-pod.yaml").write_text(
            SAMPLE_PROSPECT_YAML, encoding="utf-8"
        )

        demo_dir = tmp_path / "demo" / "comedy-pod" / "ep25"
        demo_dir.mkdir(parents=True)
        (demo_dir / "DEMO.md").write_text(SAMPLE_DEMO_MD, encoding="utf-8")

        ep_dir = tmp_path / "output" / "ep25"
        ep_dir.mkdir(parents=True)
        analysis_path = ep_dir / "ep25_analysis.json"
        analysis_path.write_text(json.dumps(SAMPLE_ANALYSIS), encoding="utf-8")

        mock_response = MagicMock()
        mock_response.choices[0].message.content = SAMPLE_GPT_RESPONSE
        gen.client.chat.completions.create.return_value = mock_response

        with patch("pitch_generator.Config") as mock_cfg:
            mock_cfg.BASE_DIR = tmp_path
            mock_cfg.OUTPUT_DIR = tmp_path / "output"
            result = gen.generate_demo_pitch("comedy-pod", "ep25")

        assert result is not None
        assert "subject" in result
        assert "email" in result
        assert "dm" in result
        assert "path" in result

    def test_writes_pitch_md_to_correct_path(self, tmp_path):
        """PITCH.md written to demo/<slug>/<ep_id>/PITCH.md."""
        gen = self._make_gen()

        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "comedy-pod.yaml").write_text(
            SAMPLE_PROSPECT_YAML, encoding="utf-8"
        )

        demo_dir = tmp_path / "demo" / "comedy-pod" / "ep25"
        demo_dir.mkdir(parents=True)
        (demo_dir / "DEMO.md").write_text(SAMPLE_DEMO_MD, encoding="utf-8")

        ep_dir = tmp_path / "output" / "ep25"
        ep_dir.mkdir(parents=True)
        analysis_path = ep_dir / "ep25_analysis.json"
        analysis_path.write_text(json.dumps(SAMPLE_ANALYSIS), encoding="utf-8")

        mock_response = MagicMock()
        mock_response.choices[0].message.content = SAMPLE_GPT_RESPONSE
        gen.client.chat.completions.create.return_value = mock_response

        with patch("pitch_generator.Config") as mock_cfg:
            mock_cfg.BASE_DIR = tmp_path
            mock_cfg.OUTPUT_DIR = tmp_path / "output"
            result = gen.generate_demo_pitch("comedy-pod", "ep25")

        expected_path = tmp_path / "demo" / "comedy-pod" / "ep25" / "PITCH.md"
        assert expected_path.exists()
        assert result["path"] == expected_path


# ---------------------------------------------------------------------------
# TestParsePitchResponse
# ---------------------------------------------------------------------------


class TestParsePitchResponse:
    """Tests for PitchGenerator._parse_pitch_response."""

    def _make_gen(self):
        with patch("pitch_generator.Config") as mock_cfg:
            mock_cfg.OPENAI_API_KEY = "sk-test"
            mock_cfg.BASE_DIR = Path(".")
            mock_cfg.OUTPUT_DIR = Path("output")
            with patch("pitch_generator.openai.OpenAI"):
                gen = PitchGenerator()
        gen.enabled = True
        return gen

    def test_parses_all_three_sections(self):
        """Parses SUBJECT, EMAIL, and DM from delimited GPT-4o response."""
        gen = self._make_gen()
        result = gen._parse_pitch_response(SAMPLE_GPT_RESPONSE)
        assert result["subject"] != ""
        assert result["email"] != ""
        assert result["dm"] != ""

    def test_parses_subject_correctly(self):
        """Subject section contains expected content."""
        gen = self._make_gen()
        result = gen._parse_pitch_response(SAMPLE_GPT_RESPONSE)
        assert (
            "save" in result["subject"].lower()
            or "podcast" in result["subject"].lower()
        )

    def test_handles_missing_sections_gracefully(self):
        """Returns empty string defaults for missing sections."""
        gen = self._make_gen()
        result = gen._parse_pitch_response("### SUBJECT\nHello world")
        assert result["subject"] == "Hello world"
        assert result["email"] == ""
        assert result["dm"] == ""

    def test_handles_empty_response(self):
        """Returns empty dict keys for completely empty response."""
        gen = self._make_gen()
        result = gen._parse_pitch_response("")
        assert result["subject"] == ""
        assert result["email"] == ""
        assert result["dm"] == ""


# ---------------------------------------------------------------------------
# TestLoadAnalysis
# ---------------------------------------------------------------------------


class TestLoadAnalysis:
    """Tests for PitchGenerator._load_analysis."""

    def _make_gen(self):
        with patch("pitch_generator.Config") as mock_cfg:
            mock_cfg.OPENAI_API_KEY = "sk-test"
            mock_cfg.BASE_DIR = Path(".")
            mock_cfg.OUTPUT_DIR = Path("output")
            with patch("pitch_generator.openai.OpenAI"):
                gen = PitchGenerator()
        gen.enabled = True
        return gen

    def test_returns_newest_analysis_by_mtime(self, tmp_path):
        """Returns newest analysis JSON by mtime when multiple exist."""
        gen = self._make_gen()

        ep_dir = tmp_path / "output" / "ep25"
        ep_dir.mkdir(parents=True)

        old_file = ep_dir / "ep25_analysis_old.json"
        old_file.write_text(json.dumps({"episode_title": "Old"}), encoding="utf-8")

        import time

        time.sleep(0.01)  # ensure mtime difference

        new_file = ep_dir / "ep25_analysis_new.json"
        new_file.write_text(json.dumps({"episode_title": "New"}), encoding="utf-8")

        with patch("pitch_generator.Config") as mock_cfg:
            mock_cfg.BASE_DIR = tmp_path
            mock_cfg.OUTPUT_DIR = tmp_path / "output"
            result = gen._load_analysis("comedy-pod", "ep25")

        assert result["episode_title"] == "New"

    def test_raises_when_no_analysis_found(self, tmp_path):
        """FileNotFoundError raised when no analysis JSON exists."""
        gen = self._make_gen()

        ep_dir = tmp_path / "output" / "ep25"
        ep_dir.mkdir(parents=True)

        with patch("pitch_generator.Config") as mock_cfg:
            mock_cfg.BASE_DIR = tmp_path
            mock_cfg.OUTPUT_DIR = tmp_path / "output"
            with pytest.raises(FileNotFoundError):
                gen._load_analysis("comedy-pod", "ep25")


# ---------------------------------------------------------------------------
# TestWritePitchMd
# ---------------------------------------------------------------------------


class TestWritePitchMd:
    """Tests for PitchGenerator._write_pitch_md."""

    def _make_gen(self):
        with patch("pitch_generator.Config") as mock_cfg:
            mock_cfg.OPENAI_API_KEY = "sk-test"
            mock_cfg.BASE_DIR = Path(".")
            mock_cfg.OUTPUT_DIR = Path("output")
            with patch("pitch_generator.openai.OpenAI"):
                gen = PitchGenerator()
        gen.enabled = True
        return gen

    def test_creates_parent_dirs(self, tmp_path):
        """Creates parent directories before writing."""
        gen = self._make_gen()
        path = tmp_path / "demo" / "comedy-pod" / "PITCH.md"
        pitch = {
            "podcast_name": "Comedy Pod",
            "subject": "Test subject",
            "email": "Test email body",
            "dm": "Test DM",
        }
        gen._write_pitch_md(path, pitch)
        assert path.exists()

    def test_returns_path(self, tmp_path):
        """Returns the Path written to."""
        gen = self._make_gen()
        path = tmp_path / "PITCH.md"
        pitch = {
            "podcast_name": "Comedy Pod",
            "subject": "Test subject",
            "email": "Test email body",
            "dm": "Test DM",
        }
        result = gen._write_pitch_md(path, pitch)
        assert result == path

    def test_writes_subject_email_dm_sections(self, tmp_path):
        """Written file contains Subject Line, Email Body, and DM Variant sections."""
        gen = self._make_gen()
        path = tmp_path / "PITCH.md"
        pitch = {
            "podcast_name": "Comedy Pod",
            "subject": "My great subject",
            "email": "Dear host,\n\nThis is the email.",
            "dm": "Short DM here",
        }
        gen._write_pitch_md(path, pitch)
        content = path.read_text(encoding="utf-8")
        assert "## Subject Line" in content
        assert "My great subject" in content
        assert "## Email Body" in content
        assert "Dear host," in content
        assert "## DM Variant" in content
        assert "Short DM here" in content


# ---------------------------------------------------------------------------
# TestCallOpenaiWithRetry
# ---------------------------------------------------------------------------


class TestCallOpenaiWithRetry:
    """Tests for PitchGenerator._call_openai_with_retry."""

    def _make_gen(self):
        with patch("pitch_generator.Config") as mock_cfg:
            mock_cfg.OPENAI_API_KEY = "sk-test"
            mock_cfg.BASE_DIR = Path(".")
            mock_cfg.OUTPUT_DIR = Path("output")
            with patch("pitch_generator.openai.OpenAI"):
                gen = PitchGenerator()
        gen.enabled = True
        gen.client = MagicMock()
        return gen

    def test_retries_on_rate_limit_error(self):
        """Retries on RateLimitError before succeeding."""
        import openai as oai

        gen = self._make_gen()
        mock_response = MagicMock()
        gen.client.chat.completions.create.side_effect = [
            oai.RateLimitError("rate limited", response=MagicMock(), body={}),
            mock_response,
        ]

        with patch("pitch_generator.time.sleep"):
            result = gen._call_openai_with_retry("sys", "user", max_retries=3)

        assert result == mock_response
        assert gen.client.chat.completions.create.call_count == 2

    def test_raises_after_max_retries_exhausted(self):
        """Raises after all retries are exhausted."""
        import openai as oai

        gen = self._make_gen()
        error = oai.RateLimitError("rate limited", response=MagicMock(), body={})
        gen.client.chat.completions.create.side_effect = error

        with patch("pitch_generator.time.sleep"):
            with pytest.raises(oai.RateLimitError):
                gen._call_openai_with_retry("sys", "user", max_retries=2)

        assert gen.client.chat.completions.create.call_count == 3  # initial + 2 retries

    def test_success_on_first_attempt(self):
        """Returns immediately on first successful call."""
        gen = self._make_gen()
        mock_response = MagicMock()
        gen.client.chat.completions.create.return_value = mock_response

        result = gen._call_openai_with_retry("sys", "user")

        assert result == mock_response
        assert gen.client.chat.completions.create.call_count == 1


# ---------------------------------------------------------------------------
# TestRunGenPitchCli
# ---------------------------------------------------------------------------


class TestRunGenPitchCli:
    """Tests for run_gen_pitch_cli standalone function."""

    def test_dispatches_to_intro_pitch_with_one_arg(self, capsys):
        """Calls generate_intro_pitch when only slug provided."""
        mock_gen = MagicMock()
        mock_gen.generate_intro_pitch.return_value = {
            "subject": "Test",
            "email": "body",
            "dm": "dm",
            "path": Path("demo/comedy-pod/PITCH.md"),
        }
        with patch("pitch_generator.PitchGenerator", return_value=mock_gen):
            run_gen_pitch_cli(["main.py", "gen-pitch", "comedy-pod"])

        mock_gen.generate_intro_pitch.assert_called_once_with("comedy-pod")
        mock_gen.generate_demo_pitch.assert_not_called()

    def test_dispatches_to_demo_pitch_with_two_args(self, capsys):
        """Calls generate_demo_pitch when slug and ep_id provided."""
        mock_gen = MagicMock()
        mock_gen.generate_demo_pitch.return_value = {
            "subject": "Test",
            "email": "body",
            "dm": "dm",
            "path": Path("demo/comedy-pod/ep25/PITCH.md"),
        }
        with patch("pitch_generator.PitchGenerator", return_value=mock_gen):
            run_gen_pitch_cli(["main.py", "gen-pitch", "comedy-pod", "ep25"])

        mock_gen.generate_demo_pitch.assert_called_once_with("comedy-pod", "ep25")
        mock_gen.generate_intro_pitch.assert_not_called()

    def test_prints_usage_when_no_slug(self, capsys):
        """Prints usage message when no slug argument provided."""
        run_gen_pitch_cli(["main.py", "gen-pitch"])
        captured = capsys.readouterr()
        assert "Usage" in captured.out

    def test_prints_path_on_success(self, capsys):
        """Prints pitch path on successful generation."""
        mock_gen = MagicMock()
        mock_gen.generate_intro_pitch.return_value = {
            "subject": "Test",
            "email": "body",
            "dm": "dm",
            "path": Path("demo/comedy-pod/PITCH.md"),
        }
        with patch("pitch_generator.PitchGenerator", return_value=mock_gen):
            run_gen_pitch_cli(["main.py", "gen-pitch", "comedy-pod"])

        captured = capsys.readouterr()
        assert "PITCH.md" in captured.out

    def test_prints_error_when_result_is_none(self, capsys):
        """Prints error message when generation returns None."""
        mock_gen = MagicMock()
        mock_gen.generate_intro_pitch.return_value = None
        with patch("pitch_generator.PitchGenerator", return_value=mock_gen):
            run_gen_pitch_cli(["main.py", "gen-pitch", "comedy-pod"])

        captured = capsys.readouterr()
        assert (
            "Error" in captured.out
            or "error" in captured.out
            or "failed" in captured.out.lower()
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
