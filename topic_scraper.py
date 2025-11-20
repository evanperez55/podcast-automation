"""Topic scraper for Fake Problems Podcast - finds new topics from Reddit and web sources."""

import praw
import requests
from datetime import datetime, timedelta
from typing import List, Dict
import json
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()


class TopicScraper:
    """Scrape topics from Reddit and other sources."""

    def __init__(self):
        """Initialize scrapers."""
        # Reddit API credentials (optional)
        self.reddit_client_id = os.getenv('REDDIT_CLIENT_ID')
        self.reddit_client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        self.reddit_user_agent = os.getenv('REDDIT_USER_AGENT', 'FakeProblems:v1.0')

        self.reddit = None
        if self.reddit_client_id and self.reddit_client_secret:
            try:
                self.reddit = praw.Reddit(
                    client_id=self.reddit_client_id,
                    client_secret=self.reddit_client_secret,
                    user_agent=self.reddit_user_agent
                )
                print("[OK] Reddit API initialized")
            except Exception as e:
                print(f"[WARNING] Reddit API failed: {e}")
                print("[INFO] Will use JSON Reddit API (no authentication)")
        else:
            print("[INFO] Reddit credentials not found - using JSON API (limited)")

    def scrape_reddit_subreddit(
        self,
        subreddit_name: str,
        time_filter: str = 'week',
        limit: int = 25
    ) -> List[Dict]:
        """
        Scrape topics from a subreddit.

        Args:
            subreddit_name: Name of subreddit (e.g., 'nottheonion')
            time_filter: 'day', 'week', 'month', 'year', 'all'
            limit: Number of posts to fetch

        Returns:
            List of topic dictionaries
        """
        topics = []

        try:
            if self.reddit:
                # Use authenticated API
                subreddit = self.reddit.subreddit(subreddit_name)
                posts = subreddit.top(time_filter=time_filter, limit=limit)

                for post in posts:
                    topics.append({
                        'title': post.title,
                        'url': f"https://reddit.com{post.permalink}",
                        'score': post.score,
                        'num_comments': post.num_comments,
                        'created_utc': datetime.fromtimestamp(post.created_utc).isoformat(),
                        'source': f'r/{subreddit_name}',
                        'source_type': 'reddit',
                        'selftext': post.selftext[:500] if post.selftext else ''
                    })
            else:
                # Use JSON API (no auth required, but limited)
                url = f'https://www.reddit.com/r/{subreddit_name}/top.json'
                params = {'t': time_filter, 'limit': limit}
                headers = {'User-Agent': self.reddit_user_agent}

                response = requests.get(url, params=params, headers=headers, timeout=10)
                response.raise_for_status()

                data = response.json()
                posts = data['data']['children']

                for post_data in posts:
                    post = post_data['data']
                    topics.append({
                        'title': post['title'],
                        'url': f"https://reddit.com{post['permalink']}",
                        'score': post['score'],
                        'num_comments': post['num_comments'],
                        'created_utc': datetime.fromtimestamp(post['created_utc']).isoformat(),
                        'source': f'r/{subreddit_name}',
                        'source_type': 'reddit',
                        'selftext': post.get('selftext', '')[:500]
                    })

            print(f"[OK] Scraped {len(topics)} topics from r/{subreddit_name}")
            return topics

        except Exception as e:
            print(f"[ERROR] Failed to scrape r/{subreddit_name}: {e}")
            return []

    def scrape_multiple_subreddits(
        self,
        subreddit_config: Dict[str, Dict] = None
    ) -> List[Dict]:
        """
        Scrape multiple subreddits with custom settings.

        Args:
            subreddit_config: Dict mapping subreddit names to config
                Example: {'nottheonion': {'time_filter': 'week', 'limit': 25}}

        Returns:
            Combined list of topics from all subreddits
        """
        if subreddit_config is None:
            # Default subreddit configuration optimized for Fake Problems
            subreddit_config = {
                # Shocking News Stories
                'nottheonion': {'time_filter': 'week', 'limit': 20},
                'offbeat': {'time_filter': 'week', 'limit': 15},
                'NewsOfTheWeird': {'time_filter': 'week', 'limit': 15},

                # Absurd Hypotheticals
                'CrazyIdeas': {'time_filter': 'week', 'limit': 20},
                'Showerthoughts': {'time_filter': 'week', 'limit': 20},
                'hypotheticalsituation': {'time_filter': 'week', 'limit': 15},

                # Dating/Social Commentary
                'Tinder': {'time_filter': 'week', 'limit': 10},
                'dating_advice': {'time_filter': 'week', 'limit': 10},
                'socialskills': {'time_filter': 'week', 'limit': 10},

                # Pop Science & Tech
                'science': {'time_filter': 'week', 'limit': 15},
                'technology': {'time_filter': 'week', 'limit': 15},
                'Futurology': {'time_filter': 'week', 'limit': 10},

                # Cultural Observations
                'mildlyinfuriating': {'time_filter': 'week', 'limit': 15},
                'antiwork': {'time_filter': 'week', 'limit': 10},
                'firstworldproblems': {'time_filter': 'week', 'limit': 10},
            }

        all_topics = []

        for subreddit, config in subreddit_config.items():
            topics = self.scrape_reddit_subreddit(
                subreddit,
                time_filter=config.get('time_filter', 'week'),
                limit=config.get('limit', 25)
            )
            all_topics.extend(topics)

        print(f"\n[OK] Total topics scraped: {len(all_topics)}")
        return all_topics

    def scrape_trending_topics(self) -> List[Dict]:
        """
        Scrape trending/viral topics from various sources.

        Returns:
            List of trending topics
        """
        topics = []

        # Reddit front page hot topics
        try:
            if self.reddit:
                hot_posts = self.reddit.subreddit('all').hot(limit=50)
                for post in hot_posts:
                    # Filter for relevant subreddits
                    if post.subreddit.display_name.lower() in [
                        'todayilearned', 'explainlikeimfive', 'askreddit',
                        'dataisbeautiful', 'coolguides'
                    ]:
                        topics.append({
                            'title': post.title,
                            'url': f"https://reddit.com{post.permalink}",
                            'score': post.score,
                            'num_comments': post.num_comments,
                            'created_utc': datetime.fromtimestamp(post.created_utc).isoformat(),
                            'source': f'r/{post.subreddit.display_name}',
                            'source_type': 'reddit_trending',
                            'selftext': post.selftext[:500] if post.selftext else ''
                        })
            print(f"[OK] Scraped {len(topics)} trending topics")
        except Exception as e:
            print(f"[WARNING] Trending scrape failed: {e}")

        return topics

    def save_scraped_topics(self, topics: List[Dict], filename: str = None) -> Path:
        """
        Save scraped topics to JSON file.

        Args:
            topics: List of topic dictionaries
            filename: Output filename (optional)

        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scraped_topics_{timestamp}.json"

        output_dir = Path('topic_data')
        output_dir.mkdir(exist_ok=True)

        output_path = output_dir / filename

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'scraped_at': datetime.now().isoformat(),
                'total_topics': len(topics),
                'topics': topics
            }, f, indent=2, ensure_ascii=False)

        print(f"[OK] Saved {len(topics)} topics to: {output_path}")
        return output_path

    def deduplicate_topics(self, topics: List[Dict]) -> List[Dict]:
        """
        Remove duplicate topics based on title similarity.

        Args:
            topics: List of topic dictionaries

        Returns:
            Deduplicated list
        """
        seen_titles = set()
        unique_topics = []

        for topic in topics:
            # Normalize title for comparison
            normalized = topic['title'].lower().strip()

            # Simple dedup - exact title match
            if normalized not in seen_titles:
                seen_titles.add(normalized)
                unique_topics.append(topic)

        removed = len(topics) - len(unique_topics)
        if removed > 0:
            print(f"[INFO] Removed {removed} duplicate topics")

        return unique_topics

    def filter_by_score(
        self,
        topics: List[Dict],
        min_score: int = 100,
        min_comments: int = 10
    ) -> List[Dict]:
        """
        Filter topics by engagement metrics.

        Args:
            topics: List of topic dictionaries
            min_score: Minimum Reddit score
            min_comments: Minimum number of comments

        Returns:
            Filtered list
        """
        filtered = [
            t for t in topics
            if t.get('score', 0) >= min_score and t.get('num_comments', 0) >= min_comments
        ]

        print(f"[INFO] Filtered to {len(filtered)} high-engagement topics (score>={min_score}, comments>={min_comments})")
        return filtered


def run_daily_scrape():
    """Run a daily topic scrape."""
    print("="*60)
    print("FAKE PROBLEMS - DAILY TOPIC SCRAPE")
    print("="*60)
    print()

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

    # Save results
    print("\nSaving results...")
    output_path = scraper.save_scraped_topics(topics)

    print()
    print("="*60)
    print("[SUCCESS] SCRAPE COMPLETE")
    print("="*60)
    print(f"Total topics found: {len(topics)}")
    print(f"Saved to: {output_path}")
    print()
    print("Next step: Run topic scorer to rate these topics")
    print("  python topic_scorer.py")
    print()

    return output_path


if __name__ == '__main__':
    run_daily_scrape()
