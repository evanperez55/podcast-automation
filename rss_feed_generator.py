"""RSS feed generator for podcast distribution."""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

from config import Config


class RSSFeedGenerator:
    """Generate and maintain podcast RSS feed for Spotify, Apple Podcasts, etc."""

    def __init__(self, feed_path: Optional[str] = None):
        """
        Initialize RSS feed generator.

        Args:
            feed_path: Path to RSS feed XML file (defaults to output/podcast_feed.xml)
        """
        if feed_path:
            self.feed_path = Path(feed_path)
        else:
            self.feed_path = Config.OUTPUT_DIR / 'podcast_feed.xml'

        self.metadata_path = Config.OUTPUT_DIR / 'podcast_metadata.json'

    def create_feed(
        self,
        title: str,
        description: str,
        website_url: str,
        author: str,
        email: str,
        categories: List[str],
        language: str = "en-us",
        artwork_url: Optional[str] = None,
        explicit: bool = False
    ) -> ET.Element:
        """
        Create new RSS feed structure.

        Args:
            title: Podcast title
            description: Podcast description
            website_url: Podcast website URL
            author: Author/Host name
            email: Contact email
            categories: List of categories (e.g., ["Comedy", "Society & Culture"])
            language: Feed language (default: en-us)
            artwork_url: URL to podcast artwork (1400x1400 to 3000x3000 px)
            explicit: Whether podcast contains explicit content

        Returns:
            RSS feed root element
        """
        # Create RSS root
        rss = ET.Element('rss', {
            'version': '2.0',
            'xmlns:itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
            'xmlns:content': 'http://purl.org/rss/1.0/modules/content/',
            'xmlns:atom': 'http://www.w3.org/2005/Atom'
        })

        # Create channel
        channel = ET.SubElement(rss, 'channel')

        # Basic metadata
        ET.SubElement(channel, 'title').text = title
        ET.SubElement(channel, 'description').text = description
        ET.SubElement(channel, 'link').text = website_url
        ET.SubElement(channel, 'language').text = language
        ET.SubElement(channel, 'copyright').text = f"Copyright {datetime.now().year} {author}"

        # iTunes-specific tags
        ET.SubElement(channel, 'itunes:author').text = author
        ET.SubElement(channel, 'itunes:summary').text = description
        ET.SubElement(channel, 'itunes:explicit').text = 'yes' if explicit else 'no'

        # Owner
        owner = ET.SubElement(channel, 'itunes:owner')
        ET.SubElement(owner, 'itunes:name').text = author
        ET.SubElement(owner, 'itunes:email').text = email

        # Artwork
        if artwork_url:
            ET.SubElement(channel, 'itunes:image', {'href': artwork_url})
            image = ET.SubElement(channel, 'image')
            ET.SubElement(image, 'url').text = artwork_url
            ET.SubElement(image, 'title').text = title
            ET.SubElement(image, 'link').text = website_url

        # Categories
        for category in categories:
            ET.SubElement(channel, 'itunes:category', {'text': category})

        return rss

    def add_episode(
        self,
        rss: ET.Element,
        episode_number: int,
        title: str,
        description: str,
        audio_url: str,
        audio_file_size: int,
        duration_seconds: int,
        pub_date: datetime,
        episode_type: str = "full",
        season_number: Optional[int] = None,
        explicit: bool = False,
        keywords: Optional[List[str]] = None
    ) -> ET.Element:
        """
        Add episode to RSS feed.

        Args:
            rss: RSS feed root element
            episode_number: Episode number
            title: Episode title
            description: Episode description
            audio_url: Public URL to audio file (MP3)
            audio_file_size: File size in bytes
            duration_seconds: Episode duration in seconds
            pub_date: Publication date
            episode_type: "full", "trailer", or "bonus"
            season_number: Season number (optional)
            explicit: Whether episode contains explicit content
            keywords: List of keywords/tags

        Returns:
            Created item element
        """
        channel = rss.find('channel')

        # Create item (episode)
        item = ET.SubElement(channel, 'item')

        # Basic metadata
        ET.SubElement(item, 'title').text = title
        ET.SubElement(item, 'description').text = description
        ET.SubElement(item, 'itunes:summary').text = description

        # Episode details
        ET.SubElement(item, 'itunes:episode').text = str(episode_number)
        if season_number:
            ET.SubElement(item, 'itunes:season').text = str(season_number)
        ET.SubElement(item, 'itunes:episodeType').text = episode_type
        ET.SubElement(item, 'itunes:explicit').text = 'yes' if explicit else 'no'

        # Duration (format: HH:MM:SS or MM:SS)
        hours = duration_seconds // 3600
        minutes = (duration_seconds % 3600) // 60
        seconds = duration_seconds % 60
        if hours > 0:
            duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            duration_str = f"{minutes:02d}:{seconds:02d}"
        ET.SubElement(item, 'itunes:duration').text = duration_str

        # Audio enclosure
        ET.SubElement(item, 'enclosure', {
            'url': audio_url,
            'length': str(audio_file_size),
            'type': 'audio/mpeg'
        })

        # Publication date (RFC 822 format)
        pub_date_str = pub_date.strftime('%a, %d %b %Y %H:%M:%S %z')
        if not pub_date_str.endswith(('+0000', '-0000')):
            # Add timezone if not present
            pub_date_str = pub_date.strftime('%a, %d %b %Y %H:%M:%S +0000')
        ET.SubElement(item, 'pubDate').text = pub_date_str

        # GUID (unique identifier)
        guid = f"episode-{episode_number}"
        ET.SubElement(item, 'guid', {'isPermaLink': 'false'}).text = guid

        # Keywords
        if keywords:
            ET.SubElement(item, 'itunes:keywords').text = ', '.join(keywords)

        return item

    def save_feed(self, rss: ET.Element, output_path: Optional[Path] = None):
        """
        Save RSS feed to file with pretty formatting.

        Args:
            rss: RSS feed root element
            output_path: Output file path (defaults to self.feed_path)
        """
        if output_path is None:
            output_path = self.feed_path

        # Convert to string with pretty formatting
        rough_string = ET.tostring(rss, encoding='utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ", encoding='utf-8')

        # Write to file
        with open(output_path, 'wb') as f:
            f.write(pretty_xml)

        print(f"[OK] RSS feed saved to: {output_path}")

    def load_feed(self, feed_path: Optional[Path] = None) -> Optional[ET.Element]:
        """
        Load existing RSS feed from file.

        Args:
            feed_path: Path to RSS feed file (defaults to self.feed_path)

        Returns:
            RSS feed root element, or None if file doesn't exist
        """
        if feed_path is None:
            feed_path = self.feed_path

        if not feed_path.exists():
            return None

        tree = ET.parse(feed_path)
        return tree.getroot()

    def update_or_create_feed(
        self,
        episode_data: Dict[str, Any],
        podcast_metadata: Dict[str, Any]
    ) -> ET.Element:
        """
        Update existing feed or create new one with episode.

        Args:
            episode_data: Episode information (number, title, description, etc.)
            podcast_metadata: Podcast-level metadata (title, author, etc.)

        Returns:
            Updated RSS feed element
        """
        # Load existing feed or create new one
        rss = self.load_feed()

        if rss is None:
            print("[INFO] Creating new RSS feed...")
            rss = self.create_feed(
                title=podcast_metadata.get('title', 'My Podcast'),
                description=podcast_metadata.get('description', ''),
                website_url=podcast_metadata.get('website_url', ''),
                author=podcast_metadata.get('author', ''),
                email=podcast_metadata.get('email', ''),
                categories=podcast_metadata.get('categories', ['Comedy']),
                language=podcast_metadata.get('language', 'en-us'),
                artwork_url=podcast_metadata.get('artwork_url'),
                explicit=podcast_metadata.get('explicit', False)
            )
            print("[OK] New RSS feed created")
        else:
            print("[INFO] Updating existing RSS feed...")

        # Check if episode already exists
        channel = rss.find('channel')
        existing_episodes = {}
        for item in channel.findall('item'):
            ep_num_elem = item.find('.//{http://www.itunes.com/dtds/podcast-1.0.dtd}episode')
            if ep_num_elem is not None:
                existing_episodes[int(ep_num_elem.text)] = item

        episode_number = episode_data.get('episode_number')

        # Remove existing episode if present (we'll re-add with updated info)
        if episode_number in existing_episodes:
            print(f"[INFO] Updating existing Episode {episode_number}")
            channel.remove(existing_episodes[episode_number])
        else:
            print(f"[INFO] Adding new Episode {episode_number}")

        # Add episode
        self.add_episode(
            rss=rss,
            episode_number=episode_number,
            title=episode_data.get('title', f"Episode {episode_number}"),
            description=episode_data.get('description', ''),
            audio_url=episode_data.get('audio_url'),
            audio_file_size=episode_data.get('audio_file_size'),
            duration_seconds=episode_data.get('duration_seconds'),
            pub_date=episode_data.get('pub_date', datetime.now()),
            episode_type=episode_data.get('episode_type', 'full'),
            season_number=episode_data.get('season_number'),
            explicit=episode_data.get('explicit', podcast_metadata.get('explicit', False)),
            keywords=episode_data.get('keywords')
        )

        return rss

    def save_podcast_metadata(self, metadata: Dict[str, Any]):
        """
        Save podcast metadata to JSON file for future use.

        Args:
            metadata: Podcast metadata dictionary
        """
        with open(self.metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"[OK] Podcast metadata saved to: {self.metadata_path}")

    def load_podcast_metadata(self) -> Dict[str, Any]:
        """
        Load podcast metadata from JSON file.

        Returns:
            Podcast metadata dictionary, or empty dict if file doesn't exist
        """
        if not self.metadata_path.exists():
            return {}

        with open(self.metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_episode_count(self, feed_path: Optional[Path] = None) -> int:
        """
        Get number of episodes in feed.

        Args:
            feed_path: Path to RSS feed file (defaults to self.feed_path)

        Returns:
            Number of episodes
        """
        rss = self.load_feed(feed_path)
        if rss is None:
            return 0

        channel = rss.find('channel')
        return len(channel.findall('item'))

    def validate_feed(self, feed_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Validate RSS feed and return validation results.

        Args:
            feed_path: Path to RSS feed file (defaults to self.feed_path)

        Returns:
            Dictionary with validation results
        """
        if feed_path is None:
            feed_path = self.feed_path

        if not feed_path.exists():
            return {
                'valid': False,
                'error': 'Feed file does not exist',
                'warnings': []
            }

        warnings = []
        rss = self.load_feed(feed_path)
        channel = rss.find('channel')

        # Check required elements
        required = ['title', 'description', 'link']
        for elem in required:
            if channel.find(elem) is None:
                warnings.append(f"Missing required element: {elem}")

        # Check iTunes required elements
        itunes_required = [
            '{http://www.itunes.com/dtds/podcast-1.0.dtd}author',
            '{http://www.itunes.com/dtds/podcast-1.0.dtd}image'
        ]
        for elem in itunes_required:
            if channel.find(elem) is None:
                warnings.append(f"Missing iTunes element: {elem}")

        # Check episodes
        items = channel.findall('item')
        if len(items) == 0:
            warnings.append("No episodes in feed")

        return {
            'valid': len(warnings) == 0,
            'warnings': warnings,
            'episode_count': len(items),
            'feed_path': str(feed_path)
        }


def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to HH:MM:SS or MM:SS string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"
