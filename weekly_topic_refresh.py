"""Weekly topic refresh - automated topic curation pipeline."""

import sys
from pathlib import Path
from datetime import datetime
from topic_scraper import TopicScraper
from topic_scorer import TopicScorer
from topic_curator import TopicCurator


def run_weekly_refresh(
    scrape: bool = True,
    score: bool = True,
    curate: bool = True,
    plan_episode: bool = True
):
    """
    Run the complete weekly topic refresh pipeline.

    Args:
        scrape: Run topic scraper
        score: Run topic scorer
        curate: Add topics to Google Doc
        plan_episode: Generate episode plan

    Returns:
        Dictionary with results from each step
    """
    print("="*60)
    print("FAKE PROBLEMS - WEEKLY TOPIC REFRESH")
    print("="*60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    results = {
        'started_at': datetime.now().isoformat(),
        'steps': {}
    }

    # Step 1: Scrape topics from Reddit and web
    if scrape:
        print("\n" + "="*60)
        print("STEP 1: SCRAPING TOPICS")
        print("="*60)
        print()

        try:
            scraper = TopicScraper()

            # Scrape all configured subreddits
            print("Scraping subreddits...")
            topics = scraper.scrape_multiple_subreddits()

            # Add trending topics
            print("\nScraping trending topics...")
            trending = scraper.scrape_trending_topics()
            topics.extend(trending)

            # Deduplicate
            print("\nRemoving duplicates...")
            topics = scraper.deduplicate_topics(topics)

            # Filter by engagement
            print("\nFiltering by engagement...")
            topics = scraper.filter_by_score(topics, min_score=100, min_comments=10)

            # Save
            scraped_file = scraper.save_scraped_topics(topics)

            results['steps']['scrape'] = {
                'success': True,
                'topics_found': len(topics),
                'output_file': str(scraped_file)
            }

            print(f"\n[OK] Scraping complete: {len(topics)} topics")

        except Exception as e:
            print(f"\n[ERROR] Scraping failed: {e}")
            results['steps']['scrape'] = {
                'success': False,
                'error': str(e)
            }
            return results

    # Step 2: Score topics with Claude AI
    if score:
        print("\n" + "="*60)
        print("STEP 2: SCORING TOPICS")
        print("="*60)
        print()

        try:
            scorer = TopicScorer()

            # Find most recent scraped file
            topic_data_dir = Path('topic_data')
            scraped_files = list(topic_data_dir.glob('scraped_topics_*.json'))

            if not scraped_files:
                raise FileNotFoundError("No scraped topics found")

            latest_scraped = max(scraped_files, key=lambda p: p.stat().st_mtime)

            print(f"Loading topics from: {latest_scraped}")

            import json
            with open(latest_scraped, 'r', encoding='utf-8') as f:
                data = json.load(f)
                topics = data.get('topics', [])

            print(f"[OK] Loaded {len(topics)} topics")

            # Score topics
            scored_topics = scorer.score_topics(topics, batch_size=10)

            # Save scored topics
            scored_file = scorer.save_scored_topics(scored_topics)

            # Get statistics
            recommended = len(scorer.filter_recommended(scored_topics))
            avg_score = sum(t.get('score', {}).get('total', 0) for t in scored_topics) / max(len(scored_topics), 1)

            results['steps']['score'] = {
                'success': True,
                'topics_scored': len(scored_topics),
                'recommended': recommended,
                'average_score': round(avg_score, 2),
                'output_file': str(scored_file)
            }

            print(f"\n[OK] Scoring complete: {recommended}/{len(scored_topics)} recommended")

        except Exception as e:
            print(f"\n[ERROR] Scoring failed: {e}")
            results['steps']['score'] = {
                'success': False,
                'error': str(e)
            }
            return results

    # Step 3: Add topics to Google Doc
    if curate:
        print("\n" + "="*60)
        print("STEP 3: CURATING TOPICS")
        print("="*60)
        print()

        try:
            curator = TopicCurator()

            # Load scored topics
            scored_data = curator.load_scored_topics()

            # Generate structured topics file
            success = curator.restructure_google_doc(scored_data)

            results['steps']['curate'] = {
                'success': success,
                'message': 'Structured topics file created'
            }

            print("\n[OK] Curation complete")
            print("[INFO] Review topic_data/structured_topics.txt")
            print("[INFO] Copy/paste into your Google Doc to update")

        except Exception as e:
            print(f"\n[ERROR] Curation failed: {e}")
            results['steps']['curate'] = {
                'success': False,
                'error': str(e)
            }

    # Step 4: Plan next episode
    if plan_episode:
        print("\n" + "="*60)
        print("STEP 4: PLANNING NEXT EPISODE")
        print("="*60)
        print()

        try:
            curator = TopicCurator()

            # Load scored topics
            scored_data = curator.load_scored_topics()

            # Generate episode plan
            episode_plan = curator.plan_next_episode(scored_data)

            results['steps']['plan'] = {
                'success': True,
                'total_topics': episode_plan.get('total_topics', 0),
                'output_file': f"topic_data/episode_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            }

            print("\n[OK] Episode planning complete")

        except Exception as e:
            print(f"\n[ERROR] Planning failed: {e}")
            results['steps']['plan'] = {
                'success': False,
                'error': str(e)
            }

    # Summary
    print("\n" + "="*60)
    print("WEEKLY REFRESH COMPLETE")
    print("="*60)
    print()

    print("Results:")
    for step, result in results['steps'].items():
        status = "[OK]" if result.get('success', False) else "[FAIL]"
        print(f"  {step.upper()}: {status}")

    print()
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Save results
    output_dir = Path('topic_data')
    output_dir.mkdir(exist_ok=True)
    results_file = output_dir / f"refresh_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    import json
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to: {results_file}")
    print()

    return results


if __name__ == '__main__':
    # Parse command line arguments
    args = sys.argv[1:]

    # Default: run all steps
    scrape = True
    score = True
    curate = True
    plan = True

    # Allow selective step execution
    if '--scrape-only' in args:
        score = curate = plan = False
    elif '--score-only' in args:
        scrape = curate = plan = False
    elif '--curate-only' in args:
        scrape = score = plan = False
    elif '--plan-only' in args:
        scrape = score = curate = False

    # Run refresh
    run_weekly_refresh(
        scrape=scrape,
        score=score,
        curate=curate,
        plan_episode=plan
    )
