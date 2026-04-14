"""Personalized outreach pitch generation via GPT-4o.

Generates cold outreach copy for podcast prospects in two modes:
- Intro pitch (pre-consent): reads client YAML prospect: block, produces email/DM
- Demo pitch (post-consent): reads DEMO.md + analysis JSON, produces episode-specific pitch

Output written to:
- Intro: demo/<slug>/PITCH.md
- Demo:  demo/<slug>/<ep_id>/PITCH.md
"""

import json
import time
from pathlib import Path
from typing import Optional

import openai
import yaml

from config import Config
from logger import logger

_SYSTEM_PROMPT = (
    "You write cold outreach for a podcast automation service called Neurova. "
    "We automate the ENTIRE post-production and social media workflow: "
    "transcription, audio normalization, AI-selected clips with subtitles, "
    "vertical video, thumbnails, blog posts with full transcripts, show notes, "
    "social captions, and scheduled posting to YouTube/Instagram/Twitter/TikTok/Bluesky. "
    "One episode in, 15+ content pieces out — automatically. "
    "The pitch is NOT about filling gaps. It's about saving hours of manual work "
    "they're already doing (or should be doing but don't have time for). "
    "The email must be under 200 words, show-specific, and outcome-focused. "
    "Never start with 'I'. Lead with their show. "
    "Never use hype or filler phrases. Write like you'd say it to a friend. "
    "Return your answer using exactly these three section headers on their own lines:\n"
    "### SUBJECT\n"
    "### EMAIL\n"
    "### DM\n"
    "The DM must be under 280 characters."
)


class PitchGenerator:
    """Generate personalized outreach pitches using GPT-4o."""

    def __init__(self):
        """Initialize with self.enabled gated on OPENAI_API_KEY."""
        self.enabled = bool(getattr(Config, "OPENAI_API_KEY", None))
        if self.enabled:
            self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)

    def generate_intro_pitch(self, client_slug: str) -> Optional[dict]:
        """Generate a pre-consent intro pitch from the prospect's YAML metadata.

        Args:
            client_slug: Client identifier matching clients/<slug>.yaml.

        Returns:
            Dict with subject, email, dm, path keys on success; None if disabled.

        Raises:
            FileNotFoundError: If client YAML does not exist.
        """
        if not self.enabled:
            logger.warning("PitchGenerator disabled — OPENAI_API_KEY not set")
            return None

        prospect_data = self._load_prospect_yaml(client_slug)
        podcast_name = prospect_data["podcast_name"]
        prospect = prospect_data["prospect"]

        # Load research report if available for richer context
        research_path = (
            Config.BASE_DIR / "output" / client_slug / "prospect_research.md"
        )
        research_excerpt = ""
        if research_path.exists():
            research_excerpt = research_path.read_text(encoding="utf-8")[:500]

        user_message = (
            f"Podcast: {podcast_name}\n"
            f"Genre: {prospect.get('genre', 'unknown')}\n"
            f"Episode count: {prospect.get('episode_count', 'unknown')}\n"
            f"Host: {prospect.get('host_name', 'unknown')}\n"
            f"Social platforms: {prospect.get('social_links', {})}\n"
            f"Research: {research_excerpt}\n\n"
            "Write an intro pitch for this podcast host. "
            "The service fully automates episode post-production AND social media: "
            "transcription, audio normalization, AI clip selection, subtitled vertical video, "
            "thumbnails, blog post with full transcript, show notes, social captions, "
            "and scheduled posting across YouTube, Instagram, Twitter, TikTok, and Bluesky. "
            "One episode becomes 15+ pieces of content automatically. "
            "Offer to process their next 4 episodes free so they can see the full output. "
            "Emphasize time savings — this replaces hours of manual editing and posting work."
        )

        try:
            response = self._call_openai_with_retry(_SYSTEM_PROMPT, user_message)
            raw = response.choices[0].message.content
            pitch = self._parse_pitch_response(raw)
            pitch["podcast_name"] = podcast_name

            output_path = Config.BASE_DIR / "demo" / client_slug / "PITCH.md"
            self._write_pitch_md(output_path, pitch)
            pitch["path"] = output_path
            return pitch
        except Exception as e:
            logger.warning("Intro pitch generation failed for %s: %s", client_slug, e)
            return None

    def generate_demo_pitch(self, client_slug: str, episode_id: str) -> Optional[dict]:
        """Generate a post-consent demo pitch referencing specific episode output.

        Args:
            client_slug: Client identifier matching clients/<slug>.yaml.
            episode_id: Episode identifier (e.g. "ep25").

        Returns:
            Dict with subject, email, dm, path keys on success; None if disabled or inputs missing.

        Raises:
            FileNotFoundError: If client YAML does not exist.
        """
        if not self.enabled:
            logger.warning("PitchGenerator disabled — OPENAI_API_KEY not set")
            return None

        prospect_data = self._load_prospect_yaml(client_slug)
        podcast_name = prospect_data["podcast_name"]
        prospect = prospect_data["prospect"]

        try:
            demo_text = self._load_demo_md(client_slug, episode_id)
        except FileNotFoundError:
            logger.warning(
                "DEMO.md not found for %s/%s — run package-demo first",
                client_slug,
                episode_id,
            )
            return None

        try:
            analysis = self._load_analysis(client_slug, episode_id)
        except FileNotFoundError:
            logger.warning(
                "Analysis JSON not found for %s/%s — run pipeline first",
                client_slug,
                episode_id,
            )
            return None

        episode_title = analysis.get("episode_title", episode_id)
        episode_summary = analysis.get("episode_summary", "")[:300]
        show_notes_excerpt = analysis.get("show_notes", "")[:200]

        user_message = (
            f"Podcast: {podcast_name}\n"
            f"Genre: {prospect.get('genre', 'unknown')}\n"
            f"Episode: {episode_title}\n"
            f"Summary excerpt: {episode_summary}\n"
            f"Show notes excerpt: {show_notes_excerpt}\n\n"
            "Demo output (from our pipeline):\n"
            f"{demo_text}\n\n"
            "Write a demo pitch for this podcast host. "
            "Reference specific metrics from the demo output above. "
            "The service automates production: transcription, audio mastering, "
            "clip extraction, captions, thumbnails, and show notes — all from one command."
        )

        try:
            response = self._call_openai_with_retry(_SYSTEM_PROMPT, user_message)
            raw = response.choices[0].message.content
            pitch = self._parse_pitch_response(raw)
            pitch["podcast_name"] = podcast_name

            output_path = (
                Config.BASE_DIR / "demo" / client_slug / episode_id / "PITCH.md"
            )
            self._write_pitch_md(output_path, pitch)
            pitch["path"] = output_path
            return pitch
        except Exception as e:
            logger.warning(
                "Demo pitch generation failed for %s/%s: %s", client_slug, episode_id, e
            )
            return None

    def _load_prospect_yaml(self, client_slug: str) -> dict:
        """Read clients/<slug>.yaml and return podcast_name + prospect block.

        Args:
            client_slug: Client identifier.

        Returns:
            Dict with podcast_name and prospect keys.

        Raises:
            FileNotFoundError: If client YAML does not exist.
        """
        yaml_path = Config.BASE_DIR / "clients" / f"{client_slug}.yaml"
        if not yaml_path.exists():
            raise FileNotFoundError(f"Client YAML not found: {yaml_path}")
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        return {
            "podcast_name": data.get("podcast_name", client_slug),
            "prospect": data.get("prospect", {}),
        }

    def _load_demo_md(self, client_slug: str, episode_id: str) -> str:
        """Read demo/<slug>/<ep_id>/DEMO.md as raw text.

        Args:
            client_slug: Client identifier.
            episode_id: Episode identifier.

        Returns:
            DEMO.md contents as string.

        Raises:
            FileNotFoundError: If DEMO.md does not exist.
        """
        demo_path = Config.BASE_DIR / "demo" / client_slug / episode_id / "DEMO.md"
        if not demo_path.exists():
            raise FileNotFoundError(f"DEMO.md not found: {demo_path}")
        return demo_path.read_text(encoding="utf-8")

    def _load_analysis(self, client_slug: str, episode_id: str) -> dict:
        """Read newest *_analysis.json from output/<ep_id>/ by mtime.

        Args:
            client_slug: Client identifier (unused, kept for interface consistency).
            episode_id: Episode identifier.

        Returns:
            Parsed analysis dict.

        Raises:
            FileNotFoundError: If no analysis JSON found.
        """
        ep_dir = Config.OUTPUT_DIR / episode_id
        candidates = sorted(
            ep_dir.glob("*_analysis.json"),
            key=lambda p: p.stat().st_mtime,
        )
        if not candidates:
            raise FileNotFoundError(f"No analysis JSON found in {ep_dir}")
        with open(candidates[-1], "r", encoding="utf-8") as f:
            return json.load(f)

    def _call_openai_with_retry(
        self, system_prompt: str, user_message: str, max_retries: int = 3
    ):
        """Call GPT-4o with exponential backoff on transient errors.

        Args:
            system_prompt: System role message.
            user_message: User role message.
            max_retries: Maximum retry attempts after first failure.

        Returns:
            OpenAI ChatCompletion response.

        Raises:
            Exception: After all retries exhausted.
        """
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                return self.client.chat.completions.create(
                    model="gpt-4o",
                    max_tokens=1500,
                    temperature=0.7,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                )
            except (
                openai.RateLimitError,
                openai.APIError,
                openai.APIConnectionError,
                openai.APITimeoutError,
            ) as e:
                last_error = e
                if attempt < max_retries:
                    delay = min(2.0 * (2**attempt), 60.0)
                    logger.warning(
                        "OpenAI API error (attempt %d/%d): %s — retrying in %.0fs",
                        attempt + 1,
                        max_retries,
                        e,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "OpenAI API failed after %d retries: %s", max_retries, e
                    )
        raise last_error

    def _parse_pitch_response(self, raw: str) -> dict:
        """Parse ### SUBJECT / ### EMAIL / ### DM sections from GPT-4o response.

        Args:
            raw: Raw GPT-4o response text.

        Returns:
            Dict with subject, email, dm keys (empty string if section missing).
        """
        result = {"subject": "", "email": "", "dm": ""}
        current_key = None
        lines_buffer: list[str] = []

        for line in raw.splitlines():
            if line.startswith("### SUBJECT"):
                current_key = "subject"
                lines_buffer = []
            elif line.startswith("### EMAIL"):
                if current_key:
                    result[current_key] = "\n".join(lines_buffer).strip()
                current_key = "email"
                lines_buffer = []
            elif line.startswith("### DM"):
                if current_key:
                    result[current_key] = "\n".join(lines_buffer).strip()
                current_key = "dm"
                lines_buffer = []
            elif current_key:
                lines_buffer.append(line)

        if current_key:
            result[current_key] = "\n".join(lines_buffer).strip()

        return result

    def _write_pitch_md(self, path: Path, pitch: dict) -> Path:
        """Write PITCH.md with subject, email, and DM sections.

        Args:
            path: Destination file path.
            pitch: Dict with podcast_name, subject, email, dm keys.

        Returns:
            The path written to.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        content = f"""# Pitch: {pitch.get("podcast_name", "")}

## Subject Line

{pitch["subject"]}

## Email Body

{pitch["email"]}

## DM Variant (Twitter/Instagram, <280 chars)

{pitch["dm"]}

---
*Generated by Podcast Automation Pipeline*
"""
        path.write_text(content, encoding="utf-8")
        logger.info("Pitch written: %s", path)
        return path


def run_gen_pitch_cli(argv: list) -> None:
    """CLI handler for gen-pitch command.

    Args:
        argv: sys.argv list (index 0 = script, 1 = "gen-pitch", 2 = slug, 3 = ep_id optional).
    """
    # argv[1] is "gen-pitch", slug is at argv[2], ep_id at argv[3]
    slug = argv[2] if len(argv) > 2 else None
    ep_id = argv[3] if len(argv) > 3 else None

    if not slug:
        print("Usage: uv run main.py gen-pitch <slug> [ep_id]")
        print("  slug    — client slug matching clients/<slug>.yaml")
        print("  ep_id   — episode ID (e.g. ep25) for post-consent demo pitch")
        return

    gen = PitchGenerator()

    try:
        if ep_id:
            result = gen.generate_demo_pitch(slug, ep_id)
        else:
            result = gen.generate_intro_pitch(slug)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    if result:
        print(f"\nPitch written to: {result['path']}")
        print(f"Subject: {result['subject']}")
    else:
        print(f"Error: pitch generation failed for {slug}")
