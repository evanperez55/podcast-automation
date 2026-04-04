"""Analytics and backfill commands extracted from pipeline/runner.py."""

import re
import json
import time
from datetime import datetime

from config import Config
from logger import logger


def run_analytics(episode_arg):
    """Collect and display analytics for episodes."""
    from analytics import AnalyticsCollector, TopicEngagementScorer

    print("=" * 60)
    print("ANALYTICS FEEDBACK LOOP")
    print("=" * 60)
    print()

    collector = AnalyticsCollector()
    scorer = TopicEngagementScorer()

    if episode_arg == "all":
        # Scan output dirs for episode numbers
        output_dir = Config.OUTPUT_DIR
        ep_dirs = sorted(output_dir.glob("ep_*"))
        for ep_dir in ep_dirs:
            match = re.search(r"ep_(\d+)", ep_dir.name)
            if match:
                ep_num = int(match.group(1))
                _collect_episode_analytics(collector, scorer, ep_num)
    else:
        match = re.search(r"(\d+)", episode_arg)
        if match:
            ep_num = int(match.group(1))
            _collect_episode_analytics(collector, scorer, ep_num)
        else:
            print(f"Invalid episode: {episode_arg}")


def _collect_episode_analytics(collector, scorer, episode_number):
    """Collect and display analytics for a single episode.

    Loads stored platform IDs (written at upload time) to pass the YouTube
    video_id directly to fetch_youtube_analytics, avoiding the expensive
    search API call (100 quota units -> 1 quota unit).

    After collecting metrics, appends/updates the cross-episode
    engagement_history.json for Phase 10 correlation scoring.
    """
    print(f"\n--- Episode {episode_number} ---")

    # Load stored platform IDs for direct video ID lookup
    platform_ids = collector._load_platform_ids(episode_number)
    video_id = platform_ids.get("youtube")

    # Collect analytics — pass video_id to skip search API when available
    analytics = collector.collect_analytics(episode_number, video_id=video_id)
    collector.save_analytics(episode_number, analytics)

    score = scorer.calculate_engagement_score(analytics)
    print(f"  Engagement score: {score}/10")

    if analytics.get("youtube"):
        yt = analytics["youtube"]
        print(f"  YouTube: {yt.get('views', 0)} views, {yt.get('likes', 0)} likes")
    if analytics.get("twitter"):
        tw = analytics["twitter"]
        print(
            f"  Twitter: {tw.get('impressions', 0)} impressions, "
            f"{tw.get('engagements', 0)} engagements"
        )

    # Accumulate engagement history — determine post_timestamp from platform_ids.json mtime
    platform_ids_path = Config.OUTPUT_DIR / f"ep_{episode_number}" / "platform_ids.json"
    if platform_ids_path.exists():
        import os

        post_timestamp = datetime.fromtimestamp(
            os.path.getmtime(platform_ids_path)
        ).isoformat()
    else:
        post_timestamp = datetime.now().isoformat()

    # Extract topics from analytics data (video_id present implies analysis ran)
    # Topics are derived from episode analysis JSON in the output dir
    topics = _load_episode_topics(episode_number)

    collector.append_to_engagement_history(
        episode_number=episode_number,
        analytics_data=analytics,
        platform_ids=platform_ids,
        topics=topics,
        post_timestamp=post_timestamp,
    )
    logger.info("Updated engagement history for Episode #%s", episode_number)


def _load_episode_topics(episode_number: int) -> list:
    """Extract topic strings from episode analysis JSON.

    Looks for *_analysis.json in the episode output dir and extracts
    suggested_title from best_clips entries (same pattern as correlate_topics).

    Args:
        episode_number: The episode number to load topics for.

    Returns:
        List of topic strings, or empty list if not found.
    """
    ep_dir = Config.OUTPUT_DIR / f"ep_{episode_number}"
    if not ep_dir.exists():
        return []

    analysis_files = list(ep_dir.glob("*_analysis.json"))
    if not analysis_files:
        return []

    # Use the most recent analysis file
    analysis_file = sorted(analysis_files)[-1]
    try:
        with open(analysis_file, "r", encoding="utf-8") as f:
            analysis = json.load(f)
        topics = []
        for clip in analysis.get("best_clips", []):
            title = clip.get("suggested_title") or clip.get("title", "")
            if title:
                topics.append(title)
        return topics
    except (json.JSONDecodeError, OSError):
        return []


def run_backfill_ids():
    """One-time backfill: look up YouTube video IDs for existing episodes.

    Iterates output/ep_* directories. For each episode that does NOT already
    have a platform_ids.json, searches YouTube Data API v3 for the episode
    video ID and writes platform_ids.json with {"youtube": video_id, "twitter": None}.

    Skips episodes that already have platform_ids.json (idempotent).
    Rate-limits at 1.5 seconds between YouTube API calls.

    After backfill, `python main.py analytics all` will use stored video IDs
    instead of search API calls (100 quota units -> 1 quota unit per episode).
    """
    from analytics import AnalyticsCollector

    print("=" * 60)
    print("BACKFILL PLATFORM IDS")
    print("=" * 60)
    print()

    collector = AnalyticsCollector()
    youtube = collector._build_youtube_client()
    if youtube is None:
        print(
            "[ERROR] Cannot build YouTube client — check credentials/youtube_token.pickle"
        )
        return

    output_dir = Config.OUTPUT_DIR
    if not output_dir.exists():
        print("No output directory found")
        return

    ep_dirs = sorted(output_dir.glob("ep_*"))
    if not ep_dirs:
        print("No episode directories found")
        return

    processed = 0
    skipped = 0

    for ep_dir in ep_dirs:
        match = re.search(r"ep_(\d+)", ep_dir.name)
        if not match:
            continue

        ep_num = int(match.group(1))
        platform_ids_path = ep_dir / "platform_ids.json"

        if platform_ids_path.exists():
            print(f"[SKIP] ep_{ep_num}: platform_ids.json already exists")
            skipped += 1
            continue

        # Search YouTube for this episode's video
        try:
            channel_id = __import__("os").getenv("YOUTUBE_CHANNEL_ID", "")
            results = (
                youtube.search()
                .list(
                    q=f"Episode #{ep_num}",
                    channelId=channel_id,
                    type="video",
                    part="id",
                    maxResults=1,
                )
                .execute()
            )
            items = results.get("items", [])
            video_id = items[0]["id"]["videoId"] if items else None
        except Exception as e:
            logger.warning("YouTube search failed for ep_%s: %s", ep_num, e)
            video_id = None

        platform_ids = {"youtube": video_id, "twitter": None}
        with open(platform_ids_path, "w", encoding="utf-8") as f:
            json.dump(platform_ids, f, indent=2)

        status = f"youtube={video_id}" if video_id else "youtube=None (not found)"
        print(f"[OK] ep_{ep_num}: {status}")
        processed += 1

        # Rate-limit: 1.5 seconds between YouTube search API calls
        time.sleep(1.5)

    print()
    print(f"Backfill complete: {processed} processed, {skipped} skipped")
