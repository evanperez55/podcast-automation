"""Test all social media platform connections."""

import sys
import io

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("\n" + "="*60)
print("TESTING ALL SOCIAL MEDIA PLATFORM CONNECTIONS")
print("="*60)
print()

platforms_status = {}

# Test YouTube
print("1. YouTube")
print("-" * 60)
try:
    from uploaders import YouTubeUploader
    yt = YouTubeUploader()
    print("[✓] YouTube: Connected and authenticated")
    platforms_status['youtube'] = 'ready'
except Exception as e:
    print(f"[✗] YouTube: {e}")
    platforms_status['youtube'] = 'not configured'
print()

# Test Twitter
print("2. Twitter/X")
print("-" * 60)
try:
    from uploaders import TwitterUploader
    tw = TwitterUploader()
    print("[✓] Twitter: Connected with API keys")
    platforms_status['twitter'] = 'ready'
except Exception as e:
    print(f"[✗] Twitter: {e}")
    platforms_status['twitter'] = 'not configured'
print()

# Test Instagram
print("3. Instagram")
print("-" * 60)
try:
    from uploaders import InstagramUploader
    ig = InstagramUploader()
    print("[✓] Instagram: Connected with access token")
    platforms_status['instagram'] = 'ready'
except Exception as e:
    print(f"[✗] Instagram: {e}")
    platforms_status['instagram'] = 'not configured'
print()

# Test TikTok
print("4. TikTok")
print("-" * 60)
try:
    from uploaders import TikTokUploader
    tt = TikTokUploader()
    print("[✓] TikTok: Connected with API credentials")
    platforms_status['tiktok'] = 'ready'
except Exception as e:
    print(f"[✗] TikTok: {e}")
    platforms_status['tiktok'] = 'not configured'
print()

# Test Spotify
print("5. Spotify (RSS Feed)")
print("-" * 60)
try:
    from uploaders import SpotifyUploader
    sp = SpotifyUploader()
    print("[✓] Spotify: Connected with API credentials")
    if hasattr(sp, 'rss_generator') and sp.rss_generator:
        print(f"    RSS generator: Ready")
    platforms_status['spotify'] = 'ready'
except Exception as e:
    print(f"[✗] Spotify: {e}")
    platforms_status['spotify'] = 'not configured'
print()

# Summary
print("="*60)
print("SUMMARY")
print("="*60)
print()
ready_count = sum(1 for status in platforms_status.values() if status == 'ready')
total_count = len(platforms_status)

print(f"Ready platforms: {ready_count}/{total_count}")
print()
for platform, status in platforms_status.items():
    status_icon = "✓" if status == "ready" else "✗"
    print(f"  [{status_icon}] {platform.capitalize()}: {status}")
print()

if ready_count == total_count:
    print("[SUCCESS] All platforms are ready for automation!")
elif ready_count > 0:
    print(f"[INFO] {ready_count} platform(s) ready. Configure remaining platforms to enable full automation.")
else:
    print("[WARNING] No platforms configured. Set up API credentials to enable automation.")
print()
