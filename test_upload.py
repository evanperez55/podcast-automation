"""Test upload: verify all social media integrations work end-to-end.

Uploads a short test clip to all configured platforms as unlisted/private,
verifies success, then auto-deletes. Use this to validate a client's
credentials before going live.

Usage:
    uv run test_upload.py [--client <name>] [--keep]
    uv run main.py test-upload [--client <name>] [--keep]
"""

import sys
import time
from pathlib import Path

from config import Config
from logger import logger

# 3-second black vertical video for testing
TEST_CLIP = Path(__file__).parent / "assets" / "test_clip.mp4"


def _init_platform(name, init_fn):
    """Try to initialize a platform uploader.

    Args:
        name: Platform display name.
        init_fn: Callable that returns an uploader instance.

    Returns:
        Uploader instance or None.
    """
    try:
        uploader = init_fn()
        return uploader
    except Exception as e:
        logger.info("[%s] Not configured: %s", name, str(e).split("\n")[0])
        return None


def run_test_upload(keep=False, yes=False):
    """Upload test clip to all configured platforms and optionally delete.

    Args:
        keep: If True, don't delete test uploads after verification.
        yes: If True, skip confirmation prompt.

    Returns:
        Dict of platform -> result.
    """
    if not TEST_CLIP.exists():
        print(f"Error: Test clip not found at {TEST_CLIP}")
        print(
            "Generate it with: ffmpeg -f lavfi -i 'color=c=black:s=1080x1920:d=3' "
            "-f lavfi -i 'anullsrc' -t 3 -c:v libx264 -c:a aac -shortest "
            "-y assets/test_clip.mp4"
        )
        return {}

    print("=" * 60)
    print("Social Media Integration Test")
    print("=" * 60)
    print(f"Client: {Config.PODCAST_NAME}")
    print(f"Test clip: {TEST_CLIP} ({TEST_CLIP.stat().st_size} bytes)")
    print(f"Auto-delete: {'No (--keep)' if keep else 'Yes'}")
    print()
    print("WARNING: This will post test content to LIVE social media accounts.")
    print("Test posts are labeled [TEST] and will be auto-deleted after verification.")
    print()

    # Require explicit confirmation unless --yes flag is passed
    if not yes:
        try:
            confirm = input("Type 'yes' to continue: ").strip().lower()
        except EOFError:
            confirm = ""
        if confirm != "yes":
            print("Aborted.")
            return {}

    results = {}
    cleanup = []  # List of (platform, cleanup_fn) tuples

    # --- Dropbox ---
    from dropbox_handler import DropboxHandler

    dbx = _init_platform("Dropbox", DropboxHandler)
    dropbox_video_url = None
    dbx_test_path = "/podcast/test_upload/test_clip.mp4"

    if dbx:
        print("[Dropbox] Uploading test clip...")
        upload_result = dbx.upload_file(str(TEST_CLIP), dbx_test_path, overwrite=True)
        if upload_result:
            dropbox_video_url = dbx.get_shared_link(dbx_test_path)
            if dropbox_video_url:
                results["dropbox"] = {"status": "success", "url": dropbox_video_url}
                print("  OK - uploaded and shared link created")
                cleanup.append(("Dropbox", lambda: dbx.delete_file(dbx_test_path)))
            else:
                results["dropbox"] = {"status": "failed", "error": "no shared link"}
                print("  FAILED - upload OK but shared link failed")
        else:
            results["dropbox"] = {"status": "failed", "error": "upload failed"}
            print("  FAILED - upload failed")
    else:
        results["dropbox"] = {"status": "skipped"}

    # --- YouTube ---
    from uploaders.youtube_uploader import YouTubeUploader

    yt = _init_platform("YouTube", YouTubeUploader)
    if yt:
        print("[YouTube] Uploading test Short (unlisted)...")
        yt_result = yt.upload_short(
            video_path=str(TEST_CLIP),
            title="[TEST] Integration test - will be deleted",
            description="Automated test upload. Will be deleted shortly.",
            tags=["test"],
            privacy_status="unlisted",
        )
        if yt_result and yt_result.get("video_id"):
            vid_id = yt_result["video_id"]
            results["youtube"] = {"status": "success", "video_id": vid_id}
            print(f"  OK - video_id: {vid_id}")
            cleanup.append(("YouTube", lambda vid=vid_id: yt.delete_video(vid)))
        else:
            results["youtube"] = {"status": "failed", "error": "upload returned None"}
            print("  FAILED - upload returned None")
    else:
        results["youtube"] = {"status": "skipped"}

    # --- Twitter ---
    from uploaders.twitter_uploader import TwitterUploader

    tw = _init_platform("Twitter", TwitterUploader)
    if tw:
        print("[Twitter] Posting test tweet...")
        tweet_result = tw.post_tweet(
            text="[TEST] Automated integration test - will be deleted shortly."
        )
        if tweet_result and tweet_result.get("tweet_id"):
            tid = tweet_result["tweet_id"]
            results["twitter"] = {"status": "success", "tweet_id": tid}
            print(f"  OK - tweet_id: {tid}")
            print(
                "  (manual delete required — Twitter API doesn't support delete at this tier)"
            )
        else:
            results["twitter"] = {"status": "failed", "error": "post returned None"}
            print("  FAILED - post returned None")
    else:
        results["twitter"] = {"status": "skipped"}

    # --- Instagram ---
    from uploaders.instagram_uploader import InstagramUploader

    ig = _init_platform("Instagram", InstagramUploader)
    if ig and ig.functional:
        if dropbox_video_url:
            print("[Instagram] Uploading test Reel...")
            ig_result = ig.upload_reel(
                video_url=dropbox_video_url,
                caption="[TEST] Automated integration test - will be deleted shortly.",
            )
            if ig_result and ig_result.get("id"):
                media_id = ig_result["id"]
                permalink = ig_result.get("permalink", "")
                results["instagram"] = {"status": "success", "media_id": media_id}
                print(f"  OK - {permalink or media_id}")
                print(
                    "  (manual delete required — Instagram API doesn't support media deletion)"
                )
            else:
                results["instagram"] = {
                    "status": "failed",
                    "error": "upload returned None",
                }
                print("  FAILED - upload returned None")
        else:
            results["instagram"] = {
                "status": "skipped",
                "reason": "Dropbox not available for public URL",
            }
            print("  SKIPPED - needs Dropbox for public video URL")
    else:
        results["instagram"] = {"status": "skipped"}

    # --- Bluesky ---
    from uploaders.bluesky_uploader import BlueskyUploader

    bs = _init_platform("Bluesky", BlueskyUploader)
    if bs:
        print("[Bluesky] Posting test post...")
        bs_result = bs.post(
            text="[TEST] Automated integration test - will be deleted shortly."
        )
        if bs_result and bs_result.get("post_uri"):
            post_uri = bs_result["post_uri"]
            results["bluesky"] = {"status": "success", "post_uri": post_uri}
            print("  OK - posted")
            cleanup.append(("Bluesky", lambda u=post_uri: bs.delete_post(u)))
        else:
            results["bluesky"] = {"status": "failed", "error": "post returned None"}
            print("  FAILED - post returned None")
    else:
        results["bluesky"] = {"status": "skipped"}

    # --- Discord ---
    if Config.DISCORD_WEBHOOK_URL:
        import requests

        print("[Discord] Testing webhook...")
        try:
            resp = requests.get(Config.DISCORD_WEBHOOK_URL, timeout=10)
            resp.raise_for_status()
            webhook_name = resp.json().get("name", "unknown")
            results["discord"] = {"status": "success", "webhook": webhook_name}
            print(f"  OK - webhook: {webhook_name}")
        except Exception as e:
            results["discord"] = {"status": "failed", "error": str(e)}
            print(f"  FAILED - {e}")
    else:
        results["discord"] = {"status": "skipped"}

    # --- Summary ---
    print()
    print("=" * 60)
    print("Results")
    print("=" * 60)
    for platform, result in results.items():
        status = result.get("status", "unknown")
        icon = {"success": "OK", "failed": "FAIL", "skipped": "SKIP"}.get(status, "?")
        print(f"  [{icon:4}] {platform}")
    print()

    succeeded = sum(1 for r in results.values() if r["status"] == "success")
    failed = sum(1 for r in results.values() if r["status"] == "failed")
    skipped = sum(1 for r in results.values() if r["status"] == "skipped")
    print(f"{succeeded} passed, {failed} failed, {skipped} skipped")

    # --- Cleanup ---
    if cleanup and not keep:
        print()
        print("Cleaning up test uploads...")
        # Give platforms a moment to process
        time.sleep(3)
        failed_cleanups = []
        for platform, cleanup_fn in cleanup:
            try:
                success = cleanup_fn()
                if success is False:
                    failed_cleanups.append(platform)
                    print(f"  [{platform}] DELETE FAILED - test content is still live!")
                else:
                    print(f"  [{platform}] Deleted")
            except Exception as e:
                failed_cleanups.append(platform)
                print(f"  [{platform}] DELETE FAILED: {e}")
                print("           ^ You must manually delete the test content!")

        if failed_cleanups:
            print()
            print(
                f"WARNING: {len(failed_cleanups)} platform(s) still have test content:"
            )
            for p in failed_cleanups:
                r = results.get(p.lower(), {})
                # Print the ID so they can manually delete
                for key in ["video_id", "tweet_id", "media_id", "post_uri", "url"]:
                    if key in r:
                        print(f"  {p}: {key}={r[key]}")
    elif cleanup and keep:
        print()
        print("--keep flag set, skipping cleanup. Test uploads remain on platforms.")

    return results


def main():
    args = sys.argv[1:]
    keep = "--keep" in args
    yes = "--yes" in args

    # Handle --client flag
    if "--client" in args:
        idx = args.index("--client")
        if idx + 1 < len(args):
            client_name = args[idx + 1]
            from client_config import activate_client

            activate_client(client_name)

    run_test_upload(keep=keep, yes=yes)


if __name__ == "__main__":
    main()
