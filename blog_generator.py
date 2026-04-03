"""Blog post generator for podcast episodes using LLM-powered content transformation."""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from config import Config
from logger import logger
from content_editor import VOICE_PERSONA as _DEFAULT_VOICE_PERSONA


class BlogPostGenerator:
    """Generate structured markdown blog posts from podcast transcripts and analysis data."""

    def __init__(self):
        """Initialize blog generator with configuration from environment variables."""
        self.enabled = os.getenv("BLOG_ENABLED", "true").lower() == "true"
        self.use_openai = os.getenv("BLOG_USE_OPENAI", "true").lower() == "true"

    def generate_blog_post(
        self,
        transcript_data: Dict[str, Any],
        analysis: Dict[str, Any],
        episode_number: int,
    ) -> str:
        """
        Generate a markdown blog post from transcript data and content analysis.

        Uses an LLM (OpenAI GPT-4o or local Ollama) to transform the raw transcript
        and analysis into an engaging, structured blog post. Falls back to a basic
        template if the LLM call fails.

        Args:
            transcript_data: Transcript data with 'segments' and/or 'words' from Whisper.
            analysis: Content analysis dict with 'episode_title', 'chapters',
                      'best_clips', 'episode_summary', 'show_notes', etc.
            episode_number: The episode number (e.g. 25).

        Returns:
            Markdown-formatted blog post string.
        """
        prompt = self._build_prompt(transcript_data, analysis, episode_number)

        try:
            if self.use_openai:
                import openai

                client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
                blog_model = getattr(Config, "OPENAI_BLOG_MODEL", "gpt-4.1-mini")
                logger.info("Generating blog post with OpenAI %s...", blog_model)
                response = client.chat.completions.create(
                    model=blog_model,
                    max_tokens=4000,
                    temperature=0.7,
                    messages=[
                        {
                            "role": "system",
                            "content": getattr(Config, "VOICE_PERSONA", None)
                            or _DEFAULT_VOICE_PERSONA,
                        },
                        {"role": "user", "content": prompt},
                    ],
                )
                markdown = response.choices[0].message.content
            else:
                from ollama_client import Ollama

                client = Ollama()
                logger.info("Generating blog post with local Ollama LLM...")
                response = client.messages.create(
                    model="llama3.2",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=4000,
                    temperature=0.7,
                )
                markdown = response.content[0].text

            logger.info("Blog post generated successfully")
            return markdown.strip()

        except Exception as e:
            logger.error("LLM blog generation failed: %s", e)
            logger.info("Falling back to basic blog post template")
            return self._generate_fallback(analysis, episode_number)

    def _build_prompt(
        self,
        transcript_data: Dict[str, Any],
        analysis: Dict[str, Any],
        episode_number: int,
    ) -> str:
        """
        Construct the LLM prompt for blog post generation.

        Args:
            transcript_data: Transcript data with 'segments' and/or 'words'.
            analysis: Content analysis dict.
            episode_number: The episode number.

        Returns:
            The full prompt string for the LLM.
        """
        episode_title = analysis.get("episode_title", f"Episode {episode_number}")
        episode_summary = analysis.get("episode_summary", "")
        show_notes = analysis.get("show_notes", "")
        chapters = analysis.get("chapters", [])
        best_clips = analysis.get("best_clips", [])

        names_to_avoid = ", ".join(Config.NAMES_TO_REMOVE)

        # Format chapters for the prompt
        chapters_text = ""
        if chapters:
            chapter_lines = []
            for ch in chapters:
                ts = ch.get("start_timestamp", "00:00:00")
                title = ch.get("title", "Untitled")
                chapter_lines.append(f"  - [{ts}] {title}")
            chapters_text = "\n".join(chapter_lines)

        # Format best clips for the prompt
        clips_text = ""
        if best_clips:
            clip_lines = []
            for i, clip in enumerate(best_clips, 1):
                start = clip.get("start", "??:??:??")
                end = clip.get("end", "??:??:??")
                description = clip.get("description", "")
                suggested_title = clip.get("suggested_title", "")
                clip_lines.append(
                    f"  {i}. [{start} - {end}] {description}"
                    + (f' (Title: "{suggested_title}")' if suggested_title else "")
                )
            clips_text = "\n".join(clip_lines)

        # Build full transcript text from segments
        segments = transcript_data.get("segments", [])
        transcript_lines = []
        for segment in segments:
            text = segment.get("text", "").strip()
            if text:
                transcript_lines.append(text)
        full_transcript = "\n".join(transcript_lines)

        blog_voice_intro = getattr(Config, "BLOG_VOICE", None)
        if not blog_voice_intro:
            blog_voice_intro = f"""Write this blog post in the voice of {Config.PODCAST_NAME} — irreverent, a little dark, casual, never corporate.

VOICE EXAMPLES for blog writing:
BAD: "In this episode, the hosts delve into the fascinating science behind lobster immortality."
GOOD: "Lobsters, it turns out, don't have a biological clock. They just keep going. This is either inspiring or deeply unfair depending on how your week is going."

BAD: "Join us as we explore thought-provoking topics."
GOOD: "Two guys talked for an hour. Some of it was funny. Here's what happened."

No filler phrases. No 'delve into'. No 'fascinating'. Write like you'd explain it to someone who already gets the joke.

"""

        prompt = f"""{blog_voice_intro}You are a skilled blog writer for "{Config.PODCAST_NAME}". Your job is to transform a podcast episode transcript and analysis into an engaging, well-structured markdown blog post.

**EPISODE INFO:**
- Episode Number: {episode_number}
- Title: {episode_title}

**EPISODE SUMMARY:**
{episode_summary}

**CHAPTER STRUCTURE:**
{chapters_text if chapters_text else "(No chapters available)"}

**BEST CLIPS / KEY MOMENTS:**
{clips_text if clips_text else "(No clips identified)"}

**SHOW NOTES:**
{show_notes if show_notes else "(No show notes available)"}

**FULL TRANSCRIPT:**
{full_transcript}

**INSTRUCTIONS:**
Write an engaging markdown blog post for this podcast episode. Follow these guidelines:

1. **Intro Hook:** Start with a compelling opening paragraph that hooks the reader and sets up the episode's themes. Do NOT start with a generic "In this episode..." opener.

2. **Chapter-Based Sections:** Use the chapter structure above to organize the post into logical sections with ## headings. Each section should:
   - Summarize the key discussion points
   - Include at least one direct quote from the transcript (use > blockquote markdown)
   - Capture the tone and humor of the conversation

3. **Notable Quotes:** Weave in memorable quotes from the best clips / key moments listed above. Use blockquote formatting (> quote).

4. **Conclusion:** End with a brief wrap-up that ties the themes together and encourages the reader to listen to the full episode.

5. **Format:** Output as clean markdown with:
   - h1 title heading for the episode (a single # heading)
   - h2 section headings for chapters (## headings for each major section)
   - > blockquotes for direct quotes
   - Bold and italic for emphasis where appropriate
   - Short, readable paragraphs

**CRITICAL - ANONYMITY REQUIREMENT:**
The following names are STRICTLY FORBIDDEN and must NEVER appear anywhere in the blog post: {names_to_avoid}
- Do NOT reference any host by name
- Refer to the hosts generically as "the hosts", "the guys", "one host", etc.
- This is a hard requirement for privacy/anonymity reasons

Output ONLY the markdown blog post. Do not include any preamble, explanation, or meta-commentary."""

        return prompt

    def _generate_fallback(self, analysis: Dict[str, Any], episode_number: int) -> str:
        """
        Generate a basic markdown blog post from analysis data without LLM assistance.

        Used as a fallback when the LLM call fails.

        Args:
            analysis: Content analysis dict with title, summary, chapters, show_notes.
            episode_number: The episode number.

        Returns:
            Basic markdown blog post string.
        """
        episode_title = analysis.get("episode_title", f"Episode {episode_number}")
        episode_summary = analysis.get("episode_summary", "")
        chapters = analysis.get("chapters", [])
        show_notes = analysis.get("show_notes", "")

        lines = []
        lines.append(f"# Episode {episode_number}: {episode_title}")
        lines.append("")

        if episode_summary:
            lines.append(episode_summary)
            lines.append("")

        for chapter in chapters:
            title = chapter.get("title", "")
            if title and title.lower() != "intro":
                lines.append(f"## {title}")
                lines.append("")

        if show_notes:
            lines.append("## Show Notes")
            lines.append("")
            lines.append(show_notes)
            lines.append("")

        return "\n".join(lines)

    def _add_seo_frontmatter(
        self, markdown: str, episode_number: int, analysis: dict
    ) -> str:
        """Prepend SEO-optimized YAML frontmatter for Jekyll/GitHub Pages.

        Args:
            markdown: The markdown blog post content.
            episode_number: The episode number.
            analysis: Content analysis dict with episode_title, episode_summary, etc.

        Returns:
            Markdown string with YAML frontmatter prepended.
        """
        title = analysis.get("episode_title", f"Episode {episode_number}")
        summary = analysis.get("episode_summary", "")
        description = (
            summary[:160]
            if summary
            else f"{Config.PODCAST_NAME} Episode {episode_number}"
        )

        frontmatter = f"""---
layout: post
title: "Episode {episode_number}: {title}"
description: "{description}"
date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
canonical_url: ""
og:title: "Episode {episode_number}: {title}"
og:description: "{description}"
og:type: article
meta_description: "{description}"
schema.org_type: PodcastEpisode
h1: "Episode {episode_number}: {title}"
h2: "Show Notes"
alt: "{Config.PODCAST_NAME} Episode {episode_number} cover art"
image_alt="{Config.PODCAST_NAME} Episode {episode_number}"
---

"""
        return frontmatter + markdown

    def save_blog_post(
        self,
        markdown: str,
        episode_output_dir: Path,
        episode_number: int,
        timestamp: Optional[str] = None,
        analysis: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Save the generated blog post markdown to a file.

        Args:
            markdown: The markdown blog post content.
            episode_output_dir: Directory to save the file in.
            episode_number: The episode number.
            timestamp: Optional timestamp string for the filename.
                       Defaults to current time in YYYYMMDD_HHMMSS format.
            analysis: Optional content analysis dict. If provided, SEO
                      frontmatter is prepended to the markdown.

        Returns:
            Path to the saved blog post file.
        """
        if analysis is not None:
            markdown = self._add_seo_frontmatter(markdown, episode_number, analysis)

        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        filename = f"ep{episode_number}_{timestamp}_blog_post.md"
        filepath = Path(episode_output_dir) / filename

        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(markdown, encoding="utf-8")

        logger.info("Blog post saved to %s", filepath)
        return filepath
