"""B019 verification: probe Twitter token scope.

Stage 1 (default): read-only — call get_me() to confirm tokens authenticate
and report which account they point at.

Stage 2 (--write-test): post a short test tweet + immediately delete it.
This is the only way to definitively test write scope on OAuth 1.0a tokens
(no introspection endpoint exists for v1 user-context tokens).

Usage:
    uv run python scripts/twitter_scope_check.py             # read-only
    uv run python scripts/twitter_scope_check.py --write-test
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--write-test",
        action="store_true",
        help="Post + immediately delete a test tweet to verify write scope.",
    )
    args = ap.parse_args()

    from uploaders.twitter_uploader import TwitterUploader

    uploader = TwitterUploader()
    print("=" * 60)
    print("Stage 1: read-only auth probe")
    print("=" * 60)
    me = uploader.client.get_me()
    if not me or not me.data:
        print("FAIL: get_me() returned no data — tokens not authenticating")
        return 1
    user = me.data
    print(f"  Authenticated as: @{user.username} (id={user.id}, name={user.name!r})")
    print()

    if not args.write_test:
        print("Read scope works. Re-run with --write-test to verify write scope.")
        return 0

    print("=" * 60)
    print("Stage 2: write probe (post + immediate delete)")
    print("=" * 60)
    text = f"scope check {int(time.time())} — auto-deleting"
    print(f"  Posting: {text!r}")
    try:
        resp = uploader.client.create_tweet(text=text)
    except Exception as e:
        print(f"  POST FAILED: {type(e).__name__}: {e}")
        print("  -> Tokens are READ-ONLY; regenerate them in the Developer Portal.")
        return 1

    tweet_id = resp.data["id"] if resp and resp.data else None
    if not tweet_id:
        print("  POST returned no tweet id — unexpected response shape:", resp)
        return 1
    print(f"  Posted tweet id={tweet_id}")
    print(
        f"  URL (in case delete fails): https://x.com/{user.username}/status/{tweet_id}"
    )

    print("  Deleting...")
    try:
        del_resp = uploader.client.delete_tweet(tweet_id)
    except Exception as e:
        print(f"  DELETE FAILED: {type(e).__name__}: {e}")
        print(
            f"  -> Tweet still live at https://x.com/{user.username}/status/{tweet_id}"
        )
        print(
            "  -> Manually delete it. Write works, but delete may need a different scope."
        )
        return 1
    print(f"  Delete response: {del_resp}")
    print()
    print("VERDICT: tokens have write + delete scope — B019 false alarm.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
