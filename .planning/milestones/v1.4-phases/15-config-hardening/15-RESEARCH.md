# Phase 15: Config Hardening - Research

**Researched:** 2026-03-28
**Domain:** Python class-level config patching, YAML validation, CLI output for config audit
**Confidence:** HIGH — all findings are from direct codebase inspection; no external research needed

---

## Summary

Phase 15 is a targeted code-hardening task. The codebase already has a working `activate_client()` / `apply_client_config()` system and a functioning `validate-client` CLI command. The gap is three specific failure modes:

1. `NAMES_TO_REMOVE` defaults to Fake Problems host names and silently stays that way when a client YAML omits the field entirely (vs. setting `[]`). Processing a real client episode with this default would inject "Joey", "Evan", etc. into the censorship pass.
2. `content_editor.py` has a hardcoded `VOICE_PERSONA` string constant at module level (Fake Problems voice) that is the fallback when `Config.VOICE_PERSONA` is absent. More critically, a `voice_examples` block with Fake Problems-specific BAD/GOOD pairs is always injected into every GPT-4o prompt unconditionally — even when a custom `voice_persona` is configured.
3. `validate-client` currently accepts a missing `names_to_remove` field as valid — it just shows "Censor names list: (OK) 9 names" because `Config.NAMES_TO_REMOVE` still holds the FP defaults after `activate_client()` ran. There is no audit-print showing where those names came from.

The fix is: (a) treat missing `names_to_remove` in a client YAML as a hard validation error in `validate_client()`, (b) print active `voice_persona`, `names_to_remove`, and `podcast_name` from live `Config` values in `validate-client` output, (c) make the voice-examples block in `_build_analysis_prompt()` conditional on whether the client is `fake-problems` or no custom persona is configured, and (d) create 2-3 real genre YAML files.

**Primary recommendation:** Fix `validate_client()` to error on missing `names_to_remove`, add an "Active config" printout block, make voice examples conditional in `content_editor.py`, and add `true-crime` and `business-interview` client YAMLs.

---

## Standard Stack

### Core (no new dependencies needed)

All changes are within existing code. `yaml`, `config.py`, `client_config.py`, and `content_editor.py` are all already present. No new packages are required for this phase.

| Component | Location | Purpose |
|-----------|----------|---------|
| `client_config.py` | root | `validate_client()`, `load_client_config()`, `activate_client()` |
| `config.py` | root | `Config.NAMES_TO_REMOVE`, `Config.PODCAST_NAME`, `Config.VOICE_PERSONA` |
| `content_editor.py` | root | `VOICE_PERSONA` fallback constant, `voice_examples` block in `_build_analysis_prompt()` |
| `clients/*.yaml` | `clients/` | Per-client YAML files (2 new real genre YAMLs) |
| `tests/test_client_config.py` | `tests/` | Existing test file — needs new test cases |

---

## Architecture Patterns

### Pattern 1: Validation Error on Missing Required Content Fields

`load_client_config()` currently skips any YAML field that resolves to `None` — this is correct for credentials (null = use env var). But `names_to_remove` is content behavior, not a credential. A missing field must be treated as an error, not a fallback.

**The precise check needed:** After parsing, if `content.names_to_remove` is absent from the YAML entirely (not present as `null` or `[]`) — raise `ValueError`. If present as `[]`, that is a valid explicit override (clears FP names). If present as a list, apply it.

```python
# In load_client_config(), after the _YAML_TO_CONFIG loop:
content_section = data.get("content", {}) or {}
if "names_to_remove" not in content_section:
    raise ValueError(
        f"Client config '{client_name}' is missing required field: "
        "content.names_to_remove\n"
        "Set to an empty list [] if this client has no hosts to censor."
    )
```

**Why this is the right boundary:** `names_to_remove` is a content-shaping field that silently changes pipeline output if wrong. This is the same category as missing credentials — it should surface at load time, not produce incorrect output silently.

### Pattern 2: Active Config Print Block in `validate_client()`

`validate_client()` needs a dedicated section that prints what GPT-4o will actually receive — not what the YAML says, but the live `Config` values after `activate_client()` runs.

```python
# After existing credential checks, add:
print()
print("Active content configuration:")
print(f"  Podcast name:      {Config.PODCAST_NAME}")
voice = getattr(Config, "VOICE_PERSONA", None) or "(using built-in Fake Problems default)"
print(f"  Voice persona:     {voice[:80]}..." if len(voice) > 80 else f"  Voice persona:     {voice}")
names = Config.NAMES_TO_REMOVE
print(f"  names_to_remove:   {names if names else '(empty — no host censorship)'}")
words = Config.WORDS_TO_CENSOR
print(f"  words_to_censor:   {len(words)} words" if words else "  words_to_censor:   (empty)")
blog_voice = getattr(Config, "BLOG_VOICE", None)
print(f"  blog_voice:        {'configured' if blog_voice else '(not set)'}")
scoring = getattr(Config, "SCORING_PROFILE", None)
print(f"  scoring_profile:   {'configured' if scoring else '(not set)'}")
```

This directly addresses CFG-03: user can see active voice persona, names, podcast name — all from the live Config state, not from re-reading YAML.

### Pattern 3: Conditional Voice Examples in `_build_analysis_prompt()`

The `voice_examples` block in `content_editor.py` at lines 262-285 is an unconditional string literal. The fix is to wrap it in a condition:

```python
# Replace unconditional assignment with:
custom_persona = getattr(Config, "VOICE_PERSONA", None)
if not custom_persona:
    # Only inject Fake Problems examples when no custom persona is set
    voice_examples = """
**VOICE EXAMPLES — match this tone in ALL output:**
...
"""
else:
    # Custom persona is in the system message — no hardcoded examples
    voice_examples = ""
```

**Critical detail:** The `voice` variable in `analyze_content()` at line 85 already reads `Config.VOICE_PERSONA` correctly:
```python
voice = getattr(Config, "VOICE_PERSONA", None) or VOICE_PERSONA
```
This is correct — it uses the system-message slot. The only remaining leak is the `voice_examples` inline block in the user-message prompt. The fix is the conditional above.

### Pattern 4: Real Genre Client YAML Structure

Two new YAML files need to be created. They must have all required fields including `content.names_to_remove` (since we are making that required). They should exercise `voice_persona`, `blog_voice`, and `scoring_profile` to satisfy CFG-02.

**true-crime-client.yaml structure:**
```yaml
client_name: "true-crime-client"
podcast_name: "Cold Case Chronicles"  # placeholder name

content:
  names_to_remove: []   # true crime podcasts don't censor host names
  words_to_censor: []   # no profanity list for this genre
  voice_persona: |
    You write for Cold Case Chronicles — a serious true crime podcast
    examining unsolved and wrongful conviction cases. Your output is
    measured, respectful to victims and families, and evidence-focused.
    Avoid sensationalism. Write like a journalist, not an entertainer.
    Never use humor about crimes or victims.
  blog_voice: |
    Write this blog post in a clear, investigative tone.
    BAD: "The hosts delve into a chilling case..."
    GOOD: "This episode examines the 1987 disappearance of..."
  scoring_profile:
    description: "a true crime podcast focused on cold cases and wrongful convictions"
    criteria:
      - name: "Case Significance"
        key: "case_significance"
        max: 3
        description: "How significant or newsworthy is this case?"
      - name: "New Evidence"
        key: "new_evidence"
        max: 3
        description: "Is there recent development, new evidence, or exoneration?"
      - name: "Victim Centered"
        key: "victim_centered"
        max: 2
        description: "Is the framing respectful to victims and families?"
      - name: "Accessible"
        key: "accessible"
        max: 2
        description: "Can a general audience follow without prior case knowledge?"
    style:
      - "Evidence-based analysis over speculation"
      - "Respectful to victims and families at all times"
    high_examples:
      - '"New DNA evidence exonerates man convicted in 1992 murder"'
    low_examples:
      - "Celebrity gossip repackaged as true crime"
    categories: ["cold_case", "wrongful_conviction", "forensic_science", "missing_person"]
```

**business-interview-client.yaml structure:**
```yaml
client_name: "business-interview-client"
podcast_name: "Founders in the Field"  # placeholder name

content:
  names_to_remove: []   # no censorship for business interviews
  words_to_censor: []
  voice_persona: |
    You write for Founders in the Field — a business interview podcast
    where entrepreneurs share real stories from building companies.
    Your output is direct, substantive, and professional without being
    corporate. Highlight concrete lessons, hard decisions, and numbers.
    Never use hype language. No exclamation points for enthusiasm.
  blog_voice: |
    Write this blog post for a professional audience interested in
    entrepreneurship and startup lessons.
    BAD: "In this inspiring episode, our guest shares their amazing journey..."
    GOOD: "Mira Chen built a $4M bootstrapped business in 18 months. Here's what she learned."
  scoring_profile:
    description: "a business interview podcast for founders and operators"
    criteria:
      - name: "Actionable Insight"
        key: "actionable_insight"
        max: 3
        description: "Does this topic yield concrete takeaways for founders?"
      - name: "Contrarian or Non-Obvious"
        key: "contrarian"
        max: 3
        description: "Does this challenge conventional business wisdom?"
      - name: "Specific and Concrete"
        key: "specific"
        max: 2
        description: "Does it include real numbers, names, or timelines?"
      - name: "Broadly Relevant"
        key: "broadly_relevant"
        max: 2
        description: "Does it apply across industries, not just one niche?"
    style:
      - "Concrete over inspirational"
      - "Numbers and outcomes over feelings and process"
    high_examples:
      - '"How we hit $1M ARR with zero paid marketing"'
    low_examples:
      - "Generic advice everyone already knows"
    categories: ["fundraising", "growth", "hiring", "product", "operations", "failure"]
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| YAML parsing | Custom file reader | `yaml.safe_load()` (already in use) |
| Config patching | New override mechanism | `setattr(Config, attr, value)` (already works) |
| Validation error formatting | Custom exception class | Plain `ValueError` with descriptive message (project convention) |

---

## Common Pitfalls

### Pitfall 1: `load_client_config()` vs. `activate_client()` — Where to Put the Validation

**What goes wrong:** Putting the `names_to_remove` required-field check inside `validate_client()` but not in `load_client_config()`. That means `process_episode()` runs fine without the check (it calls `activate_client()` which calls `load_client_config()` but not `validate_client()`).

**How to avoid:** Put the required-field check in `load_client_config()` — not in `validate_client()`. `validate_client()` calls `activate_client()` which calls `load_client_config()`, so the error fires from both the validate path and the process path. This is the correct system boundary.

**Warning sign:** Test passes for `validate_client` but `--dry-run` on the same client doesn't raise an error.

### Pitfall 2: `names_to_remove: null` vs. Field Absent — Same or Different?

**What goes wrong:** Treating `names_to_remove: null` the same as the field being absent.

**How to avoid:** In YAML, `names_to_remove: null` means the field IS present, its value is null. The current code uses `_get_nested()` which returns `None` for both cases. The check must distinguish: use `"names_to_remove" in (data.get("content", {}) or {})` to detect field presence, not `_get_nested()` return value.

**Correct logic:**
```python
content_section = data.get("content", {}) or {}
if "names_to_remove" not in content_section:
    raise ValueError(...)
# If present but null or non-list: existing logic handles it
```

### Pitfall 3: `Config.VOICE_PERSONA` Attribute May Not Exist

**What goes wrong:** `hasattr(Config, "VOICE_PERSONA")` is False by default (no such attribute defined in `config.py`). Code that does `Config.VOICE_PERSONA` without a guard raises `AttributeError`.

**How to avoid:** Always use `getattr(Config, "VOICE_PERSONA", None)`. The existing code in `content_editor.py` line 85 already does this correctly:
```python
voice = getattr(Config, "VOICE_PERSONA", None) or VOICE_PERSONA
```
The `validate_client()` printout must also use `getattr`.

**Confirmed by test:** `TestBackwardCompatibility.test_voice_persona_not_on_config_by_default` explicitly asserts `not hasattr(Config, "VOICE_PERSONA") or Config.VOICE_PERSONA is None`.

### Pitfall 4: Fake Problems Backward Compatibility — `names_to_remove` Already in YAML

**What goes wrong:** Adding the required-field check breaks loading `fake-problems.yaml` if that YAML lacks `content.names_to_remove`.

**Not a problem:** `clients/fake-problems.yaml` already has `names_to_remove` as an explicit list (lines 43-53). The check fires only when the field is completely absent. No backward compat issue.

### Pitfall 5: Minimal YAML Test Will Break

**What goes wrong:** The existing test `test_minimal_config` uses a YAML with no `content` section at all. After adding the required-field check, this test raises `ValueError` instead of returning `{"PODCAST_NAME": ...}`.

**How to handle:** Either update `MINIMAL_YAML` in the test to include `content:\n  names_to_remove: []`, or add a new test that explicitly verifies the error. The `test_minimal_config` test currently asserts `len(overrides) == 1` — that invariant is broken by the new requirement. Update the test.

### Pitfall 6: `validate-client` Currently Shows "Censor names list: OK (9 names)" for Any Client

**What goes wrong:** The current check at line 393:
```python
has_names = bool(getattr(Config, "NAMES_TO_REMOVE", None))
```
This is always `True` for any client that didn't explicitly set `names_to_remove: []`, because the FP defaults stay on `Config`. For a client that DID set `names_to_remove: []`, `bool([])` is `False`, so `validate_client` shows "Censor names list: [ ] not configured" — which looks like a failure even though it's correct.

**The fix:** Stop treating a non-empty `NAMES_TO_REMOVE` as "OK." The correct check is whether the value came from the client config vs. the default. The simplest approach: check if `names_to_remove` was present in the raw YAML (before loading). Alternatively, check if `Config.NAMES_TO_REMOVE` is exactly the FP default list — if it is, that may indicate the client YAML didn't override it (but this is fragile). The cleanest fix is for `load_client_config()` to raise on missing field (Pitfall 1), so the validation step never sees the old default.

---

## Code Examples

### CFG-01 Fix: Required Field Check in `load_client_config()`

```python
# In client_config.py, load_client_config(), after the _YAML_TO_CONFIG loop:
# Source: direct codebase analysis — _get_nested() returns None for both absent and null

content_section = data.get("content", {}) or {}
if "names_to_remove" not in content_section:
    raise ValueError(
        f"Client config '{client_name}' is missing required field: "
        "content.names_to_remove\n"
        "Set to an empty list [] if this client has no host names to censor."
    )
```

### CFG-03 Fix: Active Config Print Block in `validate_client()`

```python
# In client_config.py, validate_client(), after _check() calls:

print()
print("Active content configuration (from YAML + env):")
print(f"  Podcast name:    {Config.PODCAST_NAME}")

voice = getattr(Config, "VOICE_PERSONA", None)
if voice:
    preview = voice[:80] + "..." if len(voice) > 80 else voice
    print(f"  Voice persona:   {preview}")
else:
    print("  Voice persona:   (built-in Fake Problems default)")

names = Config.NAMES_TO_REMOVE
if names:
    print(f"  names_to_remove: {names}")
else:
    print("  names_to_remove: (empty — no host censorship)")

words = Config.WORDS_TO_CENSOR
print(f"  words_to_censor: {len(words)} words" if words else "  words_to_censor: (empty)")

blog_voice = getattr(Config, "BLOG_VOICE", None)
print(f"  blog_voice:      {'configured (' + str(len(blog_voice)) + ' chars)' if blog_voice else '(not set)'}")

scoring = getattr(Config, "SCORING_PROFILE", None)
print(f"  scoring_profile: {'configured' if scoring else '(not set)'}")
```

### Conditional Voice Examples in `content_editor.py`

```python
# In _build_analysis_prompt(), replace unconditional voice_examples assignment:

custom_persona = getattr(Config, "VOICE_PERSONA", None)
if not custom_persona:
    voice_examples = """
**VOICE EXAMPLES — match this tone in ALL output:**

Episode titles:
BAD (generic): "Exploring the Science of Lobster Immortality"
GOOD (show voice): "Lobsters Are Basically Immortal and Honestly Good for Them"
...
"""
else:
    # Custom voice persona is set in system message — don't override with FP examples
    voice_examples = ""
```

---

## State of the Art

| Old Behavior | New Behavior | What Changes |
|--------------|--------------|--------------|
| Missing `names_to_remove` silently falls back to FP defaults | Raises `ValueError` at load time | Any client YAML without this field fails immediately |
| `validate-client` shows credential checks only | Also shows active `podcast_name`, `voice_persona`, `names_to_remove` | Users can audit what GPT-4o will actually receive |
| Voice examples block always injected | Only injected when no custom `voice_persona` is set | Non-FP clients get clean prompts |
| No real genre YAMLs | 2 new client YAMLs (true-crime, business-interview) | CFG-02 satisfied |

---

## Open Questions

1. **Should `voice_persona: null` (explicit null) also be treated as a required-field error?**
   - What we know: `voice_persona` is not listed as "required" in the success criteria — only `names_to_remove` is. `voice_persona: null` means "use FP default," which may be correct for some legacy or testing scenarios.
   - Recommendation: Do not make `voice_persona` required. The success criteria only calls for missing `names_to_remove` to be an error. Leave voice_persona as optional with a fallback.

2. **The `test_minimal_config` test asserts `len(overrides) == 1` — it will break.**
   - What we know: The minimal YAML has no `content` section, so the new required-field check fires.
   - Recommendation: Update `MINIMAL_YAML` in the test file to add `content:\n  names_to_remove: []`. This is the correct behavior for a minimal client config going forward.

3. **Should the 2 new genre YAMLs include placeholder credentials (null) or no credential sections?**
   - What we know: `validate-client` iterates all known credential fields. Missing sections are harmless — they resolve to `None` via `_get_nested()` and are not applied.
   - Recommendation: Include all credential sections as `null` for clarity, matching `example-client.yaml` structure.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` (testpaths = ["tests"]) |
| Quick run command | `uv run pytest tests/test_client_config.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CFG-01 | Missing `names_to_remove` raises `ValueError` in `load_client_config()` | unit | `uv run pytest tests/test_client_config.py::TestLoadClientConfig -x` | Partial — new test case needed in existing file |
| CFG-01 | Missing `names_to_remove` raises at process time (not just validate) | unit | `uv run pytest tests/test_client_config.py::TestLoadClientConfig -x` | New test case needed |
| CFG-02 | Client YAML with `voice_persona`, `blog_voice`, `scoring_profile` loads and applies correctly | unit | `uv run pytest tests/test_client_config.py -x` | Partial — voice_persona tested, blog_voice/scoring_profile not |
| CFG-03 | `validate-client` output contains active podcast name from YAML | unit | `uv run pytest tests/test_client_config.py::TestValidateClient -x` | New test case needed |
| CFG-03 | `validate-client` output contains active `names_to_remove` values | unit | `uv run pytest tests/test_client_config.py::TestValidateClient -x` | New test case needed |
| CFG-03 | `validate-client` output contains active `voice_persona` (or "built-in default" label) | unit | `uv run pytest tests/test_client_config.py::TestValidateClient -x` | New test case needed |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_client_config.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_client_config.py` — add `TestLoadClientConfig::test_missing_names_to_remove_raises` (CFG-01)
- [ ] `tests/test_client_config.py` — add `TestLoadClientConfig::test_null_names_to_remove_is_valid` (edge case — field present but null)
- [ ] `tests/test_client_config.py` — add `TestLoadClientConfig::test_empty_names_to_remove_is_valid` (field present as [])
- [ ] `tests/test_client_config.py` — update `test_minimal_config` to include `names_to_remove: []` in MINIMAL_YAML
- [ ] `tests/test_client_config.py` — add `TestValidateClient::test_validate_prints_active_podcast_name`
- [ ] `tests/test_client_config.py` — add `TestValidateClient::test_validate_prints_active_names_to_remove`
- [ ] `tests/test_client_config.py` — add `TestValidateClient::test_validate_prints_voice_persona_or_default`

---

## Sources

### Primary (HIGH confidence)

- Direct inspection: `client_config.py` (full file) — `load_client_config()`, `apply_client_config()`, `activate_client()`, `validate_client()`
- Direct inspection: `config.py` (full file) — `NAMES_TO_REMOVE` default list (lines 141-155), `PODCAST_NAME` default (line 132)
- Direct inspection: `content_editor.py` (lines 1-290) — `VOICE_PERSONA` constant (lines 10-17), `voice_examples` block (lines 262-285), `_build_analysis_prompt()`, voice resolution at line 85
- Direct inspection: `tests/test_client_config.py` (full file) — existing coverage gaps and `test_minimal_config` that will break
- Direct inspection: `clients/fake-problems.yaml` — `names_to_remove` already present; no backward compat issue
- Direct inspection: `clients/example-client.yaml` — template structure for new genre YAMLs
- `.planning/research/PITFALLS.md` — Pitfall 1 (NAMES_TO_REMOVE leakage), Pitfall 2 (voice persona leakage), Pitfall 7 (PODCAST_NAME leakage) — HIGH confidence, code-verified

### Secondary (MEDIUM confidence)

- `.planning/research/ARCHITECTURE.md` — integration point map for config changes

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pure internal code change, no new libraries
- Architecture: HIGH — direct code inspection of all affected files
- Pitfalls: HIGH — all pitfalls confirmed by reading the actual code paths
- Test gaps: HIGH — confirmed by reading `test_client_config.py` directly

**Research date:** 2026-03-28
**Valid until:** Stable — no external dependencies; valid until `client_config.py` or `content_editor.py` are restructured

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CFG-01 | Pipeline uses only per-client config values (no Fake Problems defaults leak to other clients) | Fix: add required-field check for `names_to_remove` in `load_client_config()`; make voice examples conditional in `_build_analysis_prompt()` |
| CFG-02 | User can define genre-specific voice persona, blog voice, and scoring profile per client via YAML | Fix: create `true-crime-client.yaml` and `business-interview-client.yaml` with all three fields populated |
| CFG-03 | User can run validate-client to see active config values after client activation (names, words, voice, scoring) | Fix: add "Active content configuration" print block to `validate_client()` showing live `Config` values |
</phase_requirements>
