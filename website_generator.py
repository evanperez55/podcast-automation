"""Website landing page generator for the podcast.

Rebuilds the static index.html for the GitHub Pages site whenever a new
episode is processed.  Reads all available episode analysis files and the
content calendar to produce a complete, up-to-date landing page.
"""

import json
import os
from html import escape
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import Config
from logger import logger

try:
    from github import Github
except ImportError:
    Github = None


class WebsiteGenerator:
    """Generate and deploy the podcast landing page."""

    def __init__(self):
        self.enabled = Config.WEBSITE_ENABLED
        self.github_token = Config.GITHUB_TOKEN
        self.github_repo = Config.WEBSITE_GITHUB_REPO
        self.github_branch = Config.WEBSITE_GITHUB_BRANCH
        self.template_path = Path(__file__).parent / "templates" / "website_index.html"
        self.output_dir = Path(Config.OUTPUT_DIR)

    # ------------------------------------------------------------------
    # Data Collection
    # ------------------------------------------------------------------

    def _collect_episodes(self) -> List[Dict[str, Any]]:
        """Scan output directories for episode analysis data.

        Returns a list of episode dicts sorted by episode number descending
        (newest first).
        """
        episodes = []
        output_dir = self.output_dir

        if not output_dir.exists():
            return episodes

        for ep_dir in sorted(output_dir.iterdir(), reverse=True):
            if not ep_dir.is_dir() or not ep_dir.name.startswith("ep_"):
                continue

            # Find the analysis JSON (use the latest one if multiple)
            analysis_files = sorted(ep_dir.glob("*_analysis.json"), reverse=True)
            if not analysis_files:
                continue

            try:
                with open(analysis_files[0], encoding="utf-8") as f:
                    analysis = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Skipping %s: %s", ep_dir.name, e)
                continue

            ep_num_str = ep_dir.name.replace("ep_", "")
            try:
                ep_num = int(ep_num_str)
            except ValueError:
                continue

            episodes.append(
                {
                    "number": ep_num,
                    "title": analysis.get("episode_title", f"Episode {ep_num}"),
                    "summary": analysis.get("episode_summary", ""),
                    "clips": analysis.get("best_clips", []),
                    "quotes": analysis.get("best_quotes", []),
                    "chapters": analysis.get("chapters", []),
                }
            )

        return episodes

    def _collect_youtube_ids(self) -> Dict[str, Dict[str, str]]:
        """Read content calendar for YouTube video IDs per episode.

        Returns dict like: {"ep_30": {"episode": "NV54Ilj0zGE", "clip_3": "F6S7FjljtGU", ...}}
        """
        calendar_path = Path("topic_data/content_calendar.json")
        if not calendar_path.exists():
            return {}

        try:
            with open(calendar_path, encoding="utf-8") as f:
                calendar = json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

        result = {}
        for ep_id, ep_data in calendar.items():
            ids = {}
            for slot_key, slot in ep_data.get("slots", {}).items():
                content = slot.get("content", {})
                vid_id = content.get("youtube_video_id", "")
                if vid_id:
                    ids[slot_key] = vid_id
                # Also check upload_results for episode-level YouTube
                upload_results = slot.get("upload_results", {})
                yt_result = upload_results.get("youtube", {})
                if isinstance(yt_result, dict) and yt_result.get("video_id"):
                    ids[slot_key] = yt_result["video_id"]
            if ids:
                result[ep_id] = ids
        return result

    # ------------------------------------------------------------------
    # HTML Generation
    # ------------------------------------------------------------------

    def generate_html(self) -> str:
        """Generate the full index.html from template and episode data."""
        episodes = self._collect_episodes()
        youtube_ids = self._collect_youtube_ids()

        if not episodes:
            logger.warning("No episodes found — generating empty site")

        # Read template
        if not self.template_path.exists():
            logger.error("Website template not found: %s", self.template_path)
            raise FileNotFoundError(f"Template not found: {self.template_path}")

        template = self.template_path.read_text(encoding="utf-8")

        # Build sections
        latest = episodes[0] if episodes else None
        latest_ep_key = f"ep_{latest['number']}" if latest else ""
        latest_yt_id = (
            youtube_ids.get(latest_ep_key, {}).get("episode", "") if latest else ""
        )

        # Collect clips with YouTube IDs for the latest episode
        clips_html = self._build_clips_html(latest, youtube_ids.get(latest_ep_key, {}))

        # Collect quotes from latest episode
        quotes_html = self._build_quotes_html(latest)

        # Build latest episode section
        latest_html = self._build_latest_episode_html(latest, latest_yt_id)

        # Build older episodes list
        older_html = self._build_older_episodes_html(episodes[1:], youtube_ids)

        # Replace template placeholders
        html = template
        html = html.replace("{{LATEST_EPISODE}}", latest_html)
        html = html.replace("{{CLIPS}}", clips_html)
        html = html.replace("{{QUOTES}}", quotes_html)
        html = html.replace("{{OLDER_EPISODES}}", older_html)
        html = html.replace("{{PODCAST_NAME}}", escape(Config.PODCAST_NAME))

        return html

    def _build_latest_episode_html(
        self, episode: Optional[Dict], youtube_id: str
    ) -> str:
        if not episode:
            return '<p style="color:var(--text-dim);">No episodes yet.</p>'

        title = escape(episode["title"])
        summary = escape(episode["summary"])
        ep_num = episode["number"]

        if youtube_id:
            player = f"""<div class="video-embed">
                <iframe src="https://www.youtube.com/embed/{escape(youtube_id)}" title="Episode {ep_num}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen loading="lazy"></iframe>
            </div>"""
        else:
            player = ""

        return f"""<div class="player-wrapper reveal reveal-delay-1">
            {player}
            <div class="player-info">
                <span class="ep-tag">Episode {ep_num}</span>
                <h3>{title}</h3>
                <p>{summary}</p>
            </div>
        </div>"""

    def _build_clips_html(self, episode: Optional[Dict], yt_ids: Dict[str, str]) -> str:
        if not episode:
            return ""

        clips = episode.get("clips", [])
        if not clips:
            return ""

        cards = []
        for i, clip in enumerate(clips[:6]):
            clip_key = f"clip_{i + 1}"
            vid_id = yt_ids.get(clip_key, "")
            title = escape(clip.get("suggested_title", f"Clip {i + 1}"))

            if vid_id:
                video = f"""<div class="clip-video">
                    <iframe src="https://www.youtube.com/embed/{escape(vid_id)}" title="{title}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen loading="lazy"></iframe>
                </div>"""
            else:
                video = '<div class="clip-video" style="background:var(--bg-elevated);display:flex;align-items:center;justify-content:center;padding-bottom:177.78%;position:relative;"><span style="position:absolute;color:var(--text-dim);font-size:0.8rem;">No video</span></div>'

            cards.append(
                f"""<div class="clip-card">
                {video}
                <div class="clip-label">{title}</div>
            </div>"""
            )

        return "\n".join(cards)

    def _build_quotes_html(self, episode: Optional[Dict]) -> str:
        if not episode:
            return ""

        quotes = episode.get("quotes", [])
        if not quotes:
            return ""

        cards = []
        for q in quotes[:4]:
            text = escape(q.get("quote", ""))
            context = escape(q.get("speaker_context", ""))
            cards.append(
                f"""<div class="quote-card reveal">
                <span class="big-quote">&ldquo;</span>
                <blockquote>{text}</blockquote>
                <cite>{context}</cite>
            </div>"""
            )

        return "\n".join(cards)

    def _build_older_episodes_html(
        self, episodes: List[Dict], youtube_ids: Dict
    ) -> str:
        if not episodes:
            return ""

        cards = []
        for ep in episodes[:10]:
            title = escape(ep["title"])
            summary = escape(ep["summary"][:200])
            ep_num = ep["number"]
            ep_key = f"ep_{ep_num}"
            yt_id = youtube_ids.get(ep_key, {}).get("episode", "")

            if yt_id:
                link = f'<a href="https://www.youtube.com/watch?v={escape(yt_id)}" class="ep-link">Watch</a>'
            else:
                link = ""

            cards.append(
                f"""<div class="episode-card reveal">
                <span class="ep-tag" style="margin-bottom:0.5rem;">{ep_num}</span>
                <h3>{title}</h3>
                <p>{summary}</p>
                {link}
            </div>"""
            )

        return "\n".join(cards)

    # ------------------------------------------------------------------
    # Save & Deploy
    # ------------------------------------------------------------------

    def save_html(self, html: str) -> Path:
        """Save generated HTML locally."""
        out_dir = self.output_dir / "website"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "index.html"
        path.write_text(html, encoding="utf-8")
        logger.info("Website HTML saved: %s", path)
        return path

    def deploy(self, html: str) -> Optional[str]:
        """Push index.html to the GitHub Pages repo.

        Returns the site URL on success, None on failure.
        """
        if not self.github_token or not self.github_repo:
            logger.warning(
                "Website deploy skipped: missing GITHUB_TOKEN or WEBSITE_GITHUB_REPO"
            )
            return None

        if Github is None:
            logger.warning("Website deploy skipped: PyGithub not installed")
            return None

        try:
            g = Github(self.github_token)
            repo = g.get_repo(self.github_repo)

            content = html.encode("utf-8")

            # Upsert index.html
            try:
                existing = repo.get_contents("index.html", ref=self.github_branch)
                repo.update_file(
                    "index.html",
                    "chore: update landing page with latest episode data",
                    content,
                    existing.sha,
                    branch=self.github_branch,
                )
            except Exception:
                repo.create_file(
                    "index.html",
                    "chore: add landing page",
                    content,
                    branch=self.github_branch,
                )

            url = f"https://{self.github_repo.split('/')[0]}.github.io"
            logger.info("Website deployed to %s", url)
            return url

        except Exception as e:
            logger.warning("Website deploy failed: %s", e)
            return None

    def generate_and_deploy(self) -> Optional[str]:
        """Generate HTML from episode data and deploy to GitHub Pages.

        Returns the site URL on success, None on failure.
        """
        if not self.enabled:
            logger.info("Website generation disabled")
            return None

        html = self.generate_html()
        self.save_html(html)
        return self.deploy(html)
