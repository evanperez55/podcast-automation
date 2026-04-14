"""Episode webpage generator for podcast episodes.

Produces SEO-optimized static HTML pages from podcast episode data, including
JSON-LD structured data, Open Graph / Twitter Card meta tags, and full transcripts
with chapter navigation. Also generates and merges sitemap XML.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader

from config import Config
from logger import logger

# PyGithub import — optional at module level so the module loads without it
try:
    from github import Github  # noqa: F401
except ImportError:  # pragma: no cover
    Github = None  # type: ignore[assignment,misc]

# Sitemaps.org XML namespace
_SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"

# Podcast series name — pulled from Config for multi-client support
_PODCAST_NAME = Config.PODCAST_NAME


class EpisodeWebpageGenerator:
    """Generate static HTML episode pages with SEO metadata and transcript content."""

    def __init__(self) -> None:
        """Initialise with configuration from Config (respects client overrides)."""
        self.enabled = Config.PAGES_ENABLED
        self.github_token = Config.GITHUB_TOKEN
        self.github_pages_repo = Config.GITHUB_PAGES_REPO
        self.site_base_url = Config.SITE_BASE_URL.rstrip("/")
        self.github_pages_branch = Config.GITHUB_PAGES_BRANCH

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
            podcast_name=Config.PODCAST_NAME,
            show_notes=show_notes,
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
    # Deployment API
    # ------------------------------------------------------------------

    def _github_upsert(
        self,
        repo: Any,
        path: str,
        content: bytes,
        commit_message: str,
    ) -> None:
        """Upsert a file in a GitHub repository.

        Calls repo.update_file when the file already exists (providing its SHA),
        or repo.create_file when it does not.

        Args:
            repo: PyGithub Repository object.
            path: Repository-relative file path (e.g. "episodes/ep42.html").
            content: Raw bytes to write.
            commit_message: Commit message for the upsert operation.
        """
        try:
            existing = repo.get_contents(path, ref=self.github_pages_branch)
            repo.update_file(
                path,
                commit_message,
                content,
                existing.sha,
                branch=self.github_pages_branch,
            )
        except Exception:
            repo.create_file(
                path, commit_message, content, branch=self.github_pages_branch
            )

    def deploy(self, html_content: str, episode_number: int) -> Optional[str]:
        """Push episode HTML and updated sitemap.xml to GitHub Pages.

        Args:
            html_content: Complete HTML string to publish.
            episode_number: Episode number used to build the file path and URL.

        Returns:
            Public episode URL on success, None on failure or when credentials
            are missing.
        """
        if not self.github_token or not self.github_pages_repo:
            logger.warning(
                "Webpage deployment skipped: GITHUB_TOKEN or GITHUB_PAGES_REPO not configured"
            )
            return None

        if Github is None:  # pragma: no cover
            logger.warning("Webpage deployment skipped: PyGithub not installed")
            return None

        try:
            g = Github(self.github_token)
            repo = g.get_repo(self.github_pages_repo)

            # Upsert episode HTML
            episode_path = f"episodes/ep{episode_number}.html"
            html_bytes = html_content.encode("utf-8")
            self._github_upsert(
                repo,
                episode_path,
                html_bytes,
                f"Add/update episode {episode_number} webpage",
            )

            episode_url = self._build_episode_url(episode_number)

            # Fetch existing sitemap (None if not yet created)
            existing_xml: Optional[str] = None
            try:
                sitemap_file = repo.get_contents(
                    "sitemap.xml", ref=self.github_pages_branch
                )
                existing_xml = sitemap_file.decoded_content.decode("utf-8")
            except Exception:
                existing_xml = None

            # Generate merged sitemap and upsert
            sitemap_xml = self.generate_sitemap(existing_xml, episode_url)
            self._github_upsert(
                repo,
                "sitemap.xml",
                sitemap_xml.encode("utf-8"),
                f"Update sitemap.xml for episode {episode_number}",
            )

            logger.info("Episode webpage deployed: %s", episode_url)
            return episode_url

        except Exception as exc:
            logger.warning("Webpage deployment failed: %s", exc)
            return None

    def generate_and_deploy(
        self,
        episode_number: int,
        analysis: dict[str, Any],
        transcript_data: dict[str, Any],
        audio_url: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
    ) -> Optional[str]:
        """Generate episode HTML and deploy to GitHub Pages.

        Convenience method that calls generate_html then deploy.

        Args:
            episode_number: Integer episode number.
            analysis: Content analysis dict (episode_title, episode_summary, etc.).
            transcript_data: Transcript dict with 'segments' list.
            audio_url: Optional direct audio URL.
            thumbnail_url: Optional episode thumbnail image URL.

        Returns:
            Public episode URL on success, None on failure.
        """
        html = self.generate_html(
            episode_number=episode_number,
            analysis=analysis,
            transcript_data=transcript_data,
            audio_url=audio_url,
            thumbnail_url=thumbnail_url,
        )
        return self.deploy(html, episode_number)

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
