"""Post scheduled content calendar slots to social media platforms.

Reads pending slots from the content calendar and posts clips/quotes
to Twitter and Bluesky on their scheduled dates. Designed to run daily
via GitHub Actions.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from config import Config
from logger import logger
from content_calendar import ContentCalendar


def _init_uploaders():
    """Initialize available social media uploaders."""
    uploaders = {}

    if Config.TWITTER_ENABLED:
        try:
            from uploaders.twitter_uploader import TwitterUploader

            uploaders["twitter"] = TwitterUploader()
            logger.info("Twitter uploader initialized")
        except (ValueError, Exception) as e:
            logger.warning("Twitter not available: %s", str(e).split("\n")[0])

    try:
        from uploaders.bluesky_uploader import BlueskyUploader

        uploaders["bluesky"] = BlueskyUploader()
        logger.info("Bluesky uploader initialized")
    except (ValueError, Exception) as e:
        logger.warning("Bluesky not available: %s", str(e).split("\n")[0])

    try:
        from uploaders.instagram_uploader import InstagramUploader

        ig = InstagramUploader()
        if ig.functional:
            uploaders["instagram"] = ig
            logger.info("Instagram uploader initialized")
        else:
            logger.info("Instagram not configured")
    except (ValueError, Exception) as e:
        logger.warning("Instagram not available: %s", str(e).split("\n")[0])

    return uploaders


def _post_slot(slot, uploaders):
    """Post a single content calendar slot to its platforms.

    Args:
        slot: Slot dict with slot_type, content, platforms, episode_key, slot_name.
        uploaders: Dict of platform name -> uploader instance.

    Returns:
        Dict of platform -> result.
    """
    slot_type = slot.get("slot_type", "")
    content = slot.get("content", {})
    platforms = slot.get("platforms", [])
    prior_results = slot.get("upload_results", {})
    results = {}

    # Carry forward prior successes and skip those platforms.
    # A result must have actual content (not empty dict) and no error
    # to be considered a success worth skipping on retry.
    for platform, prior in prior_results.items():
        if (
            isinstance(prior, dict)
            and prior  # empty dict {} is not a success
            and "error" not in prior
            and prior.get("status") != "error"
        ):
            results[platform] = prior
            logger.info("Skipping %s for %s — already posted", platform, slot_type)

    caption = content.get("caption", "")
    youtube_url = content.get("youtube_url", "")
    clip_title = content.get("clip_title", "")
    image_path = content.get("image_path")

    # Build post text
    if slot_type == "teaser":
        text = caption or "New episode dropping soon!"
    elif slot_type.startswith("quote_"):
        text = content.get("quote_text", caption)
    else:
        text = caption

    # For clip slots: make the YouTube Short public before promoting it
    youtube_video_id = content.get("youtube_video_id", "")
    if slot_type.startswith("clip_") and youtube_video_id and "youtube" in platforms:
        try:
            from uploaders.youtube_uploader import YouTubeUploader

            yt = YouTubeUploader()
            if yt.set_video_privacy(youtube_video_id, "public"):
                results["youtube"] = {
                    "status": "made_public",
                    "video_id": youtube_video_id,
                }
                logger.info("Made YouTube Short %s public", youtube_video_id)
            else:
                results["youtube"] = {"error": "set_video_privacy returned False"}
                logger.warning(
                    "Failed to make YouTube Short %s public", youtube_video_id
                )
        except Exception as e:
            logger.error("YouTube privacy update failed: %s", e)
            results["youtube"] = {"error": str(e)}

    for platform in platforms:
        if platform in results:
            continue  # already succeeded (from prior attempt or YouTube above)
        if platform not in uploaders:
            continue
        if platform == "youtube":
            continue  # handled above via privacy change

        try:
            if platform == "twitter":
                uploader = uploaders["twitter"]
                media = None
                if image_path and Path(image_path).exists():
                    media = [image_path]
                tweet_text = text
                if youtube_url and not image_path:
                    url_space = len(youtube_url) + 2  # for \n\n
                    max_text = 280 - url_space
                    truncated = text[:max_text] if text else ""
                    tweet_text = (
                        f"{truncated}\n\n{youtube_url}" if truncated else youtube_url
                    )
                result = uploader.post_tweet(
                    text=tweet_text[:280],
                    media_paths=media,
                )
                if result:
                    results["twitter"] = result
                else:
                    logger.warning("Twitter post_tweet returned None for %s", slot_type)
                    results["twitter"] = {"error": "post_tweet returned None"}

            elif platform == "bluesky":
                uploader = uploaders["bluesky"]
                if (
                    image_path
                    and Path(image_path).exists()
                    and hasattr(uploader, "post_with_image")
                ):
                    result = uploader.post_with_image(
                        text=text[:300],
                        image_path=image_path,
                    )
                else:
                    result = uploader.post(
                        text=text[:300],
                        url=youtube_url if youtube_url else None,
                        url_title=clip_title,
                    )
                if result:
                    results["bluesky"] = result
                else:
                    logger.warning("Bluesky post returned None for %s", slot_type)
                    results["bluesky"] = {"error": "post returned None"}

            elif platform == "instagram":
                # Prefer pre-uploaded Dropbox URL (works in CI)
                ig_video_url = content.get("instagram_video_url", "")
                clip_path = content.get("clip_path", "")

                # Fallback: derive Dropbox shared link from clips folder
                if not ig_video_url and slot_type.startswith("clip_"):
                    ig_video_url = _resolve_clip_dropbox_url(slot)

                if ig_video_url:
                    # Dropbox URL already available — post Reel directly
                    result = _post_instagram_reel_from_url(
                        uploaders["instagram"], ig_video_url, text, youtube_url
                    )
                    if result:
                        results["instagram"] = result
                    else:
                        logger.warning(
                            "Instagram reel post returned None for %s",
                            slot_type,
                        )
                        results["instagram"] = {"error": "reel post returned None"}
                elif clip_path and Path(clip_path).exists():
                    # Fall back to local file upload (local runs only)
                    result = _post_instagram_reel(
                        uploaders["instagram"], clip_path, text, youtube_url, slot
                    )
                    if result:
                        results["instagram"] = result
                    else:
                        logger.warning(
                            "Instagram reel post returned None for %s",
                            slot_type,
                        )
                        results["instagram"] = {"error": "reel post returned None"}
                else:
                    logger.warning("[Instagram] No video URL or local file for Reel")
                    results["instagram"] = {
                        "error": "no video URL or local file available"
                    }

        except Exception as e:
            logger.error("Failed to post %s to %s: %s", slot_type, platform, e)
            results[platform] = {"error": str(e)}

    return results


def _post_instagram_reel_from_url(ig_uploader, video_url, caption_text, youtube_url):
    """Post an Instagram Reel using a pre-uploaded Dropbox URL.

    Args:
        ig_uploader: InstagramUploader instance.
        video_url: Public Dropbox URL for the video.
        caption_text: Base caption text.
        youtube_url: YouTube URL for the full episode.

    Returns:
        Result dict from Instagram upload, or None on failure.
    """
    caption = caption_text or "New clip!"
    if youtube_url:
        caption += f"\n\nWatch the full episode and find more at {youtube_url}"
    else:
        caption += f"\n\nFind all episodes on YouTube: {Config.YOUTUBE_CHANNEL_HANDLE}"

    return ig_uploader.upload_reel(video_url=video_url, caption=caption)


def _resolve_clip_dropbox_url(slot):
    """Try to find a Dropbox shared link for a clip from the standard clips folder.

    Falls back to listing the clips folder and matching by clip index when
    instagram_video_url was never populated (e.g., episodes processed before
    Instagram integration).

    Returns:
        Shared link URL string, or empty string if not found.
    """
    import re

    episode_key = slot.get("episode_key", "")
    slot_type = slot.get("slot_type", "")
    match = re.search(r"clip_(\d+)", slot_type)
    if not match or not episode_key:
        return ""

    clip_num = int(match.group(1))
    clips_folder = f"/podcast/clips/{episode_key}"

    try:
        import dropbox as dropbox_sdk
    except ImportError:
        dropbox_sdk = None

    try:
        from dropbox_handler import DropboxHandler

        dbx = DropboxHandler()

        result = dbx.dbx.files_list_folder(clips_folder)
        mp4_files = sorted(
            entry.path_display
            for entry in result.entries
            if hasattr(entry, "name") and entry.name.lower().endswith(".mp4")
        )

        if not mp4_files:
            logger.warning("[Instagram] No mp4 files in %s", clips_folder)
            return ""

        # Match by clip index (1-based) into sorted file list
        idx = clip_num - 1
        if idx < 0 or idx >= len(mp4_files):
            logger.warning(
                "[Instagram] Clip %d out of range (%d files in %s)",
                clip_num,
                len(mp4_files),
                clips_folder,
            )
            return ""

        clip_dbx_path = mp4_files[idx]
        url = dbx.get_shared_link(clip_dbx_path)
        if url:
            logger.info(
                "[Instagram] Resolved Dropbox URL for clip_%d from %s",
                clip_num,
                clip_dbx_path,
            )
        return url or ""

    except Exception as e:
        if dropbox_sdk and isinstance(e, dropbox_sdk.exceptions.ApiError):
            logger.warning(
                "[Instagram] Could not list clips folder %s: %s", clips_folder, e
            )
            return ""
        logger.warning("[Instagram] Dropbox fallback failed: %s", e)
        return ""


def _post_instagram_reel(ig_uploader, clip_path, caption_text, youtube_url, slot):
    """Upload a clip as an Instagram Reel via Dropbox shared link.

    Args:
        ig_uploader: InstagramUploader instance.
        clip_path: Local path to the video clip.
        caption_text: Base caption text (hook or title).
        youtube_url: YouTube URL for the full episode.
        slot: Slot dict with episode metadata.

    Returns:
        Result dict from Instagram upload, or None on failure.
    """
    from dropbox_handler import DropboxHandler

    try:
        dbx = DropboxHandler()
    except Exception as e:
        logger.error("[Instagram] Dropbox not available: %s", e)
        return None

    # Upload to Dropbox
    episode_key = slot.get("episode_key", "unknown")
    clip_name = Path(clip_path).name
    dbx_dest = f"/podcast/instagram/{episode_key}/{clip_name}"

    upload_result = dbx.upload_file(clip_path, dbx_dest, overwrite=True)
    if not upload_result:
        logger.error("[Instagram] Failed to upload clip to Dropbox")
        return None

    video_url = dbx.get_shared_link(dbx_dest)
    if not video_url:
        logger.error("[Instagram] Failed to get Dropbox shared link")
        return None

    # Build caption with YouTube link
    caption = caption_text or "New clip!"
    if youtube_url:
        caption += f"\n\nWatch the full episode and find more at {youtube_url}"
    else:
        caption += f"\n\nFind all episodes on YouTube: {Config.YOUTUBE_CHANNEL_HANDLE}"

    return ig_uploader.upload_reel(video_url=video_url, caption=caption)


def post_scheduled(dry_run=False):
    """Post all pending content calendar slots that are past due.

    Args:
        dry_run: If True, log what would be posted without posting.

    Returns:
        List of result dicts.
    """
    calendar = ContentCalendar()
    pending = calendar.get_all_pending_slots()

    if not pending:
        logger.info("No pending slots to post")
        return []

    logger.info("Found %d pending slot(s) to post", len(pending))

    if dry_run:
        for slot in pending:
            logger.info(
                "[DRY RUN] Would post %s/%s: %s",
                slot["episode_key"],
                slot["slot_name"],
                slot.get("content", {}).get("caption", "")[:80],
            )
        return [{"status": "dry_run", "slots": len(pending)}]

    uploaders = _init_uploaders()
    if not uploaders:
        logger.warning("No uploaders available — marking pending slots as failed")
        for slot in pending:
            calendar.mark_slot_failed(
                slot["episode_key"],
                slot["slot_name"],
                "No uploaders available (credentials missing)",
            )
        return []

    all_results = []
    for slot in pending:
        ep_key = slot["episode_key"]
        slot_name = slot["slot_name"]
        logger.info("Posting %s / %s (%s)", ep_key, slot_name, slot.get("slot_type"))

        results = _post_slot(slot, uploaders)

        if not results:
            # No platform returned a result — all returned None silently
            expected = [p for p in slot.get("platforms", []) if p in uploaders]
            error_msg = (
                f"All platforms returned empty results (expected: {', '.join(expected)})"
                if expected
                else "No matching uploaders available"
            )
            calendar.mark_slot_failed(ep_key, slot_name, error_msg)
            logger.warning("Marked %s/%s as failed: %s", ep_key, slot_name, error_msg)
        else:
            has_errors = any(
                "error" in v for v in results.values() if isinstance(v, dict)
            )
            has_successes = any(
                isinstance(v, dict) and "error" not in v for v in results.values()
            )
            if has_successes:
                # mark_slot_uploaded handles full vs partial status automatically
                calendar.mark_slot_uploaded(ep_key, slot_name, results)
                if has_errors:
                    failed_platforms = [
                        k
                        for k, v in results.items()
                        if isinstance(v, dict) and "error" in v
                    ]
                    logger.warning(
                        "Partial success for %s/%s — failed on: %s",
                        ep_key,
                        slot_name,
                        ", ".join(failed_platforms),
                    )
                else:
                    logger.info("Marked %s/%s as uploaded", ep_key, slot_name)
            else:
                # All platforms returned error dicts
                errors = "; ".join(
                    f"{k}: {v.get('error', '?')}"
                    for k, v in results.items()
                    if isinstance(v, dict) and "error" in v
                )
                calendar.mark_slot_failed(ep_key, slot_name, errors or "Unknown error")
                logger.warning("Marked %s/%s as failed: %s", ep_key, slot_name, errors)

        all_results.append(
            {
                "episode_key": ep_key,
                "slot_name": slot_name,
                "slot_type": slot.get("slot_type"),
                "results": results,
                "posted_at": datetime.now().isoformat(),
            }
        )

    # Save log
    _save_log(all_results)

    # Send Discord summary
    if all_results:
        _send_discord_summary(all_results)

    return all_results


def _send_discord_summary(results):
    """Send a summary of posted content to Discord."""
    try:
        from notifications import DiscordNotifier

        notifier = DiscordNotifier()
        if not notifier.enabled:
            return

        full_success = []
        partial_success = []
        full_failure = []

        for r in results:
            res = r.get("results") or {}
            ok_platforms = []
            failed_platforms = []
            for platform, data in res.items():
                if isinstance(data, dict) and "error" in data:
                    failed_platforms.append(platform)
                elif isinstance(data, dict):
                    ok_platforms.append(platform)
            if not ok_platforms and failed_platforms:
                full_failure.append(r)
            elif failed_platforms:
                partial_success.append((r, ok_platforms, failed_platforms))
            else:
                full_success.append((r, ok_platforms))

        posted_count = len(full_success) + len(partial_success)
        description = ""

        for r, platforms in full_success:
            slot_type = r.get("slot_type", "")
            if slot_type.startswith("clip_"):
                label = "Clip"
            elif slot_type.startswith("quote_"):
                label = "Quote card"
            else:
                label = slot_type
            description += f"**{r['episode_key']}/{r['slot_name']}**: {label} → {', '.join(platforms)}\n"

        for r, ok_platforms, bad_platforms in partial_success:
            slot_type = r.get("slot_type", "")
            if slot_type.startswith("clip_"):
                label = "Clip"
            elif slot_type.startswith("quote_"):
                label = "Quote card"
            else:
                label = slot_type
            description += (
                f"**{r['episode_key']}/{r['slot_name']}**: {label} → {', '.join(ok_platforms)}"
                f" (failed: {', '.join(bad_platforms)})\n"
            )

        if full_failure:
            description += f"\n{len(full_failure)} slot(s) fully failed"

        if full_failure:
            color = 0xFF0000
        elif partial_success:
            color = 0xFF9900
        else:
            color = 0x00FF00

        notifier.send_notification(
            title=f"Scheduled Content Posted ({posted_count}/{len(results)})",
            description=description.strip(),
            color=color,
        )
    except Exception as e:
        logger.warning("Discord notification failed: %s", e)


def _save_log(results):
    """Append posting results to a JSONL log file."""
    log_dir = Path(Config.OUTPUT_DIR) / "scheduled_content"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "post_log.jsonl"
    with open(log_path, "a", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps(result, default=str) + "\n")
    logger.info("Logged %d result(s) to %s", len(results), log_path)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    post_scheduled(dry_run=dry_run)
