"""Podcast prospect discovery: iTunes search, RSS contact extraction, YAML scaffolding.

Provides ProspectFinder to discover podcast prospects via iTunes Search API,
enrich them with contact info from RSS feeds, and scaffold client YAML configs
with genre-appropriate content defaults pre-filled.

Also exposes run_find_prospects_cli(argv) for the main.py CLI dispatch.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import feedparser
import requests
import yaml

from client_config import init_client
from config import Config
from logger import logger
from outreach_tracker import OutreachTracker

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

GENRE_IDS: Dict[str, int] = {
    "comedy": 1303,
    "true-crime": 1488,
    "business": 1321,
    "technology": 1318,
    "society": 1324,
}

GENRE_DEFAULTS: Dict[str, Dict] = {
    "comedy": {
        "voice_persona": (
            "Write show notes and social captions with wit and dry humor. "
            "Match the show's comedic tone. Lean into the absurdity."
        ),
        "compliance_style": "lenient",
        "categories": ["Comedy"],
    },
    "true-crime": {
        "voice_persona": (
            "Write show notes in a serious, investigative tone. "
            "Respect for victims is paramount. Evidence-based analysis only."
        ),
        "compliance_style": "strict",
        "categories": ["True Crime"],
    },
    "business": {
        "voice_persona": (
            "Professional but warm. Write show notes for a business-minded audience. "
            "Lead with actionable insights and clear takeaways."
        ),
        "compliance_style": "standard",
        "categories": ["Business"],
    },
}

# Mapping from iTunes primaryGenreName (lowercased, hyphenated) to GENRE_DEFAULTS key
_GENRE_NAME_MAP: Dict[str, str] = {
    "comedy": "comedy",
    "true-crime": "true-crime",
    "true crime": "true-crime",
    "business": "business",
    "technology": "technology",
    "society-culture": "society",
    "society & culture": "society",
    "society": "society",
}


class ProspectFinder:
    """Discover and qualify podcast prospects for outreach.

    Wraps three operations:
    1. Query iTunes Search API to find podcasts by genre and episode count range.
    2. Enrich a show by parsing its RSS feed for host email and social links.
    3. Scaffold a client YAML config with genre defaults and register in OutreachTracker.
    """

    def __init__(self):
        """Initialize ProspectFinder. No credentials required."""
        self.enabled = True

    def search(
        self,
        term: str,
        genre_id: Optional[int] = None,
        min_episodes: int = 20,
        max_episodes: int = 500,
        limit: int = 20,
    ) -> List[dict]:
        """Query iTunes Search API and return filtered podcast results.

        Args:
            term: Search term (e.g. genre name or show keyword).
            genre_id: Optional iTunes genre ID to filter by.
            min_episodes: Minimum episode count (inclusive). Default 20.
            max_episodes: Maximum episode count (inclusive). Default 500.
            limit: Maximum number of results to return. Default 20.

        Returns:
            List of iTunes result dicts filtered by episode count range.
            Returns empty list on any API error.
        """
        params = {
            "term": term,
            "media": "podcast",
            "limit": 200,  # fetch more, filter client-side
        }
        if genre_id is not None:
            params["genreId"] = genre_id

        try:
            resp = requests.get(
                "https://itunes.apple.com/search",
                params=params,
                timeout=10,
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
        except Exception as e:
            logger.warning("iTunes search failed for term '%s': %s", term, e)
            return []

        filtered = [
            r for r in results if min_episodes <= r.get("trackCount", 0) <= max_episodes
        ]
        return filtered[:limit]

    def enrich_from_rss(self, feed_url: str) -> dict:
        """Extract contact info and metadata from a podcast RSS feed.

        Args:
            feed_url: URL of the podcast RSS feed.

        Returns:
            Dict with keys: contact_email, website, social_links,
            last_pub_date (ISO date string or None), episode_count.
            Returns empty dict on total parse failure.
        """
        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            logger.warning("Failed to parse RSS feed %s: %s", feed_url, e)
            return {}

        if feed.bozo:
            logger.warning(
                "RSS feed has parse errors (bozo=True): %s — continuing anyway",
                feed_url,
            )

        # Email: check in priority order
        owner = feed.feed.get("itunes_owner", {}) or {}
        email = (
            owner.get("email")
            or feed.feed.get("itunes_email")
            or (feed.feed.get("author_detail") or {}).get("email")
        )

        website = feed.feed.get("link", "")

        # Social links via regex on feed description
        desc = feed.feed.get("description", "") or ""
        social = {}
        for pattern, key in [
            (r"twitter\.com/(\w+)", "twitter"),
            (r"instagram\.com/(\w+)", "instagram"),
        ]:
            m = re.search(pattern, desc, re.I)
            if m:
                domain = pattern.split(r"\.com")[0].replace("\\", "")
                social[key] = f"https://{domain}.com/{m.group(1)}"

        # Last published date from first entry
        last_pub = None
        if feed.entries:
            entry = feed.entries[0]
            published = getattr(entry, "published_parsed", None)
            if published:
                try:
                    last_pub = datetime(*published[:6]).date().isoformat()
                except Exception:
                    pass

        return {
            "contact_email": email,
            "website": website,
            "social_links": social,
            "last_pub_date": last_pub,
            "episode_count": len(feed.entries),
        }

    def save_prospect(
        self,
        slug: str,
        itunes_data: dict,
        rss_data: dict,
        genre_key: Optional[str] = None,
    ) -> Path:
        """Scaffold a client YAML config and register the prospect in OutreachTracker.

        Calls init_client(slug) if the YAML does not already exist, then merges
        the prospect: block, genre content defaults, and rss_source fields into
        the YAML. Finally registers the prospect in OutreachTracker at 'identified'
        status.

        Note: yaml.safe_load + yaml.dump round-trip strips YAML comments. This is
        expected behaviour — prospect YAMLs are programmatic configs.

        Args:
            slug: Client slug / YAML filename stem (e.g. "test-comedy").
            itunes_data: Dict from iTunes search result.
            rss_data: Dict from enrich_from_rss().
            genre_key: Key into GENRE_DEFAULTS (e.g. "comedy"). If None, no
                genre defaults are applied.

        Returns:
            Path to the client YAML file.
        """
        clients_dir = Config.BASE_DIR / "clients"
        yaml_path = clients_dir / f"{slug}.yaml"

        # Scaffold full YAML structure if it doesn't exist yet
        if not yaml_path.exists():
            init_client(slug)

        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}

        # Inject prospect: block
        data["prospect"] = {
            "itunes_id": str(itunes_data.get("collectionId", "")),
            "feed_url": itunes_data.get("feedUrl", ""),
            "genre": itunes_data.get("primaryGenreName", ""),
            "episode_count": itunes_data.get("trackCount", 0),
            "last_pub_date": rss_data.get("last_pub_date", ""),
            "contact_email": rss_data.get("contact_email", ""),
            "website": rss_data.get("website", ""),
            "social_links": rss_data.get("social_links", {}),
            "notes": "",
        }

        # Pre-fill rss_source so --client <slug> latest works immediately
        data["episode_source"] = "rss"
        data.setdefault("rss_source", {})
        data["rss_source"]["feed_url"] = itunes_data.get("feedUrl", "")
        data["rss_source"]["episode_index"] = 0

        # Pre-fill genre-appropriate content settings
        if genre_key and genre_key in GENRE_DEFAULTS:
            defaults = GENRE_DEFAULTS[genre_key]
            data.setdefault("content", {})
            for field in ("voice_persona", "compliance_style"):
                data["content"][field] = defaults[field]
            data.setdefault("rss", {})
            data["rss"]["categories"] = defaults["categories"]

        yaml_path.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )

        # Register in OutreachTracker at "identified" status
        tracker = OutreachTracker()
        tracker.add_prospect(
            slug,
            {
                "show_name": itunes_data.get("collectionName", slug),
                "genre": itunes_data.get("primaryGenreName", ""),
                "rss_feed_url": itunes_data.get("feedUrl", ""),
                "contact_email": rss_data.get("contact_email", ""),
                "social_links": rss_data.get("social_links", {}),
                "status": "identified",
            },
        )

        logger.info("Saved prospect: %s -> %s", slug, yaml_path)
        return yaml_path

    def research_prospect(self, slug: str) -> dict:
        """Research a prospect's full digital presence and save a report.

        Checks iTunes, RSS feed, YouTube, website, and podcast directories
        for the prospect's online footprint. Downloads artwork and saves
        a prospect_research.md file.

        Args:
            slug: Client slug matching a YAML config in clients/.

        Returns:
            Dict with platform presence, contact info, and assessment.
        """
        clients_dir = Config.BASE_DIR / "clients"
        yaml_path = clients_dir / f"{slug}.yaml"
        if not yaml_path.exists():
            logger.warning("No client config for %s", slug)
            return {}

        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        prospect = data.get("prospect", {})
        show_name = data.get("podcast_name", slug)
        feed_url = prospect.get("feed_url") or (data.get("rss_source") or {}).get(
            "feed_url", ""
        )

        result = {
            "show_name": show_name,
            "slug": slug,
            "genre": prospect.get("genre", ""),
            "feed_url": feed_url,
            "platforms": {},
            "host_name": None,
            "contact_email": prospect.get("contact_email"),
            "website": prospect.get("website"),
            "artwork_url": None,
        }

        # --- RSS feed enrichment ---
        if feed_url:
            rss = self._research_rss(feed_url)
            result.update(rss)

        # --- iTunes lookup ---
        itunes_id = prospect.get("itunes_id")
        if itunes_id:
            itunes = self._research_itunes(itunes_id)
            result.update(itunes)

        # --- YouTube search ---
        yt = self._search_youtube(show_name)
        if yt:
            result["platforms"]["youtube"] = yt

        # --- Website scan for socials ---
        website = result.get("website") or ""
        if website:
            socials = self._scan_website_for_socials(website)
            for platform, url in socials.items():
                if platform not in result["platforms"]:
                    result["platforms"][platform] = {"url": url, "source": "website"}

        # --- Download artwork ---
        if result.get("artwork_url"):
            art_path = self._download_artwork(slug, result["artwork_url"])
            if art_path:
                result["artwork_path"] = str(art_path)
                # Update YAML with branding
                if "branding" not in data:
                    data["branding"] = {}
                data["branding"]["logo_path"] = str(art_path)
                yaml_path.write_text(
                    yaml.dump(data, default_flow_style=False, allow_unicode=True),
                    encoding="utf-8",
                )
                logger.info("Set logo_path for %s: %s", slug, art_path)

        # --- Score prospect fit ---
        result["score"] = self._score_prospect(result)

        # --- Save research report ---
        self._save_research_report(slug, result)

        return result

    def _research_rss(self, feed_url: str) -> dict:
        """Extract detailed info from RSS feed."""
        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            logger.warning("RSS parse failed: %s", e)
            return {}

        info = {}

        # Artwork
        img = feed.feed.get("image", {})
        itunes_img = feed.feed.get("itunes_image", {})
        info["artwork_url"] = (
            itunes_img.get("href") or img.get("href") or img.get("url")
        )

        # Host name
        author = feed.feed.get("author") or feed.feed.get("itunes_author", "")
        if author:
            info["host_name"] = author

        # Email from multiple sources
        owner = feed.feed.get("itunes_owner", {}) or {}
        email = (
            owner.get("email")
            or feed.feed.get("itunes_email")
            or (feed.feed.get("author_detail") or {}).get("email")
        )
        if email:
            info["contact_email"] = email

        # Website
        link = feed.feed.get("link", "")
        if link:
            info["website"] = link

        # Episode count and last pub date
        info["episode_count"] = len(feed.entries)
        if feed.entries:
            published = getattr(feed.entries[0], "published_parsed", None)
            if published:
                try:
                    info["last_pub_date"] = datetime(*published[:6]).date().isoformat()
                except Exception:
                    pass

        # Social links from description
        desc = feed.feed.get("description", "") or ""
        for pattern, key in [
            (r"twitter\.com/(\w+)", "twitter"),
            (r"x\.com/(\w+)", "twitter"),
            (r"instagram\.com/([\w.]+)", "instagram"),
            (r"tiktok\.com/@([\w.]+)", "tiktok"),
            (r"youtube\.com/(@?[\w-]+)", "youtube"),
            (r"facebook\.com/([\w.-]+)", "facebook"),
            (r"patreon\.com/([\w-]+)", "patreon"),
        ]:
            m = re.search(pattern, desc, re.I)
            if m:
                info.setdefault("platforms", {})
                info["platforms"][key] = {
                    "handle": m.group(1),
                    "source": "rss_description",
                }

        return info

    def _research_itunes(self, itunes_id: str) -> dict:
        """Look up show details via iTunes API."""
        try:
            resp = requests.get(
                "https://itunes.apple.com/lookup",
                params={"id": itunes_id, "entity": "podcast"},
                timeout=10,
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            if results:
                r = results[0]
                return {
                    "itunes_rating": r.get("averageUserRating"),
                    "itunes_rating_count": r.get("userRatingCount"),
                    "artwork_url": r.get("artworkUrl600")
                    or r.get("artworkUrl100"),
                }
        except Exception as e:
            logger.warning("iTunes lookup failed for %s: %s", itunes_id, e)
        return {}

    def _search_youtube(self, show_name: str) -> Optional[dict]:
        """Search YouTube for a podcast channel (no API key needed)."""
        search_term = f"{show_name} podcast"
        try:
            resp = requests.get(
                "https://www.youtube.com/results",
                params={"search_query": search_term},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            if resp.status_code == 200:
                # Check if there's a channel result
                text = resp.text
                has_channel = "channel" in text.lower() and show_name.lower().replace(
                    " ", ""
                ) in text.lower().replace(" ", "")
                return {
                    "likely_exists": has_channel,
                    "search_url": f"https://www.youtube.com/results?search_query={search_term.replace(' ', '+')}",
                    "source": "youtube_search",
                }
        except Exception as e:
            logger.warning("YouTube search failed: %s", e)
        return None

    def _scan_website_for_socials(self, url: str) -> dict:
        """Scrape a website for social media links."""
        socials = {}
        try:
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                return socials
            text = resp.text
            patterns = {
                "youtube": r"(?:youtube\.com|youtu\.be)/([@\w-]+)",
                "instagram": r"instagram\.com/([\w.]+)",
                "twitter": r"(?:twitter|x)\.com/([\w]+)",
                "tiktok": r"tiktok\.com/@([\w.]+)",
                "facebook": r"facebook\.com/([\w.-]+)",
                "patreon": r"patreon\.com/([\w-]+)",
                "bluesky": r"bsky\.app/profile/([\w.-]+)",
            }
            for platform, pattern in patterns.items():
                m = re.search(pattern, text, re.I)
                if m:
                    socials[platform] = m.group(0)

            # Also look for email addresses on the page
            email_match = re.search(
                r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text
            )
            if email_match:
                socials["_email"] = email_match.group(0)
        except Exception as e:
            logger.warning("Website scan failed for %s: %s", url, e)
        return socials

    def _download_artwork(self, slug: str, artwork_url: str) -> Optional[Path]:
        """Download podcast artwork and save to clients/<slug>/."""
        try:
            resp = requests.get(artwork_url, timeout=15)
            if resp.status_code != 200:
                return None
            ext = artwork_url.rsplit(".", 1)[-1].split("?")[0][:4]
            if ext not in ("jpg", "jpeg", "png", "webp"):
                ext = "jpg"
            client_dir = Config.BASE_DIR / "clients" / slug
            client_dir.mkdir(exist_ok=True)
            path = client_dir / f"logo.{ext}"
            path.write_bytes(resp.content)
            logger.info("Downloaded artwork for %s: %s (%dKB)", slug, path, len(resp.content) // 1024)
            return path.relative_to(Config.BASE_DIR)
        except Exception as e:
            logger.warning("Artwork download failed for %s: %s", slug, e)
            return None

    def _score_prospect(self, research: dict) -> dict:
        """Score how good a fit this prospect is for our service.

        Ideal client: has content (episodes), has audience, but lacks
        short-form clips, video presence, and social distribution.
        We want to fill gaps, not compete with what they already do.

        Returns:
            Dict with total score (0-100), rating, and breakdown.
        """
        platforms = research.get("platforms", {})
        episode_count = research.get("episode_count", 0)
        last_pub = research.get("last_pub_date")
        has_email = bool(research.get("contact_email"))

        score = 0
        reasons = []

        # --- Content volume (max 20pts) ---
        # More episodes = bigger backlog we can clip from
        if episode_count >= 100:
            score += 20
            reasons.append("+20 Large episode backlog (100+)")
        elif episode_count >= 50:
            score += 15
            reasons.append(f"+15 Good episode backlog ({episode_count})")
        elif episode_count >= 20:
            score += 10
            reasons.append(f"+10 Moderate episode count ({episode_count})")
        else:
            reasons.append(f"+0 Few episodes ({episode_count})")

        # --- Activity (max 15pts) ---
        if last_pub:
            from datetime import date

            try:
                pub_date = date.fromisoformat(last_pub)
                days_ago = (date.today() - pub_date).days
                if days_ago <= 30:
                    score += 15
                    reasons.append("+15 Active (posted within 30 days)")
                elif days_ago <= 90:
                    score += 10
                    reasons.append(f"+10 Recently active ({days_ago} days ago)")
                elif days_ago <= 180:
                    score += 5
                    reasons.append(f"+5 Possibly on hiatus ({days_ago} days ago)")
                else:
                    reasons.append(f"+0 Likely dormant ({days_ago} days ago)")
            except (ValueError, TypeError):
                reasons.append("+0 Unknown activity status")
        else:
            reasons.append("+0 Unknown last publish date")

        # --- Contactability (max 10pts) ---
        if has_email:
            score += 10
            reasons.append("+10 Contact email available")
        else:
            reasons.append("+0 No contact email found")

        # --- Video gap (max 25pts) ---
        # NO video/YouTube = best fit. They need us most.
        yt = platforms.get("youtube", {})
        if not yt:
            score += 25
            reasons.append("+25 No YouTube presence — we fill this gap")
        elif isinstance(yt, dict) and not yt.get("likely_exists", True):
            score += 25
            reasons.append("+25 YouTube not confirmed — likely no channel")
        elif isinstance(yt, dict) and yt.get("likely_exists"):
            # They have YouTube — check if it's just a listing or active
            score += 5
            reasons.append("+5 Has YouTube but may lack clips/Shorts (verify manually)")
        else:
            score += 5
            reasons.append("+5 Has YouTube (verify Shorts manually)")

        # --- Social gaps (max 15pts) ---
        # Fewer social platforms = more we can help with distribution
        social_count = sum(
            1 for p in ["instagram", "tiktok", "twitter", "facebook"]
            if p in platforms
        )
        if social_count == 0:
            score += 15
            reasons.append("+15 No social media presence — full distribution gap")
        elif social_count == 1:
            score += 10
            reasons.append(f"+10 Minimal social presence ({social_count} platform)")
        elif social_count <= 2:
            score += 5
            reasons.append(f"+5 Some social presence ({social_count} platforms)")
        else:
            reasons.append(f"+0 Strong social presence ({social_count} platforms)")

        # --- Solo producer bonus (max 10pts) ---
        # Solo hosts benefit most — no team to delegate to
        host = research.get("host_name", "")
        website = research.get("website", "")
        has_patreon = "patreon" in platforms
        # Podbean/Anchor/RSS.com = indie hosting = likely solo
        indie_hosts = ["podbean", "anchor", "rss.com", "spreaker", "buzzsprout"]
        is_indie = any(h in (website or "").lower() for h in indie_hosts)
        if is_indie:
            score += 10
            reasons.append("+10 Indie-hosted (likely solo producer)")
        elif not has_patreon:
            score += 5
            reasons.append("+5 No team indicators")

        # --- Penalty: already has clips/Shorts ---
        # If they're already doing what we offer, lower priority
        if isinstance(yt, dict) and yt.get("likely_exists"):
            score -= 5
            reasons.append("-5 May already produce clips (verify)")

        # Clamp score
        score = max(0, min(100, score))

        # Rating
        if score >= 75:
            rating = "EXCELLENT"
        elif score >= 55:
            rating = "GOOD"
        elif score >= 35:
            rating = "FAIR"
        else:
            rating = "POOR"

        return {
            "total": score,
            "rating": rating,
            "reasons": reasons,
        }

    def _save_research_report(self, slug: str, research: dict) -> Path:
        """Save a prospect_research.md file to output/<slug>/."""
        output_dir = Path(Config.OUTPUT_DIR) / slug
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / "prospect_research.md"

        platforms = research.get("platforms", {})
        show_name = research.get("show_name", slug)
        today = datetime.now().strftime("%Y-%m-%d")

        lines = [
            f"# Prospect Research: {show_name}\n",
            f"**Researched:** {today}\n",
            "## Show Info",
            f"- **Host:** {research.get('host_name', 'Unknown')}",
            f"- **Genre:** {research.get('genre', 'Unknown')}",
            f"- **Episodes:** {research.get('episode_count', '?')}",
            f"- **Last Published:** {research.get('last_pub_date', 'Unknown')}",
            f"- **Email:** {research.get('contact_email') or 'NOT FOUND'}",
            f"- **Website:** {research.get('website') or 'None'}",
            "",
            "## Platform Presence",
            "| Platform | Status | Details |",
            "|---|---|---|",
        ]

        for platform in ["youtube", "instagram", "tiktok", "twitter", "facebook", "patreon", "bluesky"]:
            if platform in platforms:
                info = platforms[platform]
                if isinstance(info, dict):
                    detail = info.get("handle") or info.get("url") or info.get("search_url", "")
                    lines.append(f"| {platform.title()} | Found | {detail} |")
                else:
                    lines.append(f"| {platform.title()} | Found | {info} |")
            else:
                lines.append(f"| {platform.title()} | Not found | |")

        # Score
        score = research.get("score", {})
        if score:
            lines.extend([
                "",
                f"## Fit Score: {score.get('total', 0)}/100 ({score.get('rating', '?')})",
                "",
                "| Factor | Points |",
                "|---|---|",
            ])
            for reason in score.get("reasons", []):
                lines.append(f"| {reason} |")
            lines.append("")

        lines.extend([
            "## Artwork",
            f"- **Downloaded:** {'Yes — ' + research.get('artwork_path', '') if research.get('artwork_path') else 'No'}",
            "",
            f"---\n*Auto-generated by prospect research pipeline*\n",
        ])

        report_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Research report saved: %s", report_path)
        return report_path

    def _genre_key_from_name(self, genre_name: str) -> Optional[str]:
        """Map an iTunes primaryGenreName to a GENRE_DEFAULTS key.

        Args:
            genre_name: Genre name from iTunes (e.g. "True Crime", "Comedy").

        Returns:
            GENRE_DEFAULTS key (e.g. "true-crime") or None if not mapped.
        """
        normalised = genre_name.lower().strip()
        return _GENRE_NAME_MAP.get(normalised)


def run_find_prospects_cli(argv: list) -> None:
    """CLI handler for find-prospects command.

    Parses flags from argv, searches iTunes, prints a ranked table, and
    optionally prompts the user to save a prospect as a client YAML.

    Args:
        argv: sys.argv list (index 0 = script, 1 = "find-prospects", 2+ = flags).
    """
    genre = None
    min_ep, max_ep, limit = 20, 500, 20
    save_flag = False
    i = 2
    while i < len(argv):
        if argv[i] == "--genre" and i + 1 < len(argv):
            genre = argv[i + 1]
            i += 2
        elif argv[i] == "--min-episodes" and i + 1 < len(argv):
            min_ep = int(argv[i + 1])
            i += 2
        elif argv[i] == "--max-episodes" and i + 1 < len(argv):
            max_ep = int(argv[i + 1])
            i += 2
        elif argv[i] == "--limit" and i + 1 < len(argv):
            limit = int(argv[i + 1])
            i += 2
        elif argv[i] == "--save":
            save_flag = True
            i += 1
        else:
            i += 1

    term = genre or "podcast"
    genre_id = GENRE_IDS.get(genre) if genre else None
    finder = ProspectFinder()
    results = finder.search(
        term=term,
        genre_id=genre_id,
        min_episodes=min_ep,
        max_episodes=max_ep,
        limit=limit,
    )
    if not results:
        print("No podcasts found matching criteria.")
        return

    hdr = "{:<3} {:<40} {:<25} {:<8} {:<15} {:<50}"
    print(hdr.format("#", "Show Name", "Host", "Episodes", "Genre", "Feed URL"))
    print("-" * 145)
    for idx, r in enumerate(results, 1):
        print(
            hdr.format(
                idx,
                r.get("collectionName", "")[:40],
                r.get("artistName", "")[:25],
                r.get("trackCount", 0),
                r.get("primaryGenreName", "")[:15],
                r.get("feedUrl", "")[:50],
            )
        )

    if save_flag or results:
        choice = input("\nSave prospect? Enter number (or 'q' to quit): ").strip()
        if choice.lower() != "q" and choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(results):
                itunes_data = results[idx]
                slug = re.sub(
                    r"[^a-z0-9-]",
                    "",
                    itunes_data.get("collectionName", "").lower().replace(" ", "-"),
                )
                feed_url = itunes_data.get("feedUrl", "")
                print(f"Enriching from RSS: {feed_url}")
                rss_data = finder.enrich_from_rss(feed_url) if feed_url else {}
                genre_key = finder._genre_key_from_name(
                    itunes_data.get("primaryGenreName", "")
                )
                yaml_path = finder.save_prospect(slug, itunes_data, rss_data, genre_key)
                email = rss_data.get("contact_email", "")
                print(f"Saved prospect: {yaml_path}")
                if email:
                    print(f"Contact email: {email}")
            else:
                print("Invalid selection.")
