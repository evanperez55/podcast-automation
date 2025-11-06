"""One-time setup script for RSS feed metadata."""

from uploaders.spotify_uploader import SpotifyUploader

print("="*60)
print("RSS FEED METADATA SETUP")
print("="*60)
print()
print("This script configures your podcast information for the RSS feed.")
print("You only need to run this once.")
print()

# Get podcast information
print("Enter your podcast information:")
print()

title = input("Podcast Title: ").strip() or "Fake Problems Podcast"
description = input("Podcast Description: ").strip() or "A podcast about fake problems"
author = input("Author/Host Name(s): ").strip() or "Podcast Host"
email = input("Contact Email: ").strip() or "podcast@example.com"
website_url = input("Website URL (or social media link): ").strip() or ""

print()
print("Categories (choose from: Comedy, Society & Culture, News, Technology, etc.)")
categories_input = input("Categories (comma-separated): ").strip()
if categories_input:
    categories = [c.strip() for c in categories_input.split(",")]
else:
    categories = ["Comedy"]

print()
explicit_input = input("Contains explicit content? (yes/no): ").strip().lower()
explicit = explicit_input in ['yes', 'y', 'true']

print()
artwork_url = input("Podcast logo URL (leave blank for now if you don't have it): ").strip() or None

print()
print("-"*60)
print("Summary of your podcast information:")
print("-"*60)
print(f"Title: {title}")
print(f"Description: {description}")
print(f"Author: {author}")
print(f"Email: {email}")
print(f"Website: {website_url}")
print(f"Categories: {', '.join(categories)}")
print(f"Explicit: {'Yes' if explicit else 'No'}")
print(f"Artwork URL: {artwork_url or '(not set yet)'}")
print()

confirm = input("Save this information? (yes/no): ").strip().lower()

if confirm in ['yes', 'y']:
    # Initialize Spotify uploader
    try:
        uploader = SpotifyUploader()

        # Configure metadata
        uploader.setup_podcast_metadata(
            title=title,
            description=description,
            author=author,
            email=email,
            website_url=website_url,
            categories=categories,
            artwork_url=artwork_url,
            explicit=explicit
        )

        print()
        print("="*60)
        print("SUCCESS! Podcast metadata saved!")
        print("="*60)
        print()
        print("Next steps:")
        print("1. If you haven't set artwork URL yet:")
        print("   - Upload your podcast logo to Dropbox")
        print("   - Get a shared link (replace ?dl=0 with ?dl=1)")
        print("   - Update output/podcast_metadata.json with the URL")
        print()
        print("2. Run your automation to generate the RSS feed:")
        print("   python main.py ep25")
        print()
        print("3. See RSS_FEED_SETUP.md for complete instructions")
        print()

    except Exception as e:
        print()
        print(f"[ERROR] Failed to save metadata: {e}")
        print()
        print("Make sure Spotify credentials are configured in .env file")
else:
    print()
    print("Setup cancelled. Run this script again when ready.")
    print()
