"""Match Google Doc topics to podcast episodes using semantic analysis."""

import json
from pathlib import Path
import anthropic
from config import Config
from typing import List, Dict


class TopicMatcher:
    """Match topics to episodes using Claude AI."""

    def __init__(self):
        """Initialize the topic matcher."""
        self.anthropic_client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)

    def load_topics(self) -> List[Dict]:
        """Load topics from JSON file."""
        topics_file = Path('topic_data/google_doc_topics.json')
        with open(topics_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data['topics']

    def load_episodes(self) -> List[Dict]:
        """Load episode summaries from JSON file."""
        episodes_file = Path('topic_data/episode_summaries.json')
        with open(episodes_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data['episodes']

    def match_topics_batch(
        self,
        topics: List[Dict],
        episodes: List[Dict],
        batch_size: int = 50
    ) -> List[Dict]:
        """
        Match topics to episodes in batches using Claude.

        Args:
            topics: List of topic dictionaries
            episodes: List of episode dictionaries
            batch_size: Number of topics to process per API call

        Returns:
            List of matched topics with confidence scores
        """
        all_matches = []
        total_batches = (len(topics) + batch_size - 1) // batch_size

        print(f"[INFO] Processing {len(topics)} topics in {total_batches} batches of {batch_size}")

        # Create episode context for Claude
        episode_context = self._build_episode_context(episodes)

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(topics))
            batch_topics = topics[start_idx:end_idx]

            print(f"\n[INFO] Processing batch {batch_num + 1}/{total_batches} (topics {start_idx + 1}-{end_idx})")

            try:
                batch_matches = self._match_batch_with_claude(
                    batch_topics,
                    episode_context,
                    start_idx
                )
                all_matches.extend(batch_matches)
                print(f"[OK] Batch {batch_num + 1} complete: {len(batch_matches)} matches")

            except Exception as e:
                print(f"[ERROR] Batch {batch_num + 1} failed: {e}")
                # Add unmatched entries for failed batch
                for topic in batch_topics:
                    all_matches.append({
                        'topic_id': topic['id'],
                        'topic_text': topic['text'],
                        'discussed': False,
                        'confidence': 0.0,
                        'episodes': [],
                        'reason': 'Failed to process',
                        'status_for_notion': 'Backlog'
                    })

        return all_matches

    def _build_episode_context(self, episodes: List[Dict]) -> str:
        """Build a comprehensive context of all episodes."""
        context_parts = []

        for ep in episodes:
            ep_num = ep['episode_number']
            summary = ep['episode_summary']

            # Add clip titles for more context
            clip_info = []
            for clip in ep['best_clips']:
                clip_info.append(f"- {clip['title']}: {clip['description']}")

            clips_text = "\n  ".join(clip_info) if clip_info else "  (no clips)"

            context_parts.append(
                f"Episode {ep_num}:\n"
                f"  Summary: {summary}\n"
                f"  Key clips:\n  {clips_text}"
            )

        return "\n\n".join(context_parts)

    def _match_batch_with_claude(
        self,
        topics: List[Dict],
        episode_context: str,
        batch_start_idx: int
    ) -> List[Dict]:
        """Match a batch of topics using Claude."""

        # Build topic list
        topic_list = []
        for i, topic in enumerate(topics):
            topic_id = batch_start_idx + i + 1
            topic_list.append(f"{topic_id}. {topic['text']}")

        topics_text = "\n".join(topic_list)

        prompt = f"""You are analyzing podcast episodes to determine which topics from a topic list were discussed.

**ALL EPISODE INFORMATION (Episodes 1-24):**
{episode_context}

**TOPICS TO CHECK:**
{topics_text}

**YOUR TASK:**
For each topic in the list, determine if it was discussed in ANY episode (1-24).

A topic is "discussed" if:
- The episode's summary or clips explicitly mention this topic or concept
- A significant portion of the episode covers this topic
- The topic was a central theme, story, or discussion point
- Use SEMANTIC matching - "cheese addiction" matches "eating too much cheese"

A topic is NOT discussed if:
- Only vaguely related or tangentially mentioned
- No clear connection to episode content
- Just a brief reference or example

**CONFIDENCE SCORING:**
- 0.9-1.0: Topic is explicitly mentioned or clearly the main focus
- 0.7-0.89: Strong semantic match, clearly discussed but maybe different wording
- 0.5-0.69: Probable match but some uncertainty
- 0.3-0.49: Weak/tangential connection
- 0.0-0.29: Not discussed

**OUTPUT FORMAT:**
Return ONLY a JSON array with this exact structure:
[
  {{
    "topic_id": 1,
    "topic_text": "exact topic text from list",
    "discussed": true/false,
    "confidence": 0.0-1.0,
    "episodes": [list of episode numbers where discussed, e.g., [5, 12]],
    "reason": "brief explanation (1-2 sentences max)",
    "status_for_notion": "Published" if discussed else "Backlog"
  }}
]

**IMPORTANT:**
- Only mark discussed=true if confidence >= 0.7
- Include ALL topics from the list, even if not discussed
- Be thorough but conservative - only high-confidence matches
- Return ONLY the JSON array, no other text

Return the JSON array now:"""

        try:
            response = self.anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                temperature=0.1,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            response_text = response.content[0].text.strip()

            # Parse JSON response
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                matches = json.loads(json_match.group(0))
                return matches
            else:
                print("[WARNING] Could not parse Claude's response")
                return []

        except Exception as e:
            print(f"[ERROR] Claude API call failed: {e}")
            raise

    def generate_analysis_report(self, matches: List[Dict]) -> Dict:
        """Generate the final analysis report."""

        # Calculate statistics
        total_topics = len(matches)
        matched = [m for m in matches if m['discussed']]
        unmatched = [m for m in matches if not m['discussed']]

        # Sort matched by confidence (highest first)
        matched_sorted = sorted(matched, key=lambda x: x['confidence'], reverse=True)

        # Find potential duplicates (topics with very similar text)
        potential_duplicates = self._find_potential_duplicates(matches)

        report = {
            'total_topics': total_topics,
            'matched': len(matched),
            'unmatched': len(unmatched),
            'match_percentage': round(len(matched) / total_topics * 100, 2) if total_topics > 0 else 0,
            'top_10_matches': matched_sorted[:10],
            'potential_duplicates': potential_duplicates,
            'topics': matches
        }

        return report

    def _find_potential_duplicates(self, matches: List[Dict]) -> List[Dict]:
        """Find topics that might be duplicates based on text similarity."""
        from difflib import SequenceMatcher

        duplicates = []
        checked = set()

        for i, topic1 in enumerate(matches):
            if i in checked:
                continue

            similar_topics = []
            text1 = topic1['topic_text'].lower().strip()

            for j, topic2 in enumerate(matches):
                if i >= j or j in checked:
                    continue

                text2 = topic2['topic_text'].lower().strip()

                # Calculate similarity ratio
                ratio = SequenceMatcher(None, text1, text2).ratio()

                if ratio > 0.7:  # 70% similar
                    similar_topics.append({
                        'topic_id': topic2['topic_id'],
                        'text': topic2['topic_text'],
                        'similarity': round(ratio, 2)
                    })
                    checked.add(j)

            if similar_topics:
                duplicates.append({
                    'primary_topic_id': topic1['topic_id'],
                    'primary_text': topic1['topic_text'],
                    'similar_topics': similar_topics
                })
                checked.add(i)

        return duplicates


def main():
    """Main function to run topic matching."""
    print("="*60)
    print("TOPIC MATCHING ANALYSIS")
    print("="*60)

    matcher = TopicMatcher()

    # Load data
    print("\n[INFO] Loading topics and episodes...")
    topics = matcher.load_topics()
    episodes = matcher.load_episodes()

    print(f"[OK] Loaded {len(topics)} topics")
    print(f"[OK] Loaded {len(episodes)} episodes")

    # Match topics to episodes
    print("\n[INFO] Starting semantic matching with Claude AI...")
    matches = matcher.match_topics_batch(topics, episodes, batch_size=50)

    print(f"\n[OK] Matching complete: {len(matches)} topics processed")

    # Generate report
    print("\n[INFO] Generating analysis report...")
    report = matcher.generate_analysis_report(matches)

    # Save report
    output_path = Path('topic_data/topic_matching_analysis.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"[OK] Saved to {output_path}")

    # Print summary
    print("\n" + "="*60)
    print("ANALYSIS SUMMARY")
    print("="*60)
    print(f"Total topics analyzed: {report['total_topics']}")
    print(f"Topics matched: {report['matched']} ({report['match_percentage']}%)")
    print(f"Topics unmatched: {report['unmatched']}")
    print(f"Potential duplicates found: {len(report['potential_duplicates'])}")

    print("\n[TOP 10 MOST CONFIDENT MATCHES]")
    for i, match in enumerate(report['top_10_matches'], 1):
        episodes_str = ", ".join(map(str, match['episodes']))
        print(f"{i}. {match['topic_text'][:60]}...")
        print(f"   Episodes: {episodes_str} | Confidence: {match['confidence']:.2f}")
        print(f"   Reason: {match['reason']}")
        print()

    if report['potential_duplicates']:
        print("\n[POTENTIAL DUPLICATE TOPICS]")
        for dup in report['potential_duplicates'][:5]:
            print(f"Topic {dup['primary_topic_id']}: {dup['primary_text'][:60]}...")
            for sim in dup['similar_topics']:
                print(f"  - Similar to #{sim['topic_id']} ({sim['similarity']*100:.0f}% match): {sim['text'][:60]}...")
            print()

    print("="*60)
    print(f"\nAll results saved to: {output_path.absolute()}")
    print("="*60)


if __name__ == '__main__':
    main()
