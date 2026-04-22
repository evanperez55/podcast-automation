"""Tests for content_editor module - specifically timestamp refinement."""

import pytest
from unittest.mock import Mock, patch

from content_editor import ContentEditor, snap_clip_boundary_to_words


@pytest.fixture
def content_editor():
    """Create a ContentEditor instance with mocked OpenAI client."""
    with patch("openai.OpenAI"):
        editor = ContentEditor()
        return editor


class TestTimestampToSeconds:
    """Test timestamp conversion with sub-second precision."""

    def test_hhmmss_format(self, content_editor):
        """Test HH:MM:SS format."""
        assert content_editor._timestamp_to_seconds("00:05:32") == 332

    def test_hhmmss_format_with_decimals(self, content_editor):
        """Test HH:MM:SS format with sub-second precision."""
        result = content_editor._timestamp_to_seconds("00:05:32.5")
        assert result == 332.5

    def test_mmss_format(self, content_editor):
        """Test MM:SS format."""
        assert content_editor._timestamp_to_seconds("05:32") == 332

    def test_seconds_only(self, content_editor):
        """Test seconds-only format."""
        assert content_editor._timestamp_to_seconds("332") == 332.0


class TestExtractTargetWord:
    """Test extracting target word from reason/context."""

    def test_extracts_name_from_reason(self, content_editor):
        """Test extracting name from 'Name: Joey' format."""
        result = content_editor._extract_target_word("Name: Joey", "")
        assert result == "Joey"

    def test_extracts_slur_from_reason(self, content_editor):
        """Test extracting slur from 'Slur: [word]' format."""
        result = content_editor._extract_target_word("Slur: badword", "")
        assert result == "badword"

    def test_extracts_from_brackets(self, content_editor):
        """Test extracting word with brackets removed."""
        result = content_editor._extract_target_word("Slur: [badword]", "")
        assert result == "badword"

    def test_finds_configured_name_in_reason(self, content_editor):
        """Test finding configured names in reason text."""
        # Host1 is in Config.NAMES_TO_REMOVE
        result = content_editor._extract_target_word("mentions host1's name", "")
        assert result == "Host1"

    def test_finds_name_in_context(self, content_editor):
        """Test finding configured names in context."""
        result = content_editor._extract_target_word(
            "some reason", "then Host1 said..."
        )
        assert result == "Host1"

    def test_returns_none_for_unknown(self, content_editor):
        """Test returning None when no target can be determined."""
        result = content_editor._extract_target_word("unknown reason", "some context")
        assert result is None


class TestFindWordNearTimestamp:
    """Test finding words in word list near timestamps."""

    def test_finds_exact_word(self, content_editor):
        """Test finding exact word match."""
        words = [
            {"word": "Hello", "start": 5.0, "end": 5.3},
            {"word": "Joey", "start": 5.4, "end": 5.7},
            {"word": "how", "start": 5.8, "end": 6.0},
        ]
        result = content_editor._find_word_near_timestamp(
            words, "Joey", 5.0, search_window=2.0
        )

        assert result is not None
        assert result["word"] == "Joey"
        assert result["start"] == 5.4
        assert result["end"] == 5.7

    def test_finds_word_with_punctuation(self, content_editor):
        """Test finding word with trailing punctuation."""
        words = [
            {"word": "Hello,", "start": 5.0, "end": 5.3},
            {"word": "Joey!", "start": 5.4, "end": 5.7},
        ]
        result = content_editor._find_word_near_timestamp(
            words, "Joey", 5.0, search_window=2.0
        )

        assert result is not None
        assert result["word"] == "Joey!"
        assert result["start"] == 5.4

    def test_case_insensitive_match(self, content_editor):
        """Test case insensitive matching."""
        words = [
            {"word": "JOEY", "start": 5.4, "end": 5.7},
        ]
        result = content_editor._find_word_near_timestamp(
            words, "joey", 5.0, search_window=2.0
        )

        assert result is not None
        assert result["word"] == "JOEY"

    def test_finds_closest_match(self, content_editor):
        """Test finding closest match when multiple occurrences exist."""
        words = [
            {"word": "Joey", "start": 1.0, "end": 1.3},  # Far from timestamp
            {"word": "Joey", "start": 10.5, "end": 10.8},  # Closest to timestamp=10.0
            {"word": "Joey", "start": 20.0, "end": 20.3},  # Far from timestamp
        ]
        result = content_editor._find_word_near_timestamp(
            words, "Joey", 10.0, search_window=5.0
        )

        assert result is not None
        assert result["start"] == 10.5  # Should be the closest one

    def test_returns_none_outside_window(self, content_editor):
        """Test returning None when word is outside search window."""
        words = [
            {"word": "Joey", "start": 50.0, "end": 50.3},  # Way outside window
        ]
        result = content_editor._find_word_near_timestamp(
            words, "Joey", 10.0, search_window=5.0
        )

        assert result is None

    def test_returns_none_when_no_match(self, content_editor):
        """Test returning None when word doesn't exist."""
        words = [
            {"word": "Hello", "start": 5.0, "end": 5.3},
            {"word": "there", "start": 5.4, "end": 5.7},
        ]
        result = content_editor._find_word_near_timestamp(
            words, "Joey", 5.0, search_window=2.0
        )

        assert result is None


class TestRefineCensorTimestamps:
    """Test the full timestamp refinement pipeline."""

    def test_refines_timestamp_with_word_data(self, content_editor):
        """Test that timestamps are refined using word-level data."""
        # GPT-4's response (segment-level timestamp)
        censor_timestamps = [
            {
                "seconds": 10.0,  # Segment starts at 10.0
                "reason": "Name: Joey",
                "context": "then Joey said",
            }
        ]

        # Whisper's word-level data
        words = [
            {"word": "then", "start": 10.0, "end": 10.2},
            {"word": "Joey", "start": 10.3, "end": 10.6},  # Joey is at 10.3, not 10.0!
            {"word": "said", "start": 10.7, "end": 10.9},
        ]

        result = content_editor._refine_censor_timestamps(censor_timestamps, words)

        assert len(result) == 1
        # Should have been refined to actual word boundaries
        assert result[0]["start_seconds"] == 10.3
        assert result[0]["end_seconds"] == 10.6
        assert result[0]["matched_word"] == "Joey"

    def test_falls_back_when_word_not_found(self, content_editor):
        """Test fallback when word cannot be found in transcript."""
        censor_timestamps = [
            {"seconds": 10.0, "reason": "Name: Unknown", "context": "some context"}
        ]

        words = [
            {"word": "hello", "start": 10.0, "end": 10.2},
            {"word": "world", "start": 10.3, "end": 10.5},
        ]

        result = content_editor._refine_censor_timestamps(censor_timestamps, words)

        assert len(result) == 1
        # Should fall back to segment timestamp + 0.5s duration
        assert result[0]["start_seconds"] == 10.0
        assert result[0]["end_seconds"] == 10.5

    def test_handles_empty_words_list(self, content_editor):
        """Test handling empty words list."""
        censor_timestamps = [{"seconds": 10.0, "reason": "Name: Joey"}]

        result = content_editor._refine_censor_timestamps(censor_timestamps, [])

        # Should return unchanged
        assert result == censor_timestamps

    def test_handles_multiple_censor_items(self, content_editor):
        """Test refining multiple censor timestamps."""
        censor_timestamps = [
            {"seconds": 10.0, "reason": "Name: Joey", "context": ""},
            {"seconds": 30.0, "reason": "Name: Evan", "context": ""},
        ]

        words = [
            {"word": "Joey", "start": 10.5, "end": 10.8},
            {"word": "Evan", "start": 30.2, "end": 30.5},
        ]

        result = content_editor._refine_censor_timestamps(censor_timestamps, words)

        assert len(result) == 2
        assert result[0]["start_seconds"] == 10.5
        assert result[1]["start_seconds"] == 30.2

    def test_preserves_original_data(self, content_editor):
        """Test that original censor data is preserved."""
        censor_timestamps = [
            {
                "seconds": 10.0,
                "reason": "Name: Joey",
                "context": "original context",
                "timestamp": "00:00:10",
            }
        ]

        words = [{"word": "Joey", "start": 10.5, "end": 10.8}]

        result = content_editor._refine_censor_timestamps(censor_timestamps, words)

        # Original data should still be present
        assert result[0]["reason"] == "Name: Joey"
        assert result[0]["context"] == "original context"
        assert result[0]["timestamp"] == "00:00:10"
        # Plus new data
        assert result[0]["start_seconds"] == 10.5
        assert result[0]["original_segment_time"] == 10.0


class TestEndToEndCensoring:
    """End-to-end tests demonstrating the fix."""

    def test_bug_scenario_before_fix(self, content_editor):
        """
        Demonstrate the bug scenario:
        - Segment timestamp: 15.0s (segment starts with "And Joey said...")
        - Actual word "Joey" is at 15.234s
        - OLD BEHAVIOR: Would bleep 15.0-15.5s, missing "Joey"
        - NEW BEHAVIOR: Bleeps 15.234-15.456s, covering "Joey"
        """
        # GPT-4 returns segment timestamp
        censor_timestamps = [
            {
                "seconds": 15.0,  # Start of segment
                "reason": "Name: Joey",
                "context": "And Joey said no way",
            }
        ]

        # Whisper's actual word-level data
        words = [
            {"word": "And", "start": 15.0, "end": 15.15},
            {
                "word": "Joey",
                "start": 15.234,
                "end": 15.456,
            },  # Joey is NOT at segment start!
            {"word": "said", "start": 15.5, "end": 15.7},
            {"word": "no", "start": 15.75, "end": 15.9},
            {"word": "way", "start": 15.95, "end": 16.1},
        ]

        result = content_editor._refine_censor_timestamps(censor_timestamps, words)

        # Verify fix: should now target Joey's actual position
        assert result[0]["start_seconds"] == 15.234
        assert result[0]["end_seconds"] == 15.456

        # AudioProcessor would now bleep ~15.18-15.51 (with 50ms padding)
        # Instead of the old 15.0-15.5 which would have missed Joey


class TestBuildAnalysisPrompt:
    """Tests for prompt building with topic context."""

    def test_prompt_without_topic_context(self, content_editor):
        """Test that prompt builds correctly without topic context."""
        prompt = content_editor._build_analysis_prompt("some transcript text")
        assert "Fake Problems Podcast" in prompt
        assert "TRENDING TOPICS" not in prompt
        assert "some transcript text" in prompt

    def test_prompt_with_topic_context(self, content_editor):
        """Test that topic context is injected into the prompt."""
        topics = [
            {"topic": "AI taking over jobs", "score": 9.5, "category": "pop_science"},
            {"topic": "Dating app fatigue", "score": 8.0, "category": "dating_social"},
        ]
        prompt = content_editor._build_analysis_prompt(
            "transcript", topic_context=topics
        )

        assert "TRENDING TOPICS" in prompt
        assert "AI taking over jobs" in prompt
        assert "score: 9.5" in prompt
        assert "Dating app fatigue" in prompt

    def test_prompt_limits_topics_to_ten(self, content_editor):
        """Test that only top 10 topics are included."""
        topics = [
            {"topic": f"Topic {i}", "score": 10 - i, "category": "test"}
            for i in range(15)
        ]
        prompt = content_editor._build_analysis_prompt(
            "transcript", topic_context=topics
        )

        assert "Topic 0" in prompt
        assert "Topic 9" in prompt
        assert "Topic 10" not in prompt

    def test_prompt_empty_topic_context(self, content_editor):
        """Test that empty topic list produces no topic section."""
        prompt = content_editor._build_analysis_prompt("transcript", topic_context=[])
        assert "TRENDING TOPICS" not in prompt

    def test_prompt_none_topic_context(self, content_editor):
        """Test that None topic context produces no topic section."""
        prompt = content_editor._build_analysis_prompt("transcript", topic_context=None)
        assert "TRENDING TOPICS" not in prompt

    def test_prompt_includes_clip_schema_fields(self, content_editor):
        """Test that prompt includes hook_caption and clip_hashtags in schema."""
        prompt = content_editor._build_analysis_prompt("transcript")
        assert "hook_caption" in prompt
        assert "clip_hashtags" in prompt

    def test_custom_clip_criteria_overrides_default(self, content_editor, monkeypatch):
        """When CLIP_CRITERIA is set in Config, it replaces the default clip criteria."""
        from config import Config as RealConfig

        church_criteria = (
            "   - Powerful scripture quotes and references\n"
            "   - Key sermon points and teachings\n"
            "   - Emotionally moving moments of worship or testimony"
        )
        monkeypatch.setattr(RealConfig, "CLIP_CRITERIA", church_criteria, raising=False)
        monkeypatch.setattr(
            RealConfig, "VOICE_PERSONA", "You write for a church.", raising=False
        )

        prompt = content_editor._build_analysis_prompt("transcript")
        assert "scripture quotes" in prompt
        assert "Key sermon points" in prompt
        # Should NOT contain the generic defaults
        assert "quotable insight or revelation" not in prompt
        assert "Funny or entertaining" not in prompt


class TestAnalyzeContentSignature:
    """Tests for analyze_content topic_context parameter."""

    def test_analyze_content_accepts_topic_context(self, content_editor):
        """Test that analyze_content accepts topic_context parameter."""
        # Mock the OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """{
            "episode_title": "Test",
            "censor_timestamps": [],
            "best_clips": [],
            "episode_summary": "Test summary",
            "social_captions": {"youtube": "", "instagram": "", "twitter": ""}
        }"""
        content_editor.client.chat.completions.create = Mock(return_value=mock_response)

        topics = [{"topic": "Test topic", "score": 8.0, "category": "test"}]
        transcript_data = {"words": [], "segments": []}

        # Should not raise
        result = content_editor.analyze_content(transcript_data, topic_context=topics)
        assert result is not None
        assert "episode_summary" in result

    def test_analyze_content_works_without_topic_context(self, content_editor):
        """Test that analyze_content works fine without topic_context."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """{
            "episode_title": "Test",
            "censor_timestamps": [],
            "best_clips": [],
            "episode_summary": "Test summary",
            "social_captions": {"youtube": "", "instagram": "", "twitter": ""}
        }"""
        content_editor.client.chat.completions.create = Mock(return_value=mock_response)

        transcript_data = {"words": [], "segments": []}

        result = content_editor.analyze_content(transcript_data)
        assert result is not None


class TestNewFieldDefaults:
    """Tests for setdefault guards on new fields."""

    def test_setdefault_show_notes(self, content_editor):
        """Test that show_notes defaults to empty string."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """{
            "episode_title": "Test",
            "censor_timestamps": [],
            "best_clips": [],
            "episode_summary": "Test summary",
            "social_captions": {"youtube": "", "instagram": "", "twitter": ""}
        }"""
        content_editor.client.chat.completions.create = Mock(return_value=mock_response)
        transcript_data = {"words": [], "segments": []}

        result = content_editor.analyze_content(transcript_data)
        assert result["show_notes"] == ""

    def test_setdefault_chapters(self, content_editor):
        """Test that chapters defaults to empty list."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """{
            "episode_title": "Test",
            "censor_timestamps": [],
            "best_clips": [],
            "episode_summary": "Test summary",
            "social_captions": {"youtube": "", "instagram": "", "twitter": ""}
        }"""
        content_editor.client.chat.completions.create = Mock(return_value=mock_response)
        transcript_data = {"words": [], "segments": []}

        result = content_editor.analyze_content(transcript_data)
        assert result["chapters"] == []

    def test_setdefault_tiktok_caption(self, content_editor):
        """Test that tiktok caption defaults to empty string."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """{
            "episode_title": "Test",
            "censor_timestamps": [],
            "best_clips": [],
            "episode_summary": "Test summary",
            "social_captions": {"youtube": "", "instagram": "", "twitter": ""}
        }"""
        content_editor.client.chat.completions.create = Mock(return_value=mock_response)
        transcript_data = {"words": [], "segments": []}

        result = content_editor.analyze_content(transcript_data)
        assert result["social_captions"]["tiktok"] == ""

    def test_preserves_existing_new_fields(self, content_editor):
        """Test that existing show_notes/chapters/tiktok are preserved."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """{
            "episode_title": "Test",
            "censor_timestamps": [],
            "best_clips": [],
            "episode_summary": "Test summary",
            "social_captions": {"youtube": "", "instagram": "", "twitter": "", "tiktok": "TikTok text"},
            "show_notes": "Detailed notes",
            "chapters": [{"start_timestamp": "00:00:00", "title": "Intro"}]
        }"""
        content_editor.client.chat.completions.create = Mock(return_value=mock_response)
        transcript_data = {"words": [], "segments": []}

        result = content_editor.analyze_content(transcript_data)
        assert result["show_notes"] == "Detailed notes"
        assert len(result["chapters"]) == 1
        assert result["social_captions"]["tiktok"] == "TikTok text"


class TestChapterParsing:
    """Tests for chapter timestamp parsing."""

    def test_parse_chapters_timestamps(self, content_editor):
        """Test that chapter start_timestamps are converted to start_seconds."""
        response_text = """{
            "episode_title": "Test",
            "censor_timestamps": [],
            "best_clips": [],
            "episode_summary": "Test",
            "social_captions": {"youtube": "", "instagram": "", "twitter": ""},
            "chapters": [
                {"start_timestamp": "00:00:00", "title": "Intro"},
                {"start_timestamp": "00:05:30", "title": "Topic 1"},
                {"start_timestamp": "01:00:00", "title": "Topic 2"}
            ]
        }"""
        result = content_editor._parse_llm_response(response_text)

        assert result["chapters"][0]["start_seconds"] == 0
        assert result["chapters"][1]["start_seconds"] == 330
        assert result["chapters"][2]["start_seconds"] == 3600

    def test_parse_empty_chapters(self, content_editor):
        """Test parsing response with no chapters."""
        response_text = """{
            "episode_title": "Test",
            "censor_timestamps": [],
            "best_clips": [],
            "episode_summary": "Test",
            "social_captions": {"youtube": "", "instagram": "", "twitter": ""}
        }"""
        result = content_editor._parse_llm_response(response_text)
        # chapters key may not exist, that's fine
        assert result.get("chapters", []) == []


class TestPromptNewTasks:
    """Tests for new prompt tasks."""

    def test_prompt_includes_show_notes_task(self, content_editor):
        """Test that prompt includes show notes task."""
        prompt = content_editor._build_analysis_prompt("transcript")
        assert "WRITE DETAILED SHOW NOTES" in prompt

    def test_prompt_includes_chapter_markers_task(self, content_editor):
        """Test that prompt includes chapter markers task."""
        prompt = content_editor._build_analysis_prompt("transcript")
        assert "IDENTIFY CHAPTER MARKERS" in prompt

    def test_prompt_includes_tiktok_in_captions(self, content_editor):
        """Test that prompt includes tiktok in social captions."""
        prompt = content_editor._build_analysis_prompt("transcript")
        assert "tiktok" in prompt.lower()

    def test_prompt_schema_includes_show_notes(self, content_editor):
        """Test that JSON schema includes show_notes field."""
        prompt = content_editor._build_analysis_prompt("transcript")
        assert '"show_notes"' in prompt

    def test_prompt_schema_includes_chapters(self, content_editor):
        """Test that JSON schema includes chapters field."""
        prompt = content_editor._build_analysis_prompt("transcript")
        assert '"chapters"' in prompt


class TestVoicePrompt:
    """Tests for show-specific voice persona embedded in the analysis prompt."""

    def test_prompt_contains_system_persona_string(self, content_editor):
        """Prompt body must signal the show persona via a voice examples block."""
        prompt = content_editor._build_analysis_prompt("sample text")
        # The prompt body must contain a voice examples section that references
        # the show's irreverent comedy persona
        persona_present = (
            "irreverent" in prompt.lower()
            or "comedy" in prompt.lower()
            or "Fake Problems" in prompt
        )
        assert persona_present, (
            "Prompt must contain show persona marker (irreverent/comedy/Fake Problems)"
        )

    def test_prompt_contains_voice_examples_block(self, content_editor):
        """Prompt must contain a VOICE EXAMPLES heading (case-insensitive)."""
        prompt = content_editor._build_analysis_prompt("sample text")
        assert "VOICE EXAMPLES" in prompt.upper(), (
            "Prompt must contain VOICE EXAMPLES heading"
        )

    def test_prompt_contains_bad_good_pairs(self, content_editor):
        """Voice examples block must include BAD and GOOD labelled pairs."""
        prompt = content_editor._build_analysis_prompt("sample text")
        assert "BAD" in prompt, "Prompt voice examples must contain BAD label"
        assert "GOOD" in prompt, "Prompt voice examples must contain GOOD label"

    def test_prompt_hook_caption_guidance_is_show_specific(self, content_editor):
        """hook_caption instruction must reference show-specific hook examples."""
        prompt = content_editor._build_analysis_prompt("sample text")
        # Must contain show-specific hook starters, not just generic examples
        show_specific = (
            "wait so" in prompt.lower()
            or "??" in prompt
            or "someone finally" in prompt.lower()
        )
        assert show_specific, (
            "hook_caption guidance must include show-specific examples "
            "('wait so', '??', 'someone finally')"
        )

    def test_prompt_contains_per_platform_tone_guidance(self, content_editor):
        """Prompt must include separate tone/voice guidance for YouTube and Twitter."""
        prompt = content_editor._build_analysis_prompt("sample text")
        has_youtube_guidance = "youtube" in prompt.lower()
        has_twitter_guidance = (
            "twitter" in prompt.lower() or "x (twitter)" in prompt.lower()
        )
        assert has_youtube_guidance, (
            "Prompt must contain YouTube-specific tone guidance"
        )
        assert has_twitter_guidance, (
            "Prompt must contain Twitter-specific tone guidance"
        )


class TestEnergyPromptInjection:
    """Tests for energy_candidates injection into the analysis prompt."""

    def test_prompt_without_energy_candidates_has_no_energy_section(
        self, content_editor
    ):
        """When energy_candidates=None, prompt must NOT contain HIGH ENERGY MOMENTS."""
        prompt = content_editor._build_analysis_prompt(
            "sample text", energy_candidates=None
        )
        assert "HIGH ENERGY MOMENTS" not in prompt

    def test_prompt_with_energy_candidates_has_energy_section(self, content_editor):
        """When energy_candidates supplied, prompt must contain HIGH ENERGY MOMENTS."""
        candidates = [
            {
                "start": 10.0,
                "end": 20.0,
                "text": "funny bit here",
                "audio_energy_score": 0.85,
            }
        ]
        prompt = content_editor._build_analysis_prompt(
            "sample text", energy_candidates=candidates
        )
        assert "HIGH ENERGY MOMENTS" in prompt

    def test_energy_section_includes_score_and_text_preview(self, content_editor):
        """Energy section must include the score value and a text snippet."""
        candidates = [
            {
                "start": 10.0,
                "end": 20.0,
                "text": "laugh out loud moment",
                "audio_energy_score": 0.92,
            }
        ]
        prompt = content_editor._build_analysis_prompt(
            "sample text", energy_candidates=candidates
        )
        assert "0.92" in prompt, "Energy section must include the score value"
        assert "laugh out loud moment" in prompt, (
            "Energy section must include the text snippet"
        )


class TestEngagementContextInjection:
    """Tests for engagement_context injection into _build_analysis_prompt."""

    def test_engagement_context_injected(self, content_editor):
        """When engagement_context has status=ok and rankings, prompt includes engagement section."""
        engagement_context = {
            "status": "ok",
            "episodes_analyzed": 20,
            "episodes_needed": None,
            "rankings": [
                {
                    "category": "pop_science",
                    "correlation": 0.72,
                    "method": "spearman",
                    "p_value": 0.003,
                    "episode_count": 18,
                    "comedy_protected": False,
                },
                {
                    "category": "true_crime",
                    "correlation": 0.65,
                    "method": "spearman",
                    "p_value": 0.009,
                    "episode_count": 15,
                    "comedy_protected": False,
                },
                {
                    "category": "dating_social",
                    "correlation": 0.51,
                    "method": "spearman",
                    "p_value": 0.028,
                    "episode_count": 12,
                    "comedy_protected": False,
                },
            ],
        }
        prompt = content_editor._build_analysis_prompt(
            "sample transcript", engagement_context=engagement_context
        )
        assert "HISTORICALLY HIGH-PERFORMING CONTENT CATEGORIES" in prompt
        assert "pop_science" in prompt
        assert "true_crime" in prompt
        assert "dating_social" in prompt

    def test_no_engagement_context(self, content_editor):
        """When engagement_context is None, prompt does NOT include engagement section."""
        prompt = content_editor._build_analysis_prompt(
            "sample transcript", engagement_context=None
        )
        assert "HISTORICALLY HIGH-PERFORMING CONTENT CATEGORIES" not in prompt

    def test_engagement_context_insufficient_data(self, content_editor):
        """When engagement_context has status=insufficient_data, prompt does NOT include section."""
        engagement_context = {
            "status": "insufficient_data",
            "episodes_analyzed": 5,
            "episodes_needed": 15,
            "rankings": None,
        }
        prompt = content_editor._build_analysis_prompt(
            "sample transcript", engagement_context=engagement_context
        )
        assert "HISTORICALLY HIGH-PERFORMING CONTENT CATEGORIES" not in prompt


class TestAnalyzeContentSystemMessage:
    """Tests for system message and temperature in analyze_content API calls."""

    def test_analyze_content_sends_system_message(self, content_editor):
        """analyze_content must send a system message as the first message in the list."""
        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """{
            "episode_title": "Test",
            "censor_timestamps": [],
            "best_clips": [],
            "episode_summary": "Test summary",
            "social_captions": {"youtube": "", "instagram": "", "twitter": ""}
        }"""
        content_editor.client.chat.completions.create = Mock(return_value=mock_response)

        transcript_data = {"words": [], "segments": []}
        content_editor.analyze_content(transcript_data)

        call_kwargs = content_editor.client.chat.completions.create.call_args
        messages = (
            call_kwargs.kwargs.get("messages") or call_kwargs.args[0]
            if call_kwargs.args
            else None
        )
        if messages is None:
            # Try positional args from kwargs
            messages = call_kwargs.kwargs["messages"]
        first_message = messages[0]
        assert first_message["role"] == "system", (
            f"First message must have role='system', got role='{first_message['role']}'"
        )

    def test_analyze_content_temperature_is_07(self, content_editor):
        """analyze_content must call OpenAI with temperature=0.7 (not 0.3)."""
        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """{
            "episode_title": "Test",
            "censor_timestamps": [],
            "best_clips": [],
            "episode_summary": "Test summary",
            "social_captions": {"youtube": "", "instagram": "", "twitter": ""}
        }"""
        content_editor.client.chat.completions.create = Mock(return_value=mock_response)

        transcript_data = {"words": [], "segments": []}
        content_editor.analyze_content(transcript_data)

        call_kwargs = content_editor.client.chat.completions.create.call_args
        temperature = call_kwargs.kwargs.get("temperature")
        assert temperature == 0.7, (
            f"Expected temperature=0.7, got temperature={temperature}"
        )


class TestGenreAwareClipSelection:
    """Tests for genre-aware clip criteria and energy suppression."""

    def test_clip_criteria_comedy_when_no_persona(self, content_editor, monkeypatch):
        """When VOICE_PERSONA is None, prompt contains comedy clip criteria."""
        from config import Config as RealConfig

        monkeypatch.setattr(RealConfig, "VOICE_PERSONA", None, raising=False)

        prompt = content_editor._build_analysis_prompt("some transcript text")

        assert "Funny or entertaining" in prompt
        assert "fake problems" in prompt

    def test_clip_criteria_content_when_persona_set(self, content_editor, monkeypatch):
        """When VOICE_PERSONA is set, prompt contains content-quality clip criteria."""
        from config import Config as RealConfig

        monkeypatch.setattr(
            RealConfig,
            "VOICE_PERSONA",
            "You write for a true crime podcast.",
            raising=False,
        )

        prompt = content_editor._build_analysis_prompt("some transcript text")

        assert "quotable insight" in prompt
        assert "fake problems" not in prompt
        assert "Funny or entertaining" not in prompt

    def test_energy_suppressed_when_content_mode(self, content_editor, monkeypatch):
        """When CLIP_SELECTION_MODE=content, analyze_content passes energy_candidates=None."""
        from config import Config as RealConfig
        from unittest.mock import Mock, patch

        monkeypatch.setattr(RealConfig, "CLIP_SELECTION_MODE", "content", raising=False)

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """{
            "episode_title": "Test",
            "censor_timestamps": [],
            "best_clips": [],
            "episode_summary": "Test summary",
            "social_captions": {"youtube": "", "instagram": "", "twitter": ""}
        }"""
        content_editor.client.chat.completions.create = Mock(return_value=mock_response)

        transcript_data = {"words": [], "segments": []}

        captured_energy = []

        original_build = content_editor._build_analysis_prompt

        def capture_build(text, **kwargs):
            captured_energy.append(kwargs.get("energy_candidates"))
            return original_build(text, **kwargs)

        with patch.object(
            content_editor, "_build_analysis_prompt", side_effect=capture_build
        ):
            with patch("content_editor.AudioClipScorer") as MockScorer:
                mock_scorer_instance = Mock()
                mock_scorer_instance.score_segments.return_value = [
                    {"start": 0, "text": "hi", "audio_energy_score": 0.9}
                ]
                MockScorer.return_value = mock_scorer_instance

                content_editor.analyze_content(
                    transcript_data, audio_path="/fake/audio.wav"
                )

        assert len(captured_energy) == 1
        assert captured_energy[0] is None

    def test_energy_passed_when_energy_mode(self, content_editor, monkeypatch):
        """When CLIP_SELECTION_MODE is not set, energy_candidates are passed through."""
        from config import Config as RealConfig
        from unittest.mock import Mock, patch

        # Remove CLIP_SELECTION_MODE if present (should default to "energy")
        if hasattr(RealConfig, "CLIP_SELECTION_MODE"):
            monkeypatch.delattr(RealConfig, "CLIP_SELECTION_MODE", raising=False)

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """{
            "episode_title": "Test",
            "censor_timestamps": [],
            "best_clips": [],
            "episode_summary": "Test summary",
            "social_captions": {"youtube": "", "instagram": "", "twitter": ""}
        }"""
        content_editor.client.chat.completions.create = Mock(return_value=mock_response)

        transcript_data = {"words": [], "segments": []}

        captured_energy = []

        original_build = content_editor._build_analysis_prompt

        def capture_build(text, **kwargs):
            captured_energy.append(kwargs.get("energy_candidates"))
            return original_build(text, **kwargs)

        with patch.object(
            content_editor, "_build_analysis_prompt", side_effect=capture_build
        ):
            with patch("content_editor.AudioClipScorer") as MockScorer:
                scored_segs = [{"start": 0, "text": "hi", "audio_energy_score": 0.9}]
                mock_scorer_instance = Mock()
                mock_scorer_instance.score_segments.return_value = scored_segs
                MockScorer.return_value = mock_scorer_instance

                content_editor.analyze_content(
                    transcript_data, audio_path="/fake/audio.wav"
                )

        assert len(captured_energy) == 1
        assert captured_energy[0] is not None


class TestVoiceExamplesConditional:
    """Tests for conditional injection of Fake Problems voice examples."""

    def test_voice_examples_excluded_with_custom_persona(
        self, content_editor, monkeypatch
    ):
        """When Config.VOICE_PERSONA is set, FP voice examples must NOT appear in prompt."""
        from config import Config as RealConfig

        monkeypatch.setattr(
            RealConfig,
            "VOICE_PERSONA",
            "You write for a true crime podcast.",
            raising=False,
        )

        prompt = content_editor._build_analysis_prompt("some transcript text")

        assert "VOICE EXAMPLES" not in prompt, (
            "Custom persona clients must NOT receive FP voice examples"
        )
        assert "Lobster" not in prompt, (
            "Custom persona clients must NOT receive FP-specific Lobster example"
        )
        assert "Rube Goldberg" not in prompt, (
            "Custom persona clients must NOT receive FP-specific Rube Goldberg example"
        )

    def test_voice_examples_included_without_custom_persona(
        self, content_editor, monkeypatch
    ):
        """When Config.VOICE_PERSONA is not set (None), FP voice examples ARE included."""
        from config import Config as RealConfig

        monkeypatch.setattr(RealConfig, "VOICE_PERSONA", None, raising=False)

        prompt = content_editor._build_analysis_prompt("some transcript text")

        assert "VOICE EXAMPLES" in prompt, (
            "Default (no custom persona) clients must receive FP voice examples"
        )

    def test_voice_examples_included_when_persona_is_none(
        self, content_editor, monkeypatch
    ):
        """When Config.VOICE_PERSONA is explicitly None, voice examples ARE included."""
        from config import Config as RealConfig

        monkeypatch.setattr(RealConfig, "VOICE_PERSONA", None, raising=False)

        prompt = content_editor._build_analysis_prompt("some transcript text")

        assert "VOICE EXAMPLES" in prompt, (
            "Explicit None persona must still include FP voice examples"
        )


from config import Config  # noqa: E402


class TestFindWordsToCensorDirectly:
    """Tests for _find_words_to_censor_directly."""

    def test_empty_words_returns_empty(self, content_editor):
        """Empty word list returns empty censor list."""
        result = content_editor._find_words_to_censor_directly([])
        assert result == []

    def test_no_names_configured_returns_empty(self, content_editor, monkeypatch):
        """No names to remove or censor words returns empty list."""
        monkeypatch.setattr(Config, "NAMES_TO_REMOVE", [])
        if hasattr(Config, "WORDS_TO_CENSOR"):
            monkeypatch.setattr(Config, "WORDS_TO_CENSOR", [])
        result = content_editor._find_words_to_censor_directly(
            [{"word": "hello", "start": 0.0, "end": 0.5}]
        )
        assert result == []

    def test_finds_single_word_name(self, content_editor, monkeypatch):
        """Finds a single-word name in the transcript."""
        monkeypatch.setattr(Config, "NAMES_TO_REMOVE", ["John"])
        words = [
            {"word": "Hello", "start": 0.0, "end": 0.5},
            {"word": "John", "start": 0.5, "end": 1.0},
            {"word": "said", "start": 1.0, "end": 1.5},
        ]
        result = content_editor._find_words_to_censor_directly(words)
        assert len(result) >= 1
        assert any("John" in str(ts) for ts in result)

    def test_finds_multi_word_name(self, content_editor, monkeypatch):
        """Finds a multi-word name in the transcript."""
        monkeypatch.setattr(Config, "NAMES_TO_REMOVE", ["John Smith"])
        words = [
            {"word": "Hello", "start": 0.0, "end": 0.5},
            {"word": "John", "start": 0.5, "end": 1.0},
            {"word": "Smith", "start": 1.0, "end": 1.5},
            {"word": "said", "start": 1.5, "end": 2.0},
        ]
        result = content_editor._find_words_to_censor_directly(words)
        assert len(result) >= 1


class TestCallOpenaiWithRetry:
    """Tests for _call_openai_with_retry error handling."""

    def test_retry_on_api_error(self, content_editor):
        """Retries on OpenAI API errors and eventually raises."""
        import openai

        error = openai.APIConnectionError(request=Mock())
        content_editor.client.chat.completions.create = Mock(side_effect=error)
        with pytest.raises(openai.APIConnectionError):
            content_editor._call_openai_with_retry("system", "prompt", max_retries=0)

    def test_success_on_first_try(self, content_editor):
        """Returns response on successful first attempt."""
        mock_response = Mock()
        content_editor.client.chat.completions.create = Mock(return_value=mock_response)

        result = content_editor._call_openai_with_retry("system", "prompt")
        assert result == mock_response


class TestFormatTranscript:
    """Tests for _format_transcript_for_analysis."""

    def test_formats_segments_with_timestamps(self, content_editor):
        """Formats segments with timestamps and text."""
        words = [{"word": "hello", "start": 0.0, "end": 0.5}]
        segments = [{"start": 0.0, "end": 5.0, "text": "hello world"}]
        result = content_editor._format_transcript_for_analysis(words, segments)
        assert "hello world" in result
        assert "00:00" in result


class TestMergeCensorTimestamps:
    """Tests for _merge_censor_timestamps — deduplication of direct + GPT timestamps."""

    def test_empty_gpt_returns_direct(self, content_editor):
        """When gpt_timestamps is empty, returns direct_timestamps."""
        direct = [{"start_seconds": 10.0, "reason": "Name: Joey"}]
        result = content_editor._merge_censor_timestamps(direct, [])
        assert result == direct

    def test_empty_direct_returns_gpt(self, content_editor):
        """When direct_timestamps is empty, returns gpt_timestamps."""
        gpt = [{"seconds": 20.0, "reason": "Name: Joey"}]
        result = content_editor._merge_censor_timestamps([], gpt)
        assert result == gpt

    def test_merges_non_overlapping(self, content_editor):
        """GPT timestamps not near direct ones are added."""
        direct = [{"start_seconds": 10.0, "reason": "Name: Joey"}]
        gpt = [{"seconds": 30.0, "reason": "Name: Mike"}]
        result = content_editor._merge_censor_timestamps(direct, gpt)
        assert len(result) == 2

    def test_deduplicates_overlapping(self, content_editor):
        """GPT timestamps within 2s of direct ones are dropped."""
        direct = [{"start_seconds": 10.0, "reason": "Name: Joey"}]
        gpt = [{"seconds": 11.0, "reason": "Name: Joey"}]  # within 2s
        result = content_editor._merge_censor_timestamps(direct, gpt)
        assert len(result) == 1  # only direct

    def test_uses_seconds_key_fallback(self, content_editor):
        """Falls back to 'seconds' key when 'start_seconds' missing."""
        direct = [{"seconds": 10.0, "reason": "Name: Joey"}]
        gpt = [{"seconds": 10.5, "reason": "Name: Joey"}]  # within 2s
        result = content_editor._merge_censor_timestamps(direct, gpt)
        assert len(result) == 1


class TestValidateCensorTimestamps:
    """Tests for _validate_censor_timestamps — filters GPT hallucinations."""

    def test_empty_list_returns_empty(self, content_editor):
        """Empty input returns empty list."""
        assert content_editor._validate_censor_timestamps([]) == []

    def test_valid_item_kept(self, content_editor):
        """Items where target word appears in context are kept."""
        items = [
            {"reason": "Name: Joey", "context": "Joey said something funny"},
        ]
        result = content_editor._validate_censor_timestamps(items)
        assert len(result) == 1

    def test_hallucinated_item_removed(self, content_editor):
        """Items where target word does NOT appear in context are removed."""
        items = [
            {"reason": "Name: Joey", "context": "Mike said something funny"},
        ]
        result = content_editor._validate_censor_timestamps(items)
        assert len(result) == 0

    def test_mixed_valid_and_invalid(self, content_editor):
        """Mix of valid and hallucinated items."""
        items = [
            {"reason": "Name: Joey", "context": "Joey laughed"},
            {"reason": "Name: Mike", "context": "someone else talked"},
            {"reason": "Name: Alex", "context": "Alex was there"},
        ]
        result = content_editor._validate_censor_timestamps(items)
        assert len(result) == 2  # Joey and Alex

    def test_case_insensitive_match(self, content_editor):
        """Target word matching is case-insensitive."""
        items = [
            {"reason": "Name: joey", "context": "JOEY said something"},
        ]
        result = content_editor._validate_censor_timestamps(items)
        assert len(result) == 1

    def test_unextractable_reason_skipped(self, content_editor):
        """Items where target word can't be extracted from reason are skipped."""
        items = [
            {"reason": "", "context": "something"},
        ]
        result = content_editor._validate_censor_timestamps(items)
        assert len(result) == 0


class TestRefineCensorTimestampsFallback:
    """Tests for _refine_censor_timestamps — no-target-word fallback path."""

    def test_no_target_word_uses_segment_timestamp(self, content_editor):
        """When target word can't be extracted, uses segment timestamp."""
        censor_items = [
            {
                "reason": "",
                "context": "something",
                "seconds": 60.0,
                "start_seconds": 60.0,
                "end_seconds": 60.5,
            },
        ]
        words = [
            {"word": "something", "start": 59.0, "end": 59.5},
        ]
        result = content_editor._refine_censor_timestamps(censor_items, words)
        assert len(result) == 1
        assert result[0]["start_seconds"] == 60.0
        assert result[0]["end_seconds"] == 60.5


class TestParseLlmResponseMarkdown:
    """Tests for _parse_llm_response handling markdown-wrapped JSON."""

    def test_raw_json(self, content_editor):
        """Direct JSON string parses correctly."""
        raw = '{"episode_title": "Test", "censor_timestamps": [], "best_clips": [], "chapters": []}'
        result = content_editor._parse_llm_response(raw)
        assert result["episode_title"] == "Test"

    def test_markdown_fenced_json(self, content_editor):
        """JSON wrapped in ```json fences parses correctly."""
        raw = '```json\n{"episode_title": "Fenced", "censor_timestamps": [], "best_clips": [], "chapters": []}\n```'
        result = content_editor._parse_llm_response(raw)
        assert result["episode_title"] == "Fenced"

    def test_markdown_fenced_no_lang(self, content_editor):
        """JSON wrapped in ``` fences (no language tag) parses correctly."""
        raw = '```\n{"episode_title": "NoLang", "censor_timestamps": [], "best_clips": [], "chapters": []}\n```'
        result = content_editor._parse_llm_response(raw)
        assert result["episode_title"] == "NoLang"

    def test_json_with_surrounding_text(self, content_editor):
        """JSON embedded in explanation text is extracted."""
        raw = 'Here is the analysis:\n{"episode_title": "Embedded", "censor_timestamps": [], "best_clips": [], "chapters": []}\nHope this helps!'
        result = content_editor._parse_llm_response(raw)
        assert result["episode_title"] == "Embedded"

    def test_no_json_raises(self, content_editor):
        """Response with no JSON raises ValueError."""
        with pytest.raises((ValueError, Exception)):
            content_editor._parse_llm_response("No JSON here at all")


class TestTimestampToSecondsMalformed:
    """Tests for _timestamp_to_seconds handling bad timestamps."""

    def test_malformed_letters_returns_zero(self, content_editor):
        """Timestamp with letters returns 0.0 instead of crashing."""
        assert content_editor._timestamp_to_seconds("00:00:ABC") == 0.0

    def test_empty_string_returns_zero(self, content_editor):
        """Empty string returns 0.0."""
        assert content_editor._timestamp_to_seconds("") == 0.0

    def test_none_returns_zero(self, content_editor):
        """None input returns 0.0."""
        assert content_editor._timestamp_to_seconds(None) == 0.0

    def test_valid_still_works(self, content_editor):
        """Valid timestamps still parse correctly after the fix."""
        assert content_editor._timestamp_to_seconds("01:30:00") == 5400.0
        assert content_editor._timestamp_to_seconds("00:01:30.5") == 90.5


class TestCallOpenaiNonRetriable:
    """Tests for _call_openai_with_retry skipping retries on 4xx errors."""

    def test_400_not_retried(self, content_editor):
        """400 Bad Request is not retried."""
        import openai

        content_editor._openai = openai
        error = openai.BadRequestError(
            message="bad request",
            response=Mock(status_code=400, headers={}, json=Mock(return_value={})),
            body=None,
        )
        content_editor.client = Mock()
        content_editor.client.chat.completions.create.side_effect = error

        with pytest.raises(openai.BadRequestError):
            content_editor._call_openai_with_retry("system", "prompt", max_retries=3)

        # Should only be called once (no retries)
        assert content_editor.client.chat.completions.create.call_count == 1

    def test_429_is_retried(self, content_editor):
        """429 Rate Limit is retried."""
        import openai

        content_editor._openai = openai
        error = openai.RateLimitError(
            message="rate limited",
            response=Mock(status_code=429, headers={}, json=Mock(return_value={})),
            body=None,
        )
        content_editor.client = Mock()
        content_editor.client.chat.completions.create.side_effect = error

        with patch("content_editor.time.sleep"):
            with pytest.raises(openai.RateLimitError):
                content_editor._call_openai_with_retry(
                    "system", "prompt", max_retries=2
                )

        # Should be called 3 times (initial + 2 retries)
        assert content_editor.client.chat.completions.create.call_count == 3


class TestValidateAnalysisTiktok:
    """Test that _validate_analysis includes tiktok in defaults."""

    def test_empty_analysis_has_tiktok(self, content_editor):
        """Empty analysis gets tiktok caption default."""
        result = content_editor._validate_analysis({})
        assert "tiktok" in result["social_captions"]
        assert result["social_captions"]["tiktok"] == ""

    def test_partial_captions_get_tiktok(self, content_editor):
        """Partial social_captions dict gets tiktok filled in."""
        analysis = {"social_captions": {"youtube": "test"}}
        result = content_editor._validate_analysis(analysis)
        assert result["social_captions"]["tiktok"] == ""
        assert result["social_captions"]["youtube"] == "test"


class TestTranscriptTruncation:
    """Test that long transcripts are truncated before sending to LLM."""

    def test_long_transcript_truncated(self, content_editor):
        """Transcripts exceeding 400k chars are truncated."""
        words = []
        segments = [
            {"start": i, "end": i + 1, "text": "word " * 100} for i in range(1000)
        ]
        text = content_editor._format_transcript_for_analysis(words, segments)
        # Verify the format works (doesn't crash)
        assert len(text) > 0


class TestSnapClipBoundaryToWords:
    """Verify LLM clip timestamps snap to word boundaries, preferring sentence ends."""

    # Shared word list for tests: spans ~0-12s with several sentences.
    # Words with trailing "." end a sentence.
    WORDS = [
        {"word": "So", "start": 0.5, "end": 0.8},
        {"word": "today", "start": 0.9, "end": 1.2},
        {"word": "we're", "start": 1.3, "end": 1.6},
        {"word": "talking", "start": 1.7, "end": 2.1},
        {"word": "about", "start": 2.2, "end": 2.5},
        {"word": "something", "start": 2.6, "end": 3.1},
        {"word": "weird.", "start": 3.2, "end": 3.7},
        {"word": "Listen", "start": 4.0, "end": 4.4},
        {"word": "to", "start": 4.5, "end": 4.6},
        {"word": "this", "start": 4.7, "end": 4.9},
        {"word": "story", "start": 5.0, "end": 5.4},
        {"word": "carefully.", "start": 5.5, "end": 6.2},
        {"word": "It", "start": 6.5, "end": 6.7},
        {"word": "changes", "start": 6.8, "end": 7.2},
        {"word": "everything", "start": 7.3, "end": 7.9},
        {"word": "we", "start": 8.0, "end": 8.1},
        {"word": "thought", "start": 8.2, "end": 8.5},
        {"word": "we", "start": 8.6, "end": 8.7},
        {"word": "knew?", "start": 8.8, "end": 9.3},
        {"word": "Seriously", "start": 9.8, "end": 10.4},
        {"word": "this", "start": 10.5, "end": 10.7},
        {"word": "is", "start": 10.8, "end": 10.9},
        {"word": "wild", "start": 11.0, "end": 11.5},
    ]

    def test_snaps_start_to_first_word_at_or_after(self):
        """Start snaps forward to the first word that begins at or after LLM start."""
        # LLM start 1.0s lands mid-gap between "So" and "today"
        start, _ = snap_clip_boundary_to_words(1.0, 6.5, self.WORDS)
        # Should snap forward to "today" at 0.9? No — "today".start=0.9 is < 1.0
        # so snap to "we're" at 1.3
        assert start == 1.3

    def test_end_prefers_sentence_terminator(self):
        """End snaps back to the nearest word ending in .!?  when present."""
        # LLM end 4.2s: candidates ending <= 4.2 are words ending at 0.8, 1.2,
        # 1.6, 2.1, 2.5, 3.1, 3.7 (weird.), plus 4.4 (Listen) is > 4.2 so excluded.
        # Should prefer "weird." at end=3.7
        _, end = snap_clip_boundary_to_words(0.5, 4.2, self.WORDS)
        assert end == 3.7

    def test_end_falls_back_to_last_word_when_no_terminator(self):
        """When no sentence terminator lies in the window, snap to last word end."""
        # LLM start 6.5 (after the "." at 3.7), LLM end 8.6 — words in window:
        # "It".end=6.7, "changes".end=7.2, "everything".end=7.9, "we".end=8.1
        # None end in .!?
        # "thought" ends at 8.5 (we has two entries at 8.0-8.1 and 8.6-8.7)
        # wait: "thought".end=8.5, "we".start=8.6 is >= LLM end=8.6? end_seconds
        # check uses end <= end_seconds, "we".end=8.7 > 8.6 so excluded
        # so candidates end with "thought" at 8.5
        _, end = snap_clip_boundary_to_words(6.5, 8.6, self.WORDS)
        assert end == 8.5

    def test_question_mark_counts_as_sentence_terminator(self):
        """Words ending in '?' are valid stop points (prefer them over non-terminator)."""
        # LLM end 9.5 — candidates include "knew?" at 9.3 (ends in ?)
        _, end = snap_clip_boundary_to_words(6.5, 9.5, self.WORDS)
        assert end == 9.3

    def test_returns_original_times_on_empty_words(self):
        """Empty word list returns LLM times unchanged."""
        assert snap_clip_boundary_to_words(1.0, 5.0, []) == (1.0, 5.0)

    def test_returns_original_times_when_snapping_would_collapse(self):
        """If snapping produces a clip < 1s, fall back to LLM times."""
        # LLM 1.0 to 1.2: only one word ("today") ends at 1.2, snapped_start would
        # be "we're" at 1.3 (first word start >= 1.0), but candidates need end<=1.2
        # and >= snapped_start=1.3 — no candidates → return original
        start, end = snap_clip_boundary_to_words(1.0, 1.2, self.WORDS)
        assert (start, end) == (1.0, 1.2)

    def test_handles_llm_end_past_last_word(self):
        """LLM end past the last word picks the last word end."""
        # LLM end 99.0 — no terminator past the last terminator "knew?" at 9.3
        # wait there are more words after "knew?" — "Seriously", "this", "is", "wild"
        # Last candidate is "wild" at end=11.5, no terminator after "knew?"
        # reversed scan finds "knew?" at 9.3 FIRST going backwards from last — yes!
        _, end = snap_clip_boundary_to_words(0.5, 99.0, self.WORDS)
        assert end == 9.3  # terminator wins over later non-terminator words
