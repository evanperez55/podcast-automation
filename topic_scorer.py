"""AI-powered topic scorer — configurable per client via scoring profiles."""

import json
from pathlib import Path
from typing import List, Dict
from config import Config
from ollama_client import Ollama
from datetime import datetime

# Default scoring profile (comedy podcast). Clients can override via YAML.
DEFAULT_SCORING_PROFILE = {
    "description": "a comedy podcast about absurd scenarios, weird news, and modern life's ridiculous moments",
    "criteria": [
        {
            "name": "Shock Value",
            "key": "shock_value",
            "max": 3,
            "description": "How surprising/unexpected is this? Does it make you say 'wait, WHAT?'",
        },
        {
            "name": "Relatability",
            "key": "relatability",
            "max": 2,
            "description": "Can the audience connect to this? Is it a universal experience?",
        },
        {
            "name": "Absurdity",
            "key": "absurdity",
            "max": 2,
            "description": "How ridiculous is the logic/scenario? Does it have comedic potential?",
        },
        {
            "name": "Title Hook",
            "key": "title_hook",
            "max": 2,
            "description": "Would this make a great clip title? Does it make you want to click?",
        },
        {
            "name": "Visual Imagery",
            "key": "visual_imagery",
            "max": 1,
            "description": "Can you easily picture this scenario? Does it create a mental image?",
        },
    ],
    "style": [
        "Dark/shock humor (disturbing content made funny)",
        "Relatable awkwardness (universal cringe)",
        "Absurd logic (ridiculous premises taken seriously)",
        "Self-deprecation and modern life commentary",
        '"Fake problems" framing allows any topic',
    ],
    "high_examples": [
        '"Gas-powered adult toys existed before electric ones" (absurd history)',
        '"Plane emergency landing due to explosive diarrhea" (shocking + relatable)',
        '"Cats will eat their dead owners, dogs won\'t" (dark + surprising)',
        '"Guy ate 6-9 pounds of cheese daily, started oozing cholesterol from hands" (shocking + visual)',
    ],
    "low_examples": [
        "Generic political news without absurd angle",
        "Requires too much context to understand",
        "Too niche or technical",
        "No comedic potential",
    ],
    "categories": [
        "shocking_news",
        "absurd_hypothetical",
        "dating_social",
        "pop_science",
        "cultural_observation",
    ],
}


class TopicScorer:
    """Score topics using Ollama (local LLM) based on configurable scoring criteria."""

    def __init__(self):
        """Initialize Ollama client and load scoring profile."""
        self.client = Ollama()
        self.profile = (
            getattr(Config, "SCORING_PROFILE", None) or DEFAULT_SCORING_PROFILE
        )
        print("[OK] Ollama AI topic scorer ready (FREE)")

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
            batch = topics[i : i + batch_size]
            print(
                f"[INFO] Scoring batch {i // batch_size + 1}/{(len(topics) - 1) // batch_size + 1}..."
            )

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
            if topic.get("selftext"):
                topic_list.append(f"   Context: {topic['selftext'][:200]}")

        topic_text = "\n".join(topic_list)

        prompt = self._build_scoring_prompt(topics, topic_text)

        try:
            response = self.client.messages.create(
                model="llama3.2",
                max_tokens=4000,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.content[0].text.strip()

            # Extract JSON from response
            if response_text.startswith("["):
                scores = json.loads(response_text)
            else:
                import re

                json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
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
                    score = {
                        "total": score_data.get("total_score", 0),
                        "reason": score_data.get("reason", ""),
                        "category": score_data.get("category", "uncategorized"),
                        "recommended": score_data.get("recommended", False),
                        "scored_at": datetime.now().isoformat(),
                        "engagement_bonus": None,
                    }
                    # Extract per-criterion scores using profile keys
                    for criterion in self.profile.get("criteria", []):
                        key = criterion["key"]
                        score[key] = score_data.get(key, 0)
                    topic["score"] = score
                    # Add engagement bonus from analytics if available
                    try:
                        from analytics import TopicEngagementScorer

                        actual_ep = topic.get("episode_number")
                        if actual_ep is not None:
                            eng_scorer = TopicEngagementScorer()
                            bonus = eng_scorer.get_engagement_bonus(actual_ep)
                            if bonus is not None:
                                topic["score"]["engagement_bonus"] = bonus
                                topic["score"]["total"] = min(
                                    10, topic["score"]["total"] + bonus * 0.1
                                )
                    except Exception:
                        pass  # Analytics integration is optional
                scored_topics.append(topic)

            return scored_topics

        except Exception as e:
            print(f"[ERROR] Scoring failed: {e}")
            # Return original topics without scores
            return topics

    def _build_scoring_prompt(self, topics: List[Dict], topic_text: str) -> str:
        """Build the LLM scoring prompt from the active scoring profile."""
        p = self.profile
        total_max = sum(c["max"] for c in p["criteria"])

        # Build criteria section
        criteria_lines = []
        for i, c in enumerate(p["criteria"], 1):
            criteria_lines.append(f"{i}. **{c['name']}** (0-{c['max']} points):")
            criteria_lines.append(f"   - {c['description']}")

        # Build style section
        style_lines = "\n".join(f"- {s}" for s in p.get("style", []))

        # Build examples
        high_ex = "\n".join(f"- {ex}" for ex in p.get("high_examples", []))
        low_ex = "\n".join(f"- {ex}" for ex in p.get("low_examples", []))

        # Build output format with dynamic keys
        example_scores = ", ".join(
            f'"{c["key"]}": {c["max"] - 1}' for c in p["criteria"]
        )
        categories = ", ".join(f'"{c}"' for c in p.get("categories", []))

        return f"""You are a podcast content analyst for "{Config.PODCAST_NAME}" - {p["description"]}.

**SCORING CRITERIA** (Total: 0-{total_max} points):

{chr(10).join(criteria_lines)}

**PODCAST STYLE**:
{style_lines}

**EXAMPLES OF HIGH-SCORING TOPICS** (8-10 points):
{high_ex}

**EXAMPLES OF LOW-SCORING TOPICS** (0-3 points):
{low_ex}

**YOUR TASK**:
Score each topic below (1-{len(topics)}). For each topic, provide:
- Total score (0-{total_max})
- Breakdown by category
- Brief reason (1 sentence)
- Suggested category: {categories}
- Recommended: true/false (recommend if score >= 6)

**TOPICS TO SCORE**:
{topic_text}

**OUTPUT FORMAT** (JSON only, no other text):
[
  {{
    "topic_number": 1,
    "total_score": 7.5,
    {example_scores},
    "reason": "Brief explanation of score",
    "category": "{p.get("categories", ["general"])[0]}",
    "recommended": true
  }},
  ...
]

Return ONLY the JSON array."""

    def filter_recommended(self, scored_topics: List[Dict]) -> List[Dict]:
        """Filter to only recommended topics (score >= 6)."""
        recommended = [
            t for t in scored_topics if t.get("score", {}).get("recommended", False)
        ]
        print(f"[INFO] {len(recommended)} topics recommended (score >= 6)")
        return recommended

    def sort_by_score(self, scored_topics: List[Dict]) -> List[Dict]:
        """Sort topics by total score (descending)."""
        return sorted(
            scored_topics,
            key=lambda t: t.get("score", {}).get("total", 0),
            reverse=True,
        )

    def group_by_category(self, scored_topics: List[Dict]) -> Dict[str, List[Dict]]:
        """Group topics by category."""
        categories = {}

        for topic in scored_topics:
            category = topic.get("score", {}).get("category", "uncategorized")
            if category not in categories:
                categories[category] = []
            categories[category].append(topic)

        return categories

    def save_scored_topics(
        self, scored_topics: List[Dict], filename: str = None
    ) -> Path:
        """Save scored topics to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scored_topics_{timestamp}.json"

        output_dir = Path("topic_data")
        output_dir.mkdir(exist_ok=True)

        output_path = output_dir / filename

        # Calculate statistics
        total = len(scored_topics)
        recommended = len(
            [t for t in scored_topics if t.get("score", {}).get("recommended", False)]
        )
        avg_score = sum(
            t.get("score", {}).get("total", 0) for t in scored_topics
        ) / max(total, 1)

        # Group by category
        categories = self.group_by_category(scored_topics)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "scored_at": datetime.now().isoformat(),
                    "statistics": {
                        "total_topics": total,
                        "recommended": recommended,
                        "average_score": round(avg_score, 2),
                        "categories": {
                            cat: len(topics) for cat, topics in categories.items()
                        },
                    },
                    "topics_by_category": {
                        cat: sorted(
                            topics,
                            key=lambda t: t.get("score", {}).get("total", 0),
                            reverse=True,
                        )
                        for cat, topics in categories.items()
                    },
                    "all_topics_sorted": self.sort_by_score(scored_topics),
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

        print(f"[OK] Saved scored topics to: {output_path}")
        print("[INFO] Statistics:")
        print(f"  Total: {total}")
        print(f"  Recommended (6+): {recommended}")
        print(f"  Average score: {avg_score:.2f}")
        print(f"  Categories: {', '.join(categories.keys())}")

        return output_path


def score_scraped_topics(input_file: str = None):
    """Score topics from a scraped topics file."""
    print("=" * 60)
    print(f"{Config.PODCAST_NAME.upper()} - TOPIC SCORER")
    print("=" * 60)
    print()

    # Find most recent scraped topics file if not specified
    if input_file is None:
        topic_data_dir = Path("topic_data")
        if not topic_data_dir.exists():
            print("[ERROR] No topic_data directory found")
            print("Run topic_scraper.py first to scrape topics")
            return

        scraped_files = list(topic_data_dir.glob("scraped_topics_*.json"))
        if not scraped_files:
            print("[ERROR] No scraped topics files found")
            print("Run topic_scraper.py first to scrape topics")
            return

        input_file = max(scraped_files, key=lambda p: p.stat().st_mtime)

    print(f"Loading topics from: {input_file}")

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        topics = data.get("topics", [])

    print(f"[OK] Loaded {len(topics)} topics")
    print()

    # Score topics
    scorer = TopicScorer()
    scored_topics = scorer.score_topics(topics, batch_size=10)

    # Save results
    output_path = scorer.save_scored_topics(scored_topics)

    print()
    print("=" * 60)
    print("[SUCCESS] SCORING COMPLETE")
    print("=" * 60)
    print()
    print("Next step: Add top topics to Google Doc")
    print("  python topic_curator.py")
    print()

    return output_path


if __name__ == "__main__":
    import sys

    input_file = sys.argv[1] if len(sys.argv) > 1 else None
    score_scraped_topics(input_file)
