"""Interactive Instagram setup guide."""

import sys
import io
import webbrowser

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("\n" + "="*70)
print("INSTAGRAM SETUP GUIDE - Interactive Walkthrough")
print("="*70)
print()
print("Instagram requires:")
print("  1. Instagram Business or Creator account")
print("  2. Facebook Page linked to Instagram")
print("  3. Facebook App with Instagram Graph API")
print()
print("This will take about 15-30 minutes.")
print()

input("Press Enter to start the setup process...")

# Step 1: Check Instagram account type
print("\n" + "="*70)
print("STEP 1: Convert to Instagram Business Account")
print("="*70)
print()
print("1. Open Instagram app on your phone")
print("2. Go to: Settings → Account → Switch to Professional Account")
print("3. Choose 'Business' or 'Creator'")
print("4. Link to a Facebook Page (create one if needed)")
print()
print("Already have a Business/Creator account? Great!")
print()

input("Press Enter when your Instagram account is Business/Creator...")

# Step 2: Create Facebook App
print("\n" + "="*70)
print("STEP 2: Create Facebook Developer App")
print("="*70)
print()
print("Opening Facebook Developers in your browser...")
print()

webbrowser.open('https://developers.facebook.com/apps/create/')

print("In the browser:")
print("  1. Click 'Create App'")
print("  2. Use case: Select 'Other'")
print("  3. App type: Select 'Business'")
print("  4. App name: 'Fake Problems Podcast' (or your podcast name)")
print("  5. App contact email: Your email")
print("  6. Click 'Create App'")
print()

input("Press Enter when you've created the app...")

# Step 3: Get App ID and Secret
print("\n" + "="*70)
print("STEP 3: Get App Credentials")
print("="*70)
print()
print("In your Facebook App dashboard:")
print("  1. Go to Settings → Basic")
print("  2. Copy your App ID")
print("  3. Copy your App Secret (click 'Show' first)")
print()

app_id = input("Paste your App ID here: ").strip()
app_secret = input("Paste your App Secret here: ").strip()

print()
print(f"[OK] App ID: {app_id}")
print(f"[OK] App Secret: {app_secret[:4]}...{app_secret[-4:]}")
print()

# Step 4: Add Instagram Product
print("\n" + "="*70)
print("STEP 4: Add Instagram Graph API")
print("="*70)
print()
print("In your Facebook App dashboard:")
print("  1. Click 'Add Product' in left sidebar")
print("  2. Find 'Instagram Graph API'")
print("  3. Click 'Set Up'")
print()

input("Press Enter when Instagram Graph API is added...")

# Step 5: Get User Access Token
print("\n" + "="*70)
print("STEP 5: Generate User Access Token")
print("="*70)
print()
print("Opening Graph API Explorer...")
print()

webbrowser.open('https://developers.facebook.com/tools/explorer/')

print("In Graph API Explorer:")
print("  1. Select your app from dropdown")
print("  2. Click 'Generate Access Token'")
print("  3. Grant these permissions:")
print("     - instagram_basic")
print("     - instagram_content_publish")
print("     - pages_read_engagement")
print("     - pages_show_list")
print("  4. Click 'Generate Token'")
print("  5. Copy the short-lived token")
print()

short_token = input("Paste your short-lived access token here: ").strip()

print()
print("[OK] Short-lived token received")
print()

# Step 6: Exchange for long-lived token
print("\n" + "="*70)
print("STEP 6: Exchange for Long-Lived Token")
print("="*70)
print()
print("Generating exchange URL...")
print()

exchange_url = (
    f"https://graph.facebook.com/v18.0/oauth/access_token?"
    f"grant_type=fb_exchange_token&"
    f"client_id={app_id}&"
    f"client_secret={app_secret}&"
    f"fb_exchange_token={short_token}"
)

print("Opening exchange URL in browser...")
webbrowser.open(exchange_url)

print()
print("Copy the 'access_token' from the JSON response")
print()

long_token = input("Paste your long-lived access token here: ").strip()

print()
print("[OK] Long-lived token received")
print()

# Step 7: Get Instagram Account ID
print("\n" + "="*70)
print("STEP 7: Get Instagram Business Account ID")
print("="*70)
print()
print("Getting your Facebook Pages...")
print()

pages_url = f"https://graph.facebook.com/v18.0/me/accounts?access_token={long_token}"

webbrowser.open(pages_url)

print("From the JSON response, find your page and copy its 'id'")
print()

page_id = input("Paste your Facebook Page ID here: ").strip()

print()
print("Now getting Instagram account ID...")
print()

ig_url = f"https://graph.facebook.com/v18.0/{page_id}?fields=instagram_business_account&access_token={long_token}"

webbrowser.open(ig_url)

print("From the JSON response, copy the 'instagram_business_account' id")
print()

ig_account_id = input("Paste your Instagram Business Account ID here: ").strip()

print()
print("[OK] Instagram Account ID: " + ig_account_id)
print()

# Step 8: Save to .env
print("\n" + "="*70)
print("STEP 8: Save Credentials")
print("="*70)
print()
print("Updating .env file...")

from pathlib import Path

env_path = Path('.env')
env_lines = []

if env_path.exists():
    with open(env_path, 'r') as f:
        env_lines = f.readlines()

# Update or add credentials
updated = set()
new_lines = []

for line in env_lines:
    if line.startswith('INSTAGRAM_ACCESS_TOKEN='):
        new_lines.append(f'INSTAGRAM_ACCESS_TOKEN={long_token}\n')
        updated.add('INSTAGRAM_ACCESS_TOKEN')
    elif line.startswith('INSTAGRAM_ACCOUNT_ID='):
        new_lines.append(f'INSTAGRAM_ACCOUNT_ID={ig_account_id}\n')
        updated.add('INSTAGRAM_ACCOUNT_ID')
    else:
        new_lines.append(line)

# Add if not found
if 'INSTAGRAM_ACCESS_TOKEN' not in updated:
    new_lines.append(f'INSTAGRAM_ACCESS_TOKEN={long_token}\n')
if 'INSTAGRAM_ACCOUNT_ID' not in updated:
    new_lines.append(f'INSTAGRAM_ACCOUNT_ID={ig_account_id}\n')

with open(env_path, 'w') as f:
    f.writelines(new_lines)

print("[OK] Credentials saved to .env")
print()

# Step 9: Test connection
print("\n" + "="*70)
print("STEP 9: Test Instagram Connection")
print("="*70)
print()
print("Testing Instagram API connection...")

try:
    from uploaders import InstagramUploader
    ig = InstagramUploader()
    print("[✓] Instagram connection successful!")
    print()
    print("="*70)
    print("SETUP COMPLETE!")
    print("="*70)
    print()
    print("Instagram is now configured and ready to use.")
    print()
    print("Important notes:")
    print("  - Long-lived tokens last 60 days")
    print("  - You'll need to refresh them before expiry")
    print("  - Videos must be publicly accessible URLs")
    print("  - Reels: 3-90 seconds, 9:16 aspect ratio")
    print()
except Exception as e:
    print(f"[✗] Test failed: {e}")
    print()
    print("Please verify your credentials and try again.")
