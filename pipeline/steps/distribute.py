"""Distribute step: upload to all platforms and finalize distribution."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path

from config import Config
from pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


def _upload_youtube(
    episode_number,
    video_clip_paths,
    analysis,
    full_episode_video_path,
    components: dict,
    test_mode: bool = False,
    publish_at=None,
):
    """Upload content to YouTube (full episode + clips as Shorts)."""
    uploaders = components.get("uploaders", {})
    if "youtube" not in uploaders:
        return None

    from uploaders import create_episode_metadata

    logger.info("[YouTube] Uploading content...")
    youtube_results = {"clips": [], "full_episode": None}
    social_captions = analysis.get("social_captions", {})
    episode_summary = analysis.get("episode_summary", "")
    episode_title = analysis.get("episode_title", f"Episode {episode_number}")
    best_clips = analysis.get("best_clips", [])

    show_notes = analysis.get("show_notes", "")
    chapters = analysis.get("chapters", [])

    # Upload full episode first
    if full_episode_video_path:
        logger.info("Uploading full episode to YouTube...")
        full_title = f"Episode #{episode_number} - {episode_title}"
        metadata = create_episode_metadata(
            episode_number=episode_number,
            episode_summary=episode_summary,
            social_captions=social_captions,
            show_notes=show_notes,
            chapters=chapters,
        )
        full_description = metadata["description"]
        tags = metadata["tags"]

        if test_mode:
            logger.info(
                "[TEST MODE] Would upload full episode: %s", full_episode_video_path
            )
            youtube_results["full_episode"] = {
                "status": "test_mode",
                "title": full_title,
            }
        else:
            try:
                # If scheduling, upload as private with publishAt
                privacy = "private" if publish_at else "public"
                full_episode_result = uploaders["youtube"].upload_episode(
                    video_path=str(full_episode_video_path),
                    title=full_title[:100],
                    description=full_description,
                    tags=tags,
                    privacy_status=privacy,
                    publish_at=publish_at,
                )
                if full_episode_result:
                    youtube_results["full_episode"] = full_episode_result
                    logger.info(
                        "Full episode uploaded: %s",
                        full_episode_result.get("video_url", "Unknown URL"),
                    )
                else:
                    logger.error("Failed to upload full episode")
                    youtube_results["full_episode"] = {"status": "failed"}
            except Exception as e:
                logger.error("YouTube full episode upload error: %s", e)
                youtube_results["full_episode"] = {
                    "status": "error",
                    "error": str(e),
                }

    # Upload clips as Shorts
    if video_clip_paths:
        logger.info("Uploading %d clips as YouTube Shorts...", len(video_clip_paths))
        for i, video_path in enumerate(video_clip_paths, 1):
            if i - 1 < len(best_clips):
                clip_info = best_clips[i - 1]
                yt_full_url = None
                if youtube_results.get("full_episode"):
                    yt_full_url = youtube_results["full_episode"].get("video_url")
                metadata = create_episode_metadata(
                    episode_number=episode_number,
                    episode_summary=episode_summary,
                    social_captions=social_captions,
                    clip_info=clip_info,
                    full_episode_url=yt_full_url,
                )

                clip_title = clip_info.get("suggested_title", f"Clip {i}")
                logger.info("Uploading Clip %d: %s", i, clip_title)

                if test_mode:
                    logger.info("[TEST MODE] Would upload: %s", video_path)
                    youtube_results["clips"].append(
                        {"status": "test_mode", "title": clip_title}
                    )
                else:
                    try:
                        # First 2 clips go public immediately; rest are private
                        # for staggered release via scheduled-content workflow
                        clip_privacy = "public" if i <= 2 else "private"
                        upload_result = uploaders["youtube"].upload_short(
                            video_path=str(video_path),
                            title=metadata["title"],
                            description=metadata["description"],
                            tags=metadata["tags"],
                            privacy_status=clip_privacy,
                        )
                        if upload_result:
                            youtube_results["clips"].append(upload_result)
                            logger.info(
                                "Uploaded: %s",
                                upload_result.get("video_url", "Unknown URL"),
                            )
                        else:
                            logger.error("Failed to upload clip %d", i)
                            youtube_results["clips"].append(
                                {"status": "failed", "title": clip_title}
                            )
                    except Exception as e:
                        logger.error("YouTube upload error: %s", e)
                        youtube_results["clips"].append(
                            {"status": "error", "error": str(e)}
                        )

    return youtube_results


def _upload_twitter(
    episode_number, analysis, youtube_results, components: dict, test_mode: bool = False
):
    """Upload content to Twitter (episode announcement with YouTube links)."""
    uploaders = components.get("uploaders", {})
    if "twitter" not in uploaders:
        return None

    logger.info("[Twitter] Posting content...")
    episode_summary = analysis.get("episode_summary", "")
    best_clips = analysis.get("best_clips", [])

    # Gather YouTube URLs from upload results
    yt_full_url = None
    clip_youtube_urls = []
    if youtube_results:
        if youtube_results.get("full_episode") and youtube_results["full_episode"].get(
            "video_url"
        ):
            yt_full_url = youtube_results["full_episode"]["video_url"]
        for i, clip_result in enumerate(youtube_results.get("clips", [])):
            if clip_result.get("video_url"):
                # Use title from YouTube result (already resolved via
                # suggested_title -> title -> generic fallback chain),
                # strip #Shorts suffix for Twitter display
                clip_title = clip_result.get("title", "").replace(" #Shorts", "")
                if not clip_title:
                    clip_title = (
                        best_clips[i].get(
                            "suggested_title",
                            best_clips[i].get("title", f"Clip {i + 1}"),
                        )
                        if i < len(best_clips)
                        else f"Clip {i + 1}"
                    )
                clip_youtube_urls.append(
                    {"title": clip_title, "url": clip_result["video_url"]}
                )

    # Extract top 2 unique hashtags from clip_hashtags across all clips
    all_hashtags: list = []
    for clip in best_clips:
        all_hashtags.extend(clip.get("clip_hashtags", []))
    seen: set = set()
    unique_hashtags: list = []
    for tag in all_hashtags:
        if tag not in seen:
            seen.add(tag)
            unique_hashtags.append(tag)
    top_hashtags = unique_hashtags[:2] if unique_hashtags else None

    if test_mode:
        logger.info("[TEST MODE] Skipping Twitter posts")
        logger.info("Would post: Episode %d announcement", episode_number)
        if yt_full_url:
            logger.info("Would include YouTube URL: %s", yt_full_url)
        if clip_youtube_urls:
            logger.info("Would link %d YouTube Shorts clips", len(clip_youtube_urls))
        if top_hashtags:
            logger.info("Would append hashtags: %s", top_hashtags)
        return {"status": "test_mode", "skipped": True}
    else:
        try:
            twitter_caption = analysis.get("social_captions", {}).get("twitter")
            twitter_result = uploaders["twitter"].post_episode_announcement(
                episode_number=episode_number,
                episode_summary=episode_summary,
                youtube_url=yt_full_url,
                clip_youtube_urls=clip_youtube_urls if clip_youtube_urls else None,
                twitter_caption=twitter_caption,
                hashtags=top_hashtags,
            )
            return twitter_result
        except Exception as e:
            logger.error("Twitter upload failed: %s", e)
            return {"error": str(e)}


def _upload_instagram(
    video_clip_paths,
    episode_number=None,
    analysis=None,
    components: dict = None,
    youtube_episode_url: str = None,
):
    """Upload clips to Instagram as Reels via Dropbox shared links.

    Uploads each video clip to Dropbox, gets a public link, then posts as an
    Instagram Reel with captions from the analysis.
    """
    components = components or {}
    uploaders = components.get("uploaders", {})
    ig = uploaders.get("instagram")
    dropbox = components.get("dropbox")

    if not ig or not ig.functional:
        return None

    if not video_clip_paths:
        logger.info("[Instagram] No video clips available")
        return {"status": "no_videos"}

    if not dropbox:
        logger.warning("[Instagram] Dropbox not configured — cannot get public URLs for Reels")
        return {"status": "no_dropbox"}

    # Upload ALL clips to Dropbox (needed for both immediate and staggered posting)
    # but only post first 2 as Reels immediately
    logger.info("[Instagram] Uploading %d clips to Dropbox...", len(video_clip_paths))
    best_clips = (analysis or {}).get("best_clips", [])
    results = []
    dropbox_urls = {}  # clip index -> Dropbox shared URL (for calendar slots)

    for i, clip_path in enumerate(video_clip_paths):
        clip_path = Path(clip_path)
        clip_name = clip_path.name

        # Upload clip to Dropbox and get public link
        dbx_dest = f"/podcast/instagram/ep_{episode_number}/{clip_name}"
        upload_result = dropbox.upload_file(str(clip_path), dbx_dest, overwrite=True)
        if not upload_result:
            logger.warning("[Instagram] Failed to upload clip %d to Dropbox", i + 1)
            continue

        video_url = dropbox.get_shared_link(dbx_dest)
        if not video_url:
            logger.warning("[Instagram] Failed to get shared link for clip %d", i + 1)
            continue

        dropbox_urls[i] = video_url

        # Only post first 2 clips as Reels immediately; rest staggered via calendar
        if i < 2:
            caption = _build_instagram_caption(
                i, best_clips, episode_number, analysis, youtube_episode_url
            )
            reel_result = ig.upload_reel(video_url=video_url, caption=caption)
            if reel_result:
                logger.info(
                    "[Instagram] Clip %d posted: %s",
                    i + 1,
                    reel_result.get("permalink", ""),
                )
                results.append({"clip": i + 1, "status": "success", **reel_result})
            else:
                logger.warning("[Instagram] Clip %d upload failed", i + 1)
                results.append({"clip": i + 1, "status": "upload_failed"})

    successful = sum(1 for r in results if r.get("status") == "success")
    deferred = max(0, len(video_clip_paths) - 2)
    logger.info(
        "[Instagram] %d Reels posted, %d clips pre-uploaded for calendar, %d deferred",
        successful,
        len(dropbox_urls),
        deferred,
    )
    return {
        "status": "complete",
        "results": results,
        "successful": successful,
        "deferred": deferred,
        "dropbox_urls": dropbox_urls,
    }


def _build_instagram_caption(
    clip_index, best_clips, episode_number, analysis, youtube_episode_url=None
):
    """Build an Instagram Reel caption from clip analysis data.

    Args:
        clip_index: Zero-based index of the clip.
        best_clips: List of clip info dicts from analysis.
        episode_number: Episode number.
        analysis: Full analysis dict.
        youtube_episode_url: URL to the full episode on YouTube.

    Returns:
        Caption string for the Reel.
    """
    # Try to get clip-specific caption from analysis
    if clip_index < len(best_clips):
        clip_info = best_clips[clip_index]
        hook = clip_info.get("hook_caption", "")
        tags = clip_info.get("clip_hashtags", [])
    else:
        hook = ""
        tags = []

    # Use the Instagram social caption as fallback
    social_captions = (analysis or {}).get("social_captions", {})
    ig_caption = social_captions.get("instagram", "")

    if hook:
        caption = hook
    elif ig_caption:
        caption = ig_caption
    else:
        caption = f"Episode {episode_number} clip"

    # Append CTA with YouTube link
    if youtube_episode_url:
        caption += f"\n\nWatch the full episode and find more at {youtube_episode_url}"
    else:
        caption += f"\n\nFind all episodes on YouTube: {Config.YOUTUBE_CHANNEL_HANDLE}"

    # Append hashtags
    if tags:
        tag_str = " ".join(f"#{t.lstrip('#')}" for t in tags)
        caption = f"{caption}\n\n{tag_str}"

    return caption


def _upload_tiktok(video_clip_paths, analysis, components: dict = None):
    """Log TikTok readiness (upload not yet implemented)."""
    uploaders = (components or {}).get("uploaders", {})
    if "tiktok" not in uploaders:
        return None

    logger.info("[TikTok] Uploading clips...")
    if not video_clip_paths:
        logger.info("No video clips available")
        return {"status": "no_videos"}

    logger.info("%d vertical videos ready for TikTok", len(video_clip_paths))
    best_clips = (analysis or {}).get("best_clips", [])
    for i, clip_info in enumerate(best_clips[: len(video_clip_paths)]):
        hook = clip_info.get("hook_caption", "")
        tags = clip_info.get("clip_hashtags", [])
        if hook or tags:
            logger.info("  Clip %d caption: hook=%r hashtags=%s", i + 1, hook, tags)
    return {"status": "videos_ready", "clips": len(video_clip_paths)}


def _upload_bluesky(
    episode_number, analysis, youtube_results, components: dict = None, test_mode=False
):
    """Upload episode announcement and first 2 clips to Bluesky."""
    uploaders = (components or {}).get("uploaders", {})
    if "bluesky" not in uploaders:
        return None

    if test_mode:
        logger.info("[TEST MODE] Skipping Bluesky posts")
        return {"status": "test_mode", "skipped": True}

    yt_full_url = None
    if youtube_results and youtube_results.get("full_episode"):
        yt_full_url = youtube_results["full_episode"].get("video_url")

    try:
        bluesky_caption = analysis.get("social_captions", {}).get(
            "bluesky", analysis.get("social_captions", {}).get("twitter")
        )
        result = {}
        announcement = uploaders["bluesky"].post_episode_announcement(
            episode_number=episode_number,
            episode_summary=analysis.get("episode_summary", ""),
            youtube_url=yt_full_url,
            bluesky_caption=bluesky_caption,
        )
        if announcement:
            result["announcement"] = announcement

        # Post first 2 clips with YouTube Shorts links (rest staggered via calendar)
        clip_shorts = (youtube_results or {}).get("clips", [])[:2]
        best_clips = analysis.get("best_clips", [])
        clip_posts = []
        for i, short in enumerate(clip_shorts):
            short_url = short.get("video_url")
            short_title = short.get("title", f"Clip {i + 1}")
            hook = ""
            tags = []
            if i < len(best_clips):
                hook = best_clips[i].get("hook_caption", "")
                tags = best_clips[i].get("clip_hashtags", [])[:3]
            text = hook or short_title
            if tags:
                hashtag_line = " ".join(f"#{t}" for t in tags)
                if len(text) + len(hashtag_line) + 2 <= 300:
                    text = f"{text}\n\n{hashtag_line}"
            clip_result = uploaders["bluesky"].post(
                text=text,
                url=short_url,
                url_title=short_title,
                url_description=f"{Config.PODCAST_NAME} - Episode {episode_number}",
            )
            if clip_result:
                clip_posts.append(clip_result)
        if clip_posts:
            result["clips"] = clip_posts
            logger.info("Posted %d clip(s) to Bluesky", len(clip_posts))

        return result if result else None
    except Exception as e:
        logger.error("Bluesky upload failed: %s", e)
        return {"error": str(e)}


def _upload_to_social_media(
    episode_number: int,
    mp3_path: Path,
    video_clip_paths: list,
    analysis: dict,
    components: dict,
    test_mode: bool = False,
    full_episode_video_path: str = None,
    episode_output_dir: Path = None,
) -> dict:
    """Upload episode and clips to configured social media platforms."""
    results = {}
    uploaders = components.get("uploaders", {})
    scheduler = components.get("scheduler")

    # Check if scheduling is enabled
    if scheduler and scheduler.is_scheduling_enabled():
        logger.info("Scheduling enabled — creating upload schedule")
        schedule = scheduler.create_schedule(
            episode_folder=f"ep_{episode_number}",
            episode_number=episode_number,
            analysis=analysis,
            video_clip_paths=[str(p) for p in video_clip_paths]
            if video_clip_paths
            else None,
            full_episode_video_path=str(full_episode_video_path)
            if full_episode_video_path
            else None,
            mp3_path=str(mp3_path),
        )
        schedule_path = scheduler.save_schedule(f"ep_{episode_number}", schedule)
        logger.info("Upload schedule saved to %s", schedule_path)
        results["schedule"] = {
            "path": str(schedule_path),
            "platforms": list(schedule["platforms"].keys()),
        }

    # YouTube uploads (may use publishAt if scheduled)
    publish_at = scheduler.get_optimal_publish_at("youtube") if scheduler else None
    youtube_results = _upload_youtube(
        episode_number,
        video_clip_paths,
        analysis,
        full_episode_video_path,
        components=components,
        test_mode=test_mode,
        publish_at=publish_at,
    )
    if youtube_results:
        results["youtube"] = youtube_results

    # Twitter posts (needs YouTube URLs, so runs after YouTube)
    twitter_results = _upload_twitter(
        episode_number,
        analysis,
        youtube_results,
        components=components,
        test_mode=test_mode,
    )
    if twitter_results:
        results["twitter"] = twitter_results

    # Persist platform IDs for analytics lookups (ANLYT-01)
    if episode_output_dir is not None:
        platform_ids: dict = {}
        if youtube_results:
            full_ep = youtube_results.get("full_episode") or {}
            if full_ep.get("video_id"):
                platform_ids["youtube"] = full_ep["video_id"]
        if twitter_results and isinstance(twitter_results, list) and twitter_results:
            if twitter_results[0].get("tweet_id"):
                platform_ids["twitter"] = twitter_results[0]["tweet_id"]
        if platform_ids:
            platform_ids_path = episode_output_dir / "platform_ids.json"
            with open(platform_ids_path, "w", encoding="utf-8") as f:
                json.dump(platform_ids, f, indent=2)
            logger.info("Saved platform IDs: %s", platform_ids_path)

    # Instagram Reels
    yt_episode_url = None
    if youtube_results and youtube_results.get("full_episode"):
        yt_episode_url = youtube_results["full_episode"].get("video_url")
    instagram_results = _upload_instagram(
        video_clip_paths,
        episode_number=episode_number,
        analysis=analysis,
        components=components,
        youtube_episode_url=yt_episode_url,
    )
    if instagram_results:
        results["instagram"] = instagram_results

    # TikTok
    tiktok_results = _upload_tiktok(video_clip_paths, analysis, components=components)
    if tiktok_results:
        results["tiktok"] = tiktok_results

    # Bluesky
    bluesky_results = _upload_bluesky(
        episode_number,
        analysis,
        youtube_results,
        components=components,
        test_mode=test_mode,
    )
    if bluesky_results:
        results["bluesky"] = bluesky_results

    # Reddit
    if "reddit" in uploaders:
        yt_full_url = None
        if youtube_results and youtube_results.get("full_episode"):
            yt_full_url = youtube_results["full_episode"].get("video_url")
        if test_mode:
            logger.info("[TEST MODE] Skipping Reddit posts")
            results["reddit"] = {"status": "test_mode", "skipped": True}
        else:
            try:
                episode_title = analysis.get("episode_title", "")
                reddit_results = uploaders["reddit"].post_episode_announcement(
                    episode_number=episode_number,
                    episode_summary=analysis.get("episode_summary", ""),
                    youtube_url=yt_full_url,
                    episode_title=episode_title,
                )
                if reddit_results:
                    results["reddit"] = reddit_results
            except Exception as e:
                logger.error("Reddit upload failed: %s", e)
                results["reddit"] = {"error": str(e)}

    # Spotify (RSS feed — updated after Dropbox upload in Step 7.5)
    if "spotify" in uploaders:
        logger.info("[Spotify] RSS feed will be updated after Dropbox upload")
        results["spotify"] = {
            "status": "rss_ready",
            "note": "RSS feed updated in Step 7.5",
        }

    # Aggregated error summary
    errors = {k: v for k, v in results.items() if isinstance(v, dict) and "error" in v}
    if errors:
        logger.warning(
            "Upload errors on %d platform(s): %s",
            len(errors),
            ", ".join(errors.keys()),
        )

    return results


def run_distribute(
    ctx: PipelineContext,
    components: dict,
    state=None,
) -> PipelineContext:
    """Run Steps 7, 7.5, 8, 8.5, 9: Dropbox, RSS, social media, blog, search."""
    analysis = ctx.analysis or {}
    episode_number = ctx.episode_number
    episode_folder = ctx.episode_folder
    episode_output_dir = ctx.episode_output_dir
    timestamp = ctx.timestamp
    mp3_path = ctx.mp3_path
    clip_paths = ctx.clip_paths or []
    video_clip_paths = ctx.video_clip_paths or []
    full_episode_video_path = ctx.full_episode_video_path
    transcript_data = ctx.transcript_data
    chapters_list = analysis.get("chapters", [])
    uploaders = components.get("uploaders", {})

    # Compliance gate: block uploads on critical violations unless --force
    compliance_result = ctx.compliance_result or {}
    if compliance_result.get("critical") and not ctx.force:
        print("[BLOCKED] Critical compliance violation detected -- uploads skipped.")
        print("  Run with --force to override and upload anyway.")
        report_path = compliance_result.get("report_path", "see output dir")
        print(f"  Report: {report_path}")
        print()
        return ctx  # Skip all uploads

    # Step 7: Upload to Dropbox
    print("STEP 7: UPLOAD TO DROPBOX")
    print("-" * 60)

    if ctx.test_mode:
        logger.info("[TEST MODE] Skipping Dropbox uploads")
        logger.info("Would upload: %s", mp3_path)
        logger.info("Would upload %d clips", len(clip_paths))
        finished_path = None
        uploaded_clip_paths = []
    elif "dropbox" not in components or components["dropbox"] is None:
        logger.info("Dropbox not configured — skipping upload")
        finished_path = None
        uploaded_clip_paths = []
    else:
        dropbox = components["dropbox"]
        # Upload censored MP3 to finished_files folder
        logger.info("Uploading censored audio to finished_files...")
        # Use episode title for filename (sanitize for filesystem)
        episode_title = analysis.get("episode_title", f"Episode {episode_number}")
        safe_title = "".join(
            c for c in episode_title if c.isalnum() or c in (" ", "-", "_")
        ).strip()
        finished_filename = f"Episode #{episode_number} - {safe_title}.mp3"
        finished_path = dropbox.upload_finished_episode(
            mp3_path, episode_name=finished_filename
        )

        if finished_path:
            logger.info("Censored audio uploaded to: %s", finished_path)
        else:
            logger.error(
                "Failed to upload censored audio to Dropbox - suggest rerunning with --resume"
            )
            # Fail-fast: skip social media if Dropbox upload fails
            finished_path = None

        # Upload clips to clips folder
        logger.info("Uploading clips to Dropbox...")
        uploaded_clip_paths = dropbox.upload_clips(
            clip_paths, episode_folder_name=episode_folder
        )

        if uploaded_clip_paths:
            logger.info("Uploaded %d clips", len(uploaded_clip_paths))
            for clip_path in uploaded_clip_paths:
                logger.debug("  - %s", clip_path)
        else:
            logger.warning("Failed to upload clips")

    ctx.finished_path = finished_path
    ctx.uploaded_clip_paths = uploaded_clip_paths

    # Step 7.5: Update RSS feed (if Spotify uploader configured and Dropbox upload succeeded)
    if not ctx.test_mode and finished_path and "spotify" in uploaders:
        print("\nSTEP 7.5: UPDATING RSS FEED")
        print("-" * 60)

        try:
            dropbox = components["dropbox"]
            # Get or create shared link for the MP3
            logger.info("Creating shared link for episode...")
            audio_url = dropbox.get_shared_link(finished_path)

            if audio_url:
                logger.info("Shared link created: %s...", audio_url[:60])

                # Get MP3 file info
                mp3_file_size = os.path.getsize(mp3_path)

                # Get duration from transcript (use ctx data, not file)
                episode_duration = int((transcript_data or {}).get("duration", 3600))

                # Generate chapters JSON for podcast apps
                chapters_json_url = None
                chapter_generator = components.get("chapter_generator")
                if chapter_generator and chapter_generator.enabled and chapters_list:
                    ep_output_dir = Config.OUTPUT_DIR / f"ep_{episode_number}"
                    ep_output_dir.mkdir(parents=True, exist_ok=True)
                    chapters_json_path = str(ep_output_dir / "chapters.json")
                    chapter_generator.generate_chapters_json(
                        chapters_list, chapters_json_path
                    )
                    logger.info("Chapters JSON written to %s", chapters_json_path)
                    # chapters_json_url remains None until a public URL is available;
                    # the file is written locally for future upload enhancement.

                # Generate episode title and description
                episode_summary = analysis.get("episode_summary", "")
                show_notes = analysis.get("show_notes", "")
                ai_title = analysis.get("episode_title", "")
                episode_title = (
                    f"Episode #{episode_number} - {ai_title}"
                    if ai_title
                    else f"Episode #{episode_number}"
                )

                # Build rich episode description for RSS
                rss_description = show_notes or episode_summary
                if chapters_list:
                    chapter_lines = [
                        f"{ch.get('start_timestamp', '')} {ch.get('title', '')}"
                        for ch in chapters_list
                    ]
                    rss_description += "\n\nChapters:\n" + "\n".join(chapter_lines)

                # Extract keywords from social captions
                keywords = []
                if analysis.get("social_captions"):
                    keywords = [
                        "podcast",
                        Config.PODCAST_NAME.lower().replace(" ", "-"),
                    ]

                # Update RSS feed
                rss_feed_path = uploaders["spotify"].update_rss_feed(
                    episode_number=episode_number,
                    episode_title=episode_title,
                    episode_description=rss_description,
                    audio_url=audio_url,
                    audio_file_size=mp3_file_size,
                    duration_seconds=episode_duration,
                    pub_date=datetime.now(),
                    keywords=keywords,
                    chapters_url=chapters_json_url,
                )

                logger.info("RSS feed updated successfully!")
                logger.info("Feed location: %s", rss_feed_path)

                # Upload RSS feed to Dropbox
                logger.info("Uploading RSS feed to Dropbox...")
                rss_dropbox_path = "/podcast/podcast_feed.xml"
                dropbox.upload_file(rss_feed_path, rss_dropbox_path, overwrite=True)
                logger.info("RSS feed uploaded to Dropbox: %s", rss_dropbox_path)
                logger.info("Spotify will check for updates within 2-8 hours")

            else:
                logger.warning("Could not create shared link for RSS feed")

        except Exception as e:
            logger.error("RSS feed update failed: %s", e)
            import traceback

            traceback.print_exc()

    print()

    # Step 8: Social media uploading
    print("STEP 8: SOCIAL MEDIA PLATFORMS")
    print("-" * 60)

    social_media_results = {}

    if ctx.test_mode:
        logger.info("[TEST MODE] Skipping social media uploads")
        social_media_results = {"test_mode": True, "skipped": True}
    elif not uploaders:
        logger.info("No social media uploaders configured")
        logger.info("Set up API credentials in .env file to enable uploads")
    else:
        social_media_results = _upload_to_social_media(  # noqa: F841
            episode_number=episode_number,
            mp3_path=mp3_path,
            video_clip_paths=video_clip_paths,
            analysis=analysis,
            components=components,
            test_mode=ctx.test_mode,
            full_episode_video_path=full_episode_video_path,
            episode_output_dir=episode_output_dir,
        )

    print()

    # Step 8.5: Generate blog post
    print("STEP 8.5: GENERATING BLOG POST")
    print("-" * 60)
    blog_post_path = None
    blog_generator = components.get("blog_generator")
    if blog_generator and blog_generator.enabled:
        if state and state.is_step_completed("blog_post"):
            outputs = state.get_step_outputs("blog_post")
            blog_post_path = outputs.get("blog_post_path")
            logger.info("[RESUME] Skipping blog post (already completed)")
        else:
            try:
                markdown = blog_generator.generate_blog_post(
                    transcript_data=transcript_data,
                    analysis=analysis,
                    episode_number=episode_number,
                )
                blog_post_path = str(
                    blog_generator.save_blog_post(
                        markdown=markdown,
                        episode_output_dir=episode_output_dir,
                        episode_number=episode_number,
                        timestamp=timestamp,
                        analysis=analysis,
                    )
                )
                logger.info("Blog post generated: %s", blog_post_path)
                if state:
                    state.complete_step("blog_post", {"blog_post_path": blog_post_path})
            except Exception as e:
                logger.warning("Blog post generation failed: %s", e)
    else:
        logger.info("Blog post generation disabled or not configured")
    print()

    # Step 8.6: Deploy episode webpage
    print("STEP 8.6: DEPLOYING EPISODE WEBPAGE")
    print("-" * 60)
    webpage_generator = components.get("webpage_generator")
    if webpage_generator and webpage_generator.enabled:
        try:
            page_url = webpage_generator.generate_and_deploy(
                episode_number=episode_number,
                analysis=analysis,
                transcript_data=transcript_data,
            )
            if page_url:
                logger.info("Episode webpage deployed: %s", page_url)
        except Exception as e:
            logger.warning("Webpage deployment failed: %s", e)
    else:
        logger.info("Webpage deployment disabled or not configured")
    print()

    # Step 8.65: Generate quote cards
    try:
        from quote_card_generator import QuoteCardGenerator

        qcg = QuoteCardGenerator()
        if qcg.enabled and analysis.get("best_quotes"):
            quote_card_paths = qcg.generate_all_quote_cards(
                analysis, episode_number, str(episode_output_dir)
            )
            if quote_card_paths:
                logger.info("Generated %d quote card(s)", len(quote_card_paths))
                ctx.quote_card_paths = quote_card_paths
        else:
            logger.info("Quote card generation skipped (disabled or no quotes)")
    except Exception as e:
        logger.warning("Quote card generation failed: %s", e)

    # Step 8.7: Generate content calendar
    print("STEP 8.7: CONTENT CALENDAR")
    print("-" * 60)
    try:
        from content_calendar import ContentCalendar

        calendar = ContentCalendar()
        if calendar.enabled:
            entry = calendar.plan_episode(
                episode_number=episode_number,
                release_date=datetime.now(),
                analysis=analysis,
                video_clip_paths=[str(p) for p in video_clip_paths]
                if video_clip_paths
                else None,
                full_episode_video_path=str(full_episode_video_path)
                if full_episode_video_path
                else None,
            )
            slot_count = len(entry.get("slots", {}))
            logger.info(
                "Content calendar generated: %d slots for ep %s",
                slot_count,
                episode_number,
            )

            # Persist YouTube URLs into calendar slots for staggered social posting
            ep_key = f"ep_{episode_number}"
            yt_results = social_media_results.get("youtube", {})

            # Full episode URL -> episode slot
            full_ep = yt_results.get("full_episode") or {}
            if full_ep.get("video_url"):
                calendar.update_slot_content(
                    ep_key,
                    "episode",
                    {
                        "youtube_url": full_ep["video_url"],
                        "youtube_video_id": full_ep.get("video_id", ""),
                    },
                )

            # Shorts URLs -> clip slots
            shorts = yt_results.get("clips", [])
            best_clips = analysis.get("best_clips", [])
            for i, short in enumerate(shorts):
                slot_name = f"clip_{i + 1}"
                clip_title = ""
                clip_caption = ""
                if i < len(best_clips):
                    clip_title = best_clips[i].get("suggested_title", "")
                    clip_caption = best_clips[i].get("hook_caption", "")
                calendar.update_slot_content(
                    ep_key,
                    slot_name,
                    {
                        "youtube_url": short.get("video_url", ""),
                        "youtube_video_id": short.get("video_id", ""),
                        "clip_title": clip_title,
                        "caption": clip_caption,
                    },
                )

            # Hot take -> teaser slot
            hot_take = analysis.get("hot_take", "")
            if hot_take:
                calendar.update_slot_content(
                    ep_key,
                    "teaser",
                    {"caption": hot_take},
                )

            # Instagram Dropbox URLs -> clip slots (for staggered Reel posting from CI)
            ig_results = social_media_results.get("instagram", {})
            ig_dropbox_urls = ig_results.get("dropbox_urls", {})
            for clip_idx, dbx_url in ig_dropbox_urls.items():
                # clip_idx is 0-based; clips 3+ are in stagger slots
                clip_num = clip_idx + 1
                slot_name = f"clip_{clip_num}"
                calendar.update_slot_content(
                    ep_key,
                    slot_name,
                    {"instagram_video_url": dbx_url},
                )
            if ig_dropbox_urls:
                logger.info(
                    "Persisted %d Instagram Dropbox URLs to calendar slots",
                    len(ig_dropbox_urls),
                )

            logger.info("Persisted YouTube URLs to content calendar slots")
        else:
            logger.info("Content calendar disabled")
    except Exception as e:
        logger.warning("Content calendar generation failed: %s", e)
    print()

    # Step 8.8: Update website landing page
    print("STEP 8.8: UPDATING WEBSITE LANDING PAGE")
    print("-" * 60)
    website_generator = components.get("website_generator")
    if website_generator and website_generator.enabled:
        if state and state.is_step_completed("website"):
            logger.info("[RESUME] Skipping website update (already completed)")
        else:
            try:
                site_url = website_generator.generate_and_deploy()
                if site_url:
                    logger.info("Website updated: %s", site_url)
                if state:
                    state.complete_step("website", {"site_url": site_url or ""})
            except Exception as e:
                logger.warning("Website update failed: %s", e)
    else:
        logger.info("Website generation disabled or not configured")
    print()

    # Step 9: Index episode for search
    print("STEP 9: INDEXING EPISODE FOR SEARCH")
    print("-" * 60)
    search_index = components.get("search_index")
    if search_index:
        try:
            full_transcript = " ".join(
                seg.get("text", "") for seg in transcript_data.get("segments", [])
            )
            search_index.index_episode(
                episode_number=episode_number,
                title=analysis.get("episode_title", f"Episode {episode_number}"),
                summary=analysis.get("episode_summary", ""),
                show_notes=analysis.get("show_notes", ""),
                transcript_text=full_transcript,
                topics=[
                    c.get("description", "") for c in analysis.get("best_clips", [])
                ],
            )
            logger.info("Episode %s indexed for search", episode_number)
        except Exception as e:
            logger.warning("Search indexing failed: %s", e)
    else:
        logger.info("Search index not available")
    print()

    return ctx


def run_distribute_only(
    episode_number: int,
    skip_video: bool = False,
    skip_upload: bool = False,
) -> None:
    """Re-run distribution for an already-processed episode.

    Builds a PipelineContext from existing files on disk for the given
    episode_number, initialises only distribution components, and calls
    run_distribute(ctx, components).  This replaces continue_episode.py.
    """
    from datetime import datetime

    from dropbox_handler import DropboxHandler
    from uploaders import (
        YouTubeUploader,
        TwitterUploader,
        SpotifyUploader,
        InstagramUploader,
        TikTokUploader,
        BlueskyUploader,
        RedditUploader,
    )
    from scheduler import UploadScheduler
    from blog_generator import BlogPostGenerator
    from search_index import EpisodeSearchIndex
    from chapter_generator import ChapterGenerator
    from episode_webpage_generator import EpisodeWebpageGenerator

    print("=" * 60)
    print(f"CONTINUING EPISODE {episode_number} PROCESSING")
    print("=" * 60)
    print()

    episode_folder = f"ep_{episode_number}"
    episode_output_dir = Config.OUTPUT_DIR / episode_folder
    clips_dir = episode_output_dir / "clips"

    if not episode_output_dir.exists():
        raise FileNotFoundError(
            f"Episode output directory not found: {episode_output_dir}"
        )

    # Locate censored WAV
    censored_wavs = list(episode_output_dir.glob("*_censored.wav"))
    if not censored_wavs:
        raise FileNotFoundError(f"No censored WAV found in: {episode_output_dir}")
    censored_audio = censored_wavs[0]

    # Load analysis
    analysis_files = list(episode_output_dir.glob("*_analysis.json"))
    if not analysis_files:
        raise FileNotFoundError(f"No analysis JSON found in: {episode_output_dir}")
    with open(analysis_files[0], "r", encoding="utf-8") as f:
        analysis = json.load(f)

    # Load transcript
    transcript_data: dict = {}
    transcript_path = None
    transcript_files = list(episode_output_dir.glob("*_transcript.json"))
    if transcript_files:
        transcript_path = transcript_files[0]
        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript_data = json.load(f)

    # Find MP3 (may already exist)
    mp3_files = list(episode_output_dir.glob("*.mp3"))
    mp3_path = mp3_files[0] if mp3_files else None

    # Find video clips
    video_clip_paths: list = []
    if clips_dir.exists() and not skip_video:
        video_clip_paths = sorted(clips_dir.glob("*.mp4"))

    # Find full episode video
    full_episode_video_path = None
    video_files = list(episode_output_dir.glob("*_episode*.mp4"))
    if video_files:
        full_episode_video_path = str(video_files[0])

    # Build PipelineContext from existing files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ctx = PipelineContext(
        episode_folder=episode_folder,
        episode_number=episode_number,
        episode_output_dir=episode_output_dir,
        timestamp=timestamp,
        audio_file=censored_audio,
        censored_audio=censored_audio,
        transcript_data=transcript_data,
        transcript_path=transcript_path,
        analysis=analysis,
        mp3_path=mp3_path,
        video_clip_paths=list(video_clip_paths),
        full_episode_video_path=full_episode_video_path,
        test_mode=skip_upload,
    )

    # Initialise only distribution components
    uploaders: dict = {}

    try:
        dropbox = DropboxHandler()
    except Exception as e:
        logger.warning("Dropbox not available: %s", e)
        dropbox = None

    try:
        uploaders["youtube"] = YouTubeUploader()
        logger.info("YouTube uploader initialized")
    except Exception as e:
        logger.info("YouTube not available: %s", str(e).split("\n")[0])

    if Config.TWITTER_ENABLED:
        try:
            uploaders["twitter"] = TwitterUploader()
            logger.info("Twitter uploader initialized")
        except Exception as e:
            logger.info("Twitter not available: %s", str(e).split("\n")[0])
    else:
        logger.info("[SKIP] Twitter: disabled (TWITTER_ENABLED=false)")

    try:
        uploaders["spotify"] = SpotifyUploader()
        logger.info("Spotify uploader initialized")
    except Exception as e:
        logger.info("Spotify not available: %s", str(e).split("\n")[0])

    try:
        uploaders["instagram"] = InstagramUploader()
        logger.info("Instagram uploader initialized")
    except Exception as e:
        logger.info("Instagram not available: %s", str(e).split("\n")[0])

    try:
        uploaders["tiktok"] = TikTokUploader()
        logger.info("TikTok uploader initialized")
    except Exception as e:
        logger.info("TikTok not available: %s", str(e).split("\n")[0])

    try:
        uploaders["bluesky"] = BlueskyUploader()
        logger.info("Bluesky uploader initialized")
    except (ValueError, Exception) as e:
        logger.info("[SKIP] Bluesky: %s", str(e).split("\n")[0])

    try:
        uploaders["reddit"] = RedditUploader()
        logger.info("Reddit uploader initialized")
    except (ValueError, Exception) as e:
        logger.info("[SKIP] Reddit: %s", str(e).split("\n")[0])

    try:
        scheduler = UploadScheduler()
    except Exception as e:
        logger.warning("Scheduler not available: %s", e)
        scheduler = None

    try:
        blog_generator = BlogPostGenerator()
    except Exception as e:
        logger.warning("Blog generator not available: %s", e)
        blog_generator = None

    try:
        search_index = EpisodeSearchIndex()
    except Exception as e:
        logger.warning("Search index not available: %s", e)
        search_index = None

    try:
        chapter_generator = ChapterGenerator()
    except Exception as e:
        logger.warning("Chapter generator not available: %s", e)
        chapter_generator = None

    try:
        webpage_generator = EpisodeWebpageGenerator()
    except Exception as e:
        logger.warning("Webpage generator not available: %s", e)
        webpage_generator = None

    components = {
        "dropbox": dropbox,
        "uploaders": uploaders,
        "scheduler": scheduler,
        "blog_generator": blog_generator,
        "search_index": search_index,
        "chapter_generator": chapter_generator,
        "webpage_generator": webpage_generator,
    }

    run_distribute(ctx, components, state=None)
