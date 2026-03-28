"""Content editing using OpenAI GPT-4 to identify problematic content and best moments."""

import openai
import json
import time
from audio_clip_scorer import AudioClipScorer
from config import Config
from logger import logger

VOICE_PERSONA = (
    "You write for the Fake Problems Podcast — an irreverent comedy show "
    "hosted by two guys who talk about dark, weird, and absurd topics with "
    "deadpan confidence. Your output sounds like it was written by the hosts "
    "themselves: casual, a little dark, never corporate. No exclamation points "
    "for hype. No 'join us as we...'. Never use filler phrases like 'delve into' "
    "or 'unravel'. Write like you'd say it out loud to a friend who gets the joke."
)


class ContentEditor:
    """Use OpenAI GPT-4 to analyze transcript and identify content to censor and best clips."""

    def __init__(self):
        """Initialize OpenAI client."""
        self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        logger.info("OpenAI GPT-4 ready")

    def analyze_content(
        self,
        transcript_data,
        topic_context=None,
        audio_path=None,
        engagement_context=None,
    ):
        """
        Analyze transcript to find content to censor and identify best moments.

        Args:
            transcript_data: Transcript data with words and timestamps
            topic_context: Optional list of scored topic dicts from topic_data/
                           (each with 'topic', 'score', 'category', etc.)

        Returns:
            Dictionary with:
            - censor_timestamps: List of {start_seconds, end_seconds, reason} to beep
            - best_clips: List of {start, end, description, why_interesting, hook_caption, clip_hashtags}
            - episode_summary: Summary of the episode
            - social_captions: Suggested captions for social media
        """
        logger.info("Analyzing content with OpenAI GPT-4...")

        # Prepare transcript text with timestamps for the LLM
        words = transcript_data.get("words", [])
        segments = transcript_data.get("segments", [])

        # Store words for later word-level timestamp lookup
        self._words = words

        # Create a readable version with timestamps
        timestamped_text = self._format_transcript_for_analysis(words, segments)

        # Score segments by audio energy if audio is available
        energy_candidates = None
        if audio_path:
            scorer = AudioClipScorer()
            scored_segments = scorer.score_segments(audio_path, segments)
            # Sort by energy score descending, take top N
            sorted_segs = sorted(
                scored_segments,
                key=lambda s: s.get("audio_energy_score", 0),
                reverse=True,
            )
            energy_candidates = sorted_segs[: Config.CLIP_AUDIO_TOP_N]

        # Suppress energy candidates for content-driven genres (flat audio energy)
        clip_selection_mode = getattr(Config, "CLIP_SELECTION_MODE", "energy")
        if clip_selection_mode == "content":
            energy_candidates = None

        # Build the prompt for the LLM
        prompt = self._build_analysis_prompt(
            timestamped_text,
            topic_context=topic_context,
            energy_candidates=energy_candidates,
            engagement_context=engagement_context,
        )

        try:
            # Call OpenAI API with retry on transient failures
            voice = getattr(Config, "VOICE_PERSONA", None) or VOICE_PERSONA
            response = self._call_openai_with_retry(voice, prompt)

            # Parse GPT-4's response
            response_text = response.choices[0].message.content
            analysis = self._parse_llm_response(response_text)

            # Ensure new fields have defaults (backward compat with older responses)
            analysis.setdefault("show_notes", "")
            analysis.setdefault("chapters", [])
            analysis.get("social_captions", {}).setdefault("tiktok", "")

            # DIRECT SEARCH: Find words to censor by searching transcript directly
            # This is more reliable than GPT-4 which can hallucinate
            direct_censor_timestamps = self._find_words_to_censor_directly(self._words)

            # Validate any GPT-4 suggestions (as backup)
            validated_gpt_timestamps = self._validate_censor_timestamps(
                analysis.get("censor_timestamps", [])
            )

            # Merge direct search results with validated GPT-4 results (avoid duplicates)
            all_censor_timestamps = self._merge_censor_timestamps(
                direct_censor_timestamps, validated_gpt_timestamps
            )

            # Refine censor timestamps using word-level data from Whisper
            analysis["censor_timestamps"] = self._refine_censor_timestamps(
                all_censor_timestamps, self._words
            )

            logger.info("Content analysis complete")
            logger.info("Items to censor: %d", len(analysis["censor_timestamps"]))
            logger.info("Best clips identified: %d", len(analysis["best_clips"]))

            return analysis

        except Exception as e:
            logger.error("OpenAI analysis error: %s", e)
            raise

    def _call_openai_with_retry(self, voice_persona, prompt, max_retries=3):
        """Call OpenAI API with exponential backoff on transient errors.

        Args:
            voice_persona: System message for the LLM.
            prompt: User message content.
            max_retries: Maximum retry attempts.

        Returns:
            OpenAI ChatCompletion response.

        Raises:
            Exception: After all retries exhausted.
        """
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                return self.client.chat.completions.create(
                    model="gpt-4o",
                    max_tokens=6000,
                    temperature=0.7,
                    messages=[
                        {"role": "system", "content": voice_persona},
                        {"role": "user", "content": prompt},
                    ],
                )
            except (
                openai.RateLimitError,
                openai.APIError,
                openai.APIConnectionError,
                openai.APITimeoutError,
            ) as e:
                last_error = e
                if attempt < max_retries:
                    delay = min(2.0 * (2**attempt), 60.0)
                    logger.warning(
                        "OpenAI API error (attempt %d/%d): %s — retrying in %.0fs",
                        attempt + 1,
                        max_retries,
                        e,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "OpenAI API failed after %d retries: %s", max_retries, e
                    )
        raise last_error

    def _format_transcript_for_analysis(self, words, segments):
        """Format transcript with timestamps for Claude to analyze."""
        # Use segments for better readability
        formatted = []

        for i, segment in enumerate(segments):
            start_time = self._format_timestamp(segment["start"])
            text = segment["text"].strip()
            formatted.append(f"[{start_time}] {text}")

        return "\n".join(formatted)

    def _format_timestamp(self, seconds):
        """Convert seconds to HH:MM:SS format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _build_analysis_prompt(
        self,
        timestamped_text,
        topic_context=None,
        energy_candidates=None,
        engagement_context=None,
    ):
        """Build the prompt for Claude to analyze the content.

        Args:
            timestamped_text: Formatted transcript with timestamps
            topic_context: Optional list of scored topic dicts for clip prioritization
            energy_candidates: Optional list of high-energy segment dicts for clip prioritization
            engagement_context: Optional dict from EngagementScorer.get_category_rankings()
        """
        names_list = ", ".join(Config.NAMES_TO_REMOVE)

        # Build optional topic context section
        topic_section = ""
        if topic_context:
            topic_lines = []
            for t in topic_context[:10]:  # Top 10 topics
                topic_lines.append(
                    f"  - {t.get('topic', 'Unknown')} (score: {t.get('score', 0)}, category: {t.get('category', 'general')})"
                )
            topic_section = f"""
**TRENDING TOPICS (prioritize clips about these if they appear in the episode):**
{chr(10).join(topic_lines)}

"""

        # Build optional energy candidates section
        energy_section = ""
        if energy_candidates:
            lines = []
            for seg in energy_candidates[:10]:
                ts = self._format_timestamp(seg.get("start", 0))
                score = seg.get("audio_energy_score", 0)
                text_preview = seg.get("text", "")[:80]
                lines.append(f"  - [{ts}] energy={score:.2f}: {text_preview}")
            energy_section = (
                "\n**HIGH ENERGY MOMENTS (audio analysis — prioritize these for clips):**\n"
                + "\n".join(lines)
                + "\n"
            )

        # Build optional engagement history section
        engagement_section = ""
        if (
            engagement_context
            and engagement_context.get("status") == "ok"
            and engagement_context.get("rankings")
        ):
            lines = []
            for ranking in engagement_context["rankings"][:3]:  # Top 3 categories
                category = ranking.get("category", "unknown")
                correlation = ranking.get("correlation", 0.0)
                direction = "positive" if correlation >= 0 else "neutral"
                lines.append(
                    f"  - {category} (correlation: {correlation:.2f}, {direction})"
                )
            engagement_section = (
                "\n**HISTORICALLY HIGH-PERFORMING CONTENT CATEGORIES "
                "(bias clip selection toward these when present in episode):**\n"
                + "\n".join(lines)
                + "\n"
            )

        # Build clip criteria based on genre (VOICE_PERSONA presence indicates non-comedy client)
        custom_persona = getattr(Config, "VOICE_PERSONA", None)
        if not custom_persona:
            clip_criteria = (
                "   - Funny or entertaining moments\n"
                "   - Controversial or thought-provoking statements\n"
                '   - Relatable "fake problems" discussions\n'
                "   - Moments with good energy and pacing\n"
                "   - Self-contained stories or bits"
            )
        else:
            clip_criteria = (
                "   - Moments with a clear, quotable insight or revelation\n"
                "   - Self-contained segments that make sense out of context\n"
                "   - Emotionally compelling or tension-building moments\n"
                "   - Key data points, specific numbers, or case-breaking details\n"
                "   - Strong narrative hooks that make someone want to hear more"
            )

        # Only inject Fake Problems voice examples when no custom persona is configured.
        # Custom clients have their own voice in the system message — don't override with FP examples.
        if not custom_persona:
            voice_examples = """
**VOICE EXAMPLES — match this tone in ALL output:**

Episode titles:
BAD (generic): "Exploring the Science of Lobster Immortality"
GOOD (show voice): "Lobsters Are Basically Immortal and Honestly Good for Them"

BAD: "A Deep Dive into Rube Goldberg Machines"
GOOD: "Rube Goldberg Invented a Machine Just to Avoid Responsibility"

Twitter/X captions:
BAD: "Great episode discussing fascinating topics!"
GOOD: "we spent 20 minutes on whether horses are lying to us and I stand by every second of it"

YouTube descriptions (slightly moderated — no shock value, but still dry and authentic):
BAD: "Join us as we explore today's fascinating topics with expert analysis."
GOOD: "This week: lobster immortality, a machine designed for one very specific terrible purpose, and a myth that has apparently been following horses around for decades."

Instagram/TikTok:
BAD: "Listen to this week's episode for an eye-opening discussion 🎙️"
GOOD: "turns out immortality is real, it just only applies to lobsters. link in bio 🦞"

"""
        else:
            # Custom voice persona is set in system message — don't override with FP examples
            voice_examples = ""

        prompt = f"""You are analyzing a podcast transcript for "{Config.PODCAST_NAME}" to identify content that needs censoring and find the best moments for social media clips.
{topic_section}{engagement_section}{voice_examples}{energy_section}

**YOUR TASKS:**

1. **IDENTIFY CONTENT TO CENSOR:**
   Find all instances of:
   - Personal names: {names_list}
   - Racial slurs (the actual n-word and variants - NOT words like "black" or "white")
   - Homophobic slurs (the actual f-slur and variants)

   **CRITICAL RULES:**
   - ONLY flag content if the EXACT word appears in the transcript
   - The "context" field MUST contain the actual word being censored
   - If no names or slurs appear, return an EMPTY array: []
   - Do NOT flag crude language like "ass", "shit", "damn", etc. - only actual slurs
   - Do NOT hallucinate - if you don't see the exact word, don't include it
   - Words like "dominate" or "joe" (as in "cup of joe") do NOT count as names

   For each REAL instance, provide the timestamp and the exact quote containing the word.

2. **IDENTIFY BEST MOMENTS FOR CLIPS (15-30 seconds):**
   Find {Config.NUM_CLIPS} compelling moments that would make great social media clips. Look for:
{clip_criteria}

   For each clip, provide start/end timestamps and explain why it's interesting.

3. **CREATE A FUNNY EPISODE TITLE:**
   Generate a catchy, humorous episode title that:
   - Is derived from the funniest or most memorable quote/moment in the episode
   - Should be something one of the hosts actually said (or close to it)
   - Can be absurd, out-of-context, or ironically serious
   - Should make people curious to listen
   - Examples of good titles: "I'm Basically a Godfather Now", "Healthcare is a Scam and I Can Prove It", "POV: You Don't Know What POV Means"

4. **WRITE EPISODE SUMMARY:**
   Write a 2-3 sentence summary of the episode's main topics and themes.

## SOCIAL CAPTIONS (same irreverent voice — no corporate language, no filler phrases):
5. **CREATE SOCIAL MEDIA CAPTIONS:**
   Write engaging captions for:
   - YouTube (description format, 2-3 paragraphs — slightly moderated but still dry and authentic, algorithm-safe)
   - Instagram (short, punchy, with emojis)
   - Twitter/X (concise, under 280 chars — punchy and dry, show voice)
   - TikTok (short, punchy, under 150 chars, with emojis)

6. **WRITE DETAILED SHOW NOTES:**
   Write show notes for the episode page/description:
   - Opening paragraph (2-3 sentences setting the scene)
   - 4-8 bullet points covering the main topics discussed
   - 1-2 notable or funny quotes from the episode (without attributing to specific hosts by name)

7. **IDENTIFY CHAPTER MARKERS:**
   Identify 5-8 major topic transitions for chapter markers:
   - The first chapter MUST be "00:00:00 Intro"
   - Each chapter should have a timestamp (HH:MM:SS) and a short title (3-8 words)
   - Chapters should mark when the conversation shifts to a new topic
   - Space them relatively evenly throughout the episode

**CRITICAL - ANONYMITY REQUIREMENT:**
   The hosts' names are being CENSORED from the audio for privacy/anonymity reasons.
   You must NEVER include any of these names in ANY output: {names_list}
   - Do NOT mention host names in the episode_summary
   - Do NOT mention host names in ANY social_captions (YouTube, Instagram, Twitter)
   - Do NOT mention host names in clip descriptions
   - Refer to the hosts generically as "the hosts" or "the guys" if needed
   - This is extremely important - including names defeats the entire purpose of censoring them

**TRANSCRIPT:**

{timestamped_text}

**OUTPUT FORMAT (JSON):**

Please respond with ONLY valid JSON in this exact format:

{{
  "episode_title": "Funny episode title derived from a quote or moment",
  "censor_timestamps": [
    {{
      "timestamp": "HH:MM:SS",
      "reason": "Name: Joey",
      "context": "and then Joey said we should leave"
    }}
  ],
  "NOTE": "censor_timestamps should be an EMPTY ARRAY [] if no names or slurs are found",
  "best_clips": [
    {{
      "start": "HH:MM:SS",
      "end": "HH:MM:SS",
      "duration_seconds": 25,
      "description": "Brief description of the clip",
      "why_interesting": "Why this would work as a clip",
      "suggested_title": "Catchy title for the clip",
      "hook_caption": "Hook for the first 2 seconds. Show-specific style: 'wait so lobsters just... don't die??', 'someone finally said it out loud', 'this is the worst idea I've ever loved'. Dry, curious, or darkly amused — never generic hype.",
      "clip_hashtags": ["relevant", "hashtags", "for", "this", "clip"]
    }}
  ],
  "episode_summary": "2-3 sentence summary of the episode",
  "social_captions": {{
    "youtube": "Full YouTube description",
    "instagram": "Instagram caption with emojis",
    "twitter": "Tweet under 280 chars",
    "tiktok": "TikTok caption under 150 chars with emojis"
  }},
  "show_notes": "Opening paragraph.\\n\\n- Topic 1 bullet point\\n- Topic 2 bullet point\\n...\\n\\nNotable quote: \\"Funny quote from the episode\\"",
  "chapters": [
    {{
      "start_timestamp": "00:00:00",
      "title": "Intro"
    }},
    {{
      "start_timestamp": "00:05:30",
      "title": "Topic Title Here"
    }}
  ]
}}
"""

        return prompt

    def _parse_llm_response(self, response_text):
        """Parse Claude's JSON response."""
        try:
            # Extract JSON from response (Claude sometimes adds explanation text)
            # Find the JSON block
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1

            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in Claude's response")

            json_str = response_text[start_idx:end_idx]
            analysis = json.loads(json_str)

            # Convert timestamp strings to seconds for easier use
            for item in analysis.get("censor_timestamps", []):
                if "timestamp" in item:
                    item["seconds"] = self._timestamp_to_seconds(item["timestamp"])

            for clip in analysis.get("best_clips", []):
                if "start" in clip:
                    clip["start_seconds"] = self._timestamp_to_seconds(clip["start"])
                if "end" in clip:
                    clip["end_seconds"] = self._timestamp_to_seconds(clip["end"])

            for chapter in analysis.get("chapters", []):
                if "start_timestamp" in chapter:
                    chapter["start_seconds"] = self._timestamp_to_seconds(
                        chapter["start_timestamp"]
                    )

            return analysis

        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON response: %s", e)
            logger.debug("Response was: %s", response_text[:500])
            raise

    def _timestamp_to_seconds(self, timestamp_str):
        """Convert HH:MM:SS to seconds (with sub-second precision if present)."""
        parts = timestamp_str.split(":")
        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])  # Use float to preserve sub-second precision
            return hours * 3600 + minutes * 60 + seconds
        elif len(parts) == 2:
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        else:
            return float(parts[0])

    def _find_words_to_censor_directly(self, words):
        """
        Directly search transcript for words that need censoring.

        This bypasses GPT-4 and searches the actual transcript words against
        the configured NAMES_TO_REMOVE and WORDS_TO_CENSOR lists.

        Args:
            words: List of word dicts from Whisper with 'word', 'start', 'end'

        Returns:
            List of censor timestamp dicts
        """
        if not words:
            return []

        # Separate single-word and multi-word names
        single_words_to_find = set()
        multi_word_names = []

        # Add names
        for name in Config.NAMES_TO_REMOVE:
            name_lower = name.lower()
            if " " in name:
                multi_word_names.append(name_lower.split())
            else:
                single_words_to_find.add(name_lower)

        # Add explicit censor words
        for word in getattr(Config, "WORDS_TO_CENSOR", []):
            single_words_to_find.add(word.lower())

        if not single_words_to_find and not multi_word_names:
            return []

        logger.debug(
            "[DIRECT SEARCH] Looking for single words: %s",
            ", ".join(sorted(single_words_to_find)),
        )
        if multi_word_names:
            logger.debug(
                "[DIRECT SEARCH] Looking for multi-word names: %s",
                [" ".join(n) for n in multi_word_names],
            )

        found = []
        found_ranges = set()  # Track already-found time ranges to avoid duplicates

        # Search for multi-word names first (e.g., "Evan Perez")
        for i, word_data in enumerate(words):
            for name_parts in multi_word_names:
                if i + len(name_parts) <= len(words):
                    # Check if consecutive words match the full name
                    match = True
                    for j, name_part in enumerate(name_parts):
                        word_text = words[i + j].get("word", "").strip()
                        word_clean = word_text.lower().strip(".,!?;:\"'-()[]")
                        if word_clean != name_part:
                            match = False
                            break

                    if match:
                        start_time = words[i].get("start", 0)
                        end_time = words[i + len(name_parts) - 1].get(
                            "end", start_time + 0.5
                        )
                        full_name = " ".join(
                            [
                                words[i + j].get("word", "").strip()
                                for j in range(len(name_parts))
                            ]
                        )

                        # Add the full name span as one censor
                        found.append(
                            {
                                "timestamp": self._format_timestamp(start_time),
                                "seconds": start_time,
                                "start_seconds": start_time,
                                "end_seconds": end_time,
                                "reason": f"Name: {full_name}",
                                "context": full_name,
                                "source": "direct_search",
                            }
                        )
                        # Track this range so we don't duplicate individual words
                        for j in range(len(name_parts)):
                            found_ranges.add(i + j)

                        mins = int(start_time // 60)
                        secs = start_time % 60
                        logger.info(
                            "[FOUND] '%s' at %02d:%05.2f", full_name, mins, secs
                        )

        # Search for single words (skip if already part of a multi-word match)
        for i, word_data in enumerate(words):
            if i in found_ranges:
                continue  # Skip - already caught as part of multi-word name

            word_text = word_data.get("word", "").strip()
            word_clean = word_text.lower().strip(".,!?;:\"'-()[]")

            if word_clean in single_words_to_find:
                # Determine reason
                if word_clean in [n.lower() for n in Config.NAMES_TO_REMOVE]:
                    reason = f"Name: {word_text}"
                else:
                    reason = f"Word: {word_text}"

                found.append(
                    {
                        "timestamp": self._format_timestamp(word_data.get("start", 0)),
                        "seconds": word_data.get("start", 0),
                        "start_seconds": word_data.get("start", 0),
                        "end_seconds": word_data.get(
                            "end", word_data.get("start", 0) + 0.3
                        ),
                        "reason": reason,
                        "context": word_text,
                        "source": "direct_search",
                    }
                )
                mins = int(word_data.get("start", 0) // 60)
                secs = word_data.get("start", 0) % 60
                logger.info("[FOUND] '%s' at %02d:%05.2f", word_text, mins, secs)

        # Sort by timestamp
        found.sort(key=lambda x: x["seconds"])
        logger.info("[DIRECT SEARCH] Found %d item(s) to censor", len(found))
        return found

    def _merge_censor_timestamps(self, direct_timestamps, gpt_timestamps):
        """
        Merge direct search results with GPT-4 results, avoiding duplicates.

        Direct search results take priority since they have exact timestamps.

        Args:
            direct_timestamps: Results from direct transcript search
            gpt_timestamps: Validated results from GPT-4

        Returns:
            Merged list of censor timestamps
        """
        if not gpt_timestamps:
            return direct_timestamps

        if not direct_timestamps:
            return gpt_timestamps

        # Use direct timestamps as base
        merged = list(direct_timestamps)
        direct_times = {
            t.get("start_seconds", t.get("seconds", 0)) for t in direct_timestamps
        }

        # Add GPT-4 timestamps that don't overlap with direct ones (within 2 second window)
        for gpt_item in gpt_timestamps:
            gpt_time = gpt_item.get("seconds", 0)
            is_duplicate = any(abs(gpt_time - dt) < 2.0 for dt in direct_times)

            if not is_duplicate:
                merged.append(gpt_item)
                logger.debug(
                    "[GPT-4] Added: %s at %s",
                    gpt_item.get("reason"),
                    gpt_item.get("timestamp"),
                )

        return merged

    def _validate_censor_timestamps(self, censor_timestamps):
        """
        Validate censor timestamps by checking if the word actually appears in context.

        This catches GPT-4 hallucinations where it claims to find a word but the
        context doesn't actually contain it.

        Args:
            censor_timestamps: List of censor items from GPT-4

        Returns:
            Filtered list with only valid censor items
        """
        if not censor_timestamps:
            return []

        validated = []
        for censor in censor_timestamps:
            reason = censor.get("reason", "")
            context = censor.get("context", "")

            # Extract the target word from reason
            target_word = self._extract_target_word(reason, context)

            if not target_word:
                logger.debug(
                    "[SKIP] Could not determine target word from reason: %s", reason
                )
                continue

            # Check if target word actually appears in the context
            if target_word.lower() in context.lower():
                validated.append(censor)
                logger.debug(
                    "[VALID] Found '%s' in context: \"%s...\"",
                    target_word,
                    context[:50],
                )
            else:
                logger.warning(
                    "[HALLUCINATION] '%s' NOT in context: \"%s...\" - SKIPPING",
                    target_word,
                    context[:50],
                )

        if len(validated) < len(censor_timestamps):
            removed = len(censor_timestamps) - len(validated)
            logger.warning("Removed %d hallucinated censor item(s)", removed)

        return validated

    def _refine_censor_timestamps(self, censor_timestamps, words):
        """
        Refine censor timestamps by looking up actual word-level timing from Whisper.

        GPT-4 returns segment-level timestamps, but the actual word to censor
        may appear later in the segment. This method finds the exact word
        boundaries using Whisper's word-level timestamps.

        Args:
            censor_timestamps: List of censor items from GPT-4 with 'seconds', 'reason', 'context'
            words: List of words with timestamps from Whisper transcription

        Returns:
            List of censor items with accurate 'start_seconds' and 'end_seconds'
        """
        if not words:
            logger.warning(
                "No word-level timestamps available, using segment timestamps"
            )
            return censor_timestamps

        refined = []
        for censor in censor_timestamps:
            segment_time = censor.get("seconds", 0)
            reason = censor.get("reason", "")
            context = censor.get("context", "")

            # Extract the word to find from reason (e.g., "Name: Joey" -> "Joey")
            target_word = self._extract_target_word(reason, context)

            if target_word:
                # Find the word in the transcript near the segment timestamp
                word_match = self._find_word_near_timestamp(
                    words, target_word, segment_time, search_window=10.0
                )

                if word_match:
                    # Use exact word boundaries from Whisper
                    refined_censor = {
                        **censor,
                        "start_seconds": word_match["start"],
                        "end_seconds": word_match["end"],
                        "matched_word": word_match["word"],
                        "original_segment_time": segment_time,
                    }
                    logger.debug(
                        "[REFINED] '%s' at segment %.1fs -> word boundaries %.2fs - %.2fs",
                        target_word,
                        segment_time,
                        word_match["start"],
                        word_match["end"],
                    )
                    refined.append(refined_censor)
                else:
                    # Fallback: use segment timestamp with estimated duration
                    logger.warning(
                        "Could not find '%s' near %.1fs, using segment timestamp",
                        target_word,
                        segment_time,
                    )
                    refined_censor = {
                        **censor,
                        "start_seconds": segment_time,
                        "end_seconds": segment_time + 0.5,  # Fallback duration
                    }
                    refined.append(refined_censor)
            else:
                # No target word extracted, use segment timestamp
                refined_censor = {
                    **censor,
                    "start_seconds": segment_time,
                    "end_seconds": segment_time + 0.5,
                }
                refined.append(refined_censor)

        return refined

    def _extract_target_word(self, reason, context):
        """
        Extract the target word to censor from the reason/context.

        Args:
            reason: Reason string like "Name: Joey" or "Slur: [word]"
            context: Context quote that may contain the word

        Returns:
            The word to search for, or None if not determinable
        """
        # Try to extract from reason format "Name: Joey" or "Slur: word"
        if ":" in reason:
            parts = reason.split(":", 1)
            if len(parts) == 2:
                word = parts[1].strip()
                # Remove any brackets or quotes
                word = word.strip("[]\"'")
                if word:
                    return word

        # Try to find a name from config in the reason
        for name in Config.NAMES_TO_REMOVE:
            if name.lower() in reason.lower():
                return name

        # Try to extract from context if provided
        if context:
            for name in Config.NAMES_TO_REMOVE:
                if name.lower() in context.lower():
                    return name

        return None

    def _find_word_near_timestamp(
        self, words, target_word, timestamp, search_window=10.0
    ):
        """
        Find a word in the word list near a given timestamp.

        Args:
            words: List of word dicts with 'word', 'start', 'end'
            target_word: Word to search for (case-insensitive)
            timestamp: Approximate timestamp in seconds
            search_window: How many seconds before/after to search

        Returns:
            Word dict with 'word', 'start', 'end' or None if not found
        """
        target_lower = target_word.lower().strip()

        # Find words within the search window
        candidates = []
        for word_data in words:
            word_start = word_data.get("start", 0)
            word_text = word_data.get("word", "").strip()

            # Check if word is within search window of timestamp
            if timestamp - search_window <= word_start <= timestamp + search_window:
                # Check if word matches (handle punctuation and partial matches)
                word_clean = word_text.lower().strip(".,!?;:\"'-")

                if word_clean == target_lower or word_clean.startswith(target_lower):
                    candidates.append(
                        {
                            "word": word_text,
                            "start": word_data.get("start", 0),
                            "end": word_data.get(
                                "end", word_data.get("start", 0) + 0.3
                            ),
                            "distance": abs(word_start - timestamp),
                        }
                    )

        if not candidates:
            return None

        # Return the closest match to the timestamp
        candidates.sort(key=lambda x: x["distance"])
        best = candidates[0]
        return {"word": best["word"], "start": best["start"], "end": best["end"]}


if __name__ == "__main__":
    # Test content editor
    import sys

    if len(sys.argv) < 2:
        print("Usage: python content_editor.py <transcript.json>")
        sys.exit(1)

    transcript_file = sys.argv[1]

    with open(transcript_file, "r", encoding="utf-8") as f:
        transcript_data = json.load(f)

    editor = ContentEditor()
    analysis = editor.analyze_content(transcript_data)

    print("\n" + "=" * 60)
    print("CONTENT ANALYSIS RESULTS")
    print("=" * 60)

    print(f"\n📝 EPISODE SUMMARY:\n{analysis['episode_summary']}\n")

    print(f"🚫 ITEMS TO CENSOR: {len(analysis['censor_timestamps'])}")
    for item in analysis["censor_timestamps"][:5]:  # Show first 5
        print(f"  - {item['timestamp']}: {item['reason']}")

    print(f"\n✂️ BEST CLIPS: {len(analysis['best_clips'])}")
    for clip in analysis["best_clips"]:
        print(f"  - {clip['start']} to {clip['end']}: {clip['description']}")

    print("\n📱 SOCIAL CAPTIONS:")
    print(f"  Twitter: {analysis['social_captions']['twitter'][:100]}...")
