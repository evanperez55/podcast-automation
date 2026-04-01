"""Post daily 'Fake Problem of the Day' content to social media.

Generates a fake problem using Ollama, posts to Twitter, and saves
a log of all posted content. Designed to run unattended via scheduler.

Usage:
    python post_daily_content.py              # generate + post
    python post_daily_content.py --dry-run    # generate only, don't post
    python post_daily_content.py --topic "parking"  # themed content
"""

import json
import sys
from datetime import datetime

from config import Config
from logger import logger
from daily_content_generator import DailyContentGenerator


def post_daily(dry_run=False, topic=None):
    """Generate and post a Fake Problem of the Day.

    Args:
        dry_run: If True, generate content but don't post to platforms.
        topic: Optional topic hint for themed content.

    Returns:
        Dict with generated content and post results, or None on failure.
    """
    generator = DailyContentGenerator()
    if not generator.enabled:
        logger.warning("Daily content generator is disabled")
        return None

    # Generate content
    logger.info("Generating Fake Problem of the Day...")
    content = generator.generate_fake_problem(topic_hint=topic)
    if not content:
        logger.error("Failed to generate daily content")
        return None

    logger.info("Generated content:")
    for platform, text in content.items():
        logger.info("  %s: %s", platform, text)

    results = {"content": content, "generated_at": datetime.now().isoformat()}

    if dry_run:
        logger.info("[DRY RUN] Skipping social media posts")
        results["posted"] = False
        _save_log(results)
        return results

    # Post to Twitter
    try:
        from uploaders.twitter_uploader import TwitterUploader

        twitter = TwitterUploader()
        tweet_text = content.get("twitter", "")
        if tweet_text:
            tweet_result = twitter.post_tweet(text=tweet_text)
            if tweet_result:
                results["twitter_result"] = tweet_result
                logger.info("Posted to Twitter successfully")
            else:
                logger.warning("Twitter post returned no result")
                results["twitter_result"] = None
    except (ValueError, Exception) as e:
        logger.warning("Twitter posting skipped: %s", e)
        results["twitter_result"] = {"error": str(e)}

    results["posted"] = True
    _save_log(results)
    return results


def _save_log(results):
    """Append post results to daily content log."""
    log_dir = Config.OUTPUT_DIR / "daily_content"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "post_log.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(results, ensure_ascii=False) + "\n")

    logger.info("Logged to %s", log_file)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    topic = None
    for i, arg in enumerate(sys.argv):
        if arg == "--topic" and i + 1 < len(sys.argv):
            topic = sys.argv[i + 1]

    result = post_daily(dry_run=dry_run, topic=topic)
    if result:
        print("\n--- Fake Problem of the Day ---")
        for platform, text in result["content"].items():
            print(f"\n{platform.upper()}:\n  {text}")
        if result.get("posted"):
            print("\nPosted to Twitter!")
        else:
            print("\n(dry run — not posted)")
    else:
        print("Failed to generate content")
        sys.exit(1)
