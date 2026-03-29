# Phase 21: Pitch Generator - Research

**Researched:** 2026-03-28
**Domain:** GPT-4o outreach copy generation — personalized pitch emails and DMs from demo output
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PITCH-01 | User can generate a personalized intro message (pre-consent) from prospect metadata via GPT-4o | ProspectFinder already persists prospect YAML with show metadata; PitchGenerator reads YAML `prospect:` block; GPT-4o system prompt constructs intro without requiring demo output |
| PITCH-02 | User can generate a demo pitch (post-consent) that references the processed episode's specific output | DemoPackager already produces `demo/<slug>/<ep_id>/DEMO.md` with LUFS, clip count, time savings; analysis JSON has episode title, summary, show notes; PitchGenerator reads these at `gen-pitch <slug> <ep_id>` invocation |
</phase_requirements>

---

## Summary

Phase 21 implements `PitchGenerator` — a new top-level module (`pitch_generator.py`) that produces personalized outreach copy using GPT-4o. It is the final piece before a human can send an outreach email or DM to a qualified prospect.

The phase has two distinct modes driven by whether a demo exists. Pre-consent (`gen-pitch <slug>`): reads only the client YAML's `prospect:` block (show name, genre, episode count, host contact) to produce an intro message introducing the service and requesting consent to process a sample episode. Post-consent (`gen-pitch <slug> <ep_id>`): reads DEMO.md and analysis JSON to produce a pitch that references specific processed output — LUFS improvement, clip count, episode title, one show note excerpt.

Both modes write their output to `demo/<slug>/PITCH.md` (intro) or `demo/<slug>/<ep_id>/PITCH.md` (demo pitch). The openai SDK, the `self.enabled` pattern, and the `content_editor.py` calling convention are all directly reusable. Zero new dependencies.

**Primary recommendation:** Build `PitchGenerator` as a new standalone module following `ContentEditor`'s `_call_openai_with_retry` pattern. Two public methods — `generate_intro_pitch` and `generate_demo_pitch` — driven by CLI argument count. Write output as markdown to the demo folder.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `openai` | existing (`>=1.0.0`) | GPT-4o API call for pitch copy generation | Already used in `content_editor.py` and `blog_generator.py`; same client pattern |
| `pathlib.Path` | stdlib | File I/O for reading DEMO.md, analysis JSON, YAML; writing PITCH.md | Used throughout the project |
| `yaml` (pyyaml) | existing | Read `clients/<slug>.yaml` `prospect:` block | Already a project dependency |
| `json` | stdlib | Parse `*_analysis.json` for episode title, summary, clip metadata | Standard pattern in `demo_packager.py` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `re` | stdlib | Slugify show name or extract structured fields from DEMO.md if needed | Minimal — DEMO.md is template-generated so structure is predictable |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| GPT-4o direct prompt | Jinja2 template | Jinja2 produces mail-merge feel; GPT-4o generates contextually coherent copy that references specific episode content |
| GPT-4o direct prompt | Ollama/Llama3 | Quality gap matters for persuasive writing; GPT-4o cost is ~$0.01-0.02/pitch |

**Installation:**
```bash
# No new packages. Verify existing deps installed:
uv sync
```

---

## Architecture Patterns

### Recommended Project Structure

```
pitch_generator.py          # PitchGenerator class (new top-level module)
tests/test_pitch_generator.py  # Unit tests (mock OpenAI + mock file reads)

demo/<slug>/PITCH.md            # Output: intro pitch (pre-consent)
demo/<slug>/<ep_id>/PITCH.md    # Output: demo pitch (post-consent)
```

### Pattern 1: The `self.enabled` Module Gate

**What:** Every optional feature module in this project sets `self.enabled` in `__init__` based on credential availability. Methods return early if disabled.

**When to use:** Always — this is project convention.

**Example:**
```python
# From content_editor.py and blog_generator.py patterns
class PitchGenerator:
    def __init__(self):
        self.enabled = bool(getattr(Config, "OPENAI_API_KEY", None))

    def generate_demo_pitch(self, client_name: str, episode_id: str) -> dict:
        if not self.enabled:
            logger.warning("PitchGenerator disabled — OPENAI_API_KEY not set")
            return {}
        ...
```

### Pattern 2: OpenAI With Retry (from `content_editor.py`)

**What:** Call `client.chat.completions.create` with exponential backoff on transient errors. Exact same pattern in `content_editor.py` lines 131-178.

**When to use:** Every OpenAI call in this project.

**Example:**
```python
# Source: content_editor.py lines 148-177 (exact pattern to replicate)
return self.client.chat.completions.create(
    model="gpt-4o",
    max_tokens=1500,      # Pitch is short — 200 words output needs ~400-600 tokens
    temperature=0.7,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ],
)
```

### Pattern 3: Two CLI Modes from Argument Count

**What:** `gen-pitch <slug>` (one arg = intro) vs `gen-pitch <slug> <ep_id>` (two args = demo pitch). Dispatch in `main.py`'s `_handle_client_command`.

**When to use:** Mirrors how `package-demo` works — client + ep_id positional args.

**Example:**
```python
# In main.py _handle_client_command():
elif cmd == "gen-pitch":
    from pitch_generator import PitchGenerator
    slug = sys.argv[2] if len(sys.argv) > 2 else None
    ep_id = sys.argv[3] if len(sys.argv) > 3 else None
    if not slug:
        print("Usage: uv run main.py gen-pitch <slug> [ep_id]")
        return True
    gen = PitchGenerator()
    if ep_id:
        result = gen.generate_demo_pitch(slug, ep_id)
    else:
        result = gen.generate_intro_pitch(slug)
    if result:
        print(f"Pitch written to: {result['path']}")
```

### Pattern 4: Read Inputs from Known File Paths

**What:** Demo packager writes to predictable paths. PitchGenerator reads them by constructing the path from `client_name` and `episode_id`.

**Key paths (confirmed from `demo_packager.py`):**
- DEMO.md: `Config.BASE_DIR / "demo" / client_name / episode_id / "DEMO.md"`
- Analysis JSON: `Config.OUTPUT_DIR / episode_id / "*_analysis.json"` (glob newest)
- Client YAML: `Config.BASE_DIR / "clients" / f"{client_name}.yaml"`

**Output paths:**
- Intro pitch: `Config.BASE_DIR / "demo" / slug / "PITCH.md"`
- Demo pitch: `Config.BASE_DIR / "demo" / slug / episode_id / "PITCH.md"`

### Pattern 5: Return `None` on Failure, Data Dict on Success

**What:** Project convention — external API wrappers return `None` (or empty dict) on failure and log a warning, never raise to caller.

```python
try:
    response = self._call_openai_with_retry(system_prompt, user_message)
    pitch_text = response.choices[0].message.content
    return {"subject": ..., "email": ..., "dm": ..., "path": ...}
except Exception as e:
    logger.warning("Pitch generation failed for %s: %s", client_name, e)
    return None
```

### Recommended Module Structure

```python
"""Personalized outreach pitch generation via GPT-4o."""

import json
import time
from pathlib import Path
from typing import Optional

import openai
import yaml

from config import Config
from logger import logger


class PitchGenerator:
    def __init__(self):
        self.enabled = bool(getattr(Config, "OPENAI_API_KEY", None))
        if self.enabled:
            self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)

    def generate_intro_pitch(self, client_slug: str) -> Optional[dict]:
        """Generate pre-consent intro pitch from prospect YAML metadata."""
        ...

    def generate_demo_pitch(self, client_slug: str, episode_id: str) -> Optional[dict]:
        """Generate post-consent demo pitch from DEMO.md + analysis JSON."""
        ...

    def _load_prospect_yaml(self, client_slug: str) -> dict:
        """Read clients/<slug>.yaml and return the prospect: block."""
        ...

    def _load_demo_md(self, client_slug: str, episode_id: str) -> str:
        """Read demo/<slug>/<ep_id>/DEMO.md as raw text."""
        ...

    def _load_analysis(self, client_slug: str, episode_id: str) -> dict:
        """Read newest *_analysis.json from output/<ep_id>/ directory."""
        ...

    def _call_openai_with_retry(self, system_prompt: str, user_message: str,
                                 max_retries: int = 3):
        """Call GPT-4o with exponential backoff (mirrors content_editor.py)."""
        ...

    def _write_pitch_md(self, path: Path, pitch: dict) -> Path:
        """Write PITCH.md with subject, email, and DM sections."""
        ...
```

### Prompt Construction Strategy

**Intro pitch prompt (PITCH-01):**
- System: "You write cold outreach for a podcast production service. The email must be under 200 words, show-specific, and outcome-focused. Never start with 'I'. Lead with their show."
- User context: podcast name, genre, episode count, host name (from YAML `prospect:` block), service value proposition (6-11 hours saved, ~$1-2/episode)
- Output: subject line (< 60 chars), email body (< 200 words), DM-length variant (< 280 chars)

**Demo pitch prompt (PITCH-02):**
- Same system prompt
- User context adds: episode title, LUFS before/after (from DEMO.md), clip count, episode summary excerpt, one show note excerpt (from analysis JSON)
- Output: same structure, but email body references specific episode metrics

**Output format:** Ask GPT-4o to return structured sections delimited by headers (`### SUBJECT`, `### EMAIL`, `### DM`) for reliable parsing without JSON mode (avoids escaping issues with conversational prose).

### Anti-Patterns to Avoid

- **Live RSS fetch inside `generate_pitch`:** RSS enrichment already happened during `find-prospects`. Read from YAML only — no network calls in pitch generation.
- **JSON mode for pitch output:** Pitch copy contains colons, quotes, apostrophes. Asking for JSON introduces escaping errors. Use delimited sections (`### SUBJECT`, etc.) instead.
- **Reading analysis JSON by hardcoded path:** Use glob for `*_analysis.json` in the episode output dir (same pattern as `demo_packager.py`), not a hardcoded filename.
- **Generating pitch without checking DEMO.md exists:** For demo pitch mode, validate `DEMO.md` exists before calling OpenAI. Fail with a clear message if the demo hasn't been packaged yet.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry on transient OpenAI errors | Custom retry loop | Copy `_call_openai_with_retry` from `content_editor.py` | Already handles RateLimitError, APIError, APIConnectionError, APITimeoutError with exponential backoff |
| Personalized copy generation | Jinja2 template with merge fields | GPT-4o with structured context | Templates produce recognizable form emails; GPT-4o generates contextually coherent prose |
| DEMO.md parsing | Regex / markdown parser | Read as raw text, pass to GPT-4o | DEMO.md is structured enough for the LLM to extract metrics; no parsing library needed |

**Key insight:** The hard part of this phase is prompt engineering, not file I/O or API integration. The infrastructure (OpenAI client, file paths, module structure) is all directly reusable from existing modules.

---

## Common Pitfalls

### Pitfall 1: DEMO.md Does Not Exist for Intro Pitch Mode

**What goes wrong:** `gen-pitch <slug>` (no ep_id) may be called before any demo has been packaged. The `demo/<slug>/` directory may not exist.

**Why it happens:** Intro pitch is intentionally pre-demo — the user contacts the prospect before processing their episode. The demo folder won't exist yet.

**How to avoid:** `generate_intro_pitch` reads only `clients/<slug>.yaml`. It must not reference any demo path. The PITCH.md output goes to `demo/<slug>/PITCH.md` — create the `demo/<slug>/` directory with `mkdir(parents=True, exist_ok=True)`.

**Warning signs:** `FileNotFoundError` on `demo/<slug>/<ep_id>/DEMO.md` in intro mode.

### Pitfall 2: Analysis JSON Path Assumes Single Episode

**What goes wrong:** `output/<ep_id>/` may contain multiple analysis JSON files if the pipeline was re-run. A hardcoded name will miss the newest one.

**Why it happens:** Pipeline re-runs create new timestamped analysis files.

**How to avoid:** Glob `Config.OUTPUT_DIR / episode_id / "*_analysis.json"` and take the newest by mtime — exact same pattern as `demo_packager.py`'s `_find_analysis` method.

### Pitfall 3: GPT-4o Output Requires Reliable Parsing

**What goes wrong:** If pitch copy contains colons, quotes, or newlines and is returned as JSON, `json.loads` fails.

**Why it happens:** Conversational prose does not serialize cleanly to JSON.

**How to avoid:** Instruct GPT-4o to delimit sections with `### SUBJECT`, `### EMAIL`, `### DM` markers. Parse with `split("### ")` and strip section names. No JSON parsing needed.

### Pitfall 4: `enabled` Check in `generate_demo_pitch` Must Happen Before File I/O

**What goes wrong:** If `enabled=False` is checked after reading files, the method does unnecessary work and the warning message is misleading.

**How to avoid:** Check `self.enabled` first — return `None` immediately if not enabled, before any file reads.

### Pitfall 5: main.py Line Count

**What goes wrong:** `main.py` has a 280-line test constraint (documented in `prospect_finder.py`'s design note in STATE.md). Adding `gen-pitch` CLI logic inline could push past it.

**Why it happens:** Phase 20 extracted `run_find_prospects_cli` to `prospect_finder.py` for exactly this reason.

**How to avoid:** If the CLI handler for `gen-pitch` is more than ~20 lines, extract it to a `run_gen_pitch_cli(argv)` function in `pitch_generator.py`. Keep `main.py`'s `_handle_client_command` as a thin dispatch.

---

## Code Examples

### Loading Prospect YAML Block

```python
# Pattern: read YAML, extract prospect: block
def _load_prospect_yaml(self, client_slug: str) -> dict:
    yaml_path = Config.BASE_DIR / "clients" / f"{client_slug}.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"Client YAML not found: {yaml_path}")
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    return {
        "podcast_name": data.get("podcast_name", client_slug),
        "prospect": data.get("prospect", {}),
    }
```

### Finding Analysis JSON (glob newest — from demo_packager.py pattern)

```python
# Source: demo_packager.py _find_analysis() method
def _load_analysis(self, client_slug: str, episode_id: str) -> dict:
    ep_dir = Config.OUTPUT_DIR / episode_id
    candidates = sorted(
        ep_dir.glob("*_analysis.json"),
        key=lambda p: p.stat().st_mtime,
    )
    if not candidates:
        raise FileNotFoundError(f"No analysis JSON in {ep_dir}")
    with open(candidates[-1], "r", encoding="utf-8") as f:
        return json.load(f)
```

### Parsing GPT-4o Delimited Output

```python
def _parse_pitch_response(self, raw: str) -> dict:
    """Parse ### SUBJECT / ### EMAIL / ### DM sections from GPT-4o output."""
    result = {"subject": "", "email": "", "dm": ""}
    current_key = None
    lines_buffer = []

    for line in raw.splitlines():
        if line.startswith("### SUBJECT"):
            current_key = "subject"
            lines_buffer = []
        elif line.startswith("### EMAIL"):
            if current_key:
                result[current_key] = "\n".join(lines_buffer).strip()
            current_key = "email"
            lines_buffer = []
        elif line.startswith("### DM"):
            if current_key:
                result[current_key] = "\n".join(lines_buffer).strip()
            current_key = "dm"
            lines_buffer = []
        elif current_key:
            lines_buffer.append(line)

    if current_key:
        result[current_key] = "\n".join(lines_buffer).strip()

    return result
```

### Writing PITCH.md

```python
def _write_pitch_md(self, path: Path, pitch: dict) -> Path:
    """Write PITCH.md with subject, email, and DM sections."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"""# Pitch: {pitch.get('podcast_name', '')}

## Subject Line

{pitch['subject']}

## Email Body

{pitch['email']}

## DM Variant (Twitter/Instagram, <280 chars)

{pitch['dm']}

---
*Generated by Podcast Automation Pipeline*
"""
    path.write_text(content, encoding="utf-8")
    logger.info("Pitch written: %s", path)
    return path
```

### OpenAI Call (mirrors content_editor.py exactly)

```python
# Source: content_editor.py lines 131-178
def _call_openai_with_retry(self, system_prompt: str, user_message: str,
                             max_retries: int = 3):
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return self.client.chat.completions.create(
                model="gpt-4o",
                max_tokens=1500,
                temperature=0.7,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
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
                delay = min(2.0 * (2 ** attempt), 60.0)
                logger.warning(
                    "OpenAI API error (attempt %d/%d): %s — retrying in %.0fs",
                    attempt + 1, max_retries, e, delay,
                )
                time.sleep(delay)
            else:
                logger.error("OpenAI API failed after %d retries: %s", max_retries, e)
    raise last_error
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pure Jinja2 mail-merge templates | GPT-4o with structured context | v1.5 design decision | Produces coherent prose that references specific episode content rather than fill-in-the-blank |
| `openai.ChatCompletion.create()` (v0.x) | `client.chat.completions.create()` (v1.x) | openai SDK v1.0.0 (already adopted by this project) | Must use new API; old API removed |

**Deprecated/outdated:**
- `openai.ChatCompletion.create()`: Removed in openai SDK v1.0.0. The project already uses `client.chat.completions.create()` — do not regress.

---

## Open Questions

1. **Output path when demo folder doesn't exist for intro pitch**
   - What we know: `demo/<slug>/` may not exist before any pipeline run
   - What's unclear: Should `generate_intro_pitch` create the directory, or require it?
   - Recommendation: Create with `mkdir(parents=True, exist_ok=True)` — consistent with how `DemoPackager` creates `demo/<slug>/<ep_id>/` on demand.

2. **How much of DEMO.md to include in the demo pitch prompt**
   - What we know: DEMO.md is ~50 lines of templated markdown with tables; full text is ~1000-1500 characters
   - What's unclear: Whether to pass the full DEMO.md or extract key metrics
   - Recommendation: Pass full DEMO.md as raw text. At ~1500 chars it is well within GPT-4o context. Extraction logic adds complexity and can miss useful details.

3. **PITCH.md format: single file or separate files per pitch type**
   - What we know: Success criteria says `demo/<slug>/<ep_id>/PITCH.md` for post-demo; intro path is not specified
   - Recommendation: Intro pitch → `demo/<slug>/PITCH.md`. Demo pitch → `demo/<slug>/<ep_id>/PITCH.md`. Both in the same format.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (see `pyproject.toml` `testpaths = ["tests"]`) |
| Config file | `pyproject.toml` |
| Quick run command | `uv run pytest tests/test_pitch_generator.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PITCH-01 | `generate_intro_pitch` reads YAML `prospect:` block, calls GPT-4o, returns subject/email/dm dict | unit | `uv run pytest tests/test_pitch_generator.py::TestGenerateIntroPitch -x` | ❌ Wave 0 |
| PITCH-01 | Disabled when `OPENAI_API_KEY` not set — returns `None` without API call | unit | `uv run pytest tests/test_pitch_generator.py::TestPitchGeneratorInit -x` | ❌ Wave 0 |
| PITCH-01 | `FileNotFoundError` raised when client YAML not found | unit | `uv run pytest tests/test_pitch_generator.py::TestGenerateIntroPitch::test_missing_yaml -x` | ❌ Wave 0 |
| PITCH-01 | PITCH.md written to `demo/<slug>/PITCH.md` for intro mode | unit | `uv run pytest tests/test_pitch_generator.py::TestWritePitchMd -x` | ❌ Wave 0 |
| PITCH-02 | `generate_demo_pitch` reads DEMO.md + analysis JSON, calls GPT-4o, returns enriched pitch | unit | `uv run pytest tests/test_pitch_generator.py::TestGenerateDemoPitch -x` | ❌ Wave 0 |
| PITCH-02 | `generate_demo_pitch` returns `None` and logs warning when DEMO.md missing | unit | `uv run pytest tests/test_pitch_generator.py::TestGenerateDemoPitch::test_missing_demo_md -x` | ❌ Wave 0 |
| PITCH-02 | PITCH.md written to `demo/<slug>/<ep_id>/PITCH.md` for demo mode | unit | `uv run pytest tests/test_pitch_generator.py::TestWritePitchMd -x` | ❌ Wave 0 |
| PITCH-02 | Analysis JSON glob uses newest file by mtime | unit | `uv run pytest tests/test_pitch_generator.py::TestLoadAnalysis -x` | ❌ Wave 0 |
| PITCH-01,02 | `gen-pitch <slug>` CLI dispatches to intro mode; `gen-pitch <slug> <ep_id>` to demo mode | unit | `uv run pytest tests/test_pitch_generator.py::TestCli -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_pitch_generator.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_pitch_generator.py` — covers PITCH-01, PITCH-02 (all rows above)
- [ ] `pitch_generator.py` — the module under test itself

Framework is already installed; `tests/conftest.py` has shared fixtures; no new infra needed beyond the new files.

---

## Sources

### Primary (HIGH confidence)

- Direct codebase inspection: `content_editor.py` — exact `_call_openai_with_retry` pattern to replicate
- Direct codebase inspection: `demo_packager.py` — DEMO.md paths, analysis JSON glob, `_find_analysis` method
- Direct codebase inspection: `outreach_tracker.py` — already-shipped `prospects` schema (single table, `VALID_STATUSES` tuple)
- Direct codebase inspection: `prospect_finder.py` — `prospect:` YAML block structure, `save_prospect` method
- Direct codebase inspection: `main.py` — `_handle_client_command` dispatch table, `package-demo` argument pattern to mirror
- Direct codebase inspection: `blog_generator.py` — `temperature=0.7` pattern for persuasive/creative copy
- Direct codebase inspection: `clients/example-client.yaml` — confirmed `prospect:` block is not in `_YAML_TO_CONFIG`

### Secondary (MEDIUM confidence)

- `.planning/research/ARCHITECTURE.md` — `PitchGenerator` design, data flow, anti-patterns documented in pre-phase research
- `.planning/research/FEATURES.md` — email anatomy, pitch personalization field list, <200 word length requirement
- `.planning/research/STACK.md` — GPT-4o cost estimate (~$0.01-0.02/pitch), zero new packages confirmation

### Tertiary (LOW confidence)

- None — all critical claims verified against codebase directly.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies already in project; zero new packages
- Architecture: HIGH — module structure, file paths, and calling patterns verified against live codebase
- Pitfalls: HIGH — main.py line limit confirmed from STATE.md decision log; DEMO.md path confirmed from demo_packager.py; analysis JSON glob confirmed from demo_packager.py `_find_analysis`

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable stack — openai SDK, project patterns)
