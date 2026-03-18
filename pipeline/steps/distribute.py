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
        for i, video_path in enumerate(video_clip_paths[:3], 1):
            if i - 1 < len(best_clips):
                clip_info = best_clips[i - 1]
                metadata = create_episode_metadata(
                    episode_number=episode_number,
                    episode_summary=episode_summary,
                    social_captions=social_captions,
                    clip_info=clip_info,
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
                        upload_result = uploaders["youtube"].upload_short(
                            video_path=str(video_path),
                            title=metadata["title"],
                            description=metadata["description"],
                            tags=metadata["tags"],
                            privacy_status="public",
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

    if test_mode:
        logger.info("[TEST MODE] Skipping Twitter posts")
        logger.info("Would post: Episode %d announcement", episode_number)
        if yt_full_url:
            logger.info("Would include YouTube URL: %s", yt_full_url)
        if clip_youtube_urls:
            logger.info("Would link %d YouTube Shorts clips", len(clip_youtube_urls))
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
            )
            return twitter_result
        except Exception as e:
            logger.error("Twitter upload failed: %s", e)
            return {"error": str(e)}


def _upload_instagram(
    video_clip_paths, episode_number=None, analysis=None, components: dict = None
):
    """Upload clips to Instagram as Reels."""
    uploaders = (components or {}).get("uploaders", {})
    if "instagram" not in uploaders:
        return None

    logger.info("[Instagram] Uploading Reels...")
    if video_clip_paths:
        logger.info(
            "%d vertical videos ready for Instagram Reels", len(video_clip_paths)
        )
        logger.info("Instagram requires publicly accessible video URLs")
        logger.info(
            "Upload videos to Dropbox and get public links to enable auto-upload"
        )
        # Log prepared captions with hook + hashtags
        if analysis:
            best_clips = analysis.get("best_clips", [])
            for i, clip_info in enumerate(best_clips[: len(video_clip_paths)]):
                hook = clip_info.get("hook_caption", "")
                tags = clip_info.get("clip_hashtags", [])
                if hook or tags:
                    logger.info(
                        "  Clip %d caption: hook=%r hashtags=%s",
                        i + 1,
                        hook,
                        tags,
                    )
        return {"status": "videos_ready", "clips": len(video_clip_paths)}
    else:
        logger.info("No video clips available")
        return {"status": "no_videos"}


def _upload_to_social_media(
    episode_number: int,
    mp3_path: Path,
    video_clip_paths: list,
    analysis: dict,
    components: dict,
    test_mode: bool = False,
    full_episode_video_path: str = None,
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
    publish_at = scheduler.get_youtube_publish_at() if scheduler else None
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

    # Instagram Reels
    instagram_results = _upload_instagram(
        video_clip_paths,
        episode_number=episode_number,
        analysis=analysis,
        components=components,
    )
    if instagram_results:
        results["instagram"] = instagram_results

    # TikTok
    if "tiktok" in uploaders:
        logger.info("[TikTok] Uploading clips...")
        if video_clip_paths:
            logger.info("%d vertical videos ready for TikTok", len(video_clip_paths))
            logger.info("Ready to upload (upload code commented out for safety)")
            # Log prepared captions with hook + hashtags
            best_clips = analysis.get("best_clips", [])
            for i, clip_info in enumerate(best_clips[: len(video_clip_paths)]):
                hook = clip_info.get("hook_caption", "")
                tags = clip_info.get("clip_hashtags", [])
                if hook or tags:
                    logger.info(
                        "  Clip %d caption: hook=%r hashtags=%s",
                        i + 1,
                        hook,
                        tags,
                    )
            results["tiktok"] = {
                "status": "videos_ready",
                "clips": len(video_clip_paths),
            }
        else:
            logger.info("No video clips available")
            results["tiktok"] = {"status": "no_videos"}

    # Spotify (RSS feed — updated after Dropbox upload in Step 7.5)
    if "spotify" in uploaders:
        logger.info("[Spotify] RSS feed will be updated after Dropbox upload")
        results["spotify"] = {
            "status": "rss_ready",
            "note": "RSS feed updated in Step 7.5",
        }

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
    transcript_path = ctx.transcript_path
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

                # Get duration from transcript
                with open(transcript_path, "r", encoding="utf-8") as f:
                    transcript_data = json.load(f)
                    episode_duration = int(transcript_data.get("duration", 3600))

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
                    keywords = ["podcast", "comedy", "fake-problems"]

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
    clips_dir = Config.CLIPS_DIR / episode_folder

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

    try:
        uploaders["twitter"] = TwitterUploader()
        logger.info("Twitter uploader initialized")
    except Exception as e:
        logger.info("Twitter not available: %s", str(e).split("\n")[0])

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
