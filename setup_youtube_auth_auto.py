"""Automatically re-authenticate YouTube OAuth credentials."""

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

# Delete expired token
token_path = Path("credentials/youtube_token.pickle")
if token_path.exists():
    print(f"[INFO] Deleting expired token: {token_path}")
    token_path.unlink()
    print()

print("[INFO] Starting OAuth flow...")
print("[INFO] A browser window will open for authorization")
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
    print("The system will automatically refresh tokens as needed.")
    print("You should NOT need to re-authenticate unless:")
    print("  - You revoke access in Google account settings")
    print("  - You don't use the automation for 6+ months")
    print()
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
    print("4. If browser doesn't open, check your firewall settings")
