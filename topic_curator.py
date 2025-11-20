"""Topic curator - adds scored topics to Google Doc and plans episodes."""

import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from google_docs_tracker import GoogleDocsTopicTracker
from config import Config


class TopicCurator:
    """Curate topics and add them to Google Doc in organized structure."""

    # Category mapping with emoji and section headers
    CATEGORY_CONFIG = {
        'shocking_news': {
            'emoji': '🔥',
            'name': 'Shocking News Stories',
            'description': 'Real-world incidents with visceral impact',
            'target_per_episode': 3
        },
        'absurd_hypothetical': {
            'emoji': '🤔',
            'name': 'Absurd Hypotheticals',
            'description': 'Logical-but-ridiculous thought experiments',
            'target_per_episode': 3
        },
        'dating_social': {
            'emoji': '💔',
            'name': 'Dating & Social Commentary',
            'description': 'Modern relationship dynamics and awkwardness',
            'target_per_episode': 2
        },
        'pop_science': {
            'emoji': '🧪',
            'name': 'Pop Science & Technology',
            'description': 'Evolutionary changes, tech skepticism, medical topics',
            'target_per_episode': 2
        },
        'cultural_observation': {
            'emoji': '🙄',
            'name': 'Cultural Observations',
            'description': 'Workplace annoyances, social norms, consumer behavior',
            'target_per_episode': 2
        },
        'personal_anecdote': {
            'emoji': '😬',
            'name': 'Personal Anecdotes (Host Stories)',
            'description': 'Your embarrassing, wild, or relatable life experiences',
            'target_per_episode': 2
        }
    }

    def __init__(self):
        """Initialize curator with Google Docs connection."""
        try:
            self.docs_tracker = GoogleDocsTopicTracker()
            print("[OK] Connected to Google Docs")
        except Exception as e:
            print(f"[ERROR] Could not connect to Google Docs: {e}")
            self.docs_tracker = None

    def load_scored_topics(self, filename: str = None) -> Dict:
        """Load scored topics from JSON file."""
        if filename is None:
            topic_data_dir = Path('topic_data')
            if not topic_data_dir.exists():
                raise FileNotFoundError("No topic_data directory found")

            scored_files = list(topic_data_dir.glob('scored_topics_*.json'))
            if not scored_files:
                raise FileNotFoundError("No scored topics files found")

            filename = max(scored_files, key=lambda p: p.stat().st_mtime)

        print(f"[INFO] Loading scored topics from: {filename}")

        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)

    def format_topic_for_doc(self, topic: Dict) -> str:
        """Format a topic for Google Doc entry."""
        title = topic['title']
        score = topic.get('score', {})
        total_score = score.get('total', 0)
        source = topic.get('source', 'Unknown')
        url = topic.get('url', '')

        # Create formatted entry
        entry = f"{title}"

        # Add score badge if high-scoring
        if total_score >= 8:
            entry = f"⭐ {entry}"  # Star for excellent topics
        elif total_score >= 7:
            entry = f"✨ {entry}"  # Sparkle for great topics

        # Add source attribution (subtle)
        entry = f"{entry} [{source}]"

        return entry

    def restructure_google_doc(self, scored_data: Dict) -> bool:
        """
        Restructure Google Doc with categorized topics.

        This creates a clean, organized structure:
        - Header with instructions
        - Sections for each category
        - Topics sorted by score within each category
        - Discussed Topics section at bottom

        Args:
            scored_data: Scored topics data with categories

        Returns:
            True if successful
        """
        if not self.docs_tracker:
            print("[ERROR] Google Docs not connected")
            return False

        print("\n" + "="*60)
        print("RESTRUCTURING GOOGLE DOC")
        print("="*60)

        try:
            # Get recommended topics by category
            topics_by_category = scored_data.get('topics_by_category', {})
            stats = scored_data.get('statistics', {})

            # Build new document structure
            doc_content = []

            # Header
            doc_content.append("=" * 60)
            doc_content.append("FAKE PROBLEMS PODCAST - TOPIC BANK")
            doc_content.append("=" * 60)
            doc_content.append("")
            doc_content.append(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            doc_content.append(f"Total Topics: {stats.get('total_topics', 0)}")
            doc_content.append(f"Recommended Topics: {stats.get('recommended', 0)}")
            doc_content.append("")
            doc_content.append("HOW TO USE:")
            doc_content.append("1. Pick 8-12 topics for your next episode")
            doc_content.append("2. Mix categories for variety (see target mix below)")
            doc_content.append("3. After recording, automation will move discussed topics to bottom")
            doc_content.append("4. Run weekly scraper to refresh topics")
            doc_content.append("")
            doc_content.append("IDEAL EPISODE MIX:")
            doc_content.append("- 2-3 Shocking News Stories")
            doc_content.append("- 2-3 Absurd Hypotheticals")
            doc_content.append("- 1-2 Dating/Social Commentary")
            doc_content.append("- 1-2 Pop Science & Tech")
            doc_content.append("- 1-2 Cultural Observations")
            doc_content.append("- 1-2 Personal Anecdotes (you add these)")
            doc_content.append("")
            doc_content.append("=" * 60)
            doc_content.append("")

            # Add each category section
            for category_key, config in self.CATEGORY_CONFIG.items():
                emoji = config['emoji']
                name = config['name']
                description = config['description']
                target = config['target_per_episode']

                doc_content.append(f"{emoji} {name.upper()}")
                doc_content.append(f"({description})")
                doc_content.append(f"Target per episode: {target} topics")
                doc_content.append("")

                # Get topics for this category
                category_topics = topics_by_category.get(category_key, [])

                # Filter to recommended only (score >= 6)
                recommended = [
                    t for t in category_topics
                    if t.get('score', {}).get('recommended', False)
                ]

                if recommended:
                    for topic in recommended[:20]:  # Limit to top 20 per category
                        formatted = self.format_topic_for_doc(topic)
                        doc_content.append(f"  • {formatted}")
                else:
                    doc_content.append("  (No topics in this category yet)")

                doc_content.append("")

            # Add discussed topics section
            doc_content.append("")
            doc_content.append("=" * 60)
            doc_content.append("DISCUSSED TOPICS")
            doc_content.append("=" * 60)
            doc_content.append("")
            doc_content.append("(Topics will appear here after episodes are processed)")
            doc_content.append("")

            # Write to Google Doc
            # Note: This will REPLACE the entire document
            print("[WARNING] This will replace your entire Google Doc content")
            print(f"[INFO] New document will have {len(doc_content)} lines")
            print("[INFO] Preview:")
            for line in doc_content[:10]:
                print(f"  {line}")
            print("  ...")

            # For now, save to a text file instead of replacing doc
            output_file = Path('topic_data') / 'structured_topics.txt'
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(doc_content))

            print(f"\n[OK] Structured topics saved to: {output_file}")
            print("[INFO] Review this file, then copy/paste into your Google Doc")
            print("[INFO] Or implement full doc replacement in google_docs_tracker.py")

            return True

        except Exception as e:
            print(f"[ERROR] Restructuring failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def add_topics_to_existing_doc(
        self,
        scored_data: Dict,
        min_score: float = 7.0,
        max_per_category: int = 10
    ) -> bool:
        """
        Add new high-scoring topics to existing Google Doc structure.

        This assumes your doc already has category sections.

        Args:
            scored_data: Scored topics data
            min_score: Minimum score to add (default 7.0 for quality)
            max_per_category: Max topics to add per category

        Returns:
            True if successful
        """
        if not self.docs_tracker:
            print("[ERROR] Google Docs not connected")
            return False

        print("\n" + "="*60)
        print(f"ADDING TOPICS TO GOOGLE DOC (score >= {min_score})")
        print("="*60)

        try:
            topics_by_category = scored_data.get('topics_by_category', {})
            added_count = 0

            for category_key, topics in topics_by_category.items():
                # Filter high-scoring topics
                high_scoring = [
                    t for t in topics
                    if t.get('score', {}).get('total', 0) >= min_score
                ]

                if not high_scoring:
                    continue

                # Limit per category
                to_add = high_scoring[:max_per_category]

                config = self.CATEGORY_CONFIG.get(category_key, {})
                category_name = config.get('name', category_key)

                print(f"\n[{category_name}] Adding {len(to_add)} topics:")

                for topic in to_add:
                    formatted = self.format_topic_for_doc(topic)
                    score = topic.get('score', {}).get('total', 0)
                    print(f"  [{score:.1f}] {formatted[:80]}...")
                    added_count += 1

            print(f"\n[OK] Would add {added_count} topics")
            print("[INFO] Manual implementation: Copy topics above into your Google Doc")
            print("[INFO] Or implement automatic insertion in google_docs_tracker.py")

            return True

        except Exception as e:
            print(f"[ERROR] Adding topics failed: {e}")
            return False

    def plan_next_episode(self, scored_data: Dict) -> Dict:
        """
        Plan an episode with balanced topic selection.

        Args:
            scored_data: Scored topics data

        Returns:
            Episode plan with suggested topics
        """
        print("\n" + "="*60)
        print("EPISODE PLANNER")
        print("="*60)

        topics_by_category = scored_data.get('topics_by_category', {})
        episode_plan = {
            'planned_at': datetime.now().isoformat(),
            'categories': {},
            'total_topics': 0
        }

        for category_key, config in self.CATEGORY_CONFIG.items():
            target = config['target_per_episode']
            category_topics = topics_by_category.get(category_key, [])

            # Filter recommended
            recommended = [
                t for t in category_topics
                if t.get('score', {}).get('recommended', False)
            ]

            # Pick top N for this category
            selected = recommended[:target]

            episode_plan['categories'][category_key] = {
                'name': config['name'],
                'emoji': config['emoji'],
                'target': target,
                'selected': len(selected),
                'topics': selected
            }

            episode_plan['total_topics'] += len(selected)

        # Print plan
        print("\nSuggested Episode Structure:")
        print()

        for category_key, plan in episode_plan['categories'].items():
            emoji = plan['emoji']
            name = plan['name']
            selected = plan['selected']
            target = plan['target']

            print(f"{emoji} {name}: {selected}/{target} topics")

            for i, topic in enumerate(plan['topics'], 1):
                title = topic['title'][:70]
                score = topic.get('score', {}).get('total', 0)
                print(f"  {i}. [{score:.1f}] {title}...")

            print()

        print(f"Total: {episode_plan['total_topics']} topics")
        print()
        print("="*60)

        # Save plan
        output_dir = Path('topic_data')
        output_file = output_dir / f"episode_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(episode_plan, f, indent=2, ensure_ascii=False)

        print(f"[OK] Episode plan saved to: {output_file}")

        return episode_plan


def run_curation(mode: str = 'add'):
    """
    Run topic curation.

    Args:
        mode: 'restructure', 'add', or 'plan'
    """
    print("="*60)
    print("FAKE PROBLEMS - TOPIC CURATOR")
    print("="*60)
    print()

    curator = TopicCurator()

    # Load scored topics
    scored_data = curator.load_scored_topics()

    if mode == 'restructure':
        # Full doc restructure
        curator.restructure_google_doc(scored_data)

    elif mode == 'add':
        # Add high-scoring topics to existing doc
        curator.add_topics_to_existing_doc(scored_data, min_score=7.0, max_per_category=10)

    elif mode == 'plan':
        # Plan next episode
        curator.plan_next_episode(scored_data)

    else:
        print(f"[ERROR] Unknown mode: {mode}")
        print("Valid modes: 'restructure', 'add', 'plan'")


if __name__ == '__main__':
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else 'plan'
    run_curation(mode)
