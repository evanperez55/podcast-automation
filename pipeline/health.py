"""Health check command extracted from pipeline/runner.py."""

from pathlib import Path

from config import Config


def health_check():
    """Validate all configured credentials and print a status table."""
    import pickle

    results = []

    # YouTube: try loading the pickle token
    yt_token_path = Path(Config.BASE_DIR) / "credentials" / "youtube_token.pickle"
    if yt_token_path.exists():
        try:
            with open(yt_token_path, "rb") as f:
                creds = pickle.load(f)
            if hasattr(creds, "expired") and creds.expired:
                if hasattr(creds, "refresh_token") and creds.refresh_token:
                    results.append(
                        ("YouTube", "OK", "Token expired but refresh token available")
                    )
                else:
                    results.append(
                        ("YouTube", "ERROR", "Token expired, no refresh token")
                    )
            else:
                results.append(("YouTube", "OK", "Token loaded successfully"))
        except Exception as e:
            results.append(("YouTube", "ERROR", f"Cannot load token: {e}"))
    else:
        results.append(("YouTube", "MISSING", f"Token file not found: {yt_token_path}"))

    # Twitter: check all 4 keys
    tw_keys = [
        "TWITTER_API_KEY",
        "TWITTER_API_SECRET",
        "TWITTER_ACCESS_TOKEN",
        "TWITTER_ACCESS_SECRET",
    ]
    tw_missing = [k for k in tw_keys if not getattr(Config, k, None)]
    if not tw_missing:
        results.append(("Twitter", "OK", "All 4 credentials configured"))
    else:
        results.append(("Twitter", "MISSING", f"Missing: {', '.join(tw_missing)}"))

    # Bluesky
    bs_keys = ["BLUESKY_HANDLE", "BLUESKY_APP_PASSWORD"]
    bs_missing = [k for k in bs_keys if not getattr(Config, k, None)]
    if not bs_missing:
        results.append(("Bluesky", "OK", "Handle and app password configured"))
    else:
        results.append(("Bluesky", "MISSING", f"Missing: {', '.join(bs_missing)}"))

    # Discord
    if getattr(Config, "DISCORD_WEBHOOK_URL", None):
        results.append(("Discord", "OK", "Webhook URL configured"))
    else:
        results.append(("Discord", "MISSING", "DISCORD_WEBHOOK_URL not set"))

    # Dropbox
    if getattr(Config, "DROPBOX_REFRESH_TOKEN", None):
        results.append(("Dropbox", "OK", "Refresh token configured"))
    else:
        results.append(("Dropbox", "MISSING", "DROPBOX_REFRESH_TOKEN not set"))

    # OpenAI
    if getattr(Config, "OPENAI_API_KEY", None):
        results.append(("OpenAI", "OK", "API key configured"))
    else:
        results.append(("OpenAI", "MISSING", "OPENAI_API_KEY not set"))

    # Print table
    fmt = "{:<12} {:<10} {}"
    print(fmt.format("Platform", "Status", "Details"))
    print("-" * 60)
    for platform, status, details in results:
        print(fmt.format(platform, status, details))
