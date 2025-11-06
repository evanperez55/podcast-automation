"""Spotify uploader for podcast episodes."""

import requests
import base64
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from config import Config
from rss_feed_generator import RSSFeedGenerator


class SpotifyUploader:
    """
    Handle Spotify podcast uploads.

    Note: Spotify for Podcasters primarily uses RSS feeds for podcast distribution.
    This module provides helper functions for managing podcast metadata and
    generating RSS feed entries.

    For direct uploads, you'll need to use Spotify for Podcasters dashboard:
    https://podcasters.spotify.com
    """

    # Spotify API base URLs
    API_BASE = "https://api.spotify.com/v1"
    ACCOUNTS_BASE = "https://accounts.spotify.com/api"

    def __init__(self):
        """Initialize Spotify uploader."""
        self.client_id = Config.SPOTIFY_CLIENT_ID
        self.client_secret = Config.SPOTIFY_CLIENT_SECRET
        self.show_id = Config.SPOTIFY_SHOW_ID
        self.access_token = None

        # Initialize RSS feed generator
        self.rss_generator = RSSFeedGenerator()

        if not self.client_id or self.client_id == 'your_spotify_client_id_here':
            raise ValueError(
                "Spotify client ID not configured in .env file.\n"
                "Please follow the setup instructions:\n"
                "1. Go to https://developer.spotify.com/dashboard\n"
                "2. Create an app and get client credentials\n"
                "3. Add SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET to .env\n"
                "4. Add your show's SPOTIFY_SHOW_ID to .env\n\n"
                "Note: Spotify podcasts are typically managed via RSS feeds.\n"
                "For episode uploads, use Spotify for Podcasters:\n"
                "https://podcasters.spotify.com"
            )

        # Authenticate
        self._authenticate()

    def _authenticate(self):
        """Authenticate with Spotify API using Client Credentials flow."""
        print("[INFO] Authenticating with Spotify API...")

        # Encode credentials
        auth_str = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_str.encode('utf-8')
        auth_base64 = base64.b64encode(auth_bytes).decode('utf-8')

        # Request access token
        headers = {
            'Authorization': f'Basic {auth_base64}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        data = {
            'grant_type': 'client_credentials'
        }

        try:
            response = requests.post(
                'https://accounts.spotify.com/api/token',
                headers=headers,
                data=data
            )
            response.raise_for_status()
            token_data = response.json()

            self.access_token = token_data.get('access_token')
            print("[OK] Spotify authentication successful")

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Spotify authentication failed: {e}")
            raise

    def get_show_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the podcast show.

        Returns:
            Dictionary with show information
        """
        if not self.show_id or self.show_id == 'your_show_id_here':
            print("[WARNING] Spotify show ID not configured")
            return None

        endpoint = f"{self.API_BASE}/shows/{self.show_id}"
        headers = {
            'Authorization': f'Bearer {self.access_token}'
        }

        try:
            response = requests.get(endpoint, headers=headers)
            response.raise_for_status()
            show_data = response.json()

            return {
                'id': show_data.get('id'),
                'name': show_data.get('name'),
                'publisher': show_data.get('publisher'),
                'description': show_data.get('description'),
                'total_episodes': show_data.get('total_episodes'),
                'url': show_data.get('external_urls', {}).get('spotify')
            }

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to get show info: {e}")
            return None

    def get_episodes(self, limit: int = 20) -> Optional[list]:
        """
        Get episodes from the podcast show.

        Args:
            limit: Number of episodes to retrieve (max 50)

        Returns:
            List of episode dictionaries
        """
        if not self.show_id or self.show_id == 'your_show_id_here':
            print("[WARNING] Spotify show ID not configured")
            return None

        endpoint = f"{self.API_BASE}/shows/{self.show_id}/episodes"
        headers = {
            'Authorization': f'Bearer {self.access_token}'
        }
        params = {
            'limit': min(limit, 50)
        }

        try:
            response = requests.get(endpoint, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            episodes = []
            for ep in data.get('items', []):
                episodes.append({
                    'id': ep.get('id'),
                    'name': ep.get('name'),
                    'description': ep.get('description'),
                    'release_date': ep.get('release_date'),
                    'duration_ms': ep.get('duration_ms'),
                    'url': ep.get('external_urls', {}).get('spotify')
                })

            return episodes

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to get episodes: {e}")
            return None

    def generate_rss_item(
        self,
        episode_number: int,
        title: str,
        description: str,
        audio_url: str,
        audio_file_size: int,
        duration_seconds: int,
        pub_date: Optional[datetime] = None
    ) -> str:
        """
        Generate an RSS feed item for a podcast episode.

        This can be added to your podcast's RSS feed for distribution to Spotify
        and other podcast platforms.

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
        if not pub_date_str.endswith(('+0000', '-0000')):
            pub_date_str += ' +0000'

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
        self,
        episode_number: int,
        summary: str,
        duration_seconds: int
    ) -> Dict[str, Any]:
        """
        Create episode metadata for Spotify upload.

        Args:
            episode_number: Episode number
            summary: Episode summary
            duration_seconds: Episode duration

        Returns:
            Dictionary with episode metadata
        """
        return {
            'title': f"{Config.PODCAST_NAME} - Episode {episode_number}",
            'description': summary,
            'episode_number': episode_number,
            'season_number': 1,  # Adjust as needed
            'episode_type': 'full',  # 'full', 'trailer', or 'bonus'
            'explicit': False,
            'duration_seconds': duration_seconds,
            'language': 'en'
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
        keywords: Optional[List[str]] = None
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

        Returns:
            Path to updated RSS feed file
        """
        print("[INFO] Updating RSS feed...")

        # Load or create podcast metadata
        metadata = self.rss_generator.load_podcast_metadata()

        if not metadata:
            print("[INFO] No podcast metadata found, using defaults")
            # Try to get show info from Spotify
            show_info = self.get_show_info()
            if show_info:
                metadata = {
                    'title': show_info.get('name', Config.PODCAST_NAME),
                    'description': show_info.get('description', ''),
                    'author': show_info.get('publisher', ''),
                    'website_url': show_info.get('url', ''),
                    'email': '',  # Need to set this
                    'categories': ['Comedy'],  # Default, can be changed
                    'language': 'en-us',
                    'artwork_url': show_info.get('images', [{}])[0].get('url'),
                    'explicit': show_info.get('explicit', False)
                }
            else:
                # Use config defaults
                metadata = {
                    'title': Config.PODCAST_NAME,
                    'description': 'A podcast about fake problems',
                    'author': 'Podcast Host',
                    'website_url': '',
                    'email': 'podcast@example.com',
                    'categories': ['Comedy'],
                    'language': 'en-us',
                    'artwork_url': None,
                    'explicit': False
                }

        # Episode data
        episode_data = {
            'episode_number': episode_number,
            'title': episode_title,
            'description': episode_description,
            'audio_url': audio_url,
            'audio_file_size': audio_file_size,
            'duration_seconds': duration_seconds,
            'pub_date': pub_date or datetime.now(),
            'keywords': keywords
        }

        # Update feed
        rss = self.rss_generator.update_or_create_feed(
            episode_data=episode_data,
            podcast_metadata=metadata
        )

        # Save feed
        self.rss_generator.save_feed(rss)

        # Save metadata for future use
        self.rss_generator.save_podcast_metadata(metadata)

        print(f"[OK] RSS feed updated: {self.rss_generator.feed_path}")
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
        explicit: bool = False
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
            'title': title,
            'description': description,
            'author': author,
            'email': email,
            'website_url': website_url,
            'categories': categories,
            'language': 'en-us',
            'artwork_url': artwork_url,
            'explicit': explicit
        }

        self.rss_generator.save_podcast_metadata(metadata)
        print("[OK] Podcast metadata saved")
        print(f"[INFO] Metadata saved to: {self.rss_generator.metadata_path}")

    def validate_rss_feed(self) -> Dict[str, Any]:
        """
        Validate the current RSS feed.

        Returns:
            Validation results dictionary
        """
        return self.rss_generator.validate_feed()

    def get_episode_analytics(self, episode_id: str) -> Optional[Dict[str, Any]]:
        """
        Get analytics for a specific episode.

        Note: This requires special Spotify for Podcasters API access.

        Args:
            episode_id: Spotify episode ID

        Returns:
            Dictionary with analytics data (if available)
        """
        print("[INFO] Episode analytics require Spotify for Podcasters API access")
        print("[INFO] Visit https://podcasters.spotify.com for analytics")

        # Placeholder for future analytics integration
        return {
            'note': 'Analytics available via Spotify for Podcasters dashboard',
            'url': f'https://podcasters.spotify.com/pod/show/{self.show_id}/episodes/{episode_id}'
        }

    def generate_podcast_rss_feed(
        self,
        episodes_data: list,
        podcast_title: str,
        podcast_description: str,
        podcast_author: str,
        podcast_email: str,
        podcast_category: str = "Comedy",
        podcast_image_url: Optional[str] = None,
        podcast_website: Optional[str] = None
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
        <link>{podcast_website or ''}</link>
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
            <link>{podcast_website or ''}</link>
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
    duration_seconds: int
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
        'episode_number': episode_number,
        'title': f"{Config.PODCAST_NAME} - Episode {episode_number}",
        'description': episode_summary,
        'audio_url': audio_url,
        'audio_file_size': file_size,
        'duration_seconds': duration_seconds,
        'pub_date': datetime.now()
    }
