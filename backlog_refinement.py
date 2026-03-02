"""Backlog refinement: Update Notion topics based on existing episode analysis.

This uses the existing topic_matching_analysis.json to update all topics
that were already discussed in episodes 1-24 to "Published" status.
"""

import json
from pathlib import Path
from notion_integration import NotionTopicManager


def refine_backlog():
    """Update Notion topics based on existing episode analysis."""
    print("=" * 60)
    print("BACKLOG REFINEMENT")
    print("=" * 60)
    print()

    # Load existing topic matching analysis
    analysis_file = Path("topic_data/topic_matching_analysis.json")
    if not analysis_file.exists():
        print("[ERROR] Topic matching analysis not found")
        print("Expected file: topic_data/topic_matching_analysis.json")
        return

    print("[INFO] Loading existing topic analysis...")
    with open(analysis_file, "r", encoding="utf-8") as f:
        analysis = json.load(f)

    topics = analysis.get("topics", [])
    print(f"[OK] Loaded {len(topics)} topics")

    # Filter for discussed topics (already matched to episodes)
    discussed_topics = [
        t for t in topics if t.get("discussed", False) and t.get("episodes", [])
    ]

    print(
        f"[INFO] Found {len(discussed_topics)} topics that were discussed in episodes 1-24"
    )
    print()

    if not discussed_topics:
        print("[INFO] No topics to update")
        return

    # Initialize Notion
    print("[INFO] Connecting to Notion...")
    notion = NotionTopicManager()

    # Get all topics from Notion to match by name
    print("[INFO] Fetching existing Notion topics...")
    notion_topics = notion.get_all_existing_topics()
    print(f"[OK] Found {len(notion_topics)} topics in Notion")
    print()

    # Match and update
    updated = []
    not_found = []
    already_published = []

    print("[INFO] Updating topics to Published status...")
    print()

    for topic in discussed_topics:
        topic_text = topic["topic_text"]
        episodes = topic.get("episodes", [])
        confidence = topic.get("confidence", 0)

        # Find matching page in Notion
        if topic_text not in notion_topics:
            not_found.append(topic_text)
            print(f"  [WARN] Not found in Notion: {topic_text[:60]}...")
            continue

        page_id = notion_topics[topic_text]

        # Check current status
        try:
            # Get page details
            import requests

            response = requests.get(
                f"https://api.notion.com/v1/pages/{page_id}", headers=notion.headers
            )
            page_data = response.json()

            current_status = (
                page_data["properties"].get("Status", {}).get("select", {}).get("name")
            )

            if current_status == "Published":
                already_published.append(topic_text)
                continue

            # Update to Published
            episode_num = episodes[0] if episodes else None
            notion.mark_topic_as_discussed(page_id, episode_num)

            updated.append(topic_text)
            confidence_pct = int(confidence * 100)
            print(f"  [OK] Updated: {topic_text[:60]}...")
            print(
                f"    Episodes: {', '.join(map(str, episodes))} | Confidence: {confidence_pct}%"
            )

        except Exception as e:
            print(f"  [ERROR] Failed: {topic_text[:60]}...")
            print(f"    Error: {e}")

    print()
    print("=" * 60)
    print("BACKLOG REFINEMENT COMPLETE")
    print("=" * 60)
    print()
    print(f"[OK] Updated: {len(updated)} topics")
    print(f"[INFO] Already Published: {len(already_published)} topics")
    print(f"[WARN] Not Found: {len(not_found)} topics")
    print()

    if not_found:
        print("[WARNING] Some topics weren't found in Notion:")
        print("This might be due to:")
        print("  - Topics failed to import during migration")
        print("  - Text doesn't match exactly (punctuation, spacing)")
        print()
        print("Topics not found:")
        for topic in not_found[:10]:
            print(f"  - {topic}")
        if len(not_found) > 10:
            print(f"  ... and {len(not_found) - 10} more")
        print()

    print("[SUCCESS] Your Notion backlog is now up to date!")
    print()
    print("Next steps:")
    print("  1. Check your Notion database")
    print("  2. Filter by Status='Backlog' to see remaining topics")
    print("  3. Filter by Status='Published' to see discussed topics")
    print()


if __name__ == "__main__":
    refine_backlog()
