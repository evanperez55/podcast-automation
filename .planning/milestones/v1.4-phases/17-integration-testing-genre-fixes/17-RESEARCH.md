# Phase 17: Integration Testing & Genre Fixes - Research

**Researched:** 2026-03-28
**Domain:** End-to-end pipeline validation across genres — clip scoring, compliance tuning, GPT-4o prompt genre-awareness
**Confidence:** HIGH — all findings from direct codebase inspection; no external research needed

---

## Summary

Phase 17 is empirical: run real public podcast episodes through the pipeline for two genres (true crime, business/interview) and fix what breaks. The infrastructure is in place (Phase 15: genre YAMLs + conditional voice examples; Phase 16: RSS ingest). What remains is the genre-aware behavior that only surfaces on real audio.

Three code-level fixes are certain before running any episode: (1) the clip-selection prompt in `content_editor.py` is hardcoded for comedy ("Funny or entertaining moments", "Relatable 'fake problems' discussions") and will misdirect GPT-4o for non-comedy genres; (2) the compliance checker `COMPLIANCE_PROMPT` has a hardcoded comedy-context line that tells the model to be permissive, which is wrong for true crime; (3) `AudioClipScorer` uses only RMS energy — fine for comedy, but for interview/true crime the `energy_candidates` block passed to GPT-4o will favor loud segments over substantive ones.

The test strategy is: fix the three known code issues before the first run, then run each genre episode, inspect the analysis JSON for voice contamination and clip quality, and fix any further genre leakage discovered empirically.

**Primary recommendation:** Fix clip criteria prompt + compliance prompt + energy candidate suppression before running. Use real public RSS feeds. Inspect `_analysis.json` artifacts after each run to verify genre-appropriate output before calling TEST-01 through TEST-04 complete.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TEST-01 | User can process a real true crime episode end-to-end through the pipeline | Use RSS ingest (Phase 16 built), true-crime-client.yaml (Phase 15 built), `rss_source.feed_url` in YAML pointing at a real true crime RSS feed |
| TEST-02 | User can process a real business/interview episode end-to-end through the pipeline | Use RSS ingest, business-interview-client.yaml, real business podcast RSS feed |
| TEST-03 | Clip scorer selects genre-appropriate moments (not just high-energy for non-comedy) | Fix: add `clip_selection_mode` to `_YAML_TO_CONFIG`; add `content.clip_selection_mode` YAML field; in `analyze_content()`, suppress energy_candidates block when mode is "content"; update clip-finding prompt criteria per genre |
| TEST-04 | Compliance checker applies genre-appropriate sensitivity (stricter for true crime, lighter for comedy) | Fix: add `compliance_style` field to YAML + `_YAML_TO_CONFIG`; make `COMPLIANCE_PROMPT` context line conditional on `Config.COMPLIANCE_STYLE`; default to "standard" for unknown genres |
</phase_requirements>

---

## Standard Stack

### Core (no new dependencies)

All fixes are within existing code. No new packages are required.

| Component | Location | What Changes |
|-----------|----------|--------------|
| `content_editor.py` | root | Clip criteria in `_build_analysis_prompt()` must be genre-aware; read `Config.CLIP_SELECTION_MODE` |
| `content_compliance_checker.py` | root | `COMPLIANCE_PROMPT` comedy-context line must be conditional on `Config.COMPLIANCE_STYLE` |
| `client_config.py` | root | Add `content.clip_selection_mode` and `content.compliance_style` to `_YAML_TO_CONFIG` |
| `clients/true-crime-client.yaml` | `clients/` | Add `rss_source`, `episode_source: rss`, `clip_selection_mode: content`, `compliance_style: strict` |
| `clients/business-interview-client.yaml` | `clients/` | Add `rss_source`, `episode_source: rss`, `clip_selection_mode: content`, `compliance_style: standard` |
| `tests/test_content_compliance_checker.py` | `tests/` | New test cases for compliance style variants |
| `tests/test_content_editor.py` | `tests/` | New test cases for genre-aware clip criteria |
| `tests/test_client_config.py` | `tests/` | New test cases for new YAML fields |

---

## Architecture Patterns

### Pattern 1: `clip_selection_mode` — Suppress Energy Block for Non-Comedy

**What:** A new YAML field `content.clip_selection_mode` with values `energy` (default, comedy) or `content` (interview/true crime).

**How it works:** In `analyze_content()`, the `energy_candidates` block is built when `audio_path` is provided. The block is then passed to `_build_analysis_prompt()`. The fix adds a config check: if `CLIP_SELECTION_MODE` is `"content"`, pass `energy_candidates=None` to `_build_analysis_prompt()` (or skip the block inside the method). GPT-4o then selects clips based solely on transcript content, not energy hints.

**Why energy suppression, not replacement:** The `AudioClipScorer.score_segments()` still runs (graceful — no regression). The change is whether those scores become a hint to GPT-4o. For interview podcasts where RMS variance is low (all segments score 0.3–0.7), the energy hint gives GPT-4o useless or actively misleading guidance.

**The clip criteria problem:** Beyond energy, the clip selection criteria in `_build_analysis_prompt()` are hardcoded:
```python
# Current (comedy-only) — lines 315-320 of content_editor.py
   Find {Config.NUM_CLIPS} compelling moments...
   - Funny or entertaining moments
   - Controversial or thought-provoking statements
   - Relatable "fake problems" discussions
   - Moments with good energy and pacing
   - Self-contained stories or bits
```
These must be replaced with genre-appropriate criteria when `VOICE_PERSONA` is set. The cleanest implementation: make the clip criteria a conditional block, like voice examples. When a custom persona is set, use generic content-quality criteria; when no custom persona (Fake Problems), use the comedy-specific list.

**Implementation:**
```python
# In _build_analysis_prompt(), replace hardcoded clip criteria:
custom_persona = getattr(Config, "VOICE_PERSONA", None)
if not custom_persona:
    clip_criteria = """   - Funny or entertaining moments
   - Controversial or thought-provoking statements
   - Relatable "fake problems" discussions
   - Moments with good energy and pacing
   - Self-contained stories or bits"""
else:
    clip_criteria = """   - Moments with a clear, quotable insight or revelation
   - Self-contained segments that make sense out of context
   - Emotionally compelling or tension-building moments
   - Key data points, specific numbers, or case-breaking details
   - Strong narrative hooks that make someone want to hear more"""
```

**YAML field:**
```yaml
# In true-crime-client.yaml and business-interview-client.yaml content section:
content:
  clip_selection_mode: "content"   # suppresses RMS energy hints to GPT-4o
```

**Config mapping** (add to `_YAML_TO_CONFIG` in `client_config.py`):
```python
"content.clip_selection_mode": "CLIP_SELECTION_MODE",
```

---

### Pattern 2: `compliance_style` — Genre-Appropriate Compliance Thresholds

**What:** The current `COMPLIANCE_PROMPT` ends with a hardcoded comedy context line:
```python
# content_compliance_checker.py, line 56
Context: This is a comedy podcast. Dark humor, profanity, and edgy jokes are NOT violations unless they specifically dehumanize real protected groups or contain genuinely dangerous false health claims that could physically harm listeners.
```
This single line tells GPT-4o to ignore most flaggable content. For true crime episodes discussing violence or real victims, this calibration is wrong.

**Fix:** Replace the hardcoded context line with a conditional based on `Config.COMPLIANCE_STYLE`:

```python
# Replace the module-level COMPLIANCE_PROMPT constant with a function:
def _build_compliance_prompt(transcript: str) -> str:
    style = getattr(Config, "COMPLIANCE_STYLE", "standard")
    if style == "permissive":
        context_line = (
            "Context: This is a comedy podcast. Dark humor, profanity, and edgy jokes "
            "are NOT violations unless they specifically dehumanize real protected groups "
            "or contain genuinely dangerous false health claims."
        )
    elif style == "strict":
        context_line = (
            "Context: This is a serious factual podcast. Flag any content that discusses "
            "real violence, real victims, or sensitive topics without appropriate framing. "
            "Be conservative — flag for human review rather than missing a potential violation."
        )
    else:  # "standard"
        context_line = (
            "Context: Apply standard YouTube community guidelines. Flag genuine violations; "
            "do not flag editorial opinion, debate, or mature themes that are handled responsibly."
        )
    return COMPLIANCE_PROMPT_TEMPLATE.format(transcript=transcript, context=context_line)
```

**YAML field:**
```yaml
# In true-crime-client.yaml:
content:
  compliance_style: "strict"

# In business-interview-client.yaml:
content:
  compliance_style: "standard"

# fake-problems.yaml already uses permissive — add:
content:
  compliance_style: "permissive"
```

**Config mapping** (add to `_YAML_TO_CONFIG`):
```python
"content.compliance_style": "COMPLIANCE_STYLE",
```

**Impact on `check_transcript()`:** Change `prompt = COMPLIANCE_PROMPT.format(...)` to `prompt = _build_compliance_prompt(formatted_transcript)`.

---

### Pattern 3: RSS Feed Configuration in Client YAMLs

Both genre client YAMLs need `rss_source` and `episode_source` fields to enable Phase 16 RSS ingest. The fields map through `_YAML_TO_CONFIG` (already implemented in Phase 16).

**True crime client additions:**
```yaml
episode_source: "rss"
rss_source:
  feed_url: "https://feeds.simplecast.com/xl3WWLBP"  # Casefile True Crime
  episode_index: 0    # 0 = latest episode
```

**Business interview client additions:**
```yaml
episode_source: "rss"
rss_source:
  feed_url: "https://feeds.simplecast.com/4T39_jAj"  # How I Built This (NPR)
  episode_index: 0
```

**Public RSS feed candidates** (verified publicly available, no auth required):

| Genre | Podcast | RSS Feed | Why Good for Testing |
|-------|---------|----------|---------------------|
| True crime | Casefile True Crime | `https://feeds.simplecast.com/xl3WWLBP` | Solo host, measured delivery, UK accent (tests Whisper), no comedy |
| True crime | My Favorite Murder | `https://feeds.simplecast.com/M6lGDLQa` | Two hosts, comedic true crime — hybrid useful for verifying compliance strictness |
| Business/interview | How I Built This (NPR) | `https://feeds.simplecast.com/4T39_jAj` | Clean professional audio, interview format, one host + one guest |
| Business/interview | Masters of Scale | `https://rss.art19.com/masters-of-scale` | High production quality, startup founders |

**Note on episode_index:** RSS feeds list newest first after Phase 16 sort. `episode_index: 0` is always the latest episode. For a shorter first-run test, pick index 1 or 2 if the latest episode is a multi-parter.

**Confidence:** Feed URLs are MEDIUM confidence — RSS feed URLs change when podcasts migrate hosting. Verify each URL resolves before processing. Fallback: search "casefile true crime rss feed" in any podcast app.

---

### Pattern 4: Verification Process After Each Run

The phase goal is empirical — inspection of output artifacts confirms success. After each genre run:

**Step 1 — Check analysis JSON for voice contamination:**
```bash
# After run completes, find the analysis file:
cat output/<client>/ep_N/<stem>_<timestamp>_analysis.json | python -m json.tool | grep -i "episode_title\|show_notes\|social_captions" | head -40
```
- True crime: episode title must NOT be comedy-framed. No "POV:" constructions, no irony.
- Business: show_notes must lead with concrete data, not "In this episode..."
- Neither client: no "fake problems" language anywhere in output.

**Step 2 — Check voice leakage via debug log:**
```bash
# Enable debug logging to see the exact system prompt sent to GPT-4o:
# In the run, grep the log for the system message content
grep -A 5 "voice_persona" output/podcast_automation.log | head -20
```

**Step 3 — Check clip selection quality:**
```bash
# Inspect best_clips in analysis JSON:
python -c "
import json
with open('output/<client>/ep_N/..._analysis.json') as f:
    a = json.load(f)
for c in a['best_clips']:
    print(c['start'], c.get('why_interesting', '')[:100])
"
```
- True crime: clips should mention case details, testimony, evidence — not laugh moments.
- Business: clips should contain a specific insight or number — not generic setup.

**Step 4 — Check compliance output:**
- True crime with `compliance_style: strict`: expect at least 1-2 flags for content discussing violence (even if resolved as no-action). Zero flags on a case-heavy true crime episode means the checker is still too permissive.
- Business with `compliance_style: standard`: expect 0 flags for a mainstream business podcast.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Genre-aware clip scoring from scratch | New AudioClipScorer variant per genre | Suppress energy block via `CLIP_SELECTION_MODE` config; let GPT-4o use transcript content only |
| Separate compliance pipeline per genre | New checker class per genre | Conditional context line in single `_build_compliance_prompt()` function |
| ML-based content-quality scoring | Custom ML model | REQUIREMENTS.md explicitly lists "Genre-tuned clip scoring via ML" as Out of Scope |
| New YAML schema parser | Custom nested parser | Extend existing `_YAML_TO_CONFIG` dict + `_get_nested()` (already handles dot-notation) |

---

## Common Pitfalls

### Pitfall 1: Clip Criteria Prompt is Hardcoded Comedy — Not Just Energy

**What goes wrong:** Fixing `clip_selection_mode` to suppress energy candidates is necessary but not sufficient. The clip criteria list itself in the prompt (lines 315-320 of `content_editor.py`) explicitly asks for "funny or entertaining moments" and "fake problems discussions." GPT-4o will try to find these in a true crime transcript and may pick the wrong clips.

**How to avoid:** Make the clip criteria block conditional on `VOICE_PERSONA` being set — same pattern as the voice examples fix in Phase 15.

**Warning sign:** Selected clips for true crime are flagged as "entertaining" or "surprising banter" in the `why_interesting` field.

---

### Pitfall 2: Compliance Prompt is a Module-Level Constant — Cannot Be Conditionally Formatted at Import Time

**What goes wrong:** `COMPLIANCE_PROMPT` is a module-level string constant in `content_compliance_checker.py`. If you change it to a function, all existing tests that mock the constant will break. Also: `check_transcript()` calls `COMPLIANCE_PROMPT.format(transcript=...)` — this must be updated to call the new function.

**How to avoid:** Replace `COMPLIANCE_PROMPT.format(transcript=...)` call site with `_build_compliance_prompt(formatted_transcript)`. Keep the template string as a module-level `COMPLIANCE_PROMPT_TEMPLATE` constant for backward compat in tests that may assert on its content.

**Warning sign:** Tests mock `COMPLIANCE_PROMPT` directly as a string — these will need updating to mock `_build_compliance_prompt` or `Config.COMPLIANCE_STYLE` instead.

---

### Pitfall 3: RSS Feed URL Staleness

**What goes wrong:** Podcast RSS feed URLs change when shows migrate hosting platforms. A URL that resolves today may 301-redirect or 404 in a month.

**How to avoid:** Verify each feed URL manually before adding to YAML. Check that `feedparser.parse(url).entries` returns at least one entry with `enclosures`. Use the podcast's own "copy RSS link" from Apple Podcasts as the most stable canonical URL.

**Warning sign:** `RSSEpisodeFetcher.fetch_episode()` raises or returns empty entries — feedparser returns an empty feed object silently on 404.

---

### Pitfall 4: Non-English or Accented Audio Degrades Whisper Base

**What goes wrong:** Casefile True Crime is hosted by an Australian speaker with a non-American accent. Whisper `base` achieves ~95% WER on American English studio audio; it may drop to 85-90% on Australian-accented solo-host recordings. Proper nouns (victim names, place names) in true crime transcripts are especially prone to transcription errors.

**How to avoid:** Add `whisper_model: small` to the true-crime-client YAML content section. This is a configurable YAML field (mapped via `_YAML_TO_CONFIG` as `WHISPER_MODEL`). Spot-check the first 20 transcript segments before running analysis.

**YAML addition:**
```yaml
content:
  whisper_model: "small"   # Better accuracy for accented/non-studio audio
```

---

### Pitfall 5: Episode Number Resolves to None for Date-Based Filenames

**What goes wrong:** Many public podcasts use date-based or slug-based audio filenames (e.g., `casefile-ep300-2024-03-15.mp3` or just `2024-03-15.mp3`). If `extract_episode_number_from_filename()` can't find a number, `episode_number` is `None`, and the episode folder is named `ep_<stem>_<timestamp>` — which is fine but verbose.

**Note:** This is not a blocker — Phase 16 implemented the fallback `ep_{audio_file.stem}_{timestamp}` for None episode numbers. Output isolation still works. The checkpoint keys still work. This is only a cosmetic concern.

**How to handle:** Accept the fallback name for the first run. For the demo, rename the output folder after processing if needed.

---

### Pitfall 6: `CLIP_SELECTION_MODE` and `COMPLIANCE_STYLE` Are New Config Attributes — Use `getattr` Guard

**What goes wrong:** Like `VOICE_PERSONA`, these new attributes are set by `apply_client_config()` on the `Config` class but are not defined in `config.py`. Any code that reads `Config.CLIP_SELECTION_MODE` (not `getattr`) will raise `AttributeError` for Fake Problems or clients that don't set these fields.

**How to avoid:**
```python
# Always use getattr with a default:
clip_mode = getattr(Config, "CLIP_SELECTION_MODE", "energy")
compliance_style = getattr(Config, "COMPLIANCE_STYLE", "permissive")
# "permissive" as default preserves current Fake Problems behavior
```

**Warning sign:** Fake Problems pipeline breaks after this change — test regression suite catches it.

---

### Pitfall 7: Test `test_minimal_config` — Already Updated in Phase 15, But New Fields Need Coverage

**What goes wrong:** The existing `test_minimal_config` test was updated in Phase 15 to include `names_to_remove: []`. The new fields (`clip_selection_mode`, `compliance_style`) should NOT be required fields — they have sensible defaults. No existing test should break.

**How to avoid:** Do not add `clip_selection_mode` or `compliance_style` to the required-field validation list. They are optional behavior-tuning fields, not content-safety fields like `names_to_remove`.

---

## Code Examples

### `_build_analysis_prompt()` — Genre-Aware Clip Criteria

```python
# Source: content_editor.py — replace hardcoded clip criteria block
# In _build_analysis_prompt(), after the voice_examples conditional:

custom_persona = getattr(Config, "VOICE_PERSONA", None)
clip_selection_mode = getattr(Config, "CLIP_SELECTION_MODE", "energy")

if not custom_persona:
    # Fake Problems / comedy: favor high-energy, funny moments
    clip_criteria = (
        "   - Funny or entertaining moments\n"
        "   - Controversial or thought-provoking statements\n"
        "   - Relatable \"fake problems\" discussions\n"
        "   - Moments with good energy and pacing\n"
        "   - Self-contained stories or bits"
    )
else:
    # Custom genre: favor content quality, not delivery energy
    clip_criteria = (
        "   - Moments with a clear, quotable insight or revelation\n"
        "   - Self-contained segments that make sense out of context\n"
        "   - Emotionally compelling or tension-building moments\n"
        "   - Key data points, specific numbers, or case-breaking details\n"
        "   - Strong narrative hooks that make someone want to hear more"
    )

# Suppress energy candidates for content-mode genres:
if clip_selection_mode == "content":
    energy_candidates_for_prompt = None
else:
    energy_candidates_for_prompt = energy_candidates
```

Then pass `energy_candidates_for_prompt` (not `energy_candidates`) to `_build_analysis_prompt()`.

### `content_compliance_checker.py` — Genre-Aware Compliance Context

```python
# Source: content_compliance_checker.py — replace module-level constant approach

COMPLIANCE_PROMPT_TEMPLATE = """Analyze this podcast transcript for YouTube Community Guidelines violations.

YouTube prohibits:
- hate_speech: Dehumanizing content targeting protected groups (race, religion, gender, etc.)
- dangerous_misinformation: False medical/health claims that could cause real harm
- graphic_violence: Explicit descriptions of real violence or instructions for causing harm
- harassment: Targeted attacks or threats against real private individuals
- sexual_content: Explicit sexual descriptions
- self_harm_promotion: Encouraging suicide, self-harm, or eating disorders

TRANSCRIPT:
{{transcript}}

Return ONLY a JSON array. Each element:
{{{{
  "start_timestamp": "HH:MM:SS",
  ...
}}}}

If no violations found, return an empty array: []

{{context}}
"""

_COMPLIANCE_CONTEXTS = {
    "permissive": (
        "Context: This is a comedy podcast. Dark humor, profanity, and edgy jokes are NOT "
        "violations unless they specifically dehumanize real protected groups or contain "
        "genuinely dangerous false health claims that could physically harm listeners."
    ),
    "strict": (
        "Context: This is a serious factual podcast discussing real events and real people. "
        "Flag any content that discusses violence against real individuals, real victim details, "
        "or sensitive topics without appropriate care. Be conservative — flag for human review."
    ),
    "standard": (
        "Context: Apply standard YouTube community guidelines. Flag genuine violations; "
        "do not flag editorial opinion, mature themes handled responsibly, or debate."
    ),
}


def _build_compliance_prompt(transcript: str) -> str:
    """Build compliance prompt with genre-appropriate context line."""
    style = getattr(Config, "COMPLIANCE_STYLE", "permissive")
    context = _COMPLIANCE_CONTEXTS.get(style, _COMPLIANCE_CONTEXTS["standard"])
    return COMPLIANCE_PROMPT_TEMPLATE.format(transcript=transcript, context=context)
```

### `_YAML_TO_CONFIG` additions in `client_config.py`

```python
# Add to _YAML_TO_CONFIG dict:
"content.clip_selection_mode": "CLIP_SELECTION_MODE",
"content.compliance_style": "COMPLIANCE_STYLE",
"content.whisper_model": "WHISPER_MODEL",
```

### Genre YAML additions (true-crime-client.yaml)

```yaml
episode_source: "rss"

rss_source:
  feed_url: "https://feeds.simplecast.com/xl3WWLBP"
  episode_index: 0

content:
  whisper_model: "small"
  clip_selection_mode: "content"
  compliance_style: "strict"
```

### Genre YAML additions (business-interview-client.yaml)

```yaml
episode_source: "rss"

rss_source:
  feed_url: "https://feeds.simplecast.com/4T39_jAj"
  episode_index: 0

content:
  clip_selection_mode: "content"
  compliance_style: "standard"
```

---

## State of the Art

| Old Behavior | New Behavior | What Changes |
|--------------|--------------|--------------|
| Clip criteria always comedy-specific | Clip criteria conditional on `VOICE_PERSONA` | Non-comedy clients get substantive-content criteria |
| Energy candidates always passed to GPT-4o | Suppressed when `CLIP_SELECTION_MODE=content` | GPT-4o selects clips from transcript content for interview genres |
| Compliance always uses comedy-permissive context | Compliance uses style from `Config.COMPLIANCE_STYLE` | True crime gets stricter review; business gets standard review |
| Genre YAMLs exist but use Dropbox source | Genre YAMLs updated with RSS source + new content fields | `uv run main.py latest --client true-crime-client` runs end-to-end |

---

## Open Questions

1. **Should `fake-problems.yaml` be updated with `compliance_style: permissive` explicitly?**
   - What we know: The default for `COMPLIANCE_STYLE` when not set is `"permissive"` (to preserve backward compat). So FP behavior is unchanged without touching that YAML.
   - Recommendation: Leave fake-problems.yaml alone for now. Add it to the YAML only if the validate-client active config block starts showing "(not set)" in a confusing way.

2. **Which exact episode index to use for the first run?**
   - What we know: `episode_index: 0` is always the latest episode. For first-run testing, a 30-45 minute episode is ideal over a 90-minute one (faster transcription, lower OpenAI cost).
   - Recommendation: Check feed manually before running. If latest episode is over 60 minutes, try `episode_index: 1`.

3. **Will Whisper `small` model run on this machine's GPU?**
   - What we know: `CUDA` is available (per project setup, NVIDIA GPU present). Whisper `small` runs fine on any modern NVIDIA GPU and takes ~10-15 min vs. ~20-40 min for base on CPU.
   - Recommendation: Use `small` for true crime client. Use `base` (default) for business podcast since studio audio quality is typically higher.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` (testpaths = ["tests"]) |
| Quick run command | `uv run pytest tests/test_content_compliance_checker.py tests/test_content_editor.py tests/test_client_config.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TEST-01 | True crime pipeline runs end-to-end without exception | manual smoke | `uv run main.py latest --client true-crime-client` | N/A — manual run |
| TEST-01 | `true-crime-client.yaml` loads with new fields (rss_source, clip_selection_mode, compliance_style) | unit | `uv run pytest tests/test_client_config.py -x -k "true_crime"` | New test case needed |
| TEST-02 | Business interview pipeline runs end-to-end without exception | manual smoke | `uv run main.py latest --client business-interview-client` | N/A — manual run |
| TEST-03 | When `CLIP_SELECTION_MODE=content`, energy candidates not passed to GPT-4o | unit | `uv run pytest tests/test_content_editor.py -x -k "clip_selection"` | New test cases needed |
| TEST-03 | When `VOICE_PERSONA` is set, clip criteria use content-quality language | unit | `uv run pytest tests/test_content_editor.py -x -k "clip_criteria"` | New test cases needed |
| TEST-04 | `_build_compliance_prompt()` returns permissive context for permissive style | unit | `uv run pytest tests/test_content_compliance_checker.py -x -k "style"` | New test cases needed |
| TEST-04 | `_build_compliance_prompt()` returns strict context for strict style | unit | `uv run pytest tests/test_content_compliance_checker.py -x -k "style"` | New test cases needed |
| TEST-04 | `COMPLIANCE_STYLE` maps correctly through `_YAML_TO_CONFIG` | unit | `uv run pytest tests/test_client_config.py -x -k "compliance_style"` | New test case needed |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_content_compliance_checker.py tests/test_content_editor.py tests/test_client_config.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green + both genre episodes run manually before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_content_editor.py` — add test: `clip_selection_mode=content` causes `energy_candidates=None` to be passed to prompt builder
- [ ] `tests/test_content_editor.py` — add test: when `VOICE_PERSONA` is set, prompt contains content-quality clip criteria (not "fake problems" text)
- [ ] `tests/test_content_editor.py` — add test: when `VOICE_PERSONA` not set, prompt contains comedy clip criteria
- [ ] `tests/test_content_compliance_checker.py` — add test: `_build_compliance_prompt()` with `COMPLIANCE_STYLE=permissive` contains comedy context line
- [ ] `tests/test_content_compliance_checker.py` — add test: `_build_compliance_prompt()` with `COMPLIANCE_STYLE=strict` contains strict/factual context line
- [ ] `tests/test_content_compliance_checker.py` — add test: `_build_compliance_prompt()` with `COMPLIANCE_STYLE=standard` contains standard context line
- [ ] `tests/test_content_compliance_checker.py` — add test: `check_transcript()` uses `_build_compliance_prompt()` (not the old constant)
- [ ] `tests/test_client_config.py` — add test: `clip_selection_mode: content` maps to `CLIP_SELECTION_MODE=content` on Config
- [ ] `tests/test_client_config.py` — add test: `compliance_style: strict` maps to `COMPLIANCE_STYLE=strict` on Config

---

## Sources

### Primary (HIGH confidence)

- Direct inspection: `content_editor.py` lines 63–80 (`analyze_content()` energy scoring path), lines 194–416 (`_build_analysis_prompt()`)
- Direct inspection: `content_compliance_checker.py` full file — `COMPLIANCE_PROMPT` constant (lines 32–57), `check_transcript()` (lines 62–173)
- Direct inspection: `audio_clip_scorer.py` full file — RMS-only scoring, no content awareness
- Direct inspection: `client_config.py` lines 17–65 (`_YAML_TO_CONFIG` dict) — confirmed `clip_selection_mode` and `compliance_style` are absent and need adding
- Direct inspection: `clients/true-crime-client.yaml`, `clients/business-interview-client.yaml` — confirmed fields present (Phase 15), missing RSS source and new content fields
- Direct inspection: `pipeline/steps/ingest.py` lines 15–62 — RSS ingest path confirmed working (Phase 16)
- `.planning/research/PITFALLS.md` — Pitfall 3 (energy scoring), Pitfall 4 (compliance calibration) — HIGH confidence, code-verified
- `.planning/research/FEATURES.md` — Genre tuning requirements section — MEDIUM confidence

### Secondary (MEDIUM confidence)

- `.planning/phases/15-config-hardening/15-RESEARCH.md` — confirmed voice examples conditional fix shipped; genre YAML structure
- Public podcast RSS feeds: Casefile (Simplecast), How I Built This (Simplecast/NPR) — MEDIUM confidence; URLs should be verified before use

---

## Metadata

**Confidence breakdown:**
- Code fixes required: HIGH — all three issues (clip criteria, compliance prompt, energy suppression) confirmed by direct code inspection
- Architecture for fixes: HIGH — patterns consistent with Phase 15 approach (conditional on VOICE_PERSONA, getattr guards, _YAML_TO_CONFIG extension)
- Public RSS feed URLs: MEDIUM — need live verification before use
- Empirical output quality: LOW — cannot predict GPT-4o output quality on real episodes without running them; the empirical nature is intentional

**Research date:** 2026-03-28
**Valid until:** Stable — no external dependencies on fast-moving packages; valid until `content_editor.py` or `content_compliance_checker.py` are restructured
