# Phase 3: Content Voice and Clips - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Make all AI-generated text sound like the show's edgy comedy voice and upgrade clip detection to find actually funny/viral moments instead of topic transitions. Scope: modify GPT-4 prompts in `content_editor.py` and `blog_generator.py` with few-shot examples, add audio-energy-based clip scoring. No new platforms or distribution changes.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
User explicitly deferred all implementation decisions to Claude. The following areas are open for Claude to decide based on the show's existing content and comedy podcast best practices:

**Comedy Voice:**
- Few-shot prompt examples for edgy comedy tone (titles, descriptions, social posts, blog)
- Which content types get full edgy treatment vs. slightly toned down (e.g., YouTube descriptions may need to be less edgy for algorithm friendliness)
- System prompt personality definition for the GPT-4 calls
- Whether to use a single voice prompt template or per-platform variants
- How to extract voice examples from existing episode titles/descriptions for the few-shot bank

**Clip Detection:**
- Audio features to score (RMS energy, onset density, spectral flux, speech rate)
- How to combine audio scores with GPT-4 content analysis (weighted blend vs. audio-first filter)
- Minimum clip quality threshold before falling back to topic-based selection
- Whether to use librosa or simpler pydub-based energy analysis
- How many candidate moments to score before selecting top 3

**Hook Captions:**
- Caption style for clips (question hooks, provocative statements, cliffhangers)
- Whether captions should reference the clip content or be curiosity-gap teasers
- Platform-specific caption variants (TikTok vs. YouTube Shorts vs. Instagram)

**General approach:**
- The show is "Fake Problems Podcast" — edgy comedy, dark humor, irreverent
- Two hosts, casual banter style, not afraid to go dark or weird
- AI content should sound like it was written by the hosts, not a marketing team
- Prioritize authenticity over polish

</decisions>

<specifics>
## Specific Ideas

- Show tone described as "edgy comedy" and "dark humor, irreverent, push boundaries"
- Episode 29 topics included: lobster immortality, Rube Goldberg suicide machines, "hung like a horse" myth — this gives a sense of the humor range
- Current GPT-4 prompt produces generic output like "Join us as we unravel the myth of lobster immortality" — too corporate
- Better would be something like "Lobsters might outlive us all and honestly? Good for them."
- Clip titles from ep29: "Lobsters: The Immortal Sea Creatures?", "Rube Goldberg's Darkest Invention", "The Truth About 'Hung Like a Horse'" — these are decent but could be punchier

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `content_editor.py:analyze_content()` — Main analysis method that calls GPT-4. Returns `best_clips`, `social_captions`, `episode_summary`. This is where the voice prompt lives.
- `content_editor.py:_build_analysis_prompt()` — Builds the GPT-4 prompt. This is THE method to modify for voice.
- `blog_generator.py:generate_blog_post()` — Separate GPT-4 call for blog content. Has its own prompt.
- `content_editor.py:_find_words_to_censor_directly()` — Direct word search (more reliable than GPT-4 for censorship). Unrelated to voice work.
- `Config.CLIP_MIN_DURATION`, `Config.CLIP_MAX_DURATION` — Clip length constraints already configurable.

### Established Patterns
- GPT-4 called via `self.client.chat.completions.create()` with model `gpt-4o`
- Response parsed by `_parse_llm_response()` which extracts JSON from markdown code blocks
- Social captions already split by platform: youtube, instagram, twitter, tiktok
- Clip data includes: start/end times, description, why_interesting, suggested_title, hook_caption, clip_hashtags

### Integration Points
- `main.py:process_episode()` calls `content_editor.analyze_content()` at step 3
- Clip selection uses GPT-4 `best_clips` output — audio scoring would need to run between transcription (step 2) and analysis (step 3), or as a post-filter
- Blog generation is a separate step (8.5) that receives the transcript and analysis results

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-content-voice-and-clips*
*Context gathered: 2026-03-17*
