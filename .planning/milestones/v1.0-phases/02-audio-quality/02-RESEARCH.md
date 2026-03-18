# Phase 2: Audio Quality - Research

**Researched:** 2026-03-17
**Domain:** Audio processing — EBU R128 LUFS normalization, audio ducking / volume fade censorship
**Confidence:** HIGH

## Summary

Phase 2 replaces the beep-tone censorship in `audio_processor.py` with smooth volume ducking and upgrades the dBFS-based normalization to true EBU R128 two-pass LUFS normalization. Both changes are surgical modifications to existing methods (`apply_censorship` and `normalize_audio`) with no new modules required.

The audio ducking implementation is pure pydub: extract the censored segment, apply a short fade-in and fade-out via `AudioSegment.fade()`, reduce it to near-silence with `apply_gain(-40)`, then splice it back. This is simpler than FFmpeg sidechain compression and produces the "radio-style dip" the user described.

The normalization upgrade uses raw FFmpeg subprocess calls with the `loudnorm` filter in two-pass mode: the first pass captures measurement JSON from stderr (integrated LUFS, LRA, true peak, normalization_type), the second pass applies those measurements for linear normalization. This avoids adding the `ffmpeg-normalize` third-party library — raw subprocess is cleaner given the project already has FFmpeg at `Config.FFMPEG_PATH` and `ffmpeg-python` in requirements. Logging metadata and detecting AGC fallback (normalization_type == "dynamic") are straightforward JSON parsing tasks.

**Primary recommendation:** Implement ducking via pydub `AudioSegment.fade()` + `apply_gain()`. Implement LUFS normalization via two-pass FFmpeg subprocess — no new library dependency needed.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None — user explicitly deferred all implementation decisions to Claude.

### Claude's Discretion
All implementation choices are open:
- **Audio Ducking:** Fade-in/fade-out speed (ms), minimum volume during dip, padding around word boundaries, pydub vs FFmpeg sidechain, whether to remove or keep `assets/beep.wav`
- **LUFS Normalization:** Exact LUFS target value, AGC fallback handling strategy, ffmpeg-normalize library vs raw FFmpeg loudnorm filter, metadata fields to log, whether normalization happens before or after censorship
- **General:** Follow broadcast industry standards; prioritize professional-sounding output over configurability; keep `apply_censorship` API contract

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUDIO-01 | Censored segments use smooth audio ducking (volume fade to silence) instead of beep tones | Pydub `AudioSegment.fade(to_gain, start, duration)` + `apply_gain(-40)` implement the "radio dip" directly; existing 50ms padding kept |
| AUDIO-02 | Episodes normalized to -16 LUFS using ffmpeg-normalize EBU R128 two-pass filter | Raw FFmpeg subprocess two-pass loudnorm; -16 LUFS is the industry-standard podcast target; `normalization_type` JSON field detects linear vs dynamic |
| AUDIO-03 | Normalization metadata logged per episode (measured LUFS, gain applied, LRA) | First-pass JSON contains `input_i`, `input_lra`, `input_tp`; second-pass output JSON contains `output_i`, `output_lra`; gain = output_i - input_i |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydub | 0.25.1 (already installed) | Audio ducking: fade + gain manipulation of AudioSegment | Already used in audio_processor.py; AudioSegment.fade() is the right primitive |
| FFmpeg (subprocess) | C:\ffmpeg\bin\ffmpeg.exe (already configured) | EBU R128 two-pass LUFS normalization | FFmpeg's loudnorm filter is the reference implementation for EBU R128 |
| ffmpeg-python | 0.2.0 (already installed) | Optional: structured FFmpeg subprocess invocation | Already in requirements; can use raw subprocess instead for simplicity |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json (stdlib) | built-in | Parse loudnorm first-pass output from stderr | Always: first-pass FFmpeg writes JSON to stderr |
| subprocess (stdlib) | built-in | Run FFmpeg for two-pass normalization | Always: drives the loudnorm filter |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Raw subprocess + loudnorm | ffmpeg-normalize library | ffmpeg-normalize (v1.37.3) has a clean Python API but adds a dependency; raw subprocess is 30 lines, no new dep |
| pydub volume fade | FFmpeg sidechain compression | Sidechain is more powerful but requires FFmpeg filter graph complexity; pydub is sufficient for censorship ducking |
| pydub volume fade | FFmpeg afade filter on extracted segment | Equivalent result; pydub keeps code consistent with existing AudioProcessor style |

**Installation:**
No new packages required. All dependencies already present in requirements.txt.

---

## Architecture Patterns

### Recommended Project Structure
No new files. Modify only:
```
audio_processor.py        # _apply_duck_segment() private helper + rewrite apply_censorship(), normalize_audio()
tests/test_audio_processor.py  # Update/add tests for ducking and LUFS normalization
```

### Pattern 1: Audio Ducking via Fade + Gain Reduction

**What:** Replace the censored segment (already extracted with 50ms padding) by applying a short fade-in and fade-out at the segment boundaries and reducing the body to near-silence (-40 dB). The segment is then spliced back using the existing `audio[:start_ms] + ducked + audio[end_ms:]` pattern.

**When to use:** Every call to `apply_censorship()`. Replaces the beep-splice approach entirely.

**Fade timing recommendation:**
- Fade-in: 50ms (smooth entry; shorter than the 50ms padding so it completes before the word starts)
- Fade-out: 50ms (symmetrical)
- Body volume: -40 dB (near-silence, clearly intentional; not fully silent, which sounds like a cut)

**Example:**
```python
# Source: pydub API — AudioSegment.fade() and apply_gain()
def _apply_duck_segment(self, audio: AudioSegment, start_ms: int, end_ms: int) -> AudioSegment:
    """Replace segment with smooth volume duck (radio-style dip)."""
    FADE_MS = 50
    DUCK_DB = -40  # Near-silence but not complete cut

    segment = audio[start_ms:end_ms]
    # Reduce body volume
    ducked = segment.apply_gain(DUCK_DB)
    # Smooth edges: short fade-in at start, fade-out at end
    ducked = ducked.fade_in(FADE_MS).fade_out(FADE_MS)
    return audio[:start_ms] + ducked + audio[end_ms:]
```

### Pattern 2: EBU R128 Two-Pass Loudnorm via FFmpeg Subprocess

**What:** Run FFmpeg twice. Pass 1 captures loudness measurements from stderr as JSON (integrated LUFS, LRA, true peak, normalization_type). Pass 2 supplies those measurements back to loudnorm so it can normalize linearly.

**When to use:** Replaces `normalize_audio()` entirely.

**First-pass command:**
```bash
ffmpeg -i input.wav -af loudnorm=I=-16:LRA=11:TP=-1.5:print_format=json -f null -
```

**First-pass stderr JSON fields:**
```json
{
  "input_i": "-23.45",        // Measured integrated loudness (LUFS)
  "input_tp": "-6.23",        // Measured true peak (dBTP)
  "input_lra": "8.10",        // Measured loudness range (LU)
  "input_thresh": "-33.90",   // Threshold
  "target_offset": "0.39",    // Offset correction
  "normalization_type": "dynamic"  // "linear" = good, "dynamic" = AGC fallback — WARN
}
```

**Second-pass command (linear normalization):**
```bash
ffmpeg -i input.wav -af loudnorm=I=-16:LRA=11:TP=-1.5:linear=true:measured_I=-23.45:measured_LRA=8.10:measured_TP=-6.23:measured_thresh=-33.90:offset=0.39 -ar 44100 output.wav
```

**Gain calculation for logging:**
```python
gain_applied_db = float(stats["output_i"]) - float(stats["input_i"])
```

Note: The second pass also emits JSON to stderr. Parse it to get `output_i` and `output_lra` for logging.

**Python skeleton:**
```python
# Source: FFmpeg loudnorm documentation + ffmpeg-normalize issue #245
import subprocess, json, re

def normalize_audio(self, audio_path, output_path=None):
    # Pass 1: measure
    cmd1 = [
        Config.FFMPEG_PATH, "-i", str(audio_path),
        "-af", f"loudnorm=I={Config.LUFS_TARGET}:LRA=11:TP=-1.5:print_format=json",
        "-f", "null", "-"
    ]
    result1 = subprocess.run(cmd1, stderr=subprocess.PIPE, text=True)
    stats = _parse_loudnorm_json(result1.stderr)

    if stats.get("normalization_type") == "dynamic":
        logger.warning(
            "LUFS normalization fell back to AGC (dynamic) mode — "
            "true peak constraint prevented linear normalization. "
            "measured_I=%s LUFS, measured_TP=%s dBTP",
            stats["input_i"], stats["input_tp"]
        )

    # Pass 2: apply
    cmd2 = [
        Config.FFMPEG_PATH, "-i", str(audio_path),
        "-af",
        f"loudnorm=I={Config.LUFS_TARGET}:LRA=11:TP=-1.5:linear=true:"
        f"measured_I={stats['input_i']}:measured_LRA={stats['input_lra']}:"
        f"measured_TP={stats['input_tp']}:measured_thresh={stats['input_thresh']}:"
        f"offset={stats['target_offset']}",
        "-ar", "44100", "-y", str(output_path)
    ]
    result2 = subprocess.run(cmd2, stderr=subprocess.PIPE, text=True)
    stats2 = _parse_loudnorm_json(result2.stderr)

    logger.info(
        "Normalization complete — input: %.1f LUFS, output: %.1f LUFS, "
        "gain: %.1f dB, LRA: %.1f LU",
        float(stats["input_i"]),
        float(stats2.get("output_i", stats["input_i"])),
        float(stats2.get("output_i", stats["input_i"])) - float(stats["input_i"]),
        float(stats2.get("output_lra", stats["input_lra"]))
    )
```

### Pattern 3: Parsing Loudnorm JSON from FFmpeg Stderr

FFmpeg's loudnorm output is embedded in stderr mixed with other log lines. Extract the JSON block:

```python
def _parse_loudnorm_json(stderr_text: str) -> dict:
    """Extract loudnorm measurement JSON from ffmpeg stderr output."""
    # loudnorm JSON block is delimited by { } at the end of stderr
    match = re.search(r'\{[^{}]+\}', stderr_text, re.DOTALL)
    if not match:
        raise ValueError("Could not find loudnorm JSON in ffmpeg output")
    return json.loads(match.group())
```

### Anti-Patterns to Avoid

- **Don't apply gain reduction to the entire file before normalizing:** The pipeline order is censorship (step 4) then normalization (step 4.5). Normalization after censorship ensures LUFS is measured on the final audio (with dips), not pre-censorship audio.
- **Don't use pydub's `audio.dBFS` as a LUFS proxy:** dBFS measures RMS, not psychoacoustic loudness. It gives different readings than LUFS and is not EBU R128 compliant.
- **Don't run FFmpeg without `-y`:** The second pass needs `-y` to overwrite the output file without prompting.
- **Don't remove `assets/beep.wav` from the repo:** Keep it as a documented fallback. The `_get_beep_sound()` method can remain intact; `apply_censorship()` just won't use `self.beep_sound` anymore.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LUFS measurement | Custom audio analysis | FFmpeg loudnorm filter | loudnorm is the reference EBU R128 implementation; rolling your own will produce wrong readings |
| True peak detection | Peak sample analysis | FFmpeg loudnorm TP parameter | True peak ≠ sample peak — requires oversampling to detect intersample peaks |
| Volume fade curve | Custom gain ramp | pydub `AudioSegment.fade()` | pydub's fade is logarithmic (perceptually linear), not linear-amplitude |

**Key insight:** LUFS normalization is deceptively complex — it involves gating, psychoacoustic weighting (K-filter), and integrated measurement. FFmpeg's implementation handles all of this; reproducing it in Python would be wrong and untestable.

---

## Common Pitfalls

### Pitfall 1: loudnorm JSON Not Found in Stderr

**What goes wrong:** `_parse_loudnorm_json()` raises ValueError, normalization fails entirely.
**Why it happens:** FFmpeg writes diagnostics to stderr mixed with progress lines; the JSON block may not be at a predictable offset.
**How to avoid:** Use `re.search(r'\{[^{}]+\}', stderr, re.DOTALL)` which scans the entire stderr string, not just the last N lines.
**Warning signs:** `ValueError: Could not find loudnorm JSON` in logs.

### Pitfall 2: AGC Fallback (normalization_type == "dynamic")

**What goes wrong:** FFmpeg uses dynamic range compression instead of simple linear gain, which can alter the character of the audio.
**Why it happens:** When the measured true peak is near the TP target and the required gain boost would push it over, loudnorm falls back to dynamic mode to prevent clipping.
**How to avoid:** Log a `WARNING` message when this happens — do NOT raise an exception. The audio is still normalized, just via dynamic compression. The requirement is to warn, not fail.
**Warning signs:** `"normalization_type": "dynamic"` in first-pass JSON. Common for already-loud recordings.

### Pitfall 3: Output Path for Normalization — WAV → WAV

**What goes wrong:** FFmpeg writes output in the format it infers from the extension. Passing a `.wav` output path to a WAV input works; passing no extension crashes.
**How to avoid:** Always use `.wav` as the output extension when calling normalize_audio, consistent with the existing pipeline (audio is converted to MP3 later at step 6).

### Pitfall 4: Fade Duration Longer Than Censored Segment

**What goes wrong:** If a censored word is very short (e.g., 100ms), a 50ms fade-in + 50ms fade-out consumes the entire segment, which is fine — pydub handles this gracefully. But if fade_ms is set too large relative to segment duration, the duck will clip.
**How to avoid:** Cap fade duration: `actual_fade = min(FADE_MS, (end_ms - start_ms) // 2)`.

### Pitfall 5: subprocess Hangs if FFmpeg Waits for stdin

**What goes wrong:** FFmpeg subprocess hangs waiting for input (e.g., if `-i` path is wrong and it prompts).
**How to avoid:** Use `stdin=subprocess.DEVNULL` in subprocess.run calls. Also set `check=False` and check returncode manually to provide a useful error message.

### Pitfall 6: Existing Tests for normalize_audio Will Break

**What goes wrong:** The existing `TestNormalizeAudio` tests mock `AudioSegment.from_file` and `apply_gain` — both irrelevant after the FFmpeg subprocess rewrite.
**How to avoid:** Replace these tests with `@patch("subprocess.run")` tests that mock the FFmpeg calls and verify the correct commands are built and JSON is parsed correctly.

---

## Code Examples

### Ducking: Smooth Volume Fade
```python
# Source: pydub API — AudioSegment.fade() + apply_gain()
# Fade timing: 50ms in/out, -40dB body
DUCK_FADE_MS = 50
DUCK_GAIN_DB = -40

segment = audio[start_ms:end_ms]
ducked = segment.apply_gain(DUCK_GAIN_DB)
ducked = ducked.fade_in(DUCK_FADE_MS).fade_out(DUCK_FADE_MS)
audio = audio[:start_ms] + ducked + audio[end_ms:]
```

### Normalization: Logging Metadata
```python
# Log format matches AUDIO-03 requirement: measured LUFS, gain applied, LRA
logger.info(
    "Episode normalization: input=%.1f LUFS, output=%.1f LUFS, "
    "gain=%.1f dB, LRA=%.1f LU",
    measured_lufs,    # from first-pass input_i
    output_lufs,      # from second-pass output_i
    gain_applied_db,  # output_lufs - measured_lufs
    output_lra        # from second-pass output_lra
)
```

### AGC Fallback Warning
```python
# AUDIO-02 requirement: warn when ffmpeg-loudnorm falls back to AGC mode
if stats.get("normalization_type") == "dynamic":
    logger.warning(
        "Normalization fell back to AGC (dynamic) mode — "
        "linear normalization not possible with current true peak "
        "(measured_TP=%s dBTP, target_TP=-1.5 dBTP). "
        "Audio normalized but dynamic compression was applied.",
        stats.get("input_tp", "unknown")
    )
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pydub dBFS target | EBU R128 LUFS (ffmpeg loudnorm) | Industry standardized ~2012, podcast adoption ~2018 | dBFS is not loudness-compensated; LUFS is perceptual and platform-consistent |
| Beep-tone censorship | Volume ducking | Radio broadcast standard, now common in podcast production | Sounds professional/intentional vs. jarring |
| -23 LUFS (broadcast) | -16 LUFS (podcast) | Podcast platforms established ~2019 | Streaming platforms normalize to -14 to -16 LUFS; -16 is safe for all |

**Deprecated/outdated:**
- `audio.dBFS + apply_gain()` as a normalization approach: not LUFS-compliant, not EBU R128, inconsistent across platforms. Replace entirely.

---

## Open Questions

1. **What to do with `assets/beep.wav` after the change**
   - What we know: `_get_beep_sound()` generates or loads the beep; `self.beep_sound` is set in `__init__` and used only in `apply_censorship()`
   - What's unclear: Whether `__init__` should stop loading the beep sound (saving ~1MB on init) or keep it
   - Recommendation: Keep `_get_beep_sound()` and `self.beep_sound` intact for now (backwards compat); simply stop using it in `apply_censorship()`. A TODO comment is sufficient. The file at `assets/beep.wav` is already untracked (Git LFS issue) so no commit change needed.

2. **Second-pass JSON parsing reliability**
   - What we know: FFmpeg second pass also emits a loudnorm JSON block to stderr for the output measurements
   - What's unclear: The exact second-pass JSON field names (`output_i` vs `input_i`) vary between FFmpeg versions
   - Recommendation: Parse both first and second pass stderr. If second-pass JSON is absent, compute gain from target LUFS - measured LUFS (approximation). Log which method was used.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.4.3 |
| Config file | pyproject.toml (existing) |
| Quick run command | `pytest tests/test_audio_processor.py -x` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUDIO-01 | Censored segment is ducked (not beeped) — no beep splice, smooth fade applied | unit | `pytest tests/test_audio_processor.py::TestAudioDucking -x` | ❌ Wave 0 |
| AUDIO-01 | Duck fade-in/out of 50ms applied at segment edges | unit | `pytest tests/test_audio_processor.py::TestAudioDucking::test_duck_applies_fade -x` | ❌ Wave 0 |
| AUDIO-01 | Duck gain reduction of -40dB applied to body | unit | `pytest tests/test_audio_processor.py::TestAudioDucking::test_duck_reduces_volume -x` | ❌ Wave 0 |
| AUDIO-01 | Short segments (< 200ms) still duck correctly without fade overrun | unit | `pytest tests/test_audio_processor.py::TestAudioDucking::test_duck_short_segment -x` | ❌ Wave 0 |
| AUDIO-02 | normalize_audio() calls FFmpeg with loudnorm filter, two passes | unit | `pytest tests/test_audio_processor.py::TestNormalizeAudio -x` | ✅ (needs rewrite) |
| AUDIO-02 | normalize_audio() raises warning (not exception) when normalization_type == "dynamic" | unit | `pytest tests/test_audio_processor.py::TestNormalizeAudio::test_agc_fallback_warns -x` | ❌ Wave 0 |
| AUDIO-02 | normalize_audio() target is -16 LUFS (Config.LUFS_TARGET) | unit | `pytest tests/test_audio_processor.py::TestNormalizeAudio::test_lufs_target -x` | ❌ Wave 0 |
| AUDIO-03 | normalize_audio() logs input LUFS, output LUFS, gain, LRA | unit | `pytest tests/test_audio_processor.py::TestNormalizeAudio::test_logs_metadata -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_audio_processor.py -x`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_audio_processor.py` — `TestNormalizeAudio` class needs full rewrite (existing tests mock pydub, new implementation uses subprocess)
- [ ] `tests/test_audio_processor.py` — `TestAudioDucking` class is new (covers AUDIO-01 ducking behavior)
- No new test files needed — all changes go in the existing test file

---

## Sources

### Primary (HIGH confidence)
- FFmpeg loudnorm filter docs (ayosec.github.io/ffmpeg-filters-docs/7.1) — all filter parameters, linear/dynamic mode, JSON output fields
- pydub GitHub repository (github.com/jiaaro/pydub) — AudioSegment.fade() API, apply_gain() signature
- ffmpeg-normalize GitHub issue #245 (github.com/slhck/ffmpeg-normalize/issues/245) — confirmed `normalization_type` field, AGC fallback root cause (TP constraint violation)
- ffmpeg-normalize PyPI (pypi.org/project/ffmpeg-normalize) — confirmed v1.37.3 latest, Python >= 3.9

### Secondary (MEDIUM confidence)
- wiki.tnonline.net/w/Blog/Audio_normalization_with_FFmpeg — confirmed two-pass command structure, JSON field names (input_i, input_tp, input_lra, input_thresh, target_offset)
- sone.app/blog/podcast-loudness-standards — confirmed -16 LUFS as podcast industry standard (Apple Podcasts target, safe for all platforms)
- audioaudit.io/articles/podcast/loudness-lufs — confirmed -16 LUFS ± 2 LU is acceptable range across Spotify, Apple, YouTube

### Tertiary (LOW confidence)
- Multiple WebSearch results for pydub fade behavior — consistent with official docs, but not directly verified against source

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies already installed; FFmpeg two-pass loudnorm is well-documented and the reference implementation
- Architecture: HIGH — pydub fade+gain pattern is simple and directly supported; FFmpeg subprocess is the standard approach for non-streaming normalization
- Pitfalls: HIGH — subprocess JSON parsing, AGC fallback, fade overrun on short segments all verified from official sources and real issue reports

**Research date:** 2026-03-17
**Valid until:** 2026-09-17 (stable domain — FFmpeg loudnorm filter and pydub API change rarely)
