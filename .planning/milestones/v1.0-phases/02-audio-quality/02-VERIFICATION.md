---
phase: 02-audio-quality
verified: 2026-03-16T22:00:00Z
status: passed
score: 12/12 must-haves verified
re_verification: false
---

# Phase 2: Audio Quality Verification Report

**Phase Goal:** Episodes sound professionally mastered — censored moments are smooth volume dips and loudness meets broadcast platform standards
**Verified:** 2026-03-16T22:00:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Censored words replaced by smooth volume fade to near-silence (no audible beep) | VERIFIED | `_apply_duck_segment()` applies -40 dB gain + 50 ms fade-in/out; `apply_censorship()` calls it per timestamp; beep_sound never accessed in loop |
| 2 | A processed episode measures between -15 and -17 LUFS on any reference loudness meter | HUMAN NEEDED | `normalize_audio()` targets `Config.LUFS_TARGET=-16` via two-pass FFmpeg loudnorm; actual audio output requires a real FFmpeg run to meter |
| 3 | Pipeline log records measured LUFS, gain applied, and LRA values after normalization | VERIFIED | `logger.info("Normalization complete — input: %.1f LUFS, output: %.1f LUFS, gain: %.1f dB, LRA: %.1f LU", ...)` at audio_processor.py line 195 |
| 4 | Normalization raises a warning if ffmpeg-loudnorm falls back to AGC mode | VERIFIED | `if stats.get("normalization_type") == "dynamic": logger.warning(...)` at line 145; test `test_normalize_warns_on_agc_fallback` passes GREEN |

**Score:** 3/4 truths fully verified programmatically; 1 needs human (loudness meter on real output)

---

### Required Artifacts (02-02-PLAN and 02-03-PLAN must-haves)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `audio_processor.py` | `_apply_duck_segment()` private method | VERIFIED | Lines 65–83; `DUCK_GAIN_DB=-40`, `FADE_MS=50`, fade-cap `min(FADE_MS, segment_len // 2)` |
| `audio_processor.py` | `apply_censorship()` uses duck, not beep | VERIFIED | Line 268: `audio = self._apply_duck_segment(audio, start_ms, end_ms)`; no beep reference in loop |
| `audio_processor.py` | `normalize_audio()` two-pass FFmpeg loudnorm | VERIFIED | Lines 92–204; two `subprocess.run` calls, pass-1 with `print_format=json`, pass-2 with `linear=true` and measured values |
| `audio_processor.py` | `_parse_loudnorm_json()` module-level helper | VERIFIED | Lines 20–32; `re.search(r'\{[^{}]+\}', stderr_text, re.DOTALL)` + `json.loads` |
| `tests/test_audio_processor.py` | `TestAudioDucking` class (5 tests) | VERIFIED | Lines 433–614; 5 test methods, all PASSED GREEN (32/32 total) |
| `tests/test_audio_processor.py` | `TestNormalizeAudio` class (7 tests) | VERIFIED | Lines 617–833; 7 test methods, all PASSED GREEN |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `apply_censorship` | `_apply_duck_segment` | called per censor timestamp in loop | WIRED | Line 268: `audio = self._apply_duck_segment(audio, start_ms, end_ms)` |
| `_apply_duck_segment` | `pydub AudioSegment.apply_gain + fade_in + fade_out` | pydub API calls on extracted segment | WIRED | Lines 81–82: `segment.apply_gain(DUCK_GAIN_DB)`, `.fade_in(actual_fade).fade_out(actual_fade)` |
| `normalize_audio` | `subprocess.run` (pass 1) | `Config.FFMPEG_PATH + loudnorm filter + print_format=json` | WIRED | Lines 129–135: `subprocess.run(pass1_cmd, stderr=PIPE, stdin=DEVNULL, text=True, check=False)` |
| `normalize_audio` | `subprocess.run` (pass 2) | `linear=true` + measured values from pass-1 JSON | WIRED | Lines 171–177: pass2_cmd contains `linear=true:measured_I={...}:measured_LRA={...}` |
| `_parse_loudnorm_json` (module) | `re.search` | regex scan of stderr for JSON block | WIRED | Line 26: `match = re.search(r"\{[^{}]+\}", stderr_text, re.DOTALL)` |
| `normalize_audio` | `_parse_loudnorm_json` | method delegates to module-level function | WIRED | Line 142: `stats = self._parse_loudnorm_json(result1.stderr)` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| AUDIO-01 | 02-02-PLAN | Censored segments use smooth audio ducking instead of beep tones | SATISFIED | `_apply_duck_segment()` implemented; 5 TestAudioDucking tests pass GREEN; `apply_censorship()` loop confirmed beep-free |
| AUDIO-02 | 02-03-PLAN | Episodes normalized to -16 LUFS using FFmpeg EBU R128 two-pass filter | SATISFIED | `normalize_audio()` runs two-pass `loudnorm=I=-16:LRA=11:TP=-1.5`; 6 TestNormalizeAudio subprocess tests pass |
| AUDIO-03 | 02-03-PLAN | Normalization metadata logged per episode (LUFS, gain, LRA) | SATISFIED | `logger.info("Normalization complete — input: %.1f LUFS, output: %.1f LUFS, gain: %.1f dB, LRA: %.1f LU", ...)` verified |

All three AUDIO requirements are marked `[x]` in REQUIREMENTS.md and map to Phase 2 in the traceability table. No orphaned requirements found.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `audio_processor.py` | 42–43 | `# TODO: beep_sound kept for backward compat` | Info | Intentional per plan spec; `beep_sound` preserved for backward compatibility, not a stub |

No blockers or warnings. The single TODO is explicitly required by 02-02-PLAN: "Keep `self.beep_sound = self._get_beep_sound()` in `__init__`... Add a TODO comment."

---

### Human Verification Required

#### 1. Loudness meter check on real processed episode

**Test:** Run `python main.py ep<N> --auto-approve` against an actual episode file. After the normalize step, measure the output WAV with a LUFS reference meter (e.g., ffmpeg's `ebur128` filter: `ffmpeg -i normalized.wav -af ebur128 -f null -`).
**Expected:** Integrated loudness reads between -15.0 and -17.0 LUFS.
**Why human:** The two-pass subprocess calls require a real FFmpeg installation with an actual audio file; the test suite mocks `subprocess.run` and cannot validate the acoustic output.

#### 2. Audible smoothness of duck censorship

**Test:** Play a censored episode at a censored word. The transition into and out of the ducked segment should be inaudible — no click, pop, or abrupt cut.
**Expected:** Smooth fade-in and fade-out, volume drops to near-silence (-40 dB) during the censored word, then returns naturally.
**Why human:** The fade parameters (50 ms, -40 dB) are correct per the plan, but perceptual smoothness on real audio requires listening.

---

### Test Suite Results

```
32 passed, 1 warning in 0.53s

TestAudioProcessor         12 tests — all GREEN
TestCensoringTimestampAccuracy  5 tests — all GREEN
TestAudioDucking            5 tests — all GREEN
TestNormalizeAudio          7 tests — all GREEN
TestClipDurationValidation  3 tests — all GREEN
```

Commits verified in git history:
- `397d123` — test(02-01): RED scaffold for audio ducking + LUFS normalization
- `93bce34` — feat(02-audio-quality-02): replace beep censorship with smooth audio ducking
- `b6e7d7e` — feat(02-03): rewrite normalize_audio() with two-pass FFmpeg loudnorm

---

### Summary

Phase 2 goal is achieved. All three production code requirements (AUDIO-01, AUDIO-02, AUDIO-03) are implemented, tested, and verified against the actual codebase:

- **AUDIO-01**: `_apply_duck_segment()` replaces beep splicing with -40 dB gain reduction and 50 ms fades. The loop in `apply_censorship()` has no reference to `beep_sound`. Five dedicated tests prove the behavior.
- **AUDIO-02**: `normalize_audio()` runs two FFmpeg `loudnorm` subprocess calls targeting `-16 LUFS / LRA 11 / TP -1.5`. AGC fallback emits `logger.warning()` without raising. Seven tests cover all subprocess behaviors.
- **AUDIO-03**: The completion log line records `input LUFS`, `output LUFS`, `gain dB`, and `LRA LU` on every normalization run.

The only open item is a human loudness meter check on a real episode to confirm the -16 LUFS target is achieved end-to-end with the actual FFmpeg installation.

---

_Verified: 2026-03-16T22:00:00Z_
_Verifier: Claude (gsd-verifier)_
