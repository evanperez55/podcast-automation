"""Instagram OAuth setup script to obtain a long-lived access token.

Walks through the Instagram Login OAuth flow to get a proper token
that can be exchanged for a 60-day long-lived token.

Usage:
    uv run scripts/setup_instagram_oauth.py
"""

import http.server
import urllib.parse
import webbrowser
import requests
import sys
import os
from dotenv import load_dotenv

load_dotenv()

# Instagram App credentials
INSTAGRAM_APP_ID = os.getenv("INSTAGRAM_APP_ID", "")
INSTAGRAM_APP_SECRET = os.getenv("INSTAGRAM_APP_SECRET", "")
REDIRECT_URI = "https://localhost:8888/callback"
SCOPES = "instagram_business_basic,instagram_business_content_publish"


def exchange_code_for_token(code):
    """Exchange authorization code for short-lived token."""
    print("\n[2/3] Exchanging code for short-lived token...")
    response = requests.post(
        "https://api.instagram.com/oauth/access_token",
        data={
            "client_id": INSTAGRAM_APP_ID,
            "client_secret": INSTAGRAM_APP_SECRET,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
            "code": code,
        },
    )

    if response.status_code != 200:
        print(f"Error: {response.text}")
        return None

    data = response.json()
    print(f"  Short-lived token obtained (user_id: {data.get('user_id')})")
    return data.get("access_token")


def exchange_for_long_lived_token(short_token):
    """Exchange short-lived token for long-lived (60-day) token."""
    print("\n[3/3] Exchanging for long-lived token (60 days)...")
    response = requests.get(
        "https://graph.instagram.com/access_token",
        params={
            "grant_type": "ig_exchange_token",
            "client_secret": INSTAGRAM_APP_SECRET,
            "access_token": short_token,
        },
    )

    if response.status_code != 200:
        print(f"Error: {response.text}")
        return None

    data = response.json()
    expires_in = data.get("expires_in", 0)
    days = expires_in // 86400
    print(f"  Long-lived token obtained! Expires in {days} days.")
    return data.get("access_token")


def main():
    print("=" * 60)
    print("Instagram OAuth Setup")
    print("=" * 60)

    # Step 0: Check credentials
    if not INSTAGRAM_APP_ID or not INSTAGRAM_APP_SECRET:
        print("Error: Set INSTAGRAM_APP_ID and INSTAGRAM_APP_SECRET env vars first.")
        print("  You can find these in your Meta Developer App dashboard.")
        sys.exit(1)

    # If called with a URL or code argument, skip to token exchange
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip()
        # Could be a full callback URL or just the code
        if "?" in arg:
            parsed = urllib.parse.urlparse(arg)
            params = urllib.parse.parse_qs(parsed.query)
            code = params.get("code", [None])[0]
        else:
            code = arg

        if not code:
            print("Error: Could not find authorization code in argument")
            sys.exit(1)

        # Remove trailing #_ that Instagram sometimes adds
        code = code.rstrip("#_")
    else:
        # No argument — just print the auth URL and exit
        auth_url = (
            f"https://www.instagram.com/oauth/authorize"
            f"?client_id={INSTAGRAM_APP_ID}"
            f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
            f"&response_type=code"
            f"&scope={SCOPES}"
        )
        print(f"\nStep 1: Open this URL in your browser:")
        print(f"  {auth_url}")
        print(f"\nStep 2: After authorizing, you'll be redirected to a URL like:")
        print(f"  {REDIRECT_URI}?code=AQB...")
        print(f"\nStep 3: Run this script again with the redirect URL:")
        print(f"  uv run scripts/setup_instagram_oauth.py \"<paste_redirect_url>\"")
        sys.exit(0)

    # Step 2: Exchange code for short-lived token
    short_token = exchange_code_for_token(code)
    if not short_token:
        print("Failed to get short-lived token")
        sys.exit(1)

    # Step 3: Exchange for long-lived token
    long_token = exchange_for_long_lived_token(short_token)
    if not long_token:
        print("\nCould not get long-lived token. Using short-lived token instead.")
        long_token = short_token

    # Output
    print("\n" + "=" * 60)
    print("SUCCESS! Add this to your .env file:")
    print("=" * 60)
    print(f"\nINSTAGRAM_ACCESS_TOKEN={long_token}")
    print(f"\nToken expires in ~60 days. Run this script again to refresh.")


if __name__ == "__main__":
    main()
