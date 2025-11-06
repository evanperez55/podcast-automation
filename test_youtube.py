"""Quick test script for YouTube API authentication."""

from uploaders.youtube_uploader import YouTubeUploader

print("=" * 60)
print("TESTING YOUTUBE CONNECTION")
print("=" * 60)
print()

try:
    print("[1/2] Initializing YouTube uploader...")
    print()
    print("IMPORTANT: A browser window will open for authorization!")
    print("1. Sign in to your Google account (if needed)")
    print("2. Click 'Continue' if you see a warning about unverified app")
    print("   (This is normal - it's YOUR app)")
    print("3. Grant permissions to upload videos")
    print("4. The browser will show 'authentication successful'")
    print()
    input("Press ENTER when ready to start authentication...")
    print()

    # This will open a browser for OAuth
    uploader = YouTubeUploader()

    print()
    print("[OK] YouTube uploader initialized successfully!")
    print("[OK] Authentication token saved!")
    print()

    # Get quota info
    print("[2/2] Checking API quota information...")
    quota_info = uploader.get_upload_quota_usage()

    print("[OK] YouTube API is connected and ready!")
    print()
    print("Quota Information:")
    print(f"  Daily Limit: {quota_info['daily_limit']:,} units")
    print(f"  Upload Cost: {quota_info['upload_cost']:,} units per video")
    print(f"  Estimated uploads/day: ~{quota_info['daily_limit'] // quota_info['upload_cost']}")
    print()
    print("=" * 60)
    print("SUCCESS! YouTube is configured!")
    print("=" * 60)
    print()
    print("Your automation can now:")
    print("  - Upload full episodes to YouTube")
    print("  - Upload clips as YouTube Shorts")
    print("  - Set custom thumbnails")
    print("  - Add descriptions and tags")
    print()

except FileNotFoundError as e:
    print("[ERROR] Credentials file not found!")
    print(f"  {e}")
    print()
    print("Make sure youtube_credentials.json is in the credentials/ folder")

except Exception as e:
    print("[ERROR]:")
    print(f"  {e}")
    print()
    print("This might mean:")
    print("  1. You cancelled the authentication")
    print("  2. Wrong Google account was used")
    print("  3. Permissions weren't granted")
    print()
    print("You can run this script again to retry!")

print()
print("=" * 60)
