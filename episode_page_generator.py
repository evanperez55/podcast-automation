"""Generate SEO-optimized episode pages for the podcast website.

Creates standalone HTML pages with full transcript, show notes, chapter
markers, and structured data (JSON-LD) for search engine discovery.
Research shows transcripts drive 7.2x more organic traffic and show
notes with 300+ words drive 20% more organic traffic.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import Config
from logger import logger


class EpisodePageGenerator:
    """Generate static HTML episode pages for GitHub Pages deployment."""

    def __init__(self):
        """Initialize with enabled check."""
        self.enabled = True
        self.site_dir = Path(Config.BASE_DIR) / "website_output"

    def generate_episode_page(
        self,
        episode_number: int,
        analysis: dict,
        transcript_data: dict,
        show_notes: str = "",
        youtube_id: Optional[str] = None,
    ) -> Optional[Path]:
        """Generate a full episode HTML page with transcript and show notes.

        Args:
            episode_number: Episode number.
            analysis: Analysis dict from content_editor.
            transcript_data: Transcript dict with segments.
            show_notes: Pre-generated show notes text.
            youtube_id: Optional YouTube video ID for embedding.

        Returns:
            Path to generated HTML file, or None on failure.
        """
        if not self.enabled:
            logger.warning("Episode page generator disabled")
            return None

        title = analysis.get("episode_title", f"Episode {episode_number}")
        summary = analysis.get("episode_summary", "")
        chapters = analysis.get("chapters", [])
        quotes = analysis.get("best_quotes", [])
        social = analysis.get("social_captions", {})

        # Build transcript HTML from segments
        segments = transcript_data.get("segments", [])
        transcript_html = self._format_transcript(segments)
        word_count = sum(len(s.get("text", "").split()) for s in segments)

        # Build chapters HTML
        chapters_html = self._format_chapters(chapters)

        # Clean show notes for HTML
        show_notes_html = self._markdown_to_html(show_notes)

        # Build the page
        html = self._build_page(
            episode_number=episode_number,
            title=title,
            summary=summary,
            transcript_html=transcript_html,
            chapters_html=chapters_html,
            show_notes_html=show_notes_html,
            quotes=quotes,
            youtube_id=youtube_id,
            word_count=word_count,
        )

        # Save
        episodes_dir = self.site_dir / "episodes"
        episodes_dir.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-z0-9-]", "", title.lower().replace(" ", "-"))[:60]
        filename = f"ep{episode_number}-{slug}.html"
        output_path = episodes_dir / filename
        output_path.write_text(html, encoding="utf-8")

        logger.info(
            "Episode page generated: %s (%d words of transcript)",
            output_path,
            word_count,
        )
        return output_path

    def _format_transcript(self, segments: list) -> str:
        """Convert transcript segments to timestamped HTML."""
        if not segments:
            return "<p>Transcript not available.</p>"

        lines = []
        for seg in segments:
            start = seg.get("start", 0)
            text = seg.get("text", "").strip()
            if not text:
                continue
            mins = int(start // 60)
            secs = int(start % 60)
            timestamp = f"{mins}:{secs:02d}"
            lines.append(
                f'<p class="transcript-line">'
                f'<span class="timestamp">[{timestamp}]</span> '
                f"{text}</p>"
            )
        return "\n".join(lines)

    def _format_chapters(self, chapters: list) -> str:
        """Convert chapter markers to HTML."""
        if not chapters:
            return ""
        items = []
        for ch in chapters:
            ts = ch.get("start_timestamp", "00:00:00")
            title = ch.get("title", "")
            items.append(f'<li><span class="timestamp">{ts}</span> {title}</li>')
        return f'<ul class="chapters">{"".join(items)}</ul>'

    def _markdown_to_html(self, text: str) -> str:
        """Simple markdown to HTML conversion."""
        if not text:
            return ""
        # Convert bullet points
        lines = text.split("\n")
        html_lines = []
        in_list = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("- "):
                if not in_list:
                    html_lines.append("<ul>")
                    in_list = True
                html_lines.append(f"<li>{stripped[2:]}</li>")
            else:
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                if stripped:
                    # Bold
                    stripped = re.sub(
                        r'"([^"]+)"', r"<strong>\1</strong>", stripped
                    )
                    html_lines.append(f"<p>{stripped}</p>")
        if in_list:
            html_lines.append("</ul>")
        return "\n".join(html_lines)

    def _build_page(
        self,
        episode_number: int,
        title: str,
        summary: str,
        transcript_html: str,
        chapters_html: str,
        show_notes_html: str,
        quotes: list,
        youtube_id: Optional[str],
        word_count: int,
    ) -> str:
        """Build the full HTML page."""
        now = datetime.now().strftime("%Y-%m-%d")

        youtube_embed = ""
        if youtube_id:
            youtube_embed = f"""
            <div class="video-embed">
                <iframe src="https://www.youtube.com/embed/{youtube_id}"
                    frameborder="0" allowfullscreen
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture">
                </iframe>
            </div>"""

        quotes_html = ""
        if quotes:
            quote_items = []
            for q in quotes[:3]:
                text = q.get("quote", "")
                ts = q.get("timestamp", "")
                quote_items.append(
                    f'<blockquote>"{text}"<cite>{ts}</cite></blockquote>'
                )
            quotes_html = "\n".join(quote_items)

        # JSON-LD structured data for SEO
        json_ld = json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "PodcastEpisode",
                "name": title,
                "description": summary,
                "episodeNumber": episode_number,
                "partOfSeries": {
                    "@type": "PodcastSeries",
                    "name": "Fake Problems Podcast",
                    "url": "https://fakeproblemspodcast.com",
                },
                "datePublished": now,
                "url": f"https://fakeproblemspodcast.com/episodes/ep{episode_number}",
            },
            indent=2,
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | Fake Problems Podcast Ep. {episode_number}</title>
    <meta name="description" content="{summary[:160]}">
    <meta property="og:title" content="{title} | Fake Problems Podcast">
    <meta property="og:description" content="{summary[:200]}">
    <meta property="og:type" content="article">
    <meta property="og:image" content="../assets/podcast_logo.jpg">
    <link rel="icon" type="image/png" href="../assets/favicon.png">
    <link rel="canonical" href="https://fakeproblemspodcast.com/episodes/ep{episode_number}">
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=JetBrains+Mono:wght@400;700&family=Playfair+Display:ital,wght@1,700&display=swap" rel="stylesheet">
    <script type="application/ld+json">{json_ld}</script>
    <style>
        :root {{
            --accent: #C0582A;
            --accent-bright: #D4622B;
            --accent-glow: rgba(192, 88, 42, 0.15);
            --bg: #FAF6EE;
            --bg-elevated: #F0EBE0;
            --bg-card: #F5F0E6;
            --text: #4A3F33;
            --text-dim: #9B8E7B;
            --text-bright: #1E1810;
            --border: #DDD4C4;
            --mono: 'JetBrains Mono', monospace;
            --sans: 'Space Grotesk', sans-serif;
            --serif: 'Playfair Display', serif;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: var(--sans);
            background: var(--bg);
            color: var(--text);
            line-height: 1.7;
            -webkit-font-smoothing: antialiased;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem 1.5rem;
        }}
        .back-link {{
            display: inline-block;
            color: var(--accent);
            text-decoration: none;
            font-family: var(--mono);
            font-size: 0.85rem;
            margin-bottom: 2rem;
        }}
        .back-link:hover {{ text-decoration: underline; }}
        h1 {{
            font-size: 2rem;
            line-height: 1.2;
            color: var(--text-bright);
            margin-bottom: 0.5rem;
        }}
        .episode-meta {{
            font-family: var(--mono);
            font-size: 0.8rem;
            color: var(--text-dim);
            margin-bottom: 2rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .summary {{
            font-size: 1.1rem;
            color: var(--text);
            margin-bottom: 2rem;
            padding: 1.5rem;
            background: var(--bg-card);
            border-radius: 8px;
            border-left: 3px solid var(--accent);
        }}
        .video-embed {{
            position: relative;
            padding-bottom: 56.25%;
            height: 0;
            margin-bottom: 2rem;
            border-radius: 8px;
            overflow: hidden;
        }}
        .video-embed iframe {{
            position: absolute;
            top: 0; left: 0;
            width: 100%; height: 100%;
        }}
        h2 {{
            font-size: 1.3rem;
            color: var(--text-bright);
            margin: 2.5rem 0 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid var(--border);
        }}
        .show-notes p {{ margin-bottom: 1rem; }}
        .show-notes ul {{ margin: 1rem 0; padding-left: 1.5rem; }}
        .show-notes li {{ margin-bottom: 0.5rem; }}
        .chapters {{ list-style: none; padding: 0; }}
        .chapters li {{
            padding: 0.5rem 0;
            border-bottom: 1px solid var(--border);
        }}
        .timestamp {{
            font-family: var(--mono);
            font-size: 0.8rem;
            color: var(--accent);
            margin-right: 0.5rem;
        }}
        blockquote {{
            font-family: var(--serif);
            font-style: italic;
            font-size: 1.2rem;
            padding: 1.5rem;
            margin: 1.5rem 0;
            background: var(--bg-card);
            border-left: 3px solid var(--accent);
            border-radius: 0 8px 8px 0;
        }}
        blockquote cite {{
            display: block;
            font-family: var(--mono);
            font-size: 0.75rem;
            color: var(--text-dim);
            font-style: normal;
            margin-top: 0.5rem;
        }}
        .transcript {{
            margin-top: 1rem;
        }}
        .transcript-line {{
            margin-bottom: 0.75rem;
            font-size: 0.95rem;
        }}
        .transcript .timestamp {{
            font-size: 0.75rem;
        }}
        .cta-box {{
            text-align: center;
            padding: 2rem;
            margin: 3rem 0;
            background: var(--bg-elevated);
            border-radius: 12px;
        }}
        .cta-box h3 {{
            font-size: 1.2rem;
            margin-bottom: 0.5rem;
            color: var(--text-bright);
        }}
        .cta-box p {{
            color: var(--text-dim);
            margin-bottom: 1rem;
        }}
        .cta-box .btn {{
            display: inline-block;
            padding: 0.75rem 2rem;
            background: var(--accent);
            color: #fff;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.9rem;
        }}
        .cta-box .btn:hover {{ background: var(--accent-bright); }}
        footer {{
            text-align: center;
            padding: 2rem;
            color: var(--text-dim);
            font-size: 0.8rem;
            border-top: 1px solid var(--border);
            margin-top: 3rem;
        }}
        footer a {{ color: var(--accent); text-decoration: none; }}
        @media (max-width: 600px) {{
            h1 {{ font-size: 1.5rem; }}
            .container {{ padding: 1rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-link">&larr; Back to Fake Problems Podcast</a>

        <h1>{title}</h1>
        <div class="episode-meta">Episode {episode_number} &middot; {now} &middot; {word_count:,} words</div>

        <div class="summary">{summary}</div>

        {youtube_embed}

        <h2>Show Notes</h2>
        <div class="show-notes">
            {show_notes_html}
        </div>

        {f'<h2>Chapters</h2>{chapters_html}' if chapters_html else ''}

        {f'<h2>Notable Quotes</h2>{quotes_html}' if quotes_html else ''}

        <div class="cta-box">
            <h3>Never miss an episode</h3>
            <p>New episodes every other Saturday. Subscribe wherever you listen.</p>
            <a href="https://www.youtube.com/@fakeproblemspodcast" class="btn">Subscribe on YouTube</a>
        </div>

        <h2>Full Transcript</h2>
        <div class="transcript">
            {transcript_html}
        </div>
    </div>

    <footer>
        <p>&copy; {datetime.now().year} Fake Problems Podcast &middot;
        <a href="/">Home</a></p>
    </footer>
</body>
</html>"""


if __name__ == "__main__":
    import sys

    ep = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    gen = EpisodePageGenerator()

    # Find the latest analysis and transcript for this episode
    ep_dir = Path(Config.OUTPUT_DIR) / "fake-problems-podcast" / f"ep_{ep}"
    if not ep_dir.exists():
        print(f"No output found for ep_{ep}")
        sys.exit(1)

    analysis_files = sorted(ep_dir.glob("*_analysis.json"))
    transcript_files = sorted(ep_dir.glob("*_transcript.json"))

    if not analysis_files or not transcript_files:
        print(f"Missing analysis or transcript for ep_{ep}")
        sys.exit(1)

    analysis = json.load(open(analysis_files[-1], encoding="utf-8"))
    transcript = json.load(open(transcript_files[-1], encoding="utf-8"))

    show_notes_files = sorted(ep_dir.glob("*_show_notes.txt"))
    show_notes = ""
    if show_notes_files:
        show_notes = show_notes_files[-1].read_text(encoding="utf-8")

    path = gen.generate_episode_page(ep, analysis, transcript, show_notes)
    if path:
        print(f"Generated: {path}")
