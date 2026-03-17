"""Spotify uploader for podcast episodes via RSS feed.

Spotify for Podcasters uses RSS feeds for podcast distribution.
This module manages RSS feed generation and updates. No Spotify API needed.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from config import Config
from rss_feed_generator import RSSFeedGenerator
from logger import logger


class SpotifyUploader:
    """
    Handle Spotify podcast distribution via RSS feed.

    Spotify for Podcasters crawls your RSS feed to discover new episodes.
    No API credentials are required — just an RSS feed hosted at a public URL.

    For dashboard access: https://podcasters.spotify.com
    """

    def __init__(self):
        """Initialize Spotify uploader (RSS-only, no API credentials needed)."""
        self.rss_generator = RSSFeedGenerator()

    def generate_rss_item(
        self,
        episode_number: int,
        title: str,
        description: str,
        audio_url: str,
        audio_file_size: int,
        duration_seconds: int,
        pub_date: Optional[datetime] = None,
    ) -> str:
        """
        Generate an RSS feed item for a podcast episode.

        Args:
            episode_number: Episode number
            title: Episode title
            description: Episode description
            audio_url: Public URL to audio file (MP3)
            audio_file_size: Audio file size in bytes
            duration_seconds: Episode duration in seconds
            pub_date: Publication date (default: now)

        Returns:
            RSS XML item as string
        """
        if not pub_date:
            pub_date = datetime.now()

        # Format duration as HH:MM:SS
        hours = duration_seconds // 3600
        minutes = (duration_seconds % 3600) // 60
        seconds = duration_seconds % 60
        duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        # Format pub date as RFC 2822
        pub_date_str = pub_date.strftime("%a, %d %b %Y %H:%M:%S %z")
        if not pub_date_str.endswith(("+0000", "-0000")):
            pub_date_str += " +0000"

        rss_item = f"""
    <item>
        <title>{title}</title>
        <description><![CDATA[{description}]]></description>
        <link>{audio_url}</link>
        <guid isPermaLink="false">{Config.PODCAST_NAME}-ep{episode_number}</guid>
        <pubDate>{pub_date_str}</pubDate>
        <enclosure url="{audio_url}" length="{audio_file_size}" type="audio/mpeg"/>
        <itunes:episodeType>full</itunes:episodeType>
        <itunes:episode>{episode_number}</itunes:episode>
        <itunes:duration>{duration_str}</itunes:duration>
        <itunes:explicit>no</itunes:explicit>
    </item>"""

        return rss_item

    def create_episode_metadata(
        self, episode_number: int, summary: str, duration_seconds: int
    ) -> Dict[str, Any]:
        """
        Create episode metadata for RSS feed.

        Args:
            episode_number: Episode number
            summary: Episode summary
            duration_seconds: Episode duration

        Returns:
            Dictionary with episode metadata
        """
        return {
            "title": f"{Config.PODCAST_NAME} - Episode {episode_number}",
            "description": summary,
            "episode_number": episode_number,
            "season_number": 1,
            "episode_type": "full",
            "explicit": False,
            "duration_seconds": duration_seconds,
            "language": "en",
        }

    def update_rss_feed(
        self,
        episode_number: int,
        episode_title: str,
        episode_description: str,
        audio_url: str,
        audio_file_size: int,
        duration_seconds: int,
        pub_date: Optional[datetime] = None,
        keywords: Optional[List[str]] = None,
        chapters_url: Optional[str] = None,
    ) -> Path:
        """
        Update RSS feed with new episode.

        Args:
            episode_number: Episode number
            episode_title: Episode title
            episode_description: Episode description
            audio_url: Public URL to audio file (Dropbox, etc.)
            audio_file_size: File size in bytes
            duration_seconds: Episode duration in seconds
            pub_date: Publication date (default: now)
            keywords: List of keywords/tags
            chapters_url: Public URL to Podcasting 2.0 chapters JSON (optional)

        Returns:
            Path to updated RSS feed file
        """
        logger.info("Updating RSS feed...")

        # Load or create podcast metadata
        metadata = self.rss_generator.load_podcast_metadata()

        if not metadata:
            logger.info("No podcast metadata found, using defaults")
            metadata = {
                "title": Config.PODCAST_NAME,
                "description": "A podcast about fake problems",
                "author": "Podcast Host",
                "website_url": "",
                "email": "podcast@example.com",
                "categories": ["Comedy"],
                "language": "en-us",
                "artwork_url": None,
                "explicit": False,
            }

        # Episode data
        episode_data = {
            "episode_number": episode_number,
            "title": episode_title,
            "description": episode_description,
            "audio_url": audio_url,
            "audio_file_size": audio_file_size,
            "duration_seconds": duration_seconds,
            "pub_date": pub_date or datetime.now(),
            "keywords": keywords,
            "chapters_url": chapters_url,
        }

        # Update feed
        rss = self.rss_generator.update_or_create_feed(
            episode_data=episode_data, podcast_metadata=metadata
        )

        # Save feed
        self.rss_generator.save_feed(rss)

        # Save metadata for future use
        self.rss_generator.save_podcast_metadata(metadata)

        logger.info("RSS feed updated: %s", self.rss_generator.feed_path)
        return self.rss_generator.feed_path

    def setup_podcast_metadata(
        self,
        title: str,
        description: str,
        author: str,
        email: str,
        website_url: str,
        categories: List[str],
        artwork_url: Optional[str] = None,
        explicit: bool = False,
    ):
        """
        Set up podcast metadata for RSS feed generation.

        Args:
            title: Podcast title
            description: Podcast description
            author: Author/Host name
            email: Contact email
            website_url: Podcast website URL
            categories: List of categories (e.g., ["Comedy", "Society & Culture"])
            artwork_url: URL to podcast artwork (1400x1400 to 3000x3000 px)
            explicit: Whether podcast contains explicit content
        """
        metadata = {
            "title": title,
            "description": description,
            "author": author,
            "email": email,
            "website_url": website_url,
            "categories": categories,
            "language": "en-us",
            "artwork_url": artwork_url,
            "explicit": explicit,
        }

        self.rss_generator.save_podcast_metadata(metadata)
        logger.info("Podcast metadata saved")
        logger.info("Metadata saved to: %s", self.rss_generator.metadata_path)

    def validate_rss_feed(self) -> Dict[str, Any]:
        """
        Validate the current RSS feed.

        Returns:
            Validation results dictionary
        """
        return self.rss_generator.validate_feed()

    def generate_podcast_rss_feed(
        self,
        episodes_data: list,
        podcast_title: str,
        podcast_description: str,
        podcast_author: str,
        podcast_email: str,
        podcast_category: str = "Comedy",
        podcast_image_url: Optional[str] = None,
        podcast_website: Optional[str] = None,
    ) -> str:
        """
        Generate a complete RSS feed for the podcast.

        Args:
            episodes_data: List of episode data dictionaries
            podcast_title: Podcast title
            podcast_description: Podcast description
            podcast_author: Podcast author/host name
            podcast_email: Contact email
            podcast_category: iTunes category
            podcast_image_url: URL to podcast artwork (min 1400x1400)
            podcast_website: Podcast website URL

        Returns:
            Complete RSS feed XML as string
        """
        rss_header = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:content="http://purl.org/rss/1.0/modules/content/">
    <channel>
        <title>{podcast_title}</title>
        <description>{podcast_description}</description>
        <link>{podcast_website or ""}</link>
        <language>en-us</language>
        <copyright>Copyright {datetime.now().year} {podcast_author}</copyright>
        <itunes:author>{podcast_author}</itunes:author>
        <itunes:summary>{podcast_description}</itunes:summary>
        <itunes:owner>
            <itunes:name>{podcast_author}</itunes:name>
            <itunes:email>{podcast_email}</itunes:email>
        </itunes:owner>
        <itunes:explicit>no</itunes:explicit>
        <itunes:category text="{podcast_category}"/>"""

        if podcast_image_url:
            rss_header += f"""
        <itunes:image href="{podcast_image_url}"/>
        <image>
            <url>{podcast_image_url}</url>
            <title>{podcast_title}</title>
            <link>{podcast_website or ""}</link>
        </image>"""

        rss_header += "\n"

        # Add episodes
        rss_items = ""
        for ep_data in episodes_data:
            rss_items += self.generate_rss_item(**ep_data)

        rss_footer = """
    </channel>
</rss>"""

        return rss_header + rss_items + rss_footer


def create_spotify_episode_data(
    episode_number: int,
    episode_summary: str,
    audio_url: str,
    audio_file_path: str,
    duration_seconds: int,
) -> Dict[str, Any]:
    """
    Create episode data for RSS feed generation.

    Args:
        episode_number: Episode number
        episode_summary: Episode summary
        audio_url: Public URL to audio file
        audio_file_path: Local path to audio file (for size)
        duration_seconds: Episode duration

    Returns:
        Dictionary with episode data for RSS generation
    """
    audio_path = Path(audio_file_path)
    file_size = audio_path.stat().st_size if audio_path.exists() else 0

    return {
        "episode_number": episode_number,
        "title": f"{Config.PODCAST_NAME} - Episode {episode_number}",
        "description": episode_summary,
        "audio_url": audio_url,
        "audio_file_size": file_size,
        "duration_seconds": duration_seconds,
        "pub_date": datetime.now(),
    }
