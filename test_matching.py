"""Test topic matching with a small sample."""

import json
from pathlib import Path
from match_topics_to_episodes import TopicMatcher


def test_matching():
    """Test with first 10 topics."""
    print("Testing topic matching...")

    matcher = TopicMatcher()

    # Load data
    topics = matcher.load_topics()[:10]  # Just first 10
    episodes = matcher.load_episodes()

    print(f"Loaded {len(topics)} topics")
    print(f"Loaded {len(episodes)} episodes")

    # Test matching
    print("\nTesting Claude API...")
    matches = matcher.match_topics_batch(topics, episodes, batch_size=10)

    print(f"\nResults: {len(matches)} matches")
    for match in matches:
        print(f"  - {match['topic_text'][:50]}: discussed={match['discussed']}, confidence={match['confidence']}")


if __name__ == '__main__':
    test_matching()
