"""Tests for ContentComplianceChecker — YouTube community guidelines compliance analysis."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from content_compliance_checker import (
    ContentComplianceChecker,
    VIOLATION_CATEGORIES,
    SEVERITY_MAP,
    _build_compliance_prompt,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_TRANSCRIPT = {
    "segments": [
        {"start": 0.0, "end": 5.0, "text": "Welcome to the show."},
        {"start": 5.0, "end": 10.0, "text": "Today we discuss some dark topics."},
        {
            "start": 1234.0,
            "end": 1238.0,
            "text": "Drinking bleach cures cancer, trust me.",
        },
    ],
    "words": [],
}

SAMPLE_VIOLATION_RESPONSE = json.dumps(
    [
        {
            "start_timestamp": "00:20:34",
            "end_timestamp": "00:20:38",
            "text": "Drinking bleach cures cancer, trust me.",
            "category": "dangerous_misinformation",
            "reason": "False medical claim that could cause physical harm",
        }
    ]
)

SAMPLE_EMPTY_RESPONSE = json.dumps([])

SAMPLE_HATE_SPEECH_RESPONSE = json.dumps(
    [
        {
            "start_timestamp": "00:05:00",
            "end_timestamp": "00:05:05",
            "text": "Some hate speech content.",
            "category": "hate_speech",
            "reason": "Dehumanizing content targeting a protected group",
        }
    ]
)

SAMPLE_WARNING_RESPONSE = json.dumps(
    [
        {
            "start_timestamp": "00:08:20",
            "end_timestamp": "00:08:25",
            "text": "Graphic violence description.",
            "category": "graphic_violence",
            "reason": "Explicit description of violence",
        }
    ]
)

SAMPLE_MIXED_RESPONSE = json.dumps(
    [
        {
            "start_timestamp": "00:05:00",
            "end_timestamp": "00:05:05",
            "text": "Some hate speech content.",
            "category": "hate_speech",
            "reason": "Dehumanizing content targeting a protected group",
        },
        {
            "start_timestamp": "00:08:20",
            "end_timestamp": "00:08:25",
            "text": "Graphic violence description.",
            "category": "graphic_violence",
            "reason": "Explicit description of violence",
        },
    ]
)


def make_mock_client(response_content: str):
    """Build a mock OpenAI client that returns the given content."""
    mock_message = Mock()
    mock_message.content = response_content
    mock_choice = Mock()
    mock_choice.message = mock_message
    mock_response = Mock()
    mock_response.choices = [mock_choice]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


# ---------------------------------------------------------------------------
# TestCheckTranscript
# ---------------------------------------------------------------------------


class TestCheckTranscript:
    """Tests for check_transcript() with mocked GPT-4o responses."""

    def test_returns_structured_dict_with_flagged_items_critical_and_report_path(
        self, tmp_path
    ):
        """check_transcript() returns dict with flagged, critical, and report_path keys."""
        with patch("content_compliance_checker.openai.OpenAI"):
            checker = ContentComplianceChecker()
            checker.client = make_mock_client(SAMPLE_VIOLATION_RESPONSE)

            result = checker.check_transcript(
                transcript_data=SAMPLE_TRANSCRIPT,
                episode_output_dir=tmp_path,
                episode_number=29,
            )

        assert "flagged" in result
        assert "critical" in result
        assert "report_path" in result
        assert isinstance(result["flagged"], list)
        assert isinstance(result["critical"], bool)

    def test_flagged_items_contain_required_fields(self, tmp_path):
        """Each flagged item has start_seconds, end_seconds, text, category, severity."""
        with patch("content_compliance_checker.openai.OpenAI"):
            checker = ContentComplianceChecker()
            checker.client = make_mock_client(SAMPLE_VIOLATION_RESPONSE)

            result = checker.check_transcript(
                transcript_data=SAMPLE_TRANSCRIPT,
                episode_output_dir=tmp_path,
                episode_number=29,
            )

        assert len(result["flagged"]) == 1
        item = result["flagged"][0]
        assert "start_seconds" in item
        assert "end_seconds" in item
        assert "text" in item
        assert "category" in item
        assert "severity" in item
        assert isinstance(item["start_seconds"], (int, float))
        assert isinstance(item["end_seconds"], (int, float))

    def test_empty_gpt_response_returns_empty_flagged_and_critical_false(
        self, tmp_path
    ):
        """When GPT-4o returns empty array, flagged is empty and critical is False."""
        with patch("content_compliance_checker.openai.OpenAI"):
            checker = ContentComplianceChecker()
            checker.client = make_mock_client(SAMPLE_EMPTY_RESPONSE)

            result = checker.check_transcript(
                transcript_data=SAMPLE_TRANSCRIPT,
                episode_output_dir=tmp_path,
                episode_number=29,
            )

        assert result["flagged"] == []
        assert result["critical"] is False

    def test_transcript_formatted_using_segments_not_raw_words(self, tmp_path):
        """Transcript uses segments (timestamped text lines) for compact formatting."""
        with patch("content_compliance_checker.openai.OpenAI"):
            checker = ContentComplianceChecker()
            mock_client = make_mock_client(SAMPLE_EMPTY_RESPONSE)
            checker.client = mock_client

            checker.check_transcript(
                transcript_data=SAMPLE_TRANSCRIPT,
                episode_output_dir=tmp_path,
                episode_number=29,
            )

        # Verify GPT-4o was called with a user prompt containing timestamped segments
        call_args = mock_client.chat.completions.create.call_args
        messages = (
            call_args.kwargs.get("messages") or call_args.args[0]
            if call_args.args
            else call_args.kwargs["messages"]
        )
        user_message = next(m for m in messages if m["role"] == "user")
        # The prompt should include HH:MM:SS format timestamps from segments
        assert (
            "[00:00:00]" in user_message["content"]
            or "00:00:00" in user_message["content"]
        )


# ---------------------------------------------------------------------------
# TestDisabled
# ---------------------------------------------------------------------------


class TestDisabled:
    """Tests for COMPLIANCE_ENABLED=false behavior."""

    def test_disabled_returns_empty_result_without_calling_llm(self, tmp_path):
        """When COMPLIANCE_ENABLED=false, check_transcript returns empty result without calling LLM."""
        with patch.dict(os.environ, {"COMPLIANCE_ENABLED": "false"}):
            with patch("content_compliance_checker.openai.OpenAI") as MockOpenAI:
                checker = ContentComplianceChecker()

                result = checker.check_transcript(
                    transcript_data=SAMPLE_TRANSCRIPT,
                    episode_output_dir=tmp_path,
                    episode_number=29,
                )

                # OpenAI client should not be instantiated when disabled
                MockOpenAI.assert_not_called()

        assert result == {"flagged": [], "critical": False, "report_path": None}

    def test_enabled_true_by_default(self):
        """COMPLIANCE_ENABLED defaults to 'true' when env var not set."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("COMPLIANCE_ENABLED", None)
            with patch("content_compliance_checker.openai.OpenAI"):
                checker = ContentComplianceChecker()
                assert checker.enabled is True

    def test_disabled_flag_sets_enabled_false(self):
        """COMPLIANCE_ENABLED=false sets self.enabled to False."""
        with patch.dict(os.environ, {"COMPLIANCE_ENABLED": "false"}):
            with patch("content_compliance_checker.openai.OpenAI"):
                checker = ContentComplianceChecker()
                assert checker.enabled is False


# ---------------------------------------------------------------------------
# TestReportStructure
# ---------------------------------------------------------------------------


class TestReportStructure:
    """Tests for compliance report JSON structure."""

    def test_compliance_report_contains_required_top_level_fields(self, tmp_path):
        """Compliance report JSON has episode_number, checked_at, critical, flagged, warnings."""
        with patch("content_compliance_checker.openai.OpenAI"):
            checker = ContentComplianceChecker()
            checker.client = make_mock_client(SAMPLE_MIXED_RESPONSE)

            result = checker.check_transcript(
                transcript_data=SAMPLE_TRANSCRIPT,
                episode_output_dir=tmp_path,
                episode_number=29,
            )

        # Read the saved report
        report_path = Path(result["report_path"])
        assert report_path.exists()
        with open(report_path) as f:
            report = json.load(f)

        assert "episode_number" in report
        assert "checked_at" in report
        assert "critical" in report
        assert "flagged" in report
        assert "warnings" in report
        assert report["episode_number"] == 29

    def test_flagged_and_warnings_separated_by_severity(self, tmp_path):
        """Critical severity items go to flagged; warning severity items go to warnings."""
        with patch("content_compliance_checker.openai.OpenAI"):
            checker = ContentComplianceChecker()
            # hate_speech = critical, graphic_violence = warning
            checker.client = make_mock_client(SAMPLE_MIXED_RESPONSE)

            result = checker.check_transcript(
                transcript_data=SAMPLE_TRANSCRIPT,
                episode_output_dir=tmp_path,
                episode_number=29,
            )

        report_path = Path(result["report_path"])
        with open(report_path) as f:
            report = json.load(f)

        # hate_speech should be in flagged (critical)
        flagged_categories = [item["category"] for item in report["flagged"]]
        warning_categories = [item["category"] for item in report["warnings"]]
        assert "hate_speech" in flagged_categories
        assert "graphic_violence" in warning_categories


# ---------------------------------------------------------------------------
# TestSaveReport
# ---------------------------------------------------------------------------


class TestSaveReport:
    """Tests for save_report() file writing behavior."""

    def test_save_report_writes_valid_json(self, tmp_path):
        """save_report() writes valid JSON to the episode output directory."""
        with patch("content_compliance_checker.openai.OpenAI"):
            checker = ContentComplianceChecker()

        compliance_result = {
            "flagged": [],
            "critical": False,
            "report_path": None,
        }
        checker.save_report(
            result=compliance_result,
            episode_output_dir=tmp_path,
            episode_number=29,
            timestamp="20260318_210000",
        )

        files = list(tmp_path.glob("compliance_report_29_*.json"))
        assert len(files) == 1
        with open(files[0]) as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_save_report_creates_directory_if_missing(self, tmp_path):
        """save_report() creates episode_output_dir if it does not exist."""
        nonexistent_dir = tmp_path / "ep99" / "output"

        with patch("content_compliance_checker.openai.OpenAI"):
            checker = ContentComplianceChecker()

        compliance_result = {
            "flagged": [],
            "critical": False,
            "report_path": None,
        }
        checker.save_report(
            result=compliance_result,
            episode_output_dir=nonexistent_dir,
            episode_number=99,
            timestamp="20260318_210000",
        )

        files = list(nonexistent_dir.glob("compliance_report_99_*.json"))
        assert len(files) == 1

    def test_save_report_filename_contains_episode_number_and_timestamp(self, tmp_path):
        """Saved filename follows compliance_report_{episode_number}_{timestamp}.json pattern."""
        with patch("content_compliance_checker.openai.OpenAI"):
            checker = ContentComplianceChecker()

        checker.save_report(
            result={"flagged": [], "critical": False, "report_path": None},
            episode_output_dir=tmp_path,
            episode_number=42,
            timestamp="20260318_210000",
        )

        files = list(tmp_path.glob("compliance_report_42_20260318_210000.json"))
        assert len(files) == 1


# ---------------------------------------------------------------------------
# TestMergeIntoTimestamps
# ---------------------------------------------------------------------------


class TestMergeIntoTimestamps:
    """Tests for get_censor_entries() — censor_timestamps-compatible output."""

    def test_converts_flagged_items_to_censor_entries(self):
        """get_censor_entries() converts flagged items to censor_timestamps dicts."""
        with patch("content_compliance_checker.openai.OpenAI"):
            checker = ContentComplianceChecker()

        compliance_result = {
            "flagged": [
                {
                    "start_seconds": 1234.5,
                    "end_seconds": 1238.0,
                    "text": "Drinking bleach cures cancer, trust me.",
                    "category": "dangerous_misinformation",
                    "severity": "critical",
                    "reason": "False medical claim",
                }
            ],
            "critical": True,
            "report_path": "/some/path.json",
        }

        entries = checker.get_censor_entries(compliance_result)

        assert len(entries) == 1
        entry = entries[0]
        assert entry["start_seconds"] == 1234.5
        assert entry["end_seconds"] == 1238.0
        assert "Compliance:" in entry["reason"]
        assert "dangerous_misinformation" in entry["reason"]
        assert "context" in entry

    def test_context_truncated_to_100_chars(self):
        """get_censor_entries() truncates context to 100 chars."""
        with patch("content_compliance_checker.openai.OpenAI"):
            checker = ContentComplianceChecker()

        long_text = "x" * 200
        compliance_result = {
            "flagged": [
                {
                    "start_seconds": 10.0,
                    "end_seconds": 15.0,
                    "text": long_text,
                    "category": "hate_speech",
                    "severity": "critical",
                    "reason": "Hate speech",
                }
            ],
            "critical": True,
            "report_path": None,
        }

        entries = checker.get_censor_entries(compliance_result)
        assert len(entries[0]["context"]) <= 100

    def test_empty_flagged_returns_empty_list(self):
        """get_censor_entries() returns empty list when no flagged items."""
        with patch("content_compliance_checker.openai.OpenAI"):
            checker = ContentComplianceChecker()

        entries = checker.get_censor_entries(
            {"flagged": [], "critical": False, "report_path": None}
        )
        assert entries == []


# ---------------------------------------------------------------------------
# TestSeverityMap
# ---------------------------------------------------------------------------


class TestSeverityMap:
    """Tests for critical vs warning severity classification."""

    def test_critical_true_when_hate_speech_found(self, tmp_path):
        """critical=True when any flagged item has category hate_speech."""
        with patch("content_compliance_checker.openai.OpenAI"):
            checker = ContentComplianceChecker()
            checker.client = make_mock_client(SAMPLE_HATE_SPEECH_RESPONSE)

            result = checker.check_transcript(
                transcript_data=SAMPLE_TRANSCRIPT,
                episode_output_dir=tmp_path,
                episode_number=29,
            )

        assert result["critical"] is True

    def test_critical_true_when_dangerous_misinformation_found(self, tmp_path):
        """critical=True when any flagged item has category dangerous_misinformation."""
        with patch("content_compliance_checker.openai.OpenAI"):
            checker = ContentComplianceChecker()
            checker.client = make_mock_client(SAMPLE_VIOLATION_RESPONSE)

            result = checker.check_transcript(
                transcript_data=SAMPLE_TRANSCRIPT,
                episode_output_dir=tmp_path,
                episode_number=29,
            )

        assert result["critical"] is True

    def test_critical_false_when_only_warning_severity_found(self, tmp_path):
        """critical=False when only warning-severity items (graphic_violence, harassment, sexual_content)."""
        with patch("content_compliance_checker.openai.OpenAI"):
            checker = ContentComplianceChecker()
            checker.client = make_mock_client(SAMPLE_WARNING_RESPONSE)

            result = checker.check_transcript(
                transcript_data=SAMPLE_TRANSCRIPT,
                episode_output_dir=tmp_path,
                episode_number=29,
            )

        assert result["critical"] is False

    def test_severity_map_has_all_violation_categories(self):
        """SEVERITY_MAP covers all entries in VIOLATION_CATEGORIES."""
        for category in VIOLATION_CATEGORIES:
            assert category in SEVERITY_MAP, f"Missing severity mapping for: {category}"

    def test_critical_categories_are_correct(self):
        """hate_speech, dangerous_misinformation, self_harm_promotion are critical."""
        assert SEVERITY_MAP["hate_speech"] == "critical"
        assert SEVERITY_MAP["dangerous_misinformation"] == "critical"
        assert SEVERITY_MAP["self_harm_promotion"] == "critical"

    def test_warning_categories_are_correct(self):
        """graphic_violence, harassment, sexual_content are warnings."""
        assert SEVERITY_MAP["graphic_violence"] == "warning"
        assert SEVERITY_MAP["harassment"] == "warning"
        assert SEVERITY_MAP["sexual_content"] == "warning"


# ---------------------------------------------------------------------------
# TestComplianceStylePrompt
# ---------------------------------------------------------------------------


class TestComplianceStylePrompt:
    """Tests for genre-aware compliance prompt via _build_compliance_prompt()."""

    def test_build_compliance_prompt_permissive(self, monkeypatch):
        """COMPLIANCE_STYLE=permissive returns prompt containing comedy podcast context."""
        from config import Config

        monkeypatch.setattr(Config, "COMPLIANCE_STYLE", "permissive", raising=False)
        result = _build_compliance_prompt("test transcript")
        assert "comedy podcast" in result

    def test_build_compliance_prompt_strict(self, monkeypatch):
        """COMPLIANCE_STYLE=strict returns prompt containing serious factual podcast context."""
        from config import Config

        monkeypatch.setattr(Config, "COMPLIANCE_STYLE", "strict", raising=False)
        result = _build_compliance_prompt("test transcript")
        assert "serious factual podcast" in result

    def test_build_compliance_prompt_standard(self, monkeypatch):
        """COMPLIANCE_STYLE=standard returns prompt containing standard YouTube community guidelines context."""
        from config import Config

        monkeypatch.setattr(Config, "COMPLIANCE_STYLE", "standard", raising=False)
        result = _build_compliance_prompt("test transcript")
        assert "standard YouTube community guidelines" in result

    def test_build_compliance_prompt_default_is_permissive(self, monkeypatch):
        """When COMPLIANCE_STYLE is not set, defaults to permissive (comedy podcast context)."""
        from config import Config

        # Remove COMPLIANCE_STYLE if present
        if hasattr(Config, "COMPLIANCE_STYLE"):
            monkeypatch.delattr(Config, "COMPLIANCE_STYLE", raising=False)

        result = _build_compliance_prompt("test transcript")
        assert "comedy podcast" in result

    def test_build_compliance_prompt_includes_transcript(self, monkeypatch):
        """_build_compliance_prompt includes the transcript text."""
        from config import Config

        monkeypatch.setattr(Config, "COMPLIANCE_STYLE", "permissive", raising=False)
        result = _build_compliance_prompt("my unique transcript content here")
        assert "my unique transcript content here" in result

    def test_check_transcript_uses_build_compliance_prompt(self, tmp_path):
        """check_transcript() calls _build_compliance_prompt (not the old constant directly)."""
        with patch("content_compliance_checker.openai.OpenAI"):
            checker = ContentComplianceChecker()
            checker.client = make_mock_client(SAMPLE_EMPTY_RESPONSE)

            with patch(
                "content_compliance_checker._build_compliance_prompt",
                return_value="mocked prompt",
            ) as mock_build:
                checker.check_transcript(
                    transcript_data=SAMPLE_TRANSCRIPT,
                    episode_output_dir=tmp_path,
                    episode_number=29,
                )

            mock_build.assert_called_once()
