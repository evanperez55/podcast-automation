"""Re-post episode announcements to Twitter/X with correct titles and YouTube links.

Usage:
    python repost_twitter.py --dry-run       # Preview what would be posted
    python repost_twitter.py                  # Actually post
    python repost_twitter.py --episode 28     # Re-post a single episode
"""

import argparse
import json
import time
from config import Config
from logger import logger

# Delay between episode threads to avoid spam detection (seconds)
INTER_EPISODE_DELAY = 300  # 5 minutes between episodes


def load_episode_data(episode_number):
    """Load results and analysis data for an episode.

    Returns dict with youtube_url, clip_youtube_urls, episode_summary,
    twitter_caption, episode_number, or None if insufficient data.
    """
    output_dir = Config.OUTPUT_DIR / f"ep_{episode_number}"
    if not output_dir.exists():
        logger.warning("No output directory for episode %d", episode_number)
        return None

    # Find the latest results file
    results_files = sorted(output_dir.glob("*_results.json"))
    if not results_files:
        logger.warning("No results files for episode %d", episode_number)
        return None

    # Use the latest results file
    results_path = results_files[-1]
    with open(results_path, encoding="utf-8") as f:
        results = json.load(f)

    # Extract YouTube full episode URL (handle both result structures)
    youtube_url = None
    clip_youtube_urls = []

    # Structure 1: social_media_results.youtube (ep 25, 28)
    sm_results = results.get("social_media_results", {})
    yt_results = sm_results.get("youtube", {})
    if yt_results:
        full_ep = yt_results.get("full_episode", {})
        if full_ep.get("video_url"):
            youtube_url = full_ep["video_url"]
        for clip in yt_results.get("clips", []):
            if clip.get("video_url"):
                clip_youtube_urls.append(clip)

    # Structure 2: youtube_full_episode / youtube_shorts (ep 26)
    if not youtube_url and results.get("youtube_full_episode", {}).get("video_url"):
        youtube_url = results["youtube_full_episode"]["video_url"]
    if not clip_youtube_urls and results.get("youtube_shorts"):
        clip_youtube_urls = [c for c in results["youtube_shorts"] if c.get("video_url")]

    if not youtube_url and not clip_youtube_urls:
        logger.warning("No YouTube URLs found for episode %d", episode_number)
        return None

    # Get clip titles from best_clips_info (results) or analysis file
    best_clips = results.get("best_clips_info", [])

    # Resolve clip titles: prefer suggested_title from analysis, fall back to
    # YouTube result title (strip #Shorts), fall back to generic
    resolved_clips = []
    for i, clip in enumerate(clip_youtube_urls):
        title = None
        # Try best_clips_info first
        if i < len(best_clips):
            title = best_clips[i].get("suggested_title") or best_clips[i].get("title")
        # Fall back to YouTube result title
        if not title:
            yt_title = clip.get("title", "")
            yt_title = yt_title.replace(" #Shorts", "")
            # Skip generic titles
            if yt_title and "Clip" not in yt_title and "clip" not in yt_title:
                title = yt_title
        if not title:
            title = f"Clip {i + 1}"
        resolved_clips.append({"title": title, "url": clip["video_url"]})

    # Get twitter caption and episode summary
    twitter_caption = None
    episode_summary = results.get("episode_summary", "")

    # Check results first for social_captions
    if results.get("social_captions", {}).get("twitter"):
        twitter_caption = results["social_captions"]["twitter"]

    # Fall back to analysis file
    if not twitter_caption:
        analysis_files = sorted(output_dir.glob("*_analysis.json"))
        if analysis_files:
            with open(analysis_files[-1], encoding="utf-8") as f:
                analysis = json.load(f)
            twitter_caption = analysis.get("social_captions", {}).get("twitter")
            if not episode_summary:
                episode_summary = analysis.get("episode_summary", "")

    return {
        "episode_number": episode_number,
        "youtube_url": youtube_url,
        "clip_youtube_urls": resolved_clips,
        "episode_summary": episode_summary,
        "twitter_caption": twitter_caption,
    }


def repost_episode(episode_data, dry_run=False):
    """Post an episode announcement thread to Twitter."""
    ep_num = episode_data["episode_number"]
    youtube_url = episode_data["youtube_url"]
    clips = episode_data["clip_youtube_urls"]
    summary = episode_data["episode_summary"]
    twitter_caption = episode_data["twitter_caption"]

    logger.info("=== Episode %d ===", ep_num)
    logger.info("YouTube URL: %s", youtube_url)
    logger.info("Clips: %d", len(clips))
    for clip in clips:
        logger.info("  - %s: %s", clip["title"], clip["url"])
    if twitter_caption:
        logger.info("Caption: %s", twitter_caption[:100])

    if dry_run:
        logger.info("[DRY RUN] Would post episode %d announcement thread", ep_num)
        return {"status": "dry_run", "episode": ep_num}

    from uploaders.twitter_uploader import TwitterUploader

    uploader = TwitterUploader()
    result = uploader.post_episode_announcement(
        episode_number=ep_num,
        episode_summary=summary,
        youtube_url=youtube_url,
        clip_youtube_urls=clips if clips else None,
        twitter_caption=twitter_caption,
    )

    if result:
        logger.info("Episode %d posted successfully!", ep_num)
    else:
        logger.error("Episode %d posting failed!", ep_num)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Re-post episode announcements to Twitter/X"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview without posting"
    )
    parser.add_argument(
        "--episode", type=int, help="Re-post a single episode (default: 25, 26, 28)"
    )
    args = parser.parse_args()

    episodes_to_post = [args.episode] if args.episode else [25, 26, 28]

    # Load all episode data first
    episodes = []
    for ep_num in episodes_to_post:
        data = load_episode_data(ep_num)
        if data:
            episodes.append(data)
        else:
            logger.warning("Skipping episode %d — insufficient data", ep_num)

    if not episodes:
        logger.error("No episodes to post")
        return

    logger.info("Will post %d episode(s): %s", len(episodes), episodes_to_post)

    for i, episode_data in enumerate(episodes):
        repost_episode(episode_data, dry_run=args.dry_run)

        # Wait between episodes to avoid spam detection
        if not args.dry_run and i < len(episodes) - 1:
            logger.info(
                "Waiting %d seconds before next episode...", INTER_EPISODE_DELAY
            )
            time.sleep(INTER_EPISODE_DELAY)

    logger.info("Done!")


if __name__ == "__main__":
    main()
