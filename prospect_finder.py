"""Podcast prospect discovery: iTunes search, RSS contact extraction, YAML scaffolding.

Provides ProspectFinder to discover podcast prospects via iTunes Search API,
enrich them with contact info from RSS feeds, and scaffold client YAML configs
with genre-appropriate content defaults pre-filled.
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

    def _genre_key_from_name(self, genre_name: str) -> Optional[str]:
        """Map an iTunes primaryGenreName to a GENRE_DEFAULTS key.

        Args:
            genre_name: Genre name from iTunes (e.g. "True Crime", "Comedy").

        Returns:
            GENRE_DEFAULTS key (e.g. "true-crime") or None if not mapped.
        """
        normalised = genre_name.lower().strip()
        return _GENRE_NAME_MAP.get(normalised)
