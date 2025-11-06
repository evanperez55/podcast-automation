"""Quick test script for Spotify API credentials."""

from uploaders.spotify_uploader import SpotifyUploader

print("=" * 60)
print("TESTING SPOTIFY CONNECTION")
print("=" * 60)
print()

try:
    # Initialize Spotify uploader
    print("[1/3] Initializing Spotify uploader...")
    uploader = SpotifyUploader()
    print("[OK] Spotify uploader initialized successfully!")
    print()

    # Get show info
    print("[2/3] Fetching your podcast show info...")
    show_info = uploader.get_show_info()

    if show_info:
        print("[OK] Successfully connected to Spotify!")
        print()
        print("Podcast Show Information:")
        print(f"  Name: {show_info['name']}")
        print(f"  Publisher: {show_info['publisher']}")
        print(f"  Total Episodes: {show_info['total_episodes']}")
        print(f"  URL: {show_info['url']}")
        print()

        # Get recent episodes
        print("[3/3] Fetching recent episodes...")
        episodes = uploader.get_episodes(limit=5)

        if episodes:
            print(f"[OK] Found {len(episodes)} recent episodes:")
            print()
            for i, ep in enumerate(episodes, 1):
                print(f"  {i}. {ep['name']}")
                print(f"     Released: {ep['release_date']}")
                duration_min = ep['duration_ms'] // 60000
                print(f"     Duration: {duration_min} minutes")
                print()
        else:
            print("[INFO] No episodes found")
    else:
        print("[ERROR] Failed to get show info")
        print("Check your SPOTIFY_SHOW_ID in .env file")

    print("=" * 60)
    print("SUCCESS! Spotify is configured!")
    print("=" * 60)
    print()
    print("Your automation can now:")
    print("  - Get show information and analytics")
    print("  - Fetch episode details")
    print("  - Generate RSS feed entries")
    print()
    print("NOTE: For episode uploads, use Spotify for Podcasters:")
    print("  https://podcasters.spotify.com")
    print()

except ValueError as e:
    print("[ERROR] Configuration Error:")
    print(f"  {e}")
    print()
    print("Make sure all three Spotify credentials are set in .env:")
    print("  - SPOTIFY_CLIENT_ID")
    print("  - SPOTIFY_CLIENT_SECRET")
    print("  - SPOTIFY_SHOW_ID")

except Exception as e:
    print("[ERROR]:")
    print(f"  {e}")
    print()
    print("This might mean:")
    print("  1. Credentials are incorrect")
    print("  2. Show ID is wrong")
    print("  3. App doesn't have correct permissions")

print()
print("=" * 60)
