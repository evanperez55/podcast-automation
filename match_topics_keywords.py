"""Match topics to episodes using keyword-based semantic matching."""

import json
from pathlib import Path
from typing import List, Dict, Tuple
from difflib import SequenceMatcher
import re


class KeywordTopicMatcher:
    """Match topics using keyword extraction and similarity."""

    def __init__(self):
        """Initialize the keyword matcher."""
        pass

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

    def extract_keywords(self, text: str) -> set:
        """Extract meaningful keywords from text."""
        # Convert to lowercase
        text = text.lower()

        # Remove common words
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'from', 'by', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
            'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'what', 'which', 'who', 'when', 'where', 'why', 'how', 'about',
            'into', 'through', 'during', 'before', 'after', 'above', 'below',
            'up', 'down', 'out', 'off', 'over', 'under', 'again', 'further',
            'then', 'once', 'here', 'there', 'all', 'both', 'each', 'few',
            'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
            'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just',
            'episode', 'episodes', 'podcast', 'discuss', 'discussing'
        }

        # Extract words (alphanumeric sequences)
        words = re.findall(r'\b\w+\b', text)

        # Filter stopwords and short words
        keywords = {w for w in words if w not in stopwords and len(w) > 2}

        return keywords

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity score."""
        # Direct substring match
        if text1.lower() in text2.lower() or text2.lower() in text1.lower():
            return 0.9

        # Keyword overlap
        keywords1 = self.extract_keywords(text1)
        keywords2 = self.extract_keywords(text2)

        if not keywords1 or not keywords2:
            return 0.0

        # Jaccard similarity
        intersection = keywords1 & keywords2
        union = keywords1 | keywords2
        jaccard = len(intersection) / len(union) if union else 0.0

        # Sequence matching
        sequence_ratio = SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

        # Combine scores (weighted average)
        combined = (jaccard * 0.6) + (sequence_ratio * 0.4)

        return combined

    def match_topic_to_episode(
        self,
        topic_text: str,
        episode: Dict
    ) -> Tuple[bool, float, str]:
        """
        Match a single topic to an episode.

        Returns:
            (discussed, confidence, reason)
        """
        # Build episode text
        episode_text = f"{episode['episode_summary']} "
        episode_text += " ".join([clip['description'] for clip in episode['best_clips']])
        episode_text += " ".join([clip['title'] for clip in episode['best_clips']])
        episode_text += episode.get('youtube_description', '')

        # Calculate similarity
        similarity = self.calculate_similarity(topic_text, episode_text)

        # Determine if discussed based on threshold
        discussed = similarity >= 0.3  # 30% threshold

        # Generate reason
        if similarity >= 0.7:
            reason = "Strong keyword match with episode content"
        elif similarity >= 0.5:
            reason = "Moderate keyword overlap with episode themes"
        elif similarity >= 0.3:
            reason = "Weak keyword match, possibly tangentially discussed"
        else:
            reason = "No significant keyword overlap found"

        return discussed, similarity, reason

    def match_all_topics(
        self,
        topics: List[Dict],
        episodes: List[Dict]
    ) -> List[Dict]:
        """Match all topics to all episodes."""
        matches = []

        print(f"[INFO] Matching {len(topics)} topics to {len(episodes)} episodes...")

        for i, topic in enumerate(topics):
            if (i + 1) % 50 == 0:
                print(f"[INFO] Progress: {i + 1}/{len(topics)} topics processed")

            topic_text = topic['text']
            best_confidence = 0.0
            matched_episodes = []
            best_reason = "No match found"

            # Check against all episodes
            for episode in episodes:
                discussed, confidence, reason = self.match_topic_to_episode(
                    topic_text,
                    episode
                )

                if discussed and confidence >= 0.3:
                    matched_episodes.append(episode['episode_number'])
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_reason = reason

            # Create match entry
            match = {
                'topic_id': topic['id'],
                'topic_text': topic_text,
                'discussed': len(matched_episodes) > 0,
                'confidence': round(best_confidence, 2),
                'episodes': sorted(matched_episodes),
                'reason': best_reason,
                'status_for_notion': 'Published' if len(matched_episodes) > 0 else 'Backlog'
            }

            matches.append(match)

        print(f"[OK] Matching complete: {len(matches)} topics processed")
        return matches

    def generate_analysis_report(self, matches: List[Dict]) -> Dict:
        """Generate the final analysis report."""

        # Calculate statistics
        total_topics = len(matches)
        matched = [m for m in matches if m['discussed']]
        unmatched = [m for m in matches if not m['discussed']]

        # Sort matched by confidence (highest first)
        matched_sorted = sorted(matched, key=lambda x: x['confidence'], reverse=True)

        # Find potential duplicates
        potential_duplicates = self._find_potential_duplicates(matches)

        report = {
            'total_topics': total_topics,
            'matched': len(matched),
            'unmatched': len(unmatched),
            'match_percentage': round(len(matched) / total_topics * 100, 2) if total_topics > 0 else 0,
            'matching_method': 'keyword-based semantic matching (fallback)',
            'note': 'This analysis uses keyword matching instead of AI due to API limits',
            'top_10_matches': matched_sorted[:10],
            'potential_duplicates': potential_duplicates[:20],  # Limit to 20
            'topics': matches
        }

        return report

    def _find_potential_duplicates(self, matches: List[Dict]) -> List[Dict]:
        """Find topics that might be duplicates."""
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

                # Calculate similarity
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
    """Main function."""
    print("="*60)
    print("TOPIC MATCHING ANALYSIS (KEYWORD-BASED)")
    print("="*60)

    matcher = KeywordTopicMatcher()

    # Load data
    print("\n[INFO] Loading topics and episodes...")
    topics = matcher.load_topics()
    episodes = matcher.load_episodes()

    print(f"[OK] Loaded {len(topics)} topics")
    print(f"[OK] Loaded {len(episodes)} episodes")

    # Match topics
    print("\n[INFO] Starting keyword-based matching...")
    matches = matcher.match_all_topics(topics, episodes)

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
        print("\n[POTENTIAL DUPLICATE TOPICS (First 10)]")
        for dup in report['potential_duplicates'][:10]:
            print(f"Topic {dup['primary_topic_id']}: {dup['primary_text'][:60]}...")
            for sim in dup['similar_topics']:
                print(f"  - Similar to #{sim['topic_id']} ({sim['similarity']*100:.0f}% match): {sim['text'][:60]}...")
            print()

    print("="*60)
    print(f"\nAll results saved to: {output_path.absolute()}")
    print("="*60)


if __name__ == '__main__':
    main()
