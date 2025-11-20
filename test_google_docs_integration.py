"""Test script for Google Docs Topic Tracker integration."""

import sys
from pathlib import Path
from google_docs_tracker import GoogleDocsTopicTracker


def test_basic_functionality():
    """Test basic Google Docs functionality."""
    print("="*60)
    print("GOOGLE DOCS TOPIC TRACKER - INTEGRATION TEST")
    print("="*60)
    print()

    try:
        # Initialize tracker
        print("[1/5] Initializing tracker...")
        tracker = GoogleDocsTopicTracker()
        print("  [OK] Tracker initialized successfully")
        print()

        # Fetch document
        print("[2/5] Fetching document...")
        document = tracker.get_document_content()
        print(f"  [OK] Connected to document: {document.get('title', 'Unknown')}")
        print()

        # Extract topics
        print("[3/5] Extracting topics...")
        topics = tracker.extract_topics(document)
        print(f"  [OK] Found {len(topics)} active topics")

        if topics:
            print("\n  First 5 topics:")
            for i, topic in enumerate(topics[:5], 1):
                topic_text = topic['text'][:60]
                print(f"    {i}. {topic_text}...")
        print()

        # Test topic matching (dry run)
        print("[4/5] Testing topic matching...")
        print("  Using sample transcript about cheese...")

        sample_transcript = """
        Today we're talking about an interesting fake problem - what if you ate too much cheese?
        There's this crazy story about a guy who ate 6-9 pounds of cheese every day and started
        oozing cholesterol from his hands. It's absolutely disgusting but fascinating.
        We also briefly mention some robot cafes in Japan as an example of unique dining experiences.
        """

        sample_summary = "Discussion about extreme cheese consumption and its health consequences"

        if topics:
            matched = tracker.match_topics_with_transcript(
                topics[:10],  # Test with first 10 topics only
                sample_transcript,
                sample_summary,
                episode_number=999
            )

            if matched:
                print(f"  [OK] Matched {len(matched)} topics from sample")
                for topic in matched:
                    conf_pct = int(topic['confidence'] * 100)
                    print(f"    - {topic['text'][:50]}... ({conf_pct}%)")
            else:
                print("  [OK] No topics matched (this is normal if your topics don't mention cheese)")
        print()

        # Show section structure
        print("[5/5] Checking document structure...")
        discussed_section = tracker._find_discussed_section(document)

        if discussed_section:
            print("  [OK] Found 'Discussed Topics' section")
        else:
            print("  [INFO] No 'Discussed Topics' section yet (will be created automatically)")
        print()

        print("="*60)
        print("[SUCCESS] ALL TESTS PASSED")
        print("="*60)
        print()
        print("Your Google Docs Topic Tracker is ready to use!")
        print()
        print("Next steps:")
        print("  1. Run your normal automation: python main.py latest")
        print("  2. After processing, check your Google Doc for updates")
        print()

        return True

    except FileNotFoundError as e:
        print()
        print("[ERROR] Credentials not found")
        print()
        print(str(e))
        print()
        print("Please run: python setup_google_docs.py")
        print()
        return False

    except Exception as e:
        print()
        print(f"[ERROR] {e}")
        print()
        import traceback
        traceback.print_exc()
        print()
        print("Troubleshooting:")
        print("  1. Make sure GOOGLE_DOC_ID is set in .env")
        print("  2. Run: python setup_google_docs.py")
        print("  3. Check that the Google account has access to the doc")
        print()
        return False


def test_dry_run():
    """Test a full update without actually modifying the document."""
    print("="*60)
    print("DRY RUN TEST - NO CHANGES WILL BE MADE")
    print("="*60)
    print()
    print("This test shows what WOULD happen during episode processing")
    print("without actually modifying your Google Doc.")
    print()

    try:
        tracker = GoogleDocsTopicTracker()

        sample_transcript = """
        Welcome to another episode of Fake Problems Podcast!
        Today we're diving deep into the world of cheese addiction.

        So there was this guy who decided to only eat cheese - like 6 to 9 pounds per day.
        And you know what happened? He started oozing cholesterol from his hands!
        His skin was literally secreting this waxy substance because his body couldn't
        process all that dairy fat.

        It's both disgusting and fascinating. Like, imagine shaking someone's hand and
        they're just... greasy with their own excess cholesterol. That's a fake problem
        we can all be thankful we don't have.

        We also briefly discussed some robot cafes in Japan where robots serve you food.
        Pretty cool concept, though not as gross as cholesterol hands.
        """

        sample_summary = (
            "Deep dive into extreme cheese consumption and its bizarre health effects. "
            "Main story about a man who ate 6-9 pounds of cheese daily and developed "
            "cholesterol-oozing hands. Brief mention of robot cafes in Japan."
        )

        print("Sample Episode Info:")
        print(f"  Episode: 999 (Test Episode)")
        print(f"  Topics: Cheese addiction, Robot cafes")
        print()

        # Fetch and display topics
        document = tracker.get_document_content()
        topics = tracker.extract_topics(document)

        print(f"Your Google Doc has {len(topics)} active topics")
        print()

        # Match topics
        print("Running Claude topic matching...")
        matched = tracker.match_topics_with_transcript(
            topics,
            sample_transcript,
            sample_summary,
            episode_number=999
        )

        if matched:
            print()
            print(f"Would move {len(matched)} topics:")
            for topic in matched:
                conf_pct = int(topic['confidence'] * 100)
                print(f"\n  Topic: {topic['text']}")
                print(f"  Confidence: {conf_pct}%")
                print(f"  Reason: {topic['reason']}")
        else:
            print()
            print("No topics matched (try topics about cheese or robots)")

        print()
        print("="*60)
        print("DRY RUN COMPLETE - No changes made to your doc")
        print("="*60)
        print()

        return True

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--dry-run':
        success = test_dry_run()
    else:
        success = test_basic_functionality()

    sys.exit(0 if success else 1)
