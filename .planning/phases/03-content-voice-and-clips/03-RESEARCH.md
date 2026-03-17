# Phase 3: Content Voice and Clips - Research

**Researched:** 2026-03-17
**Domain:** LLM prompt engineering, few-shot prompting, audio energy analysis
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None — user explicitly deferred all implementation decisions to Claude.

### Claude's Discretion
All of the following are open for Claude to decide:

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

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VOICE-01 | All AI-generated text (titles, descriptions, social posts, blog) uses edgy comedy tone via few-shot prompts | Few-shot prompt engineering pattern for `_build_analysis_prompt()` and `_build_prompt()` in blog_generator; system-role personas; per-platform tone variants |
| VOICE-02 | Clip detection scores moments by audio energy, laughter patterns, and conversation dynamics (not just topic changes) | pydub-based RMS energy analysis on audio segments; combining audio scores with GPT-4 clip selection; new `AudioClipScorer` class pattern |
| VOICE-03 | Generated clips include hook-style captions matching show's humor | Hook caption prompt engineering inside `_build_analysis_prompt()`; `hook_caption` field already exists in the JSON schema — this is a prompt quality upgrade |
</phase_requirements>

---

## Summary

Phase 3 has two distinct sub-problems: (1) prompt engineering to inject the show's edgy comedy voice into all LLM-generated text, and (2) augmenting clip selection with audio energy analysis so the pipeline favors funny/high-energy moments rather than arbitrary topic transitions.

The prompt engineering work is entirely in `content_editor._build_analysis_prompt()` and `blog_generator._build_prompt()`. The current prompts are generic; adding a system-role persona, explicit tone description, and a few-shot example bank will shift output from "corporate podcast summary" to "written by the hosts." This is well-understood prompt engineering with no new dependencies.

The audio energy work needs to run on the already-downloaded audio file before or during content analysis (step 3 in the pipeline). pydub is already in requirements and is sufficient for RMS energy windowing; librosa would add more features but also adds a large dependency. The recommendation is to implement a lightweight `AudioClipScorer` class using pydub that produces energy-ranked candidate windows, then pass those candidates to GPT-4 as prioritized timestamps rather than replacing GPT-4 clip selection entirely.

**Primary recommendation:** Modify both LLM prompts with a persona + few-shot block; add pydub-based energy scoring as a pre-filter that ranks transcript segments and biases GPT-4's clip selection, not replaces it.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| openai | >=1.0.0 | GPT-4o API calls | Already in requirements; both content_editor and blog_generator use it |
| pydub | 0.25.1 | Audio RMS energy analysis | Already in requirements; no new install needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| librosa | ~0.10.x | Spectral/onset detection | If pydub RMS proves insufficient; NOT recommended — large dep, torch version conflict risk |
| numpy | (pydub dependency) | Signal math | Already transitive dep via torch/whisper |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pydub RMS | librosa | librosa gives spectral flux and onset detection but requires a separate install; may conflict with torch==2.1.0 pin from WhisperX |
| Prompt-only few-shot | Fine-tuning | Fine-tuning would be more consistent but requires labeled data and costs significantly more; out of scope |
| Per-call few-shot examples | Persistent system message | OpenAI chat completions support a `system` role message — using it as the persona anchor is cleaner than embedding everything in the user prompt |

**No new installations needed for this phase.** pydub is sufficient for audio energy scoring.

---

## Architecture Patterns

### Recommended Project Structure
No new files needed. All work is modifications to existing files:
```
content_editor.py     # _build_analysis_prompt() — persona + few-shot + hook guidance
blog_generator.py     # _build_prompt() — persona + few-shot blog voice
audio_clip_scorer.py  # NEW: AudioClipScorer using pydub RMS windowing
config.py             # Add CLIP_AUDIO_WEIGHT env var for audio score blend weight
tests/
├── test_content_editor.py   # New test class for voice prompt content
├── test_blog_generator.py   # New test class for blog voice prompt content
└── test_audio_clip_scorer.py  # NEW test file
```

### Pattern 1: System Role Persona + Few-Shot in `_build_analysis_prompt()`
**What:** Replace the current flat user-role prompt with a two-message structure: a `system` message defining the personality, and a `user` message with the task and few-shot examples.
**When to use:** Every GPT-4o call that produces user-facing text (episode title, summary, social captions, show notes).
**Example:**
```python
# In ContentEditor.analyze_content()
messages = [
    {
        "role": "system",
        "content": (
            "You write for the Fake Problems Podcast — an irreverent comedy show "
            "hosted by two guys who talk about dark, weird, and absurd topics with "
            "deadpan confidence. Your output sounds like it was written by the hosts "
            "themselves: casual, a little dark, never corporate. No exclamation points "
            "for hype. No 'join us as we...' Never use filler phrases like 'delve into' "
            "or 'unravel'. Write like you'd say it out loud to a friend who gets the joke."
        ),
    },
    {"role": "user", "content": prompt},
]
response = self.client.chat.completions.create(
    model="gpt-4o",
    max_tokens=6000,
    temperature=0.7,   # Increase from 0.3 — creativity matters here
    messages=messages,
)
```
Note: Temperature should increase from 0.3 to ~0.7 for voice tasks. 0.3 was appropriate for the deterministic censorship tasks but suppresses creative voice.

### Pattern 2: Few-Shot Examples Embedded in the Prompt Body
**What:** Add a `## VOICE EXAMPLES` section inside `_build_analysis_prompt()` with 3-5 contrasting "bad vs. good" pairs.
**When to use:** For episode titles, social captions, and episode summaries — the most visible outputs.
**Example block to add to prompt:**
```
**VOICE EXAMPLES — match this tone:**

Episode titles:
BAD (generic): "Exploring the Science of Lobster Immortality"
GOOD (show voice): "Lobsters Are Basically Immortal and Honestly Good for Them"

BAD: "A Deep Dive into Rube Goldberg Machines"
GOOD: "Rube Goldberg Invented a Machine Just to Avoid Responsibility"

Twitter captions:
BAD: "Great episode today discussing some fascinating topics!"
GOOD: "we spent 20 minutes on whether horses are lying to us and I stand by every second of it"

Instagram captions:
BAD: "Listen to this week's episode for an eye-opening discussion 🎙️"
GOOD: "turns out immortality is real, it just only applies to lobsters. link in bio 🦞"

Hook captions (for clips):
BAD: "Here's an interesting clip from our latest episode"
GOOD: "wait so lobsters just... don't die??"
BAD: "The guys discuss an unusual topic"
GOOD: "someone finally said it out loud"
```

### Pattern 3: pydub RMS Energy Windowing for Clip Scoring
**What:** Slide a window across the audio file computing RMS energy per window, normalize to 0-1 scale, then map high-energy windows back to transcript segments. Pass the top-N windows as "high energy moments" in the GPT-4 prompt.
**When to use:** Between transcription (step 2) and content analysis (step 3). The audio file path is available at analysis time.
**Example:**
```python
# audio_clip_scorer.py
from pydub import AudioSegment
import statistics

class AudioClipScorer:
    """Score transcript segments by audio energy using pydub RMS windowing."""

    def __init__(self, window_ms=500, hop_ms=250):
        self.window_ms = window_ms
        self.hop_ms = hop_ms

    def score_segments(self, audio_path: str, segments: list[dict]) -> list[dict]:
        """
        Add an 'audio_energy_score' (0.0-1.0) to each segment dict.

        Args:
            audio_path: Path to the processed audio file (.mp3 or .wav)
            segments: Transcript segments with 'start', 'end', 'text'

        Returns:
            Segments list with 'audio_energy_score' added to each item
        """
        audio = AudioSegment.from_file(audio_path)
        total_ms = len(audio)

        # Build energy map: window_start_ms -> rms
        energy_map = {}
        pos = 0
        while pos + self.window_ms <= total_ms:
            chunk = audio[pos:pos + self.window_ms]
            energy_map[pos] = chunk.rms
            pos += self.hop_ms

        if not energy_map:
            return segments

        max_rms = max(energy_map.values()) or 1
        min_rms = min(energy_map.values())
        rms_range = max_rms - min_rms or 1

        # Score each segment: mean normalized energy across its span
        scored = []
        for seg in segments:
            start_ms = int(seg["start"] * 1000)
            end_ms = int(seg["end"] * 1000)
            # Collect all window positions that fall within this segment
            window_energies = [
                v for k, v in energy_map.items()
                if start_ms <= k < end_ms
            ]
            if window_energies:
                mean_energy = statistics.mean(window_energies)
                score = (mean_energy - min_rms) / rms_range
            else:
                score = 0.0
            scored.append({**seg, "audio_energy_score": round(score, 3)})

        return scored
```

### Pattern 4: Injecting Audio Scores into the GPT-4 Prompt
**What:** After scoring segments, identify the top-N by energy, format them as a hint section in the prompt, so GPT-4 considers energy-rich moments when selecting clips.
**When to use:** As an additive section in `_build_analysis_prompt()`, similar to the existing `topic_section`.
**Example addition to `_build_analysis_prompt()`:**
```python
# After scoring, pass top 10 high-energy segments
energy_section = ""
if energy_candidates:
    lines = []
    for seg in energy_candidates[:10]:
        ts = self._format_timestamp(seg["start"])
        score = seg.get("audio_energy_score", 0)
        text_preview = seg["text"][:80]
        lines.append(f"  - [{ts}] energy={score:.2f}: {text_preview}")
    energy_section = (
        "\n**HIGH ENERGY MOMENTS (audio analysis — prioritize these for clips):**\n"
        + "\n".join(lines)
        + "\n"
    )
```

### Anti-Patterns to Avoid
- **Replacing GPT-4 clip selection with pure audio scoring:** Audio energy alone will select shouting, crosstalk, or ad breaks — not necessarily funny. Use energy as a bias/hint to GPT-4, not as the sole selector.
- **Setting temperature=0.3 for voice tasks:** Low temperature produces safe, predictable text. The comedy voice requires some variance. Use 0.7 for voice outputs.
- **Embedding the persona inside the user message:** Using a proper `system` role message is cleaner, costs fewer tokens per call, and is the correct pattern for persistent personality instructions.
- **Making `AudioClipScorer` dependent on the audio file existing:** The scorer must gracefully degrade (return segments unchanged) if the audio file is not yet available or if scoring fails — clips must still be selected.
- **Platform-uniform voice:** YouTube descriptions face demonetization risk from extreme content. Instagram and TikTok reward punchy irreverence. Twitter/X rewards dry wit. Segment the voice guidance by platform in the prompt.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RMS energy per time window | Custom FFT/signal processing | `pydub.AudioSegment.rms` on sliced chunks | pydub already slices and exposes `.rms` (root mean square amplitude); exact same result with zero math code |
| JSON schema validation for LLM output | Custom response validator | Existing `_parse_llm_response()` + `setdefault()` guards | Already handles malformed JSON, missing fields, markdown code fences |
| Platform character limits | Custom truncation logic | Enforce in prompt instructions | GPT-4o reliably respects "under 280 chars" constraints in system prompts |

**Key insight:** The voice problem is 95% prompt engineering and 5% code. The risk is over-engineering a "voice module" when the real fix is rewriting ~30 lines of prompt text.

---

## Common Pitfalls

### Pitfall 1: Prompt Tone Drift at High Token Counts
**What goes wrong:** GPT-4o drifts back toward generic/safe language in long responses. The comedy voice degrades by the time it writes the blog section or later captions.
**Why it happens:** The system message persona weakens as the context fills. Instructions near the bottom of a long prompt carry less weight.
**How to avoid:** Repeat the tone reminder immediately before each output section. Example: `"## SOCIAL CAPTIONS (write these in the same irreverent voice — no corporate language):"`.
**Warning signs:** Episode summary sounds edgy but YouTube description sounds like a press release.

### Pitfall 2: Audio Scoring on Compressed MP3
**What goes wrong:** RMS energy scores are distorted when run on heavily compressed MP3 files — the dynamic range has been flattened by the codec.
**Why it happens:** MP3 compression applies psychoacoustic masking that normalizes peaks. RMS on a 128kbps MP3 gives less variance than on the original WAV.
**How to avoid:** Run the scorer on the normalized (but pre-final-compress) WAV/AIFF if available, or on the pydub-loaded AudioSegment before export. The audio at step 4.5 (normalize) should be the input.
**Warning signs:** All energy scores cluster between 0.4-0.6 with little variation.

### Pitfall 3: pydub Loads Entire File into RAM
**What goes wrong:** `AudioSegment.from_file()` on a 90-minute episode loads ~500MB-1GB into memory.
**Why it happens:** pydub reads the entire file eagerly.
**How to avoid:** The scorer only needs a representative sample for scoring. Either (a) load in chunks using pydub's `AudioSegment.from_file()` with `start_second`/`duration` (supported for some formats), or (b) accept the RAM cost since this machine has it and the audio is already in memory during processing. For a podcast pipeline this is acceptable.
**Warning signs:** MemoryError on long episodes, or scoring taking >30 seconds.

### Pitfall 4: Energy Score Overrides Genuinely Funny Quiet Moments
**What goes wrong:** A deadpan punchline delivered quietly (which is a common comedy technique) scores near zero on energy and gets excluded.
**Why it happens:** RMS energy measures loudness, not comedic value.
**How to avoid:** Use energy as a booster, not a gate. In the prompt, frame the energy list as "these had unusually high energy — they may be funny" but explicitly tell GPT-4 to also find quiet/deadpan moments that work as clips.
**Warning signs:** All selected clips are from arguments or moments where hosts are talking over each other — none are from slower, deadpan exchanges.

### Pitfall 5: `hook_caption` Already Exists in Schema but Prompts are Generic
**What goes wrong:** The `hook_caption` field already exists in the JSON schema and GPT-4 is already producing it — but the current prompt example is generic ("'Wait for it...' or 'This is too real'").
**Why it happens:** The prompt example is too safe. GPT-4 copies the example style.
**How to avoid:** Replace the example guidance with show-specific hook patterns: dry observations, questions that assume weird knowledge, cliffhangers using the actual episode content. VOICE-03 is largely a prompt update to the existing `hook_caption` instruction, not a structural change.

---

## Code Examples

Verified patterns from existing codebase:

### How GPT-4 is currently called (content_editor.py:50-57)
```python
response = self.client.chat.completions.create(
    model="gpt-4o",
    max_tokens=6000,
    temperature=0.3,
    messages=[{"role": "user", "content": prompt}],
)
```
To add a system message, change `messages` to:
```python
messages=[
    {"role": "system", "content": VOICE_PERSONA},
    {"role": "user", "content": prompt},
]
```

### How pydub computes RMS on a slice (already used in audio_processor.py)
```python
from pydub import AudioSegment
audio = AudioSegment.from_file("episode.wav")
chunk = audio[5000:5500]   # ms slice
energy = chunk.rms          # int, proportional to amplitude
```

### Existing topic_section injection pattern (content_editor.py:126-137)
The energy section follows the same pattern: build a multi-line string, prepend it to the prompt body. This is the established convention for optional context injection.

### How `analyze_content()` receives audio_path context
Currently `analyze_content(transcript_data, topic_context=None)`. The audio scorer needs an audio file path. Best approach: add `audio_path=None` as a third optional parameter, matching the optional pattern of `topic_context`.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Generic "analyze transcript" user prompt | System role persona + few-shot examples | GPT-4o (2024) | Significant improvement in voice consistency; system role persists across long outputs |
| Topic-boundary clip detection | Audio energy + content scoring hybrid | Industry shift 2023-2024 | Clips that match engagement patterns, not just semantic coherence |
| Single voice for all platforms | Per-platform tone variants | TikTok/Shorts rise 2022-2024 | Platform algorithms reward native-sounding content |

**Note on temperature:** The existing code uses `temperature=0.3`. For the censorship and timestamp detection portions of the prompt, this is correct (low variance is good). But voice/creative output at 0.3 produces overly safe text. Phase 3 should either split the calls (censorship at 0.3, voice at 0.7) or accept 0.7 for the combined call and compensate with stricter censor instructions.

Recommendation: Keep the single call but raise temperature to 0.7 — the censor detection relies on the direct word search (`_find_words_to_censor_directly`) anyway, so GPT-4's censor output is already a backup path and is validated. This was established in Phase 2's accumulated context.

---

## Open Questions

1. **Audio file availability at analysis time**
   - What we know: `content_editor.analyze_content()` is called at step 3; the audio file has been downloaded (step 1) but may not yet be processed (censor/normalize happens steps 4-4.5)
   - What's unclear: Whether the original download or the processed file is more useful for scoring. Normalized audio at -16 LUFS would give more consistent energy scores.
   - Recommendation: Accept `audio_path` pointing to the raw downloaded file and document that scores are relative-not-absolute. The normalization pass has not run yet at step 3, but relative comparison across segments still works.

2. **Blog voice: full irreverence or slightly moderated?**
   - What we know: Blog posts may be indexed by search engines; extremely edgy titles could affect discoverability
   - What's unclear: The show's actual SEO strategy (no hosting decision made yet, v2 scope)
   - Recommendation: Apply the full comedy voice to the blog. The show is edgy comedy — sanitizing it defeats the purpose. If SEO becomes a concern, it belongs in a later phase.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.4.3 |
| Config file | `pyproject.toml` (pytest section present) |
| Quick run command | `pytest tests/test_content_editor.py tests/test_blog_generator.py tests/test_audio_clip_scorer.py -x -q` |
| Full suite command | `pytest --cov` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VOICE-01 | Prompt contains persona/system message | unit | `pytest tests/test_content_editor.py::TestVoicePrompt -x` | ❌ Wave 0 |
| VOICE-01 | Prompt contains few-shot examples | unit | `pytest tests/test_content_editor.py::TestVoicePrompt -x` | ❌ Wave 0 |
| VOICE-01 | Blog prompt contains personality instructions | unit | `pytest tests/test_blog_generator.py::TestBlogVoicePrompt -x` | ❌ Wave 0 |
| VOICE-01 | `analyze_content()` passes system message to API | unit | `pytest tests/test_content_editor.py::TestVoicePrompt -x` | ❌ Wave 0 |
| VOICE-02 | `AudioClipScorer.score_segments()` returns segments with `audio_energy_score` | unit | `pytest tests/test_audio_clip_scorer.py -x` | ❌ Wave 0 |
| VOICE-02 | Higher-energy segment gets higher score | unit | `pytest tests/test_audio_clip_scorer.py::TestEnergyScoring -x` | ❌ Wave 0 |
| VOICE-02 | Scorer degrades gracefully on missing audio file | unit | `pytest tests/test_audio_clip_scorer.py::TestEnergyScoring -x` | ❌ Wave 0 |
| VOICE-02 | Energy hints appear in analysis prompt when scores provided | unit | `pytest tests/test_content_editor.py::TestEnergyPromptInjection -x` | ❌ Wave 0 |
| VOICE-03 | Prompt contains hook caption style guidance | unit | `pytest tests/test_content_editor.py::TestVoicePrompt -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_content_editor.py tests/test_blog_generator.py tests/test_audio_clip_scorer.py -x -q`
- **Per wave merge:** `pytest --cov`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_audio_clip_scorer.py` — covers VOICE-02 audio energy logic; new file for new module
- [ ] `tests/test_content_editor.py::TestVoicePrompt` — new test class in existing file; covers VOICE-01 and VOICE-03 prompt content assertions
- [ ] `tests/test_blog_generator.py::TestBlogVoicePrompt` — new test class in existing file; covers VOICE-01 blog prompt assertions

---

## Sources

### Primary (HIGH confidence)
- Codebase direct read: `content_editor.py`, `blog_generator.py`, `config.py`, `requirements.txt` — full implementation read, no inference
- Codebase direct read: `tests/test_content_editor.py`, `tests/test_blog_generator.py` — existing test patterns confirmed
- OpenAI chat completions API: `system` role message is documented in the API spec and supported by `openai>=1.0.0` — confirmed by reading existing `client.chat.completions.create()` calls in codebase
- pydub `AudioSegment.rms` attribute: documented in pydub 0.25.1 — already used in audio processing pipeline

### Secondary (MEDIUM confidence)
- Temperature 0.7 for creative voice tasks: standard LLM practice documented across OpenAI cookbook examples; contrasted with 0.3 (deterministic/factual tasks) already in the codebase
- System role persona pattern for persistent tone: documented in OpenAI best practices guides; widely validated in prompt engineering literature

### Tertiary (LOW confidence)
- MP3 dynamic range compression affecting RMS scores: plausible based on codec theory, but not benchmarked against this specific pipeline's audio files

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; pydub and openai already installed and in use
- Architecture: HIGH — patterns derived directly from reading existing source code
- Pitfalls: MEDIUM — temperature/MP3 pitfalls are general LLM/audio knowledge; energy-vs-quiet-comedy pitfall is show-specific reasoning
- Prompt examples: MEDIUM — examples are derived from CONTEXT.md episode 29 specifics and general comedy podcast conventions, not validated against actual episode output

**Research date:** 2026-03-17
**Valid until:** 2026-04-17 (30 days — stable tech, no fast-moving dependencies)
