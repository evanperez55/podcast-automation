"""Tests for blog_generator module - BlogPostGenerator class."""

from unittest.mock import patch, MagicMock

from blog_generator import BlogPostGenerator
from config import Config


SAMPLE_ANALYSIS = {
    "episode_title": "Test Episode",
    "episode_summary": "A test episode about testing.",
    "chapters": [
        {"start_timestamp": "00:00:00", "title": "Intro", "start_seconds": 0},
        {"start_timestamp": "00:05:00", "title": "Main Topic", "start_seconds": 300},
    ],
    "best_clips": [
        {
            "start": "00:05:00",
            "end": "00:05:25",
            "description": "Great moment",
            "suggested_title": "Test Clip",
        }
    ],
    "show_notes": "Show notes content here.",
    "social_captions": {"youtube": "YT caption"},
}

SAMPLE_TRANSCRIPT = {
    "segments": [{"text": "Hello world"}, {"text": "This is a test"}],
    "words": [],
    "duration": 600,
}


class TestBlogPostGeneratorInit:
    """Test BlogPostGenerator initialization from environment variables."""

    def test_init_defaults(self):
        """Default init should have enabled=True and use_openai=True."""
        with patch.dict("os.environ", {}, clear=False):
            gen = BlogPostGenerator()
            assert gen.enabled is True
            assert gen.use_openai is True

    @patch.dict("os.environ", {"BLOG_ENABLED": "false"})
    def test_init_disabled(self):
        """BLOG_ENABLED=false should set enabled=False."""
        gen = BlogPostGenerator()
        assert gen.enabled is False
        assert gen.use_openai is True

    @patch.dict("os.environ", {"BLOG_USE_OPENAI": "false"})
    def test_init_use_ollama(self):
        """BLOG_USE_OPENAI=false should set use_openai=False."""
        gen = BlogPostGenerator()
        assert gen.enabled is True
        assert gen.use_openai is False


class TestBuildPrompt:
    """Test _build_prompt constructs a proper LLM prompt."""

    def test_build_prompt_contains_episode_info(self):
        """Prompt should contain the episode number and title."""
        gen = BlogPostGenerator()
        prompt = gen._build_prompt(SAMPLE_TRANSCRIPT, SAMPLE_ANALYSIS, 42)
        assert "Episode Number: 42" in prompt
        assert "Test Episode" in prompt

    def test_build_prompt_contains_chapters(self):
        """Prompt should include chapter timestamps and titles."""
        gen = BlogPostGenerator()
        prompt = gen._build_prompt(SAMPLE_TRANSCRIPT, SAMPLE_ANALYSIS, 1)
        assert "[00:00:00] Intro" in prompt
        assert "[00:05:00] Main Topic" in prompt

    def test_build_prompt_contains_anonymity(self):
        """Prompt should reference names from Config.NAMES_TO_REMOVE."""
        gen = BlogPostGenerator()
        prompt = gen._build_prompt(SAMPLE_TRANSCRIPT, SAMPLE_ANALYSIS, 1)
        for name in Config.NAMES_TO_REMOVE:
            assert name in prompt, f"Expected '{name}' in prompt anonymity section"

    def test_build_prompt_contains_transcript(self):
        """Prompt should include segment text from the transcript."""
        gen = BlogPostGenerator()
        prompt = gen._build_prompt(SAMPLE_TRANSCRIPT, SAMPLE_ANALYSIS, 1)
        assert "Hello world" in prompt
        assert "This is a test" in prompt


class TestGenerateFallback:
    """Test the _generate_fallback template-based blog generation."""

    def test_generate_fallback_structure(self):
        """Fallback should produce markdown with # heading, summary, and ## sections."""
        gen = BlogPostGenerator()
        result = gen._generate_fallback(SAMPLE_ANALYSIS, 10)
        assert result.startswith("# Episode 10: Test Episode")
        assert "A test episode about testing." in result
        assert "## Main Topic" in result
        assert "## Show Notes" in result

    def test_generate_fallback_skips_intro(self):
        """Fallback should not include a section heading for the 'Intro' chapter."""
        gen = BlogPostGenerator()
        result = gen._generate_fallback(SAMPLE_ANALYSIS, 10)
        assert "## Intro" not in result


class TestGenerateBlogPost:
    """Test generate_blog_post with mocked LLM calls."""

    def test_generate_blog_post_openai_success(self):
        """Successful OpenAI call should return stripped markdown."""
        mock_openai = MagicMock()
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "  # Blog Post\n\nContent here.  "
        mock_client.chat.completions.create.return_value = mock_response

        gen = BlogPostGenerator()
        gen.use_openai = True

        with patch.dict("sys.modules", {"openai": mock_openai}):
            result = gen.generate_blog_post(SAMPLE_TRANSCRIPT, SAMPLE_ANALYSIS, 5)

        assert result == "# Blog Post\n\nContent here."
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == "gpt-4o"

    def test_generate_blog_post_fallback_on_error(self):
        """When OpenAI raises an exception, fallback template should be used."""
        mock_openai = MagicMock()
        mock_openai.OpenAI.side_effect = RuntimeError("API key invalid")

        gen = BlogPostGenerator()
        gen.use_openai = True

        with patch.dict("sys.modules", {"openai": mock_openai}):
            result = gen.generate_blog_post(SAMPLE_TRANSCRIPT, SAMPLE_ANALYSIS, 7)

        # Should fall back to template-based output
        assert "# Episode 7: Test Episode" in result
        assert "A test episode about testing." in result


class TestSaveBlogPost:
    """Test save_blog_post file writing."""

    def test_save_blog_post(self, tmp_path):
        """Should create a markdown file with correct content."""
        gen = BlogPostGenerator()
        markdown = "# My Blog Post\n\nHello world."

        result_path = gen.save_blog_post(markdown, tmp_path, 25)

        assert result_path.exists()
        assert result_path.suffix == ".md"
        assert "ep25_" in result_path.name
        assert "_blog_post.md" in result_path.name
        assert result_path.read_text(encoding="utf-8") == markdown

    def test_save_blog_post_custom_timestamp(self, tmp_path):
        """Passing a timestamp should use it in the filename."""
        gen = BlogPostGenerator()
        markdown = "# Custom Timestamp Post"

        result_path = gen.save_blog_post(
            markdown, tmp_path, 30, timestamp="20260302_120000"
        )

        expected_name = "ep30_20260302_120000_blog_post.md"
        assert result_path.name == expected_name
        assert result_path.exists()
        assert result_path.read_text(encoding="utf-8") == markdown


VOICE_TRANSCRIPT_DATA = {"segments": [], "words": []}

VOICE_ANALYSIS = {
    "episode_title": "Test Episode",
    "episode_summary": "Test summary",
    "best_clips": [],
    "chapters": [],
    "show_notes": "",
}


class TestBlogVoicePrompt:
    """Tests for show-specific voice persona embedded in the blog generation prompt."""

    def test_blog_prompt_contains_persona_instruction(self):
        """Blog prompt must contain an irreverent/comedy voice instruction."""
        gen = BlogPostGenerator()
        prompt = gen._build_prompt(VOICE_TRANSCRIPT_DATA, VOICE_ANALYSIS, 25)
        has_persona = (
            "irreverent" in prompt.lower()
            or "edgy" in prompt.lower()
            or (
                "hosts" in prompt.lower()
                and ("tone" in prompt.lower() or "voice" in prompt.lower())
            )
        )
        assert has_persona, (
            "Blog prompt must signal the show's irreverent/edgy/comedy voice persona"
        )

    def test_blog_prompt_contains_voice_examples(self):
        """Blog prompt must contain BAD/GOOD example pairs showing desired tone."""
        gen = BlogPostGenerator()
        prompt = gen._build_prompt(VOICE_TRANSCRIPT_DATA, VOICE_ANALYSIS, 25)
        has_examples = ("BAD" in prompt and "GOOD" in prompt) or (
            "don't write" in prompt.lower() and "do write" in prompt.lower()
        )
        assert has_examples, (
            "Blog prompt must contain voice example pairs (BAD/GOOD or DON'T/DO format)"
        )

    def test_blog_generate_passes_system_message_to_openai(self):
        """generate_blog_post must include a system message as first item in messages list."""
        mock_openai = MagicMock()
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "# Generated Blog Post\n\nContent."
        mock_client.chat.completions.create.return_value = mock_response

        gen = BlogPostGenerator()
        gen.use_openai = True

        with patch.dict("sys.modules", {"openai": mock_openai}):
            gen.generate_blog_post(VOICE_TRANSCRIPT_DATA, VOICE_ANALYSIS, 25)

        call_kwargs = mock_client.chat.completions.create.call_args
        messages = call_kwargs.kwargs.get("messages") or (
            call_kwargs.args[0] if call_kwargs.args else None
        )
        assert messages is not None, "messages argument must be passed to create()"
        first_message = messages[0]
        assert first_message["role"] == "system", (
            f"First message must have role='system', got role='{first_message['role']}'"
        )
