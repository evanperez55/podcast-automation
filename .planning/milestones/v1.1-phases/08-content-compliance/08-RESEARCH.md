# Phase 8: Content Compliance - Research

**Researched:** 2026-03-18
**Domain:** AI-based transcript analysis, YouTube community guidelines, audio muting, pipeline upload gating
**Confidence:** HIGH

## Summary

Phase 8 adds a safety gate that scans episode transcripts against YouTube community guidelines before any upload runs. The gate produces a compliance report (timestamps + quoted text + violation category), can auto-mute flagged segments in the video/audio, and blocks the upload step on critical violations unless `--force` is passed.

The project already has the key building blocks: `ContentEditor` calls GPT-4o for transcript analysis, `AudioProcessor.apply_censorship()` ducks audio by time range, and `pipeline/steps/distribute.py` is the exact place to insert the upload block. The new work is a `ContentComplianceChecker` module that uses GPT-4o (the same client already in use) to classify transcript segments by YouTube violation category, writes a JSON compliance report, and sets a flag on `PipelineContext` that `run_distribute` checks before proceeding.

Audio muting for flagged segments can reuse `AudioProcessor._apply_duck_segment()` directly — no new FFmpeg code is needed. The video muting question is trickier: the video file is created after audio processing, so the compliance check must either (a) run before video rendering and pass muted timestamps to the video step, or (b) re-encode the video. Option (a) is simpler and fits the existing pipeline order (compliance runs right after analysis, before censorship).

**Primary recommendation:** Insert `ContentComplianceChecker` as Step 3.6 (after analysis, before censorship). It reads `ctx.transcript_data` + `ctx.analysis`, calls GPT-4o for violation classification, writes a report JSON, and sets `ctx.compliance_result` on the context. `run_distribute` reads `ctx.compliance_result` before any upload and blocks if `ctx.compliance_result["critical"] is True` and `ctx.force` is not set. Flagged segments are merged into `analysis["censor_timestamps"]` so the existing audio/video censorship machinery handles muting automatically.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SAFE-01 | Transcript analyzed against YouTube community guidelines before upload | GPT-4o prompt with structured violation categories; runs as Step 3.6, before distribute |
| SAFE-02 | Flagged segments include timestamps, quoted text, and rule category | Compliance report JSON structure documented below; sourced from transcript word-level data |
| SAFE-03 | Flagged segments can be auto-muted or cut from the video before upload | Merge flagged segments into `analysis["censor_timestamps"]` — AudioProcessor.apply_censorship() handles the rest |
| SAFE-04 | Upload blocked when critical violations detected (requires --force to override) | `ctx.compliance_blocked` flag checked at top of run_distribute; `--force` flag added to CLI |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| openai | already installed | GPT-4o for violation classification | Already used by ContentEditor; no new dep |
| pydub | already installed | Audio segment manipulation for muting | Already used by AudioProcessor |
| json (stdlib) | stdlib | Compliance report serialization | No dep needed |
| pathlib (stdlib) | stdlib | File paths | Project convention |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| unittest.mock | stdlib | Mocking OpenAI in tests | All tests that hit GPT-4o |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| GPT-4o classification | Keyword list / regex | Regex can't catch context-dependent violations (cancer misinformation, self-harm context); GPT-4o already paid for |
| Merging into censor_timestamps | Separate mute pass | Separate pass means duplicated FFmpeg logic; merge is simpler and reuses proven code |
| `--force` flag | `--skip-compliance` | `--force` is more general and may be useful for other blocks; consistent with existing `--auto-approve` pattern |

**Installation:**
```bash
# No new packages required — openai and pydub already in requirements.txt
```

## Architecture Patterns

### Recommended Project Structure
```
podcast-automation/
├── content_compliance_checker.py   # New module (top-level, matches flat convention)
├── tests/
│   └── test_content_compliance_checker.py  # New test file
├── pipeline/
│   ├── runner.py                   # Add Step 3.6 call + --force flag passthrough
│   └── context.py                  # Add compliance_result field + force flag field
```

### Pattern 1: ContentComplianceChecker Module

**What:** A self-contained module with `self.enabled` pattern, identical to every other module (blog_generator, webpage_generator, etc.). Callable independently from analysis.

**When to use:** After analysis (has transcript + AI analysis), before censorship (so flagged segments can be merged).

**Example:**
```python
# content_compliance_checker.py
import json
import openai
from pathlib import Path
from config import Config
from logger import logger


VIOLATION_CATEGORIES = [
    "hate_speech",
    "graphic_violence",
    "dangerous_misinformation",  # medical/health claims without basis
    "harassment",
    "sexual_content",
    "self_harm_promotion",
]

SEVERITY_MAP = {
    "hate_speech": "critical",
    "graphic_violence": "warning",
    "dangerous_misinformation": "critical",
    "harassment": "warning",
    "sexual_content": "warning",
    "self_harm_promotion": "critical",
}


class ContentComplianceChecker:
    def __init__(self):
        self.enabled = os.getenv("COMPLIANCE_ENABLED", "true").lower() == "true"
        if self.enabled:
            self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        logger.info("Content compliance checker %s", "ready" if self.enabled else "disabled")

    def check_transcript(self, transcript_data, episode_output_dir, episode_number):
        """Analyze transcript for YouTube policy violations.

        Returns:
            dict with keys:
              - flagged: list of {start_seconds, end_seconds, text, category, severity}
              - critical: bool  (True if any "critical" severity item found)
              - report_path: str path to saved JSON report
        """
        ...

    def save_report(self, result, episode_output_dir, episode_number, timestamp):
        """Write compliance report JSON to output directory."""
        ...
```

### Pattern 2: PipelineContext Extension

Add two fields to `PipelineContext`:

```python
# pipeline/context.py additions
compliance_result: Optional[dict] = None   # Output of ContentComplianceChecker.check_transcript()
force: bool = False                         # --force flag bypasses upload block
```

### Pattern 3: Step 3.6 in runner.py

```python
# pipeline/runner.py — insert after run_analysis(), before _run_process_audio()

# Step 3.6: Content compliance check
print("STEP 3.6: CONTENT COMPLIANCE CHECK")
print("-" * 60)
compliance_checker = components.get("compliance_checker")
if compliance_checker and compliance_checker.enabled:
    compliance_result = compliance_checker.check_transcript(
        transcript_data=ctx.transcript_data,
        episode_output_dir=ctx.episode_output_dir,
        episode_number=ctx.episode_number,
    )
    ctx.compliance_result = compliance_result

    # Merge flagged segments into censor_timestamps for auto-muting
    if compliance_result.get("flagged"):
        existing = ctx.analysis.get("censor_timestamps", [])
        for item in compliance_result["flagged"]:
            existing.append({
                "start_seconds": item["start_seconds"],
                "end_seconds": item["end_seconds"],
                "reason": f"Compliance: {item['category']}",
                "context": item["text"][:100],
            })
        ctx.analysis["censor_timestamps"] = existing
        logger.info(
            "Merged %d compliance flags into censor list",
            len(compliance_result["flagged"])
        )
print()
```

### Pattern 4: Upload Block in run_distribute

```python
# pipeline/steps/distribute.py — top of run_distribute(), before Step 7

compliance_result = ctx.compliance_result or {}
if compliance_result.get("critical") and not ctx.force:
    print("[BLOCKED] Critical compliance violation detected — upload skipped.")
    print("  Run with --force to override and upload anyway.")
    print(f"  Report: {compliance_result.get('report_path', 'see output dir')}")
    return ctx  # Skip all uploads
```

### Pattern 5: GPT-4o Prompt for Violation Classification

The prompt must be structured to return JSON (matching the pattern in ContentEditor):

```python
COMPLIANCE_PROMPT = """
Analyze this podcast transcript for YouTube Community Guidelines violations.

YouTube prohibits:
- hate_speech: Dehumanizing content targeting protected groups (race, religion, gender, etc.)
- dangerous_misinformation: False medical/health claims that could cause real harm
- graphic_violence: Explicit descriptions of real violence or instructions for harm
- harassment: Targeted attacks or threats against real private individuals
- sexual_content: Explicit sexual descriptions
- self_harm_promotion: Encouraging suicide, self-harm, or eating disorders

TRANSCRIPT:
{transcript}

Return ONLY a JSON array. Each element:
{{
  "start_timestamp": "HH:MM:SS",
  "end_timestamp": "HH:MM:SS",
  "text": "exact quoted text",
  "category": "<one of the categories above>",
  "reason": "brief explanation"
}}

If no violations found, return an empty array: []
Context: This is a comedy podcast. Dark humor, profanity, and edgy jokes are NOT violations unless they specifically dehumanize real protected groups or contain genuinely dangerous false health claims.
"""
```

**Critical nuance:** The ep29 YouTube strike was for "cancer misinformation" (per project memory). The prompt must specifically call out dangerous_misinformation as health/medical claims without scientific basis — NOT just any edgy joke about illness.

### Anti-Patterns to Avoid

- **Don't call the LLM on the full raw transcript at once:** The transcript can be 2+ hours. Split into segments or use the already-formatted `_format_transcript_for_analysis()` output from ContentEditor. Better yet, reuse the timestamped text that analysis already produced.
- **Don't block on warnings, only on critical:** Step 8's requirement says "critical violations" block. Dark jokes that are flagged as warnings should appear in the report but not block upload.
- **Don't create a new audio muting function:** `apply_censorship()` in AudioProcessor already handles timestamp-based ducking. Merge compliance flags into `censor_timestamps` and let existing code do it.
- **Don't store compliance_result outside PipelineContext:** The report path is stored in the JSON file; the in-memory result lives on `ctx`. This matches how analysis works.
- **Don't add `--force` parsing only in main.py:** It must flow through `run()` → `_init_components()` → `PipelineContext.force`. Check how `auto_approve` is wired for the pattern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Transcript violation detection | Custom keyword classifier | GPT-4o via existing openai client | Context-dependent violations (misinformation, dehumanization) need LLM reasoning |
| Audio muting of flagged segments | New FFmpeg mute filter | Merge into censor_timestamps → AudioProcessor.apply_censorship() | AudioProcessor already handles ducking with fade-in/out |
| Report serialization | Custom format | json.dump to episode_output_dir | Consistent with how analysis JSON is saved |
| --force flag propagation | New mechanism | Follow auto_approve pattern in runner.py | Already works for test_mode/dry_run |

**Key insight:** This phase is almost entirely glue code — the LLM client, the audio muting, the pipeline state, and the JSON serialization are all pre-built. The main new work is the prompt design and the upload block logic.

## Common Pitfalls

### Pitfall 1: Over-blocking Comedy Content
**What goes wrong:** GPT-4o classifies dark humor as hate speech because the words are dark, even in comedic context.
**Why it happens:** LLMs default to cautious classification without explicit guidance.
**How to avoid:** Include explicit instruction in the system prompt that comedy context, profanity, and edgy-but-not-targeted humor are NOT violations. Test with ep29's actual content (cancer misinformation) and ep-style content (dark jokes) to calibrate.
**Warning signs:** Test produces flags on benign edgy jokes; increase the threshold in the prompt.

### Pitfall 2: Missing the `--force` Flag Through the Whole Stack
**What goes wrong:** `--force` is parsed in main.py but never reaches `ctx.force`, so the block never lifts.
**Why it happens:** main.py currently strips known flags (`flag_args` list) before passing to run(). Adding `--force` requires updating main.py, run(), _init_components(), and PipelineContext.
**How to avoid:** Trace `--auto-approve` through main.py → run() → _init_components() → ctx. Follow the exact same pattern for `--force`.
**Warning signs:** `--force` in CLI but upload still blocked → ctx.force is False.

### Pitfall 3: Compliance Runs After Audio Processing
**What goes wrong:** Compliance check runs after Step 4 (censor), so flagged segments are never muted.
**Why it happens:** Placing compliance in distribute.py (natural location for upload logic) means it's too late to affect audio.
**How to avoid:** Place compliance as Step 3.6, immediately after analysis, before censorship. Merge flags into analysis["censor_timestamps"] before audio processing runs.
**Warning signs:** Flagged segments appear in report but audio is not muted.

### Pitfall 4: Transcript Too Long for Single API Call
**What goes wrong:** Very long episodes (2+ hours) produce a transcript that exceeds GPT-4o's context window or produces timeouts.
**Why it happens:** Raw Whisper transcripts for 2-hour episodes can be 50,000+ words.
**How to avoid:** Use the already-formatted timestamped_text from ContentEditor (which uses segments, not raw words), or chunk the transcript into 20-minute blocks and merge results. The existing `_format_transcript_for_analysis()` method in ContentEditor already produces a compact format.
**Warning signs:** OpenAI API timeout or context_length_exceeded error.

### Pitfall 5: Report File Location Mismatch
**What goes wrong:** Report written to wrong path; compliance_result["report_path"] doesn't match actual file.
**Why it happens:** episode_output_dir may not exist yet at Step 3.6 time.
**How to avoid:** Call `episode_output_dir.mkdir(parents=True, exist_ok=True)` before writing. Check how analysis.py handles this — it does the same.
**Warning signs:** report_path in result is a path to a non-existent file.

## Code Examples

### Example: Existing apply_censorship signature (reuse for compliance muting)
```python
# audio_processor.py — existing API
def apply_censorship(self, audio_file_path, censor_timestamps, output_path=None):
    """
    censor_timestamps: List of dicts with 'start_seconds', 'end_seconds', 'reason'
    """
```

### Example: ContentEditor LLM call pattern (replicate in ContentComplianceChecker)
```python
# content_editor.py — existing pattern
response = self.client.chat.completions.create(
    model="gpt-4o",
    max_tokens=6000,
    temperature=0.7,
    messages=[
        {"role": "system", "content": VOICE_PERSONA},
        {"role": "user", "content": prompt},
    ],
)
response_text = response.choices[0].message.content
```

### Example: Module enabled pattern (replicate in ContentComplianceChecker)
```python
# Every module uses this pattern
import os
class ContentComplianceChecker:
    def __init__(self):
        self.enabled = os.getenv("COMPLIANCE_ENABLED", "true").lower() == "true"
```

### Example: --force flag in main.py (follows --auto-approve pattern)
```python
# main.py additions
force = "--force" in sys.argv
flag_args = [..., "--force"]  # add to strip list
args = {..., "force": force}

# pipeline/runner.py run() additions
force = args.get("force", False) if isinstance(args, dict) else getattr(args, "force", False)

# PipelineContext
ctx = PipelineContext(..., force=force)
```

### Example: PipelineContext compliance fields
```python
# pipeline/context.py additions
compliance_result: Optional[dict] = None
force: bool = False
```

### Compliance Report JSON Schema
```json
{
  "episode_number": 29,
  "checked_at": "2026-03-18T21:00:00Z",
  "critical": true,
  "flagged": [
    {
      "start_seconds": 1234.5,
      "end_seconds": 1238.0,
      "text": "drinking bleach cures cancer",
      "category": "dangerous_misinformation",
      "severity": "critical",
      "reason": "False medical claim that could cause physical harm"
    }
  ],
  "warnings": [
    {
      "start_seconds": 500.0,
      "end_seconds": 502.0,
      "text": "...",
      "category": "graphic_violence",
      "severity": "warning",
      "reason": "..."
    }
  ]
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Keyword regex for slurs | GPT-4o + direct word search (both) | Already done in Phase 3 | Context-aware detection |
| Upload always runs | Upload gated by compliance | Phase 8 | Prevents ep29-style strikes |
| Manual content review | Automated flagging with human-override via --force | Phase 8 | No manual step required |

**Deprecated/outdated:**
- `SLURS_TO_REMOVE` in config.py: already marked "Legacy — kept for backwards compatibility" with empty list; compliance checker makes this even more redundant.

## Open Questions

1. **Transcript chunking strategy for long episodes**
   - What we know: GPT-4o context window is 128k tokens; a 2-hour formatted transcript is ~15-20k tokens (well within limit)
   - What's unclear: Whether the compliance analysis should be a separate LLM call from the main analysis or merged
   - Recommendation: Separate call. ContentEditor already makes one expensive call; a second focused compliance call is cleaner and easier to test. Temperature 0.1 for deterministic classification.

2. **Severity threshold for "critical" vs "warning"**
   - What we know: ep29 was struck for health misinformation; hate speech terminates channels
   - What's unclear: Whether graphic violence should be critical or warning for a comedy podcast
   - Recommendation: critical = hate_speech, dangerous_misinformation, self_harm_promotion; warning = graphic_violence, harassment, sexual_content. Planner can tune this.

3. **What happens to warnings in the report — do they mute too?**
   - What we know: SAFE-03 says "flagged segments can be auto-muted"; SAFE-04 says upload blocked on "critical violations"
   - What's unclear: Whether warnings trigger auto-muting or only appear in the report
   - Recommendation: Auto-mute ALL flagged segments (both critical and warning) since we have the capability. Upload is only blocked on critical. This satisfies SAFE-03 and SAFE-04 independently.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | none (uses pytest discovery) |
| Quick run command | `pytest tests/test_content_compliance_checker.py -x` |
| Full suite command | `pytest` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SAFE-01 | check_transcript() calls GPT-4o and returns structured result | unit | `pytest tests/test_content_compliance_checker.py::TestCheckTranscript -x` | Wave 0 |
| SAFE-01 | COMPLIANCE_ENABLED=false skips LLM call | unit | `pytest tests/test_content_compliance_checker.py::TestDisabled -x` | Wave 0 |
| SAFE-02 | Report JSON contains timestamps, quoted text, category per flagged item | unit | `pytest tests/test_content_compliance_checker.py::TestReportStructure -x` | Wave 0 |
| SAFE-02 | save_report() writes valid JSON to episode_output_dir | unit | `pytest tests/test_content_compliance_checker.py::TestSaveReport -x` | Wave 0 |
| SAFE-03 | Flagged segments merged into analysis["censor_timestamps"] | unit | `pytest tests/test_content_compliance_checker.py::TestMergeIntoTimestamps -x` | Wave 0 |
| SAFE-04 | run_distribute() returns early when ctx.compliance_result["critical"] is True and ctx.force is False | unit | `pytest tests/test_pipeline_refactor.py::TestComplianceBlock -x` | Wave 0 |
| SAFE-04 | run_distribute() proceeds when ctx.force is True even with critical=True | unit | `pytest tests/test_pipeline_refactor.py::TestComplianceForce -x` | Wave 0 |
| SAFE-04 | --force flag flows from main.py through ctx.force | integration | `pytest tests/test_pipeline_refactor.py::TestForceFlag -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_content_compliance_checker.py -x`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_content_compliance_checker.py` — covers SAFE-01 through SAFE-03
- [ ] Additional test methods in `tests/test_pipeline_refactor.py` — covers SAFE-04 block/force behavior

*(Existing test_pipeline_refactor.py exists and covers runner.py; new test classes can be added there for SAFE-04. test_content_compliance_checker.py is new.)*

## Sources

### Primary (HIGH confidence)
- Direct code reading of `audio_processor.py`, `content_editor.py`, `pipeline/runner.py`, `pipeline/context.py`, `pipeline/steps/distribute.py` — architecture patterns
- Direct code reading of `config.py` — module enabled pattern, env var conventions
- Direct code reading of `tests/test_content_editor.py`, `tests/test_subtitle_clip_generator.py` — test conventions
- Project MEMORY.md — ep29 YouTube strike context (cancer misinformation)

### Secondary (MEDIUM confidence)
- [YouTube Community Guidelines](https://support.google.com/youtube/answer/9288567?hl=en) — official violation categories
- [YouTube Hate Speech Policy](https://support.google.com/youtube/answer/2801939?hl=en) — hate speech definition
- [Viralyft: YouTube Community Guidelines 2025](https://viralyft.com/blog/youtube-community-guidelines) — category summary

### Tertiary (LOW confidence)
- N/A

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries needed; all dependencies already installed
- Architecture: HIGH — patterns directly read from existing codebase
- Pitfalls: HIGH — force flag propagation and compliance placement verified by tracing existing code paths
- YouTube violation categories: MEDIUM — official docs verified, category-to-severity mapping is judgment call

**Research date:** 2026-03-18
**Valid until:** 2026-06-18 (YouTube policy changes infrequently; codebase patterns stable)
