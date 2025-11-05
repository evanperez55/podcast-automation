"""Content editing using Claude AI to identify problematic content and best moments."""

import anthropic
import json
from config import Config


class ContentEditor:
    """Use Claude to analyze transcript and identify content to censor and best clips."""

    def __init__(self):
        """Initialize Anthropic Claude client."""
        if not Config.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        print(f"[OK] Claude AI ready")

    def analyze_content(self, transcript_data):
        """
        Analyze transcript to find content to censor and identify best moments.

        Args:
            transcript_data: Transcript data with words and timestamps

        Returns:
            Dictionary with:
            - censor_timestamps: List of {start, end, reason} to beep
            - best_clips: List of {start, end, description, why_interesting}
            - episode_summary: Summary of the episode
            - social_captions: Suggested captions for social media
        """
        print("Analyzing content with Claude...")

        # Prepare transcript text with timestamps for Claude
        words = transcript_data.get('words', [])
        segments = transcript_data.get('segments', [])

        # Create a readable version with timestamps
        timestamped_text = self._format_transcript_for_analysis(words, segments)

        # Build the prompt for Claude
        prompt = self._build_analysis_prompt(timestamped_text)

        try:
            # Call Claude API
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",  # Latest Claude model
                max_tokens=4000,
                temperature=0.3,  # Lower temperature for more consistent output
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Parse Claude's response
            response_text = response.content[0].text
            analysis = self._parse_claude_response(response_text)

            print(f"[OK] Content analysis complete")
            print(f"  Items to censor: {len(analysis['censor_timestamps'])}")
            print(f"  Best clips identified: {len(analysis['best_clips'])}")

            return analysis

        except Exception as e:
            print(f"[ERROR] Claude analysis error: {e}")
            raise

    def _format_transcript_for_analysis(self, words, segments):
        """Format transcript with timestamps for Claude to analyze."""
        # Use segments for better readability
        formatted = []

        for i, segment in enumerate(segments):
            start_time = self._format_timestamp(segment['start'])
            text = segment['text'].strip()
            formatted.append(f"[{start_time}] {text}")

        return "\n".join(formatted)

    def _format_timestamp(self, seconds):
        """Convert seconds to HH:MM:SS format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _build_analysis_prompt(self, timestamped_text):
        """Build the prompt for Claude to analyze the content."""
        names_list = ", ".join(Config.NAMES_TO_REMOVE)

        prompt = f"""You are analyzing a podcast transcript for the "Fake Problems Podcast" to identify content that needs censoring and find the best moments for social media clips.

**YOUR TASKS:**

1. **IDENTIFY CONTENT TO CENSOR:**
   Find all instances of:
   - Personal names: {names_list}
   - Racial slurs (any racial slurs, including n-word variants)
   - Homophobic slurs (including f-slur variants, d-slur, etc.)
   - Any other highly offensive language

   For each instance, provide the timestamp and a brief reason.

2. **IDENTIFY BEST MOMENTS FOR CLIPS (15-30 seconds):**
   Find {Config.NUM_CLIPS} compelling moments that would make great social media clips. Look for:
   - Funny or entertaining moments
   - Controversial or thought-provoking statements
   - Relatable "fake problems" discussions
   - Moments with good energy and pacing
   - Self-contained stories or bits

   For each clip, provide start/end timestamps and explain why it's interesting.

3. **WRITE EPISODE SUMMARY:**
   Write a 2-3 sentence summary of the episode's main topics and themes.

4. **CREATE SOCIAL MEDIA CAPTIONS:**
   Write engaging captions for:
   - YouTube (description format, 2-3 paragraphs)
   - Instagram/TikTok (short, punchy, with emojis)
   - Twitter (concise, under 280 chars)

**TRANSCRIPT:**

{timestamped_text}

**OUTPUT FORMAT (JSON):**

Please respond with ONLY valid JSON in this exact format:

{{
  "censor_timestamps": [
    {{
      "timestamp": "HH:MM:SS",
      "reason": "Name: Joey",
      "context": "brief quote showing the word"
    }}
  ],
  "best_clips": [
    {{
      "start": "HH:MM:SS",
      "end": "HH:MM:SS",
      "duration_seconds": 25,
      "description": "Brief description of the clip",
      "why_interesting": "Why this would work as a clip",
      "suggested_title": "Catchy title for the clip"
    }}
  ],
  "episode_summary": "2-3 sentence summary of the episode",
  "social_captions": {{
    "youtube": "Full YouTube description",
    "instagram": "Instagram caption with emojis",
    "twitter": "Tweet under 280 chars"
  }}
}}
"""

        return prompt

    def _parse_claude_response(self, response_text):
        """Parse Claude's JSON response."""
        try:
            # Extract JSON from response (Claude sometimes adds explanation text)
            # Find the JSON block
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1

            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in Claude's response")

            json_str = response_text[start_idx:end_idx]
            analysis = json.loads(json_str)

            # Convert timestamp strings to seconds for easier use
            for item in analysis.get('censor_timestamps', []):
                if 'timestamp' in item:
                    item['seconds'] = self._timestamp_to_seconds(item['timestamp'])

            for clip in analysis.get('best_clips', []):
                if 'start' in clip:
                    clip['start_seconds'] = self._timestamp_to_seconds(clip['start'])
                if 'end' in clip:
                    clip['end_seconds'] = self._timestamp_to_seconds(clip['end'])

            return analysis

        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse Claude's JSON response: {e}")
            print(f"Response was: {response_text[:500]}")
            raise

    def _timestamp_to_seconds(self, timestamp_str):
        """Convert HH:MM:SS to seconds."""
        parts = timestamp_str.split(':')
        if len(parts) == 3:
            hours, minutes, seconds = map(int, parts)
            return hours * 3600 + minutes * 60 + seconds
        elif len(parts) == 2:
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
        else:
            return int(parts[0])


if __name__ == '__main__':
    # Test content editor
    import sys

    if len(sys.argv) < 2:
        print("Usage: python content_editor.py <transcript.json>")
        sys.exit(1)

    transcript_file = sys.argv[1]

    with open(transcript_file, 'r', encoding='utf-8') as f:
        transcript_data = json.load(f)

    editor = ContentEditor()
    analysis = editor.analyze_content(transcript_data)

    print("\n" + "="*60)
    print("CONTENT ANALYSIS RESULTS")
    print("="*60)

    print(f"\n📝 EPISODE SUMMARY:\n{analysis['episode_summary']}\n")

    print(f"🚫 ITEMS TO CENSOR: {len(analysis['censor_timestamps'])}")
    for item in analysis['censor_timestamps'][:5]:  # Show first 5
        print(f"  - {item['timestamp']}: {item['reason']}")

    print(f"\n✂️ BEST CLIPS: {len(analysis['best_clips'])}")
    for clip in analysis['best_clips']:
        print(f"  - {clip['start']} to {clip['end']}: {clip['description']}")

    print(f"\n📱 SOCIAL CAPTIONS:")
    print(f"  Twitter: {analysis['social_captions']['twitter'][:100]}...")
