"""RSS episode fetcher — parses podcast RSS feeds and downloads audio enclosures."""

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import feedparser
import requests
from tqdm import tqdm

from logger import logger


def _clean_download_filename(url: str) -> str:
    """Produce a clean on-disk filename for an RSS audio enclosure.

    Subsplash and anchor.fm-to-cloudfront redirector URLs encode the real
    audio path as a base64 or URL-encoded segment (e.g.
    `...../aHR0cHM6Ly9jZG4uc3Vic3BsYXNoLmNvbS8....mp3`). Using that raw
    `Path(url).name` as the on-disk filename leaks the ugly string into
    every downstream artifact name (ep_dir, transcript.json, clip MP4s,
    and eventually the Drive demo package a prospect sees).

    Heuristics that flag a filename as "encoded URL, not a real name":
      * Length > 60 chars
      * Starts with `aHR0c` (the base64 prefix for `http` / `https`)
      * Contains `%3A` (URL-encoded `:` found in `http%3A//...` forms)
      * Contains no `.` before the extension (encoded strings often have
        no real extension separator — but we can't easily test this)

    When any heuristic trips, we replace the filename with
    `ep_<sha1(url)[:8]>.<ext>` — deterministic, stable across reruns,
    human-readable-enough.
    """
    parsed = urlparse(url)
    original = Path(parsed.path).name
    ext = Path(parsed.path).suffix or ".mp3"
    looks_encoded = (
        len(original) > 60
        or original.startswith("aHR0c")
        or "%3A" in original
        or "%2F" in original
    )
    if looks_encoded:
        short = hashlib.sha1(url.encode()).hexdigest()[:8]
        return f"ep_{short}{ext}"
    return original


@dataclass
class EpisodeMeta:
    """Metadata for a single podcast episode extracted from an RSS feed entry."""

    title: str
    audio_url: str
    pub_date: Optional[datetime]
    episode_number: Optional[int]
    duration_seconds: Optional[int]
    description: Optional[str]


def extract_episode_number_from_filename(filename: str) -> Optional[int]:
    """Extract episode number from a filename using common podcast naming patterns.

    Supports formats:
    - "Episode 25 - Title.wav"
    - "Ep 25 - Title.wav", "ep_25_title.mp3", "ep25.mp3"
    - "25 - Title.wav"
    - "podcast #25.mp3"

    Args:
        filename: Audio filename (basename only or full path — only last component used).

    Returns:
        Episode number as int, or None if no pattern matches.
    """
    patterns = [
        r"[Ee]pisode\s*(\d+)",  # Episode 25
        r"[Ee]p[_\s]*(\d+)",  # Ep 25, ep_25, ep25
        r"^(\d+)\s*[-_]",  # 25 - Title
        r"#(\d+)",  # #25
    ]
    name = Path(filename).name
    for pattern in patterns:
        match = re.search(pattern, name)
        if match:
            return int(match.group(1))
    return None


def _parse_itunes_duration(raw: Optional[str]) -> Optional[int]:
    """Convert an iTunes duration string to total seconds.

    Handles:
    - "HH:MM:SS"  → hours*3600 + minutes*60 + seconds
    - "MM:SS"     → minutes*60 + seconds
    - "NNNN"      → plain seconds as int
    - None / ""   → None

    Args:
        raw: Raw itunes_duration string from feedparser entry.

    Returns:
        Duration in seconds as int, or None if unparseable.
    """
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None
    if ":" in raw:
        parts = raw.split(":")
        try:
            int_parts = [int(p) for p in parts]
        except ValueError:
            return None
        if len(int_parts) == 3:
            hours, minutes, seconds = int_parts
            return hours * 3600 + minutes * 60 + seconds
        if len(int_parts) == 2:
            minutes, seconds = int_parts
            return minutes * 60 + seconds
        return None
    try:
        return int(raw)
    except ValueError:
        return None


class RSSEpisodeFetcher:
    """Fetch and download podcast episodes from a public RSS feed.

    No credentials required — works with any publicly accessible RSS 2.0 /
    Atom feed that includes audio enclosures.
    """

    def __init__(self) -> None:
        """Initialize the fetcher. Always enabled — no credentials needed."""
        self.enabled = True

    def fetch_latest(self, rss_url: str) -> EpisodeMeta:
        """Fetch metadata for the most recent episode in the feed.

        Args:
            rss_url: URL or local path to the RSS feed XML.

        Returns:
            EpisodeMeta for the most recent entry.

        Raises:
            ValueError: If the feed fails to parse (bozo), has no entries, or
                        the latest entry has no audio enclosure.
        """
        return self.fetch_episode(rss_url, index=0)

    def fetch_episode(self, rss_url: str, index: int = 0) -> EpisodeMeta:
        """Fetch metadata for the episode at *index* (0 = most recent with audio).

        Entries are sorted by published_parsed descending, then filtered to
        only those carrying an audio enclosure, before indexing. Some feeds
        (especially WordPress `/category/sermons/feed/` style) intermix
        non-audio announcement posts with sermon audio; this skip-and-continue
        behavior lets index=0 always land on the most recent actual sermon
        rather than crashing on a vision-statement post that lacks audio.

        Args:
            rss_url: URL or local path to the RSS feed XML.
            index:   0-based position after descending date sort (0 = newest).

        Returns:
            EpisodeMeta for the selected entry.

        Raises:
            ValueError: If the feed is malformed, empty, or the selected
                        entry has no audio enclosure.
        """
        logger.info("Fetching RSS feed: %s (index=%d)", rss_url, index)
        feed = feedparser.parse(rss_url)

        if feed.bozo:
            exc = feed.bozo_exception
            # Encoding mismatches are harmless — feedparser still parses correctly
            if isinstance(exc, feedparser.CharacterEncodingOverride):
                logger.warning("RSS feed encoding mismatch (harmless): %s", exc)
            elif feed.entries:
                logger.warning("RSS feed flagged bozo but has entries: %s", exc)
            else:
                raise ValueError(f"RSS feed parse error (bozo): {exc}")

        if not feed.entries:
            raise ValueError(f"No entries found in RSS feed: {rss_url}")

        # Sort newest-first. Use getattr — feedparser entries raise
        # AttributeError on missing keys rather than returning None, so a
        # direct truthiness check would crash on feeds that omit pub dates
        # (e.g. Subsplash).
        sorted_entries = sorted(
            feed.entries,
            key=lambda e: getattr(e, "published_parsed", None) or (0,) * 9,
            reverse=True,
        )

        # Filter out non-audio entries before indexing. Some church feeds
        # (e.g. parkchurch.org/category/sermons/feed/) interleave vision
        # statements / blog posts that have no enclosure. Without this filter,
        # index=0 would crash whenever the latest item happens to be one of
        # those, even though there's a valid sermon at index=1.
        audio_entries = [e for e in sorted_entries if getattr(e, "enclosures", None)]
        skipped = len(sorted_entries) - len(audio_entries)
        if skipped > 0:
            skipped_titles = [
                getattr(e, "title", "?")
                for e in sorted_entries
                if not getattr(e, "enclosures", None)
            ]
            logger.info(
                "Skipped %d non-audio entries: %s",
                skipped,
                skipped_titles[:3],
            )

        if not audio_entries:
            raise ValueError(f"No entries with audio enclosures in RSS feed: {rss_url}")

        if index >= len(audio_entries):
            raise ValueError(
                f"Index {index} out of range — only {len(audio_entries)} "
                f"audio entries available (total feed entries: {len(sorted_entries)})"
            )

        entry = audio_entries[index]
        audio_url: str = entry.enclosures[0]["url"]

        # Episode number: iTunes tag first, then filename fallback
        itunes_episode_raw = entry.get("itunes_episode")
        episode_number: Optional[int] = None
        if itunes_episode_raw is not None:
            try:
                episode_number = int(itunes_episode_raw)
            except (ValueError, TypeError):
                episode_number = None
        if episode_number is None:
            filename = Path(urlparse(audio_url).path).name
            episode_number = extract_episode_number_from_filename(filename)

        # Duration
        duration_seconds = _parse_itunes_duration(entry.get("itunes_duration"))

        # Publication date
        pub_date: Optional[datetime] = None
        if entry.published_parsed:
            try:
                pub_date = datetime(*entry.published_parsed[:6])
            except Exception:
                pub_date = None

        description = getattr(entry, "summary", None)

        meta = EpisodeMeta(
            title=entry.title,
            audio_url=audio_url,
            pub_date=pub_date,
            episode_number=episode_number,
            duration_seconds=duration_seconds,
            description=description,
        )
        logger.info(
            "Fetched episode: %s (ep %s, %s sec)",
            meta.title,
            meta.episode_number,
            meta.duration_seconds,
        )
        return meta

    def download_audio(self, url: str, dest_dir: Path) -> Path:
        """Stream audio from *url* to *dest_dir*, showing a tqdm progress bar.

        Skips download if the destination file already exists.

        Args:
            url:      Direct URL to the audio file.
            dest_dir: Directory in which to save the file.

        Returns:
            Path to the downloaded (or already-existing) file.

        Raises:
            requests.HTTPError: If the server returns a 4xx/5xx response.
        """
        # Strip query params; also replace encoded-URL filenames from
        # Subsplash / anchor-cloudfront redirectors so downstream artifact
        # names don't inherit the ugly base64/URL-encoded prefix (B022).
        filename = _clean_download_filename(url)
        dest_path = Path(dest_dir) / filename

        if dest_path.exists():
            logger.info("Audio already exists, skipping download: %s", dest_path)
            return dest_path

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Downloading audio from %s -> %s", url, dest_path)

        headers = {"User-Agent": "PodcastAutomation/1.4 (podcast downloader)"}
        with requests.get(url, stream=True, timeout=60, headers=headers) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0)) or None
            chunk_size = 64 * 1024  # 64 KB

            with tqdm(
                total=total,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc=filename,
            ) as progress:
                with open(dest_path, "wb") as fh:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            fh.write(chunk)
                            progress.update(len(chunk))

        logger.info("Download complete: %s", dest_path)
        return dest_path
