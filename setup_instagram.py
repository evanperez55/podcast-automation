"""Interactive Instagram setup guide with programmatic token exchange."""

import sys
import io
import webbrowser
import requests
from pathlib import Path


def update_env_var(key: str, value: str):
    """Update or add a key=value pair in .env file."""
    env_path = Path(".env")
    env_lines = []

    if env_path.exists():
        with open(env_path, "r") as f:
            env_lines = f.readlines()

    found = False
    new_lines = []
    for line in env_lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={value}\n")

    with open(env_path, "w") as f:
        f.writelines(new_lines)


def refresh_token():
    """Refresh an existing Instagram long-lived token (extends by 60 days)."""
    print("\n" + "=" * 70)
    print("INSTAGRAM TOKEN REFRESH")
    print("=" * 70)
    print()

    env_path = Path(".env")
    current_token = None

    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith("INSTAGRAM_ACCESS_TOKEN="):
                    current_token = line.strip().split("=", 1)[1]
                    break

    if not current_token or current_token == "your_instagram_access_token_here":
        print("[ERROR] No Instagram access token found in .env")
        print("Run 'python setup_instagram.py' first to do initial setup.")
        return

    print(f"[INFO] Current token: {current_token[:10]}...{current_token[-6:]}")
    print("[INFO] Requesting token refresh from Meta API...")
    print()

    try:
        response = requests.get(
            "https://graph.facebook.com/v18.0/oauth/access_token",
            params={"grant_type": "ig_refresh_token", "access_token": current_token},
        )
        response.raise_for_status()
        data = response.json()

        new_token = data.get("access_token")
        expires_in = data.get("expires_in", 0)

        if new_token:
            update_env_var("INSTAGRAM_ACCESS_TOKEN", new_token)
            days = expires_in // 86400
            print("[OK] Token refreshed successfully!")
            print(f"[OK] New token expires in {days} days")
            print("[OK] Saved to .env")
        else:
            print(f"[ERROR] Unexpected response: {data}")

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Token refresh failed: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"[ERROR] Response: {e.response.text}")
        print()
        print("If the token has expired, you'll need to run the full setup again:")
        print("  python setup_instagram.py")


def full_setup():
    """Run the full interactive Instagram setup."""
    print("\n" + "=" * 70)
    print("INSTAGRAM SETUP GUIDE - Interactive Walkthrough")
    print("=" * 70)
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
    print("\n" + "=" * 70)
    print("STEP 1: Convert to Instagram Business Account")
    print("=" * 70)
    print()
    print("1. Open Instagram app on your phone")
    print("2. Go to: Settings > Account > Switch to Professional Account")
    print("3. Choose 'Business' or 'Creator'")
    print("4. Link to a Facebook Page (create one if needed)")
    print()
    print("Already have a Business/Creator account? Great!")
    print()

    input("Press Enter when your Instagram account is Business/Creator...")

    # Step 2: Create Facebook App
    print("\n" + "=" * 70)
    print("STEP 2: Create Facebook Developer App")
    print("=" * 70)
    print()
    print("Opening Facebook Developers in your browser...")
    print()

    webbrowser.open("https://developers.facebook.com/apps/create/")

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
    print("\n" + "=" * 70)
    print("STEP 3: Get App Credentials")
    print("=" * 70)
    print()
    print("In your Facebook App dashboard:")
    print("  1. Go to Settings > Basic")
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
    print("\n" + "=" * 70)
    print("STEP 4: Add Instagram Graph API")
    print("=" * 70)
    print()
    print("In your Facebook App dashboard:")
    print("  1. Click 'Add Product' in left sidebar")
    print("  2. Find 'Instagram Graph API'")
    print("  3. Click 'Set Up'")
    print()

    input("Press Enter when Instagram Graph API is added...")

    # Step 5: Get User Access Token (with permission checklist)
    print("\n" + "=" * 70)
    print("STEP 5: Generate User Access Token")
    print("=" * 70)
    print()
    print("!! IMPORTANT - READ BEFORE PROCEEDING !!")
    print()
    print("You MUST add ALL of these permissions BEFORE generating the token:")
    print()
    print("  [  ] instagram_basic")
    print("  [  ] instagram_content_publish")
    print("  [  ] pages_read_engagement")
    print("  [  ] pages_show_list")
    print()
    print("If you generate the token first and add permissions later,")
    print("the token will NOT have those permissions and uploads will fail.")
    print()

    input("Press Enter to open Graph API Explorer...")

    webbrowser.open("https://developers.facebook.com/tools/explorer/")

    print()
    print("In Graph API Explorer:")
    print("  1. Select your app from the dropdown at the top")
    print("  2. Click 'Add a Permission' on the right side")
    print("  3. Add ALL FOUR permissions listed above")
    print("  4. Click 'Generate Access Token'")
    print("  5. Authorize in the popup")
    print("  6. Copy the token shown in the Access Token field")
    print()

    short_token = input("Paste your short-lived access token here: ").strip()

    print()
    print("[OK] Short-lived token received")
    print()

    # Step 6: Exchange for long-lived token (PROGRAMMATIC)
    print("\n" + "=" * 70)
    print("STEP 6: Exchange for Long-Lived Token")
    print("=" * 70)
    print()
    print("[INFO] Exchanging short-lived token for long-lived token...")
    print()

    try:
        response = requests.get(
            "https://graph.facebook.com/v18.0/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": app_id,
                "client_secret": app_secret,
                "fb_exchange_token": short_token,
            },
        )
        response.raise_for_status()
        data = response.json()

        long_token = data.get("access_token")
        if not long_token:
            print(f"[ERROR] No access_token in response: {data}")
            print("Please check your App ID, App Secret, and short-lived token.")
            sys.exit(1)

        expires_in = data.get("expires_in", 0)
        days = expires_in // 86400 if expires_in else "~60"
        print(f"[OK] Long-lived token obtained (expires in {days} days)")

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Token exchange failed: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"[ERROR] Response: {e.response.text}")
        print()
        print("Falling back to manual exchange...")
        exchange_url = (
            f"https://graph.facebook.com/v18.0/oauth/access_token?"
            f"grant_type=fb_exchange_token&"
            f"client_id={app_id}&"
            f"client_secret={app_secret}&"
            f"fb_exchange_token={short_token}"
        )
        webbrowser.open(exchange_url)
        print("Copy the 'access_token' from the JSON response")
        print()
        long_token = input("Paste your long-lived access token here: ").strip()

    print()

    # Step 7: Get Instagram Account ID (PROGRAMMATIC)
    print("\n" + "=" * 70)
    print("STEP 7: Get Instagram Business Account ID")
    print("=" * 70)
    print()
    print("[INFO] Fetching your Facebook Pages...")
    print()

    page_id = None
    ig_account_id = None

    try:
        response = requests.get(
            "https://graph.facebook.com/v18.0/me/accounts",
            params={"access_token": long_token},
        )
        response.raise_for_status()
        data = response.json()

        pages = data.get("data", [])
        if not pages:
            print("[ERROR] No Facebook Pages found.")
            print("Make sure your Instagram account is linked to a Facebook Page.")
            sys.exit(1)

        if len(pages) == 1:
            page_id = pages[0]["id"]
            page_name = pages[0].get("name", "Unknown")
            print(f"[OK] Found page: {page_name} (ID: {page_id})")
        else:
            print("Multiple pages found:")
            for i, page in enumerate(pages, 1):
                print(f"  {i}. {page.get('name', 'Unknown')} (ID: {page['id']})")
            print()
            choice = input(f"Select page (1-{len(pages)}): ").strip()
            try:
                page_id = pages[int(choice) - 1]["id"]
            except (ValueError, IndexError):
                print("[ERROR] Invalid selection")
                sys.exit(1)

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to fetch pages: {e}")
        print("Falling back to manual entry...")
        pages_url = (
            f"https://graph.facebook.com/v18.0/me/accounts?access_token={long_token}"
        )
        webbrowser.open(pages_url)
        print("From the JSON response, find your page and copy its 'id'")
        print()
        page_id = input("Paste your Facebook Page ID here: ").strip()

    print()
    print("[INFO] Fetching Instagram Business Account ID...")
    print()

    try:
        response = requests.get(
            f"https://graph.facebook.com/v18.0/{page_id}",
            params={"fields": "instagram_business_account", "access_token": long_token},
        )
        response.raise_for_status()
        data = response.json()

        ig_biz = data.get("instagram_business_account")
        if ig_biz and ig_biz.get("id"):
            ig_account_id = ig_biz["id"]
            print(f"[OK] Instagram Account ID: {ig_account_id}")
        else:
            print("[ERROR] No Instagram Business Account found for this page.")
            print("Make sure your Instagram is linked as a Business/Creator account.")
            sys.exit(1)

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to fetch Instagram account: {e}")
        print("Falling back to manual entry...")
        ig_url = f"https://graph.facebook.com/v18.0/{page_id}?fields=instagram_business_account&access_token={long_token}"
        webbrowser.open(ig_url)
        print("From the JSON response, copy the 'instagram_business_account' id")
        print()
        ig_account_id = input("Paste your Instagram Business Account ID here: ").strip()

    print()

    # Step 8: Save to .env
    print("\n" + "=" * 70)
    print("STEP 8: Save Credentials")
    print("=" * 70)
    print()
    print("Updating .env file...")

    update_env_var("INSTAGRAM_ACCESS_TOKEN", long_token)
    update_env_var("INSTAGRAM_ACCOUNT_ID", ig_account_id)

    print("[OK] Credentials saved to .env")
    print()

    # Step 9: Test connection
    print("\n" + "=" * 70)
    print("STEP 9: Test Instagram Connection")
    print("=" * 70)
    print()
    print("Testing Instagram API connection...")

    try:
        from uploaders import InstagramUploader

        InstagramUploader()
        print("[OK] Instagram connection successful!")
        print()
        print("=" * 70)
        print("SETUP COMPLETE!")
        print("=" * 70)
        print()
        print("Instagram is now configured and ready to use.")
        print()
        print("Important notes:")
        print("  - Long-lived tokens last 60 days")
        print("  - Refresh before expiry: python setup_instagram.py refresh")
        print("  - Videos must be publicly accessible URLs (Dropbox links work)")
        print("  - Reels: 3-90 seconds, 9:16 aspect ratio")
        print()
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        print()
        print("Please verify your credentials and try again.")


if __name__ == "__main__":
    # Fix encoding for Windows terminals
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    if len(sys.argv) > 1 and sys.argv[1].lower() == "refresh":
        refresh_token()
    else:
        full_setup()
