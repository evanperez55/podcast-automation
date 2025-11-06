"""Test script for RSS feed generation."""

from rss_feed_generator import RSSFeedGenerator
from pathlib import Path
from datetime import datetime

print("="*60)
print("TESTING RSS FEED GENERATOR")
print("="*60)
print()

try:
    # Initialize generator
    print("[1/4] Initializing RSS feed generator...")
    generator = RSSFeedGenerator()
    print("[OK] Generator initialized")
    print()

    # Create sample podcast metadata
    print("[2/4] Creating sample RSS feed...")
    podcast_metadata = {
        'title': 'Test Podcast',
        'description': 'A test podcast for RSS feed generation',
        'author': 'Test Author',
        'email': 'test@example.com',
        'website_url': 'https://example.com',
        'categories': ['Comedy', 'Technology'],
        'language': 'en-us',
        'artwork_url': None,
        'explicit': False
    }

    # Create sample episode
    episode_data = {
        'episode_number': 1,
        'title': 'Test Episode 1',
        'description': 'This is a test episode to verify RSS feed generation works correctly.',
        'audio_url': 'https://example.com/test_episode_1.mp3',
        'audio_file_size': 10000000,  # 10 MB
        'duration_seconds': 3600,  # 1 hour
        'pub_date': datetime.now(),
        'keywords': ['test', 'podcast', 'rss']
    }

    # Generate feed
    rss = generator.update_or_create_feed(
        episode_data=episode_data,
        podcast_metadata=podcast_metadata
    )

    print("[OK] RSS feed structure created")
    print()

    # Save feed
    print("[3/4] Saving RSS feed to file...")
    test_feed_path = Path('output/test_podcast_feed.xml')
    generator.save_feed(rss, test_feed_path)
    print()

    # Validate feed
    print("[4/4] Validating RSS feed...")
    validation = generator.validate_feed(test_feed_path)

    if validation['valid']:
        print("[OK] RSS feed is valid!")
        print(f"[OK] Episodes in feed: {validation['episode_count']}")
    else:
        print("[WARNING] RSS feed has validation warnings:")
        for warning in validation['warnings']:
            print(f"  - {warning}")

    print()
    print("="*60)
    print("SUCCESS! RSS feed generation is working!")
    print("="*60)
    print()
    print(f"Test feed saved to: {test_feed_path}")
    print()
    print("You can:")
    print("1. Open the file to see the XML structure")
    print("2. Validate at https://podba.se/validate/")
    print("3. Run 'python setup_rss_metadata.py' to configure your podcast")
    print("4. Run 'python main.py ep25' to generate your real RSS feed")
    print()

except Exception as e:
    print()
    print("[ERROR] RSS feed generation failed:")
    print(f"  {e}")
    import traceback
    traceback.print_exc()
    print()
