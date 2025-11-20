"""AI-powered topic scorer for Fake Problems Podcast."""

import json
from pathlib import Path
from typing import List, Dict
import anthropic
from config import Config
from datetime import datetime


class TopicScorer:
    """Score topics using Claude AI based on Fake Problems success criteria."""

    def __init__(self):
        """Initialize Claude client."""
        if not Config.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        print("[OK] Claude AI topic scorer ready")

    def score_topics(self, topics: List[Dict], batch_size: int = 10) -> List[Dict]:
        """
        Score a list of topics using Claude AI.

        Args:
            topics: List of topic dictionaries from scraper
            batch_size: Number of topics to score in each API call

        Returns:
            List of topics with scores and analysis
        """
        print(f"[INFO] Scoring {len(topics)} topics...")
        scored_topics = []

        # Process in batches to optimize API usage
        for i in range(0, len(topics), batch_size):
            batch = topics[i:i+batch_size]
            print(f"[INFO] Scoring batch {i//batch_size + 1}/{(len(topics)-1)//batch_size + 1}...")

            batch_scores = self._score_batch(batch)
            scored_topics.extend(batch_scores)

        print(f"[OK] Scored all {len(scored_topics)} topics")
        return scored_topics

    def _score_batch(self, topics: List[Dict]) -> List[Dict]:
        """Score a batch of topics in a single API call."""

        # Build topic list for Claude
        topic_list = []
        for idx, topic in enumerate(topics, 1):
            topic_list.append(f"{idx}. {topic['title']}")
            if topic.get('selftext'):
                topic_list.append(f"   Context: {topic['selftext'][:200]}")

        topic_text = "\n".join(topic_list)

        prompt = f"""You are a podcast content analyst for "Fake Problems Podcast" - a comedy podcast about absurd scenarios, weird news, and modern life's ridiculous moments.

**SCORING CRITERIA** (Total: 0-10 points):

1. **Shock Value** (0-3 points):
   - How surprising/unexpected is this?
   - Does it make you say "wait, WHAT?"
   - 3pts: Totally shocking, 2pts: Very surprising, 1pt: Mildly unexpected, 0pts: Boring

2. **Relatability** (0-2 points):
   - Can the audience connect to this?
   - Is it a universal experience or feeling?
   - 2pts: Very relatable, 1pt: Somewhat relatable, 0pts: Too niche

3. **Absurdity** (0-2 points):
   - How ridiculous is the logic/scenario?
   - Does it have comedic potential?
   - 2pts: Highly absurd, 1pt: Moderately absurd, 0pts: Too normal

4. **Title Hook** (0-2 points):
   - Would this make a great clip title?
   - Does it make you want to click/listen?
   - 2pts: Amazing hook, 1pt: Decent hook, 0pts: Boring title

5. **Visual Imagery** (0-1 point):
   - Can you easily picture this scenario?
   - Does it create a mental image?
   - 1pt: Strong visual, 0pts: Abstract/hard to visualize

**PODCAST STYLE**:
- Dark/shock humor (disturbing content made funny)
- Relatable awkwardness (universal cringe)
- Absurd logic (ridiculous premises taken seriously)
- Self-deprecation and modern life commentary
- "Fake problems" framing allows any topic

**EXAMPLES OF HIGH-SCORING TOPICS** (8-10 points):
- "Gas-powered adult toys existed before electric ones" (absurd history)
- "Plane emergency landing due to explosive diarrhea" (shocking + relatable)
- "Cats will eat their dead owners, dogs won't" (dark + surprising)
- "Guy ate 6-9 pounds of cheese daily, started oozing cholesterol from hands" (shocking + visual)

**EXAMPLES OF LOW-SCORING TOPICS** (0-3 points):
- Generic political news without absurd angle
- Requires too much context to understand
- Too niche or technical
- No comedic potential

**YOUR TASK**:
Score each topic below (1-{len(topics)}). For each topic, provide:
- Total score (0-10)
- Breakdown by category
- Brief reason (1 sentence)
- Suggested category: "shocking_news", "absurd_hypothetical", "dating_social", "pop_science", "cultural_observation"
- Recommended: true/false (recommend if score >= 6)

**TOPICS TO SCORE**:
{topic_text}

**OUTPUT FORMAT** (JSON only, no other text):
[
  {{
    "topic_number": 1,
    "total_score": 7.5,
    "shock_value": 2,
    "relatability": 2,
    "absurdity": 2,
    "title_hook": 1,
    "visual_imagery": 0.5,
    "reason": "Brief explanation of score",
    "category": "shocking_news",
    "recommended": true
  }},
  ...
]

Return ONLY the JSON array."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text.strip()

            # Extract JSON from response
            if response_text.startswith('['):
                scores = json.loads(response_text)
            else:
                import re
                json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                if json_match:
                    scores = json.loads(json_match.group(0))
                else:
                    print("[ERROR] Could not parse Claude's response")
                    return topics

            # Merge scores with original topics
            scored_topics = []
            for i, topic in enumerate(topics):
                if i < len(scores):
                    score_data = scores[i]
                    topic['score'] = {
                        'total': score_data.get('total_score', 0),
                        'shock_value': score_data.get('shock_value', 0),
                        'relatability': score_data.get('relatability', 0),
                        'absurdity': score_data.get('absurdity', 0),
                        'title_hook': score_data.get('title_hook', 0),
                        'visual_imagery': score_data.get('visual_imagery', 0),
                        'reason': score_data.get('reason', ''),
                        'category': score_data.get('category', 'uncategorized'),
                        'recommended': score_data.get('recommended', False),
                        'scored_at': datetime.now().isoformat()
                    }
                scored_topics.append(topic)

            return scored_topics

        except Exception as e:
            print(f"[ERROR] Scoring failed: {e}")
            # Return original topics without scores
            return topics

    def filter_recommended(self, scored_topics: List[Dict]) -> List[Dict]:
        """Filter to only recommended topics (score >= 6)."""
        recommended = [t for t in scored_topics if t.get('score', {}).get('recommended', False)]
        print(f"[INFO] {len(recommended)} topics recommended (score >= 6)")
        return recommended

    def sort_by_score(self, scored_topics: List[Dict]) -> List[Dict]:
        """Sort topics by total score (descending)."""
        return sorted(
            scored_topics,
            key=lambda t: t.get('score', {}).get('total', 0),
            reverse=True
        )

    def group_by_category(self, scored_topics: List[Dict]) -> Dict[str, List[Dict]]:
        """Group topics by category."""
        categories = {}

        for topic in scored_topics:
            category = topic.get('score', {}).get('category', 'uncategorized')
            if category not in categories:
                categories[category] = []
            categories[category].append(topic)

        return categories

    def save_scored_topics(self, scored_topics: List[Dict], filename: str = None) -> Path:
        """Save scored topics to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scored_topics_{timestamp}.json"

        output_dir = Path('topic_data')
        output_dir.mkdir(exist_ok=True)

        output_path = output_dir / filename

        # Calculate statistics
        total = len(scored_topics)
        recommended = len([t for t in scored_topics if t.get('score', {}).get('recommended', False)])
        avg_score = sum(t.get('score', {}).get('total', 0) for t in scored_topics) / max(total, 1)

        # Group by category
        categories = self.group_by_category(scored_topics)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'scored_at': datetime.now().isoformat(),
                'statistics': {
                    'total_topics': total,
                    'recommended': recommended,
                    'average_score': round(avg_score, 2),
                    'categories': {cat: len(topics) for cat, topics in categories.items()}
                },
                'topics_by_category': {
                    cat: sorted(topics, key=lambda t: t.get('score', {}).get('total', 0), reverse=True)
                    for cat, topics in categories.items()
                },
                'all_topics_sorted': self.sort_by_score(scored_topics)
            }, f, indent=2, ensure_ascii=False)

        print(f"[OK] Saved scored topics to: {output_path}")
        print(f"[INFO] Statistics:")
        print(f"  Total: {total}")
        print(f"  Recommended (6+): {recommended}")
        print(f"  Average score: {avg_score:.2f}")
        print(f"  Categories: {', '.join(categories.keys())}")

        return output_path


def score_scraped_topics(input_file: str = None):
    """Score topics from a scraped topics file."""
    print("="*60)
    print("FAKE PROBLEMS - TOPIC SCORER")
    print("="*60)
    print()

    # Find most recent scraped topics file if not specified
    if input_file is None:
        topic_data_dir = Path('topic_data')
        if not topic_data_dir.exists():
            print("[ERROR] No topic_data directory found")
            print("Run topic_scraper.py first to scrape topics")
            return

        scraped_files = list(topic_data_dir.glob('scraped_topics_*.json'))
        if not scraped_files:
            print("[ERROR] No scraped topics files found")
            print("Run topic_scraper.py first to scrape topics")
            return

        input_file = max(scraped_files, key=lambda p: p.stat().st_mtime)

    print(f"Loading topics from: {input_file}")

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        topics = data.get('topics', [])

    print(f"[OK] Loaded {len(topics)} topics")
    print()

    # Score topics
    scorer = TopicScorer()
    scored_topics = scorer.score_topics(topics, batch_size=10)

    # Save results
    output_path = scorer.save_scored_topics(scored_topics)

    print()
    print("="*60)
    print("[SUCCESS] SCORING COMPLETE")
    print("="*60)
    print()
    print("Next step: Add top topics to Google Doc")
    print("  python topic_curator.py")
    print()

    return output_path


if __name__ == '__main__':
    import sys
    input_file = sys.argv[1] if len(sys.argv) > 1 else None
    score_scraped_topics(input_file)
