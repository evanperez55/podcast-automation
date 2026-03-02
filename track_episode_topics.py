"""Track which topics were discussed in a podcast episode.

Usage:
    python track_episode_topics.py path/to/episode.mp3 --episode-number 25
"""

import sys
import json
from pathlib import Path
from typing import List, Dict
import argparse
from ollama_client import Ollama
from notion_integration import NotionTopicManager


class EpisodeTopicTracker:
    """Match episode transcripts to Notion topics and update their status."""

    def __init__(self):
        """Initialize with Ollama and Notion clients."""
        self.ollama = Ollama()
        self.notion = NotionTopicManager()
        print("[OK] Episode topic tracker ready (using Ollama - FREE)")

    def transcribe_audio(self, audio_path: Path) -> str:
        """
        Transcribe audio file using Whisper.

        Args:
            audio_path: Path to audio file

        Returns:
            Transcript text
        """
        import whisper

        print(f"[INFO] Transcribing {audio_path.name}...")
        print("[WARNING] This may take several minutes for long episodes...")

        model = whisper.load_model("base")
        result = model.transcribe(str(audio_path))

        transcript = result["text"]
        print(f"[OK] Transcription complete ({len(transcript)} characters)")

        return transcript

    def get_episode_summary(self, transcript: str) -> str:
        """
        Generate episode summary using Ollama.

        Args:
            transcript: Full transcript text

        Returns:
            Summary of episode
        """
        print("[INFO] Generating episode summary with Ollama...")

        # Use first 4000 chars of transcript for summary
        transcript_excerpt = transcript[:4000]

        prompt = f"""Summarize this podcast episode in 2-3 sentences. Focus on the main topics discussed.

TRANSCRIPT:
{transcript_excerpt}

SUMMARY (2-3 sentences):"""

        response = self.ollama.messages.create(
            model="llama3.2",
            max_tokens=200,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )

        summary = response.content[0].text.strip()
        print("[OK] Summary generated")
        return summary

    def match_topics_to_episode(
        self, transcript: str, summary: str, episode_number: int
    ) -> List[Dict]:
        """
        Match Notion topics to this episode using Ollama.

        Args:
            transcript: Full transcript
            summary: Episode summary
            episode_number: Episode number

        Returns:
            List of matched topics with confidence scores
        """
        print("[INFO] Fetching topics from Notion...")

        # Get all backlog topics from Notion
        notion_topics = self.notion.query_database()
        backlog_topics = [
            t
            for t in notion_topics
            if t["properties"].get("Status", {}).get("select", {}).get("name")
            == "Backlog"
        ]

        print(f"[OK] Found {len(backlog_topics)} backlog topics to check")

        if not backlog_topics:
            print("[WARNING] No backlog topics found in Notion")
            return []

        # Build topic list for Ollama
        topic_list = []
        topic_map = {}  # Map index to topic data

        for idx, topic in enumerate(backlog_topics, 1):
            title_prop = topic["properties"].get("Name", {})
            if title_prop.get("title"):
                topic_text = title_prop["title"][0]["text"]["content"]
                topic_list.append(f"{idx}. {topic_text}")
                topic_map[idx] = {"id": topic["id"], "text": topic_text}

        # Batch topics into groups of 50 to avoid token limits
        batch_size = 50
        all_matches = []

        for batch_start in range(0, len(topic_list), batch_size):
            batch_end = min(batch_start + batch_size, len(topic_list))
            batch_topics = "\n".join(topic_list[batch_start:batch_end])

            print(
                f"[INFO] Matching topics {batch_start + 1}-{batch_end} against episode..."
            )

            prompt = f"""You are analyzing a podcast transcript to identify which topics were discussed in this episode.

EPISODE #{episode_number} SUMMARY:
{summary}

TRANSCRIPT EXCERPT (first 3000 chars):
{transcript[:3000]}

TOPICS TO CHECK:
{batch_topics}

For each topic, determine if it was discussed in this episode.

A topic is "discussed" if:
- The main subject matter matches (even if wording differs)
- A significant portion of conversation was about this topic
- The topic was a central theme or story

A topic is NOT discussed if:
- Only briefly mentioned in passing
- Used as a minor example
- Not actually covered

OUTPUT FORMAT (JSON only, no other text):
[
  {{
    "topic_number": 1,
    "discussed": true/false,
    "confidence": 0.0-1.0,
    "reason": "brief explanation"
  }}
]

Return ONLY the JSON array."""

            try:
                response = self.ollama.messages.create(
                    model="llama3.2",
                    max_tokens=2000,
                    temperature=0.1,
                    messages=[{"role": "user", "content": prompt}],
                )

                response_text = response.content[0].text.strip()

                # Parse JSON
                import re

                json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
                if json_match:
                    matches = json.loads(json_match.group(0))

                    # Filter for high-confidence matches
                    for match in matches:
                        if (
                            match.get("discussed", False)
                            and match.get("confidence", 0) >= 0.7
                        ):
                            topic_num = match["topic_number"] + batch_start
                            if topic_num in topic_map:
                                all_matches.append(
                                    {
                                        "page_id": topic_map[topic_num]["id"],
                                        "text": topic_map[topic_num]["text"],
                                        "confidence": match["confidence"],
                                        "reason": match.get("reason", ""),
                                    }
                                )

            except Exception as e:
                print(f"[ERROR] Failed to match batch: {e}")

        print(f"[OK] Found {len(all_matches)} matching topics")
        return all_matches

    def update_notion_topics(self, matched_topics: List[Dict], episode_number: int):
        """
        Update matched topics in Notion to Published status.

        Args:
            matched_topics: List of matched topic dictionaries
            episode_number: Episode number
        """
        if not matched_topics:
            print("[INFO] No topics to update")
            return

        print(f"[INFO] Updating {len(matched_topics)} topics in Notion...")

        for topic in matched_topics:
            try:
                # Update status to Published and add episode number
                self.notion.mark_topic_as_discussed(topic["page_id"], episode_number)
                print(f"  ✓ Updated: {topic['text'][:60]}...")

            except Exception as e:
                print(f"  ✗ Failed to update: {topic['text'][:60]}...")
                print(f"    Error: {e}")

        print(f"[OK] Updated {len(matched_topics)} topics to Published")

    def process_episode(self, audio_path: Path, episode_number: int) -> Dict:
        """
        Process an episode: transcribe, match topics, update Notion.

        Args:
            audio_path: Path to audio file
            episode_number: Episode number

        Returns:
            Dictionary with results
        """
        print("=" * 60)
        print(f"TRACKING TOPICS FOR EPISODE #{episode_number}")
        print("=" * 60)
        print()

        # Step 1: Transcribe
        transcript = self.transcribe_audio(audio_path)

        # Step 2: Generate summary
        summary = self.get_episode_summary(transcript)
        print(f"\nEpisode Summary:\n{summary}\n")

        # Step 3: Match topics
        matched_topics = self.match_topics_to_episode(
            transcript, summary, episode_number
        )

        if matched_topics:
            print("\n[MATCHED TOPICS]:")
            for topic in matched_topics:
                confidence_pct = int(topic["confidence"] * 100)
                print(f"  • {topic['text']} ({confidence_pct}% confidence)")
                print(f"    Reason: {topic['reason']}")

        # Step 4: Update Notion
        print()
        self.update_notion_topics(matched_topics, episode_number)

        print()
        print("=" * 60)
        print("[SUCCESS] EPISODE TRACKING COMPLETE")
        print("=" * 60)

        return {
            "episode_number": episode_number,
            "transcript_length": len(transcript),
            "summary": summary,
            "topics_matched": len(matched_topics),
            "topics": matched_topics,
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Track which topics were discussed in a podcast episode"
    )
    parser.add_argument(
        "audio_file", type=str, help="Path to audio file (mp3, wav, etc.)"
    )
    parser.add_argument(
        "--episode-number", type=int, required=True, help="Episode number"
    )

    args = parser.parse_args()

    audio_path = Path(args.audio_file)
    if not audio_path.exists():
        print(f"[ERROR] Audio file not found: {audio_path}")
        sys.exit(1)

    tracker = EpisodeTopicTracker()
    result = tracker.process_episode(audio_path, args.episode_number)

    print(
        f"\nTracked {result['topics_matched']} topics for Episode #{result['episode_number']}"
    )


if __name__ == "__main__":
    main()
