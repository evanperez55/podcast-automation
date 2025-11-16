"""Re-authenticate YouTube OAuth credentials."""

import os
from pathlib import Path

print("\n" + "="*60)
print("YOUTUBE OAUTH AUTHENTICATION")
print("="*60)
print()
print("About Google OAuth tokens:")
print("- Access tokens expire after 1 hour")
print("- Refresh tokens last indefinitely (until revoked)")
print("- This script will get a NEW refresh token")
print("- Future runs will auto-refresh without manual intervention")
print()
print("This will open a browser window for you to authorize the app.")
print("Make sure you're signed into the Google account associated with")
print("your YouTube channel.")
print()

# Delete expired token
token_path = Path("credentials/youtube_token.pickle")
if token_path.exists():
    print(f"[INFO] Deleting expired token: {token_path}")
    token_path.unlink()
    print()

input("Press Enter to continue...")
print()

# Initialize uploader (will trigger OAuth flow)
from uploaders import YouTubeUploader

try:
    uploader = YouTubeUploader()
    print()
    print("="*60)
    print("[SUCCESS] YouTube authentication complete!")
    print("="*60)
    print()
    print("Your credentials are saved and will be used for future uploads.")
    print("You can now run the automation with YouTube uploads enabled.")
except Exception as e:
    print()
    print("="*60)
    print("[ERROR] Authentication failed")
    print("="*60)
    print()
    print(f"Error: {e}")
    print()
    print("Troubleshooting:")
    print("1. Make sure credentials/youtube_credentials.json exists")
    print("2. Ensure you're signing in with the correct Google account")
    print("3. Check that the YouTube Data API v3 is enabled in Google Cloud")
