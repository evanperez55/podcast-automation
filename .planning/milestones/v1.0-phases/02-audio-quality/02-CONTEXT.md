# Phase 2: Audio Quality - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace beep censorship with smooth audio ducking and upgrade normalization from dBFS approximation to true EBU R128 LUFS. Scope: modify `audio_processor.py` censorship and normalization methods, add `ffmpeg-normalize` dependency, log normalization metadata. No new features beyond audio quality improvements.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
User explicitly deferred all implementation decisions to Claude. The following areas are open for Claude to decide based on professional audio standards and research:

**Audio Ducking:**
- Fade-in/fade-out speed (milliseconds) for volume dips
- Minimum volume level during ducked segments (full silence vs. faint original audio)
- Padding around censored word boundaries (how much extra to duck)
- Whether to use pydub volume manipulation or FFmpeg sidechain compression
- Whether the beep sound asset (`assets/beep.wav`) should be removed or kept as fallback

**LUFS Normalization:**
- Exact LUFS target value (current Config.LUFS_TARGET is -16)
- How to handle ffmpeg-loudnorm AGC fallback (warning, re-process, or accept)
- Whether to use `ffmpeg-normalize` library or raw FFmpeg loudnorm filter
- What metadata to log (measured LUFS, gain applied, LRA, true peak)
- Whether normalization should happen before or after censorship in the pipeline

**General approach:**
- Follow broadcast industry standards for podcast audio
- Prioritize professional-sounding output over configurability
- Keep the existing `apply_censorship` API contract (same input/output, just different processing)

</decisions>

<specifics>
## Specific Ideas

- User described wanting "smooth volume dip, like radio" — this means a gradual fade, not an abrupt cut
- The show is edgy comedy — the censorship should feel intentional and professional, not accidental
- Current beep censorship at ep29 censored "Dom" (0.70s) and "retarded" (0.74s) — these are typical durations

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `audio_processor.py:apply_censorship()` — Current beep-splice implementation at line 96. Accepts `censor_timestamps` list with `start_seconds`/`end_seconds` keys. This is the method to modify.
- `audio_processor.py:normalize_audio()` — Current dBFS normalization at line 47. Uses `Config.LUFS_TARGET` (-16). This needs full replacement with ffmpeg-loudnorm.
- `Config.FFMPEG_PATH` — FFmpeg binary path already configured at `C:\ffmpeg\bin\ffmpeg.exe`
- `Config.LUFS_TARGET` — Already exists with default -16
- `assets/beep.wav` — Current beep sound file, may become unused

### Established Patterns
- `audio_processor.py` uses pydub `AudioSegment` for all audio manipulation
- Censorship adds 50ms padding on each side of word boundaries (line 142-143)
- Tests in `tests/test_audio_processor.py` mock audio operations

### Integration Points
- `main.py:process_episode()` calls `audio_processor.apply_censorship()` then `normalize_audio()` in sequence
- Normalization happens after censorship in the pipeline (step 4 → step 4.5)
- Output goes to `output/ep_N/` directory as WAV, later converted to MP3

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-audio-quality*
*Context gathered: 2026-03-17*
