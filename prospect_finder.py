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

        # --- Scan ALL websites for socials ---
        # Check both the podcast host URL and the show's own website
        websites_to_scan = set()
        website = result.get("website") or ""
        if website:
            websites_to_scan.add(website)
        show_website = prospect.get("website") or ""
        if show_website and show_website != website:
            websites_to_scan.add(show_website)

        # Derive likely show website from slug/name (e.g. kccpod.com)
        slug_clean = slug.replace("-", "")
        for domain in [f"https://{slug}.com", f"https://www.{slug}.com"]:
            websites_to_scan.add(domain)

        for site_url in websites_to_scan:
            socials = self._scan_website_for_socials(site_url)
            for platform, url in socials.items():
                if platform not in result["platforms"]:
                    result["platforms"][platform] = {"url": url, "source": site_url}
            # Pick up email from website if we don't have one
            if not result.get("contact_email") and socials.get("_email"):
                result["contact_email"] = socials["_email"]

        # --- Direct platform handle checks ---
        # Build handles from show name and host name, NOT the slug
        handles_to_try = []

        # From show name: "The Dr Pompa Podcast" -> "drpompapodcast", "thedrpompapodcast"
        name_clean = re.sub(r"[^a-z0-9 ]", "", show_name.lower()).strip()
        name_no_spaces = name_clean.replace(" ", "")
        # Without common prefixes (the, a)
        name_no_prefix = re.sub(r"^(the|a) ", "", name_clean).replace(" ", "")
        for h in [name_no_spaces, name_no_prefix]:
            if h and h not in handles_to_try:
                handles_to_try.append(h)

        # From host name: "Dr. Daniel Pompa" -> "danielpompa", "drpompa", "drdanielpompa"
        host = result.get("host_name") or ""
        if host:
            host_clean = re.sub(r"[^a-z0-9 ]", "", host.lower()).strip()
            host_no_spaces = host_clean.replace(" ", "")
            if host_no_spaces and host_no_spaces not in handles_to_try:
                handles_to_try.append(host_no_spaces)
            # Try last name only (common handle pattern)
            host_parts = host_clean.split()
            if len(host_parts) >= 2:
                last = host_parts[-1]
                if last not in handles_to_try:
                    handles_to_try.append(last)

        # Extract handle from podcast hosting URL (e.g. kccpod.podbean.com -> kccpod)
        for url_field in [feed_url, website, show_website]:
            if not url_field:
                continue
            # Match subdomain-based hosts: kccpod.podbean.com, show.spreaker.com
            import urllib.parse

            parsed = urllib.parse.urlparse(url_field)
            hostname = parsed.hostname or ""
            for host_domain in [
                "podbean.com", "spreaker.com", "buzzsprout.com",
                "anchor.fm", "transistor.fm", "libsyn.com",
            ]:
                if hostname.endswith(host_domain):
                    # Try subdomain first (e.g. kccpod.podbean.com)
                    subdomain = hostname.replace(f".{host_domain}", "").replace("feed.", "")
                    if subdomain and subdomain not in handles_to_try and subdomain != "www":
                        handles_to_try.append(subdomain)
                    # Also try path-based handle (e.g. feed.podbean.com/kccpod/feed.xml)
                    path_parts = parsed.path.strip("/").split("/")
                    if path_parts and path_parts[0] not in ("feed.xml", "rss", ""):
                        path_handle = path_parts[0]
                        if path_handle not in handles_to_try:
                            handles_to_try.append(path_handle)
            # Match path-based hosts: rss.com/podcasts/showname/
            if "rss.com/podcasts/" in url_field:
                path_handle = url_field.split("rss.com/podcasts/")[1].strip("/").split("/")[0]
                if path_handle and path_handle not in handles_to_try:
                    handles_to_try.append(path_handle)

        # Extract handles already found by website scanning and check them
        # across ALL platforms (a handle found on IG might also be on TikTok)
        for _platform, info in result.get("platforms", {}).items():
            if isinstance(info, dict):
                handle = info.get("handle", "")
                if handle and handle not in handles_to_try:
                    handles_to_try.append(handle)
            elif isinstance(info, str):
                # Extract handle from URL like "instagram.com/kccpod"
                parts = info.rstrip("/").rsplit("/", 1)
                if len(parts) == 2:
                    extracted = parts[1].lstrip("@")
                    if extracted and extracted not in handles_to_try:
                        handles_to_try.append(extracted)

        self._check_platform_handles(result, handles_to_try)

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

    def _check_platform_handles(self, result: dict, handles: List[str]) -> None:
        """Directly check if handles exist on TikTok, Instagram, YouTube, and Twitter.

        This is more reliable than scraping websites because it checks the
        platforms directly. A 200 response means the account exists.

        Args:
            result: Research result dict to update with platform findings.
            handles: List of handle strings to check (e.g. ["kccpod"]).
        """
        platforms_to_check = {
            "tiktok": "https://www.tiktok.com/@{handle}",
            "instagram": "https://www.instagram.com/{handle}/",
            "youtube": "https://www.youtube.com/@{handle}",
            "twitter": "https://x.com/{handle}",
        }

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        for handle in handles:
            for platform, url_template in platforms_to_check.items():
                # Skip if we already confirmed this platform exists
                existing = result.get("platforms", {}).get(platform, {})
                if isinstance(existing, dict) and existing.get("confirmed"):
                    continue

                url = url_template.format(handle=handle)
                try:
                    # Always use GET — HEAD is unreliable for platform checks
                    resp = requests.get(
                        url,
                        headers=headers,
                        timeout=8,
                        allow_redirects=True,
                    )
                    if resp.status_code == 200:
                        final_url = resp.url if hasattr(resp, "url") else url
                        body = resp.text[:5000].lower()

                        # Filter out false positives: pages that say account not found
                        not_found_signals = [
                            "couldn't find this account",
                            "this account doesn't exist",
                            "page not found",
                            "user not found",
                            "sorry, this page isn",
                            "this page is not available",
                            '"statuscode":10202',  # TikTok API "user not found"
                        ]
                        is_fake = any(sig in body for sig in not_found_signals)

                        # Also filter redirects to generic/login pages
                        if not is_fake and handle.lower() in final_url.lower():
                            result.setdefault("platforms", {})
                            result["platforms"][platform] = {
                                "handle": handle,
                                "url": url,
                                "confirmed": True,
                                "source": "direct_check",
                            }
                            logger.info(
                                "Confirmed %s account: @%s", platform, handle
                            )
                except Exception:
                    pass  # Connection errors are expected for non-existent handles

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
        """Score how good a fit this prospect is for full automation service.

        Ideal client: active show with content, reachable host, indie
        producer who'd benefit from automated transcription, clips, blog
        posts, social posting, and scheduling. Social presence is neutral
        — we automate the workflow, not fill a gap.

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

        # --- Activity (max 20pts) ---
        if last_pub:
            from datetime import date

            try:
                pub_date = date.fromisoformat(last_pub)
                days_ago = (date.today() - pub_date).days
                if days_ago <= 14:
                    score += 20
                    reasons.append("+20 Very active (posted within 2 weeks)")
                elif days_ago <= 30:
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

        # --- Contactability (max 15pts) ---
        if has_email:
            # Personal email is better than generic support@
            email = research.get("contact_email", "")
            generic = ["support@", "info@", "podcast@", "hello@", "contact@"]
            if any(email.lower().startswith(g) for g in generic):
                score += 10
                reasons.append("+10 Generic contact email available")
            else:
                score += 15
                reasons.append("+15 Personal contact email available")
        else:
            reasons.append("+0 No contact email found")

        # --- Social presence (max 15pts) ---
        # Having social accounts is GOOD — means they care about distribution
        # and would value automating it. No social = may not care.
        confirmed_platforms = []
        for p in ["youtube", "tiktok", "instagram", "twitter"]:
            info = platforms.get(p, {})
            if isinstance(info, dict) and info.get("confirmed"):
                confirmed_platforms.append(p)

        confirmed_count = len(confirmed_platforms)
        if confirmed_count >= 3:
            score += 15
            reasons.append(f"+15 Active on {confirmed_count} platforms — values distribution")
        elif confirmed_count >= 1:
            score += 10
            reasons.append(f"+10 On {confirmed_count} platform(s) — some distribution effort")
        else:
            score += 5
            reasons.append("+5 No confirmed social — may not prioritize distribution")

        # --- Solo/indie producer (max 20pts) ---
        # Indie hosts are more likely to need automation than network shows
        website = research.get("website", "")
        host_name = research.get("host_name", "")
        has_patreon = "patreon" in platforms

        network_signals = [
            "iheartpodcasts", "pushkin", "megaphone", "vox media",
            "audible", "wondery", "npr", "bbc", "fox news",
            "wall street journal", "wsj", "lemonada", "earwolf",
            "comedy central", "simplecast", "smartless",
        ]
        is_network = any(
            sig in (host_name or "").lower() or sig in (website or "").lower()
            for sig in network_signals
        )

        indie_hosts = ["podbean", "anchor", "rss.com", "spreaker", "buzzsprout"]
        is_indie = any(h in (research.get("feed_url") or "").lower() for h in indie_hosts)

        if is_network:
            score -= 10
            reasons.append("-10 Network/studio-backed show — unlikely to need us")
        elif is_indie:
            score += 20
            reasons.append("+20 Indie-hosted — likely solo producer")
        elif has_patreon:
            score += 15
            reasons.append("+15 Has Patreon — monetizing independently")
        else:
            score += 10
            reasons.append("+10 No network indicators")

        # --- Release cadence bonus (max 10pts) ---
        # Regular releasers benefit most from automation
        if episode_count >= 20 and last_pub:
            try:
                pub_date = date.fromisoformat(last_pub)
                days_ago = (date.today() - pub_date).days
                if days_ago <= 14 and episode_count >= 40:
                    score += 10
                    reasons.append("+10 High-volume active show — automation saves real time")
                elif days_ago <= 30:
                    score += 5
                    reasons.append("+5 Regular release cadence")
            except (ValueError, TypeError):
                pass

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
    save_all = False
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
        elif argv[i] == "--save-all":
            save_all = True
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
        line = hdr.format(
            idx,
            r.get("collectionName", "")[:40],
            r.get("artistName", "")[:25],
            r.get("trackCount", 0),
            r.get("primaryGenreName", "")[:15],
            r.get("feedUrl", "")[:50],
        )
        print(line.encode("ascii", errors="replace").decode("ascii"))

    def _make_slug(name: str) -> str:
        """Create a slug from a podcast name, max 40 chars."""
        raw = re.sub(r"[^a-z0-9-]", "", name.lower().replace(" ", "-"))
        raw = re.sub(r"-{2,}", "-", raw).strip("-")
        if len(raw) > 40:
            raw = raw[:40].rstrip("-")
        return raw

    if save_all:
        for idx, itunes_data in enumerate(results):
            slug = _make_slug(itunes_data.get("collectionName", ""))
            feed_url = itunes_data.get("feedUrl", "")
            print(f"\n[{idx + 1}/{len(results)}] Enriching {slug} from RSS...")
            rss_data = finder.enrich_from_rss(feed_url) if feed_url else {}
            genre_key = finder._genre_key_from_name(
                itunes_data.get("primaryGenreName", "")
            )
            yaml_path = finder.save_prospect(slug, itunes_data, rss_data, genre_key)
            email = rss_data.get("contact_email", "")
            print(f"  Saved: {yaml_path}")
            if email:
                print(f"  Contact: {email}")
        print(f"\nSaved {len(results)} prospects.")
    elif save_flag or results:
        choice = input("\nSave prospect? Enter number (or 'q' to quit): ").strip()
        if choice.lower() != "q" and choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(results):
                itunes_data = results[idx]
                slug = _make_slug(itunes_data.get("collectionName", ""))
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
