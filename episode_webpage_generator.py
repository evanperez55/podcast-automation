"""Episode webpage generator for podcast episodes.

Produces SEO-optimized static HTML pages from podcast episode data, including
JSON-LD structured data, Open Graph / Twitter Card meta tags, and full transcripts
with chapter navigation. Also generates and merges sitemap XML.
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader

from logger import logger

# Sitemaps.org XML namespace
_SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"

# Podcast series name (matches config.py PODCAST_NAME)
_PODCAST_NAME = "Fake Problems Podcast"


class EpisodeWebpageGenerator:
    """Generate static HTML episode pages with SEO metadata and transcript content."""

    def __init__(self) -> None:
        """Initialise with configuration from environment variables."""
        self.enabled = os.getenv("PAGES_ENABLED", "true").lower() == "true"
        self.github_token = os.getenv("GITHUB_TOKEN", "")
        self.github_pages_repo = os.getenv("GITHUB_PAGES_REPO", "")
        self.site_base_url = os.getenv("SITE_BASE_URL", "").rstrip("/")
        self.github_pages_branch = os.getenv("GITHUB_PAGES_BRANCH", "main")

        # Jinja2 environment with autoescaping for XSS protection
        templates_dir = Path(__file__).parent / "templates"
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=True,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_keywords(self, text: Optional[str], n: int = 10) -> list[str]:
        """Extract up to n keyphrases from text using YAKE.

        Uses analysis show_notes or episode_summary (NOT raw transcript) to avoid
        noisy filler words from raw Whisper output.

        Args:
            text: Source text (show notes or summary). Returns [] if empty/None.
            n: Maximum number of keywords to return (default 10).

        Returns:
            List of keyword strings, empty list on error or empty input.
        """
        if not text or not text.strip():
            return []

        try:
            import yake  # noqa: PLC0415

            extractor = yake.KeywordExtractor(
                lan="en",
                n=2,
                dedupLim=0.7,
                top=n,
            )
            keywords_with_scores = extractor.extract_keywords(text)
            # yake returns list of (keyword, score) tuples — lower score = more relevant
            return [kw for kw, _score in keywords_with_scores]
        except Exception as exc:  # pragma: no cover
            logger.warning("YAKE keyword extraction failed: %s", exc)
            return []

    def generate_html(
        self,
        episode_number: int,
        analysis: dict[str, Any],
        transcript_data: dict[str, Any],
        audio_url: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
    ) -> str:
        """Generate a complete HTML page for a podcast episode.

        Args:
            episode_number: Integer episode number.
            analysis: Content analysis dict with episode_title, episode_summary,
                      show_notes, chapters.
            transcript_data: Transcript dict with 'segments' list.
            audio_url: Optional direct audio URL.
            thumbnail_url: Optional episode thumbnail image URL.

        Returns:
            Complete HTML string ready to write to disk.
        """
        episode_title = analysis.get("episode_title", f"Episode {episode_number}")
        episode_summary = analysis.get("episode_summary", "")
        show_notes = analysis.get("show_notes", episode_summary)
        chapters = analysis.get("chapters", [])

        episode_url = self._build_episode_url(episode_number)
        keywords = self.extract_keywords(show_notes or episode_summary)

        # Build transcript segments list with integer start times for template
        raw_segments = transcript_data.get("segments", [])
        segments = [
            {
                "text": seg.get("text", ""),
                "start_int": int(seg.get("start", 0)),
                "end": seg.get("end", 0),
            }
            for seg in raw_segments
        ]

        # JSON-LD structured data (WEB-02)
        jsonld = {
            "@context": "https://schema.org",
            "@type": "PodcastEpisode",
            "name": episode_title,
            "description": episode_summary,
            "episodeNumber": episode_number,
            "url": episode_url,
            "inLanguage": "en",
            "partOfSeries": {
                "@type": "PodcastSeries",
                "name": _PODCAST_NAME,
                "url": self.site_base_url or "",
            },
        }
        if audio_url:
            jsonld["contentUrl"] = audio_url
        if thumbnail_url:
            jsonld["image"] = thumbnail_url

        template = self._jinja_env.get_template("episode.html.j2")
        return template.render(
            episode_title=episode_title,
            episode_summary=episode_summary,
            episode_url=episode_url,
            chapters=chapters,
            segments=segments,
            keywords=keywords,
            jsonld=jsonld,
            thumbnail_url=thumbnail_url,
            audio_url=audio_url,
        )

    def generate_sitemap(
        self,
        existing_xml: Optional[str],
        new_url: str,
    ) -> str:
        """Generate sitemap XML, merging new_url into existing entries.

        Args:
            existing_xml: Existing sitemap XML string, or None if no sitemap yet.
            new_url: The episode page URL to add.

        Returns:
            Complete sitemap XML string with sitemaps.org namespace.
        """
        # Register namespace so ET uses a clean prefix
        ET.register_namespace("", _SITEMAP_NS)

        if existing_xml:
            try:
                root = ET.fromstring(existing_xml)
            except ET.ParseError:
                logger.warning("Could not parse existing sitemap XML; starting fresh.")
                root = ET.Element(f"{{{_SITEMAP_NS}}}urlset")
        else:
            root = ET.Element(f"{{{_SITEMAP_NS}}}urlset")

        # Collect existing URLs to avoid duplicates
        existing_locs: set[str] = set()
        for url_el in root.findall(f"{{{_SITEMAP_NS}}}url"):
            loc_el = url_el.find(f"{{{_SITEMAP_NS}}}loc")
            if loc_el is not None and loc_el.text:
                existing_locs.add(loc_el.text.strip())

        if new_url not in existing_locs:
            url_el = ET.SubElement(root, f"{{{_SITEMAP_NS}}}url")
            loc_el = ET.SubElement(url_el, f"{{{_SITEMAP_NS}}}loc")
            loc_el.text = new_url

        return ET.tostring(root, encoding="unicode", xml_declaration=True)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_episode_url(self, episode_number: int) -> str:
        """Construct the canonical episode page URL.

        Args:
            episode_number: Integer episode number.

        Returns:
            Full URL string, e.g. 'https://example.com/episodes/ep42.html'.
        """
        base = self.site_base_url or ""
        return f"{base}/episodes/ep{episode_number}.html"
