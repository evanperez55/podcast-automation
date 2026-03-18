# Phase 6: Subtitle Clip Generator - Research

**Researched:** 2026-03-18
**Domain:** FFmpeg ASS subtitle burn-in, WhisperX word timestamps, short-form video upload
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CLIP-01 | Clips rendered as vertical 9:16 video with word-by-word bold captions burned in | pysubs2 ASS generation + FFmpeg `ass=` filter on existing 720x1280 vertical canvas; `subtitle_clip_generator.py` replaces audiogram path in Step 5.5 |
| CLIP-02 | Active word highlighted with accent color as it's spoken | ASS inline `{\c&H...&}` color override tags applied to the active word in each pysubs2 `SSAEvent`; surrounding words rendered in white |
| CLIP-03 | Word timing sourced from WhisperX word-level JSON (not sentence-level SRT) | `transcript_data["words"]` is already persisted to JSON at Step 2 and loaded on resume; `SubtitleGenerator.extract_words_for_clip()` already extracts clip-relative word timestamps from this data |
| CLIP-04 | Subtitle clips uploaded to YouTube Shorts, Instagram Reels, and TikTok | All three uploaders already exist in `uploaders/` and are wired in `pipeline/steps/distribute.py`; `video_clip_paths` on context feeds them; no new upload code needed |
</phase_requirements>

---

## Summary

Phase 6 replaces the audiogram clip generator with a Hormozi-style word-by-word subtitle clip generator. The feature is almost entirely additive: a new `subtitle_clip_generator.py` module slotting into an existing branch point in `pipeline/steps/video.py` (Step 5.5), writing to the same `video_clip_paths` context field that already feeds all three short-form uploaders.

The critical technical work is: (1) consuming WhisperX word-level timestamps already present on `transcript_data["words"]`, (2) normalizing those timestamps to close gaps and resolve overlaps before generating the ASS file, (3) generating ASS subtitle files via `pysubs2` with per-word `{\c}` highlight tags, and (4) invoking FFmpeg with the `ass=` filter on the existing 9:16 black canvas. Upload code requires zero changes — `video_clip_paths` already drives all three short-form uploaders.

Four critical pitfalls are well-understood and must be addressed in order before any clips generate: Windows path colon escaping in FFmpeg filter strings, WhisperX timestamp normalization, font resolution via `fontsdir`, and ASS override tag corruption from naive string construction. All four are mitigated by known patterns. The `pysubs2` library is the correct tool; raw f-string ASS construction must not be used anywhere.

**Primary recommendation:** Build `subtitle_clip_generator.py` as a clean new module; wire it as the first-checked branch in `pipeline/steps/video.py` Step 5.5 under `USE_SUBTITLE_CLIPS=true`; leave audiogram path intact as fallback.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pysubs2 | 1.8.0 | ASS subtitle file generation | Handles ASS encoding quirks, BGR hex color format, and escape rules correctly; used by subtitle toolchain authors; released December 2024 |
| FFmpeg binary | existing (C:\ffmpeg\bin\ffmpeg.exe) | Video encoding + subtitle burn-in via `ass=` filter | Already validated in this project; `ass=` filter is the correct approach for styled timed subtitles |
| ffmpeg-python | 0.2.0 (existing) | FFmpeg subprocess wrapper | Already in project; use `subprocess.run(list_args)` directly for subtitle filter to avoid escaping layers |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Anton font (Google Fonts OFL) | latest | Bold all-caps caption font | Must be committed to `assets/fonts/` before any end-to-end test; prevents libass silent DejaVu substitution |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pysubs2 | Raw f-string ASS construction | Raw construction fails on transcripts with `{`, `}`, apostrophes, numbers — pysubs2 handles all correctly |
| pysubs2 ASS | FFmpeg `drawtext` filter chain | 150+ chained drawtext filters per 60s clip → 5-10x slower, hits filter graph limits; ASS `\k` karaoke handles all timing in one filter call |
| pysubs2 ASS | WhisperX `highlight_words` ASS output | Requires re-running transcription; pysubs2 consumes already-cached word timestamps |
| pysubs2 ASS | SRT + `force_style` override | SRT cannot do per-word timing or per-word color changes; `force_style` is line-level only |

**Installation:**

```bash
pip install pysubs2==1.8.0
```

---

## Architecture Patterns

### Recommended Project Structure

The feature is one new file plus modifications to three existing files:

```
subtitle_clip_generator.py    # NEW — core module
pipeline/steps/video.py       # MODIFIED — add subtitle clip branch in Step 5.5
pipeline/runner.py             # MODIFIED — register SubtitleClipGenerator in _init_components()
assets/fonts/Anton-Regular.ttf  # NEW — font file for libass
```

`pipeline/context.py` requires no changes — `video_clip_paths` already holds the output.

### Pattern 1: Step 5.5 Branch Insertion

**What:** Add a new first-checked branch in `run_video()` before the audiogram check.

**When to use:** `USE_SUBTITLE_CLIPS` env var is `"true"` (default). Audiogram path remains as fallback.

```python
# Source: pipeline/steps/video.py (existing pattern — add before audiogram branch)
subtitle_clip_generator = components.get("subtitle_clip_generator")

if subtitle_clip_generator and subtitle_clip_generator.enabled and clip_paths:
    # New path: word-by-word subtitle clips
    srt_list = [str(s) if s else None for s in srt_paths]
    video_clip_paths = [
        Path(p) for p in subtitle_clip_generator.create_subtitle_clips(
            clip_paths=[str(p) for p in clip_paths],
            srt_paths=srt_list,
            format_type="vertical",
        )
    ]
elif audiogram_generator and audiogram_generator.enabled and clip_paths:
    # Existing audiogram path (unchanged)
    ...
```

The existing `convert_videos` checkpoint key already stores `video_clip_paths`, so checkpoint/resume is unchanged.

### Pattern 2: SubtitleClipGenerator Class Interface

**What:** Mirrors `AudiogramGenerator`'s interface for a clean swap.

```python
# Source: architecture research — derived from AudiogramGenerator interface
class SubtitleClipGenerator:
    def __init__(self):
        self.enabled = os.getenv("USE_SUBTITLE_CLIPS", "true").lower() == "true"
        self.ffmpeg_path = Config.FFMPEG_PATH
        self.logo_path = Config.ASSETS_DIR / "podcast_logo.png"
        self.font_size = int(os.getenv("SUBTITLE_FONT_SIZE", "72"))
        self.font_color = os.getenv("SUBTITLE_FONT_COLOR", "white")
        self.accent_color = os.getenv("SUBTITLE_ACCENT_COLOR", "0x00e0ff")
        self.bg_color = os.getenv("SUBTITLE_BG_COLOR", "0x1a1a2e")
        self.fonts_dir = str(Config.ASSETS_DIR / "fonts")

    def create_subtitle_clips(
        self,
        clip_paths: list[str],
        srt_paths: list[str | None],
        format_type: str = "vertical",
    ) -> list[str]:
        """Batch process clips into MP4s with burned-in word captions."""

    def create_subtitle_clip(
        self,
        audio_path: str,
        srt_path: str | None,
        output_path: str | None = None,
        format_type: str = "vertical",
    ) -> str | None:
        """Create a single subtitle clip. Returns output path or None."""
```

### Pattern 3: Word Timestamp Normalization

**What:** Post-process WhisperX word list before ASS generation to close gaps, resolve overlaps, and interpolate missing timestamps.

**When to use:** Always — called before passing words to pysubs2. This is a prerequisite, not optional.

```python
# Source: pitfalls research — WhisperX PRs #816 and #999
def normalize_word_timestamps(words: list[dict]) -> list[dict]:
    """Close gaps, resolve overlaps, interpolate unaligned words.

    Args:
        words: List of {'word': str, 'start': float, 'end': float}
               Some entries may have start=end=0 (unaligned words).

    Returns:
        Normalized list with no gap > 150ms between consecutive words,
        no overlapping timestamps, and interpolated times for unaligned words.
    """
    if not words:
        return words

    result = [w.copy() for w in words]

    # Pass 1: interpolate missing timestamps from neighbors
    for i, w in enumerate(result):
        if w.get("start", 0) == 0 and w.get("end", 0) == 0:
            # Find nearest aligned neighbors
            prev_end = result[i - 1]["end"] if i > 0 else 0
            next_start = None
            for j in range(i + 1, len(result)):
                if result[j].get("start", 0) > 0:
                    next_start = result[j]["start"]
                    break
            if next_start is None:
                next_start = prev_end + 0.5
            # Distribute proportionally (equal split for simplicity)
            w["start"] = prev_end
            w["end"] = (prev_end + next_start) / 2 if prev_end < next_start else prev_end + 0.1

    # Pass 2: close sub-150ms gaps by extending end time
    for i in range(len(result) - 1):
        gap = result[i + 1]["start"] - result[i]["end"]
        if 0 < gap < 0.15:
            result[i]["end"] = result[i + 1]["start"]

    # Pass 3: resolve overlaps
    for i in range(len(result) - 1):
        if result[i]["end"] > result[i + 1]["start"]:
            result[i]["end"] = result[i + 1]["start"] - 0.001

    return result
```

### Pattern 4: ASS Generation via pysubs2

**What:** Build ASS file with per-word segments. Active word uses accent color; surrounding context (remaining words in group) is white. One `SSAEvent` per word display card.

```python
# Source: pysubs2 readthedocs.io — SSAEvent API
import pysubs2

def _generate_ass_file(
    self,
    clip_words: list[dict],
    output_path: str,
    width: int,
    height: int,
) -> str:
    subs = pysubs2.SSAFile()

    # Define base style — large bold white, black outline
    style = pysubs2.SSAStyle(
        fontname="Anton",
        fontsize=self.font_size,       # 72 default
        bold=True,
        primarycolor=pysubs2.Color(255, 255, 255, 0),   # white
        outlinecolor=pysubs2.Color(0, 0, 0, 0),         # black outline
        backcolor=pysubs2.Color(0, 0, 0, 128),          # semi-transparent shadow
        outline=3,
        shadow=1,
        alignment=2,       # bottom-center
        marginv=80,        # distance from bottom
    )
    subs.styles["Default"] = style

    # Group words into cards of 1-3 words
    cards = _group_into_cards(clip_words, max_words=3)

    for card in cards:
        card_start_ms = int(card[0]["start"] * 1000)
        card_end_ms = int(card[-1]["end"] * 1000)

        for active_idx, active_word in enumerate(card):
            # Event showing the card with active word highlighted
            word_start_ms = int(active_word["start"] * 1000)
            word_end_ms = int(active_word["end"] * 1000)

            # Build text with ASS inline color override for active word
            parts = []
            for j, w in enumerate(card):
                text = w["word"].upper()
                # Escape literal braces in transcript text
                text = text.replace("{", r"\{").replace("}", r"\}")
                if j == active_idx:
                    # Accent color for active word using BGR hex
                    parts.append(f"{{\\c&H{_to_bgr_hex(self.accent_color)}&}}{text}{{\\c&HFFFFFF&}}")
                else:
                    parts.append(text)

            line_text = " ".join(parts)
            event = pysubs2.SSAEvent(
                start=word_start_ms,
                end=word_end_ms,
                text=line_text,
            )
            subs.events.append(event)

    subs.save(output_path)
    return output_path
```

### Pattern 5: FFmpeg Path Escaping (Windows)

**What:** Convert absolute Windows paths to FFmpeg filter-safe form before using in `-vf` strings.

**When to use:** Any time a file path appears inside an FFmpeg filter expression on Windows.

```python
# Source: MSYS2 MINGW-packages issue #11018
def _escape_ffmpeg_filter_path(path: str) -> str:
    """Convert a Windows absolute path to FFmpeg filter-safe form.

    C:\\Users\\foo\\file.ass  ->  C\\:/Users/foo/file.ass

    Must be used for any path inside a -vf filter expression.
    Does NOT apply to top-level -i input arguments.
    """
    # Forward slashes for all directory separators
    path = path.replace("\\", "/")
    # Escape the drive letter colon (FFmpeg filter graph option separator)
    if len(path) >= 2 and path[1] == ":":
        path = path[0] + "\\:" + path[2:]
    return path
```

### Pattern 6: FFmpeg Command for Subtitle Clip

**What:** Vertical canvas with branded background + podcast logo + ASS subtitle burn-in. Audio copied without re-encoding.

```python
# Source: FFmpeg docs + existing audiogram_generator.py patterns
def _build_ffmpeg_command(
    self,
    audio_path: str,
    ass_path: str,
    output_path: str,
    width: int,
    height: int,
) -> list:
    escaped_ass = self._escape_ffmpeg_filter_path(ass_path)
    fonts_dir_escaped = self._escape_ffmpeg_filter_path(self.fonts_dir)
    use_logo = Path(self.logo_path).exists()

    if use_logo:
        vf = (
            f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color={self.bg_color},"
            f"setsar=1,fps=25[bg];"
            f"[bg]subtitles='{escaped_ass}':fontsdir='{fonts_dir_escaped}'[final]"
        )
        input_args = ["-loop", "1", "-i", str(self.logo_path)]
    else:
        vf = (
            f"color=c={self.bg_color}:s={width}x{height}:r=25[bg];"
            f"[bg]subtitles='{escaped_ass}':fontsdir='{fonts_dir_escaped}'[final]"
        )
        input_args = ["-f", "lavfi", "-i", f"color=c={self.bg_color}:s={width}x{height}:r=25"]

    return [
        self.ffmpeg_path, "-y",
        *input_args,
        "-i", str(audio_path),
        "-filter_complex", vf,
        "-map", "[final]",
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-c:a", "copy",          # CRITICAL: never re-encode audio
        "-shortest",
        "-movflags", "+faststart",
        str(output_path),
    ]
```

### Pattern 7: Word Data Source

**What:** Word-level timestamps come from `transcript_data["words"]`, NOT from the SRT files.

The existing `SubtitleGenerator.extract_words_for_clip()` already has the correct logic to extract clip-relative words from `transcript_data`. `SubtitleClipGenerator` should use this method (or reuse its pattern directly).

```python
# Source: subtitle_generator.py — extract_words_for_clip() method
# transcript_data["words"] is already persisted to JSON at Step 2 (transcription.py line 113)
# and loaded on resume from the JSON file. It contains word-level timestamps.
# The 'subtitles' checkpoint key stores ONLY srt_paths — word data lives on ctx.transcript_data.

# Usage in subtitle_clip_generator:
from subtitle_generator import SubtitleGenerator
sub_gen = SubtitleGenerator()
clip_words = sub_gen.extract_words_for_clip(
    transcript_data=transcript_data,
    clip_start=clip_info["start_seconds"],
    clip_end=clip_info["end_seconds"],
)
```

### Anti-Patterns to Avoid

- **Raw f-string ASS construction:** ASS format has encoding-sensitive color fields (`&H00FFFFFF&` BGR hex with alpha prefix) and escape rules. One misformatted field silently corrupts the entire subtitle file. Use `pysubs2` exclusively.
- **Chained `drawtext` filters:** One drawtext node per word for a 60s clip = ~150 filter instantiations. Causes 5-10x slowdown and may crash FFmpeg. Use ASS `\k` or per-word `SSAEvent` instead.
- **SRT as word-level data source:** The `srt_paths` on context are segment-level (5 words/2.5s per line). Word-level data lives on `transcript_data["words"]` only. Do not read SRT files for per-word timing.
- **Re-encoding audio on subtitle burn-in:** FFmpeg re-encodes all streams by default. Must pass `-c:a copy` explicitly. Missing this causes double lossy AAC compression.
- **`shell=True` subprocess:** Changes escaping rules. Use `subprocess.run(list_args)` always for FFmpeg calls in this project.
- **Using same `subtitles` checkpoint key:** The existing `subtitles` key marks SRT generation. The subtitle clip video output is covered by the existing `convert_videos` key. No new checkpoint key needed.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ASS file generation | Manual f-string ASS concatenation | `pysubs2==1.8.0` | ASS format has BGR hex colors, alpha prefix, and escape rules that raw strings get wrong silently |
| Word-to-card grouping | Custom grouping logic from scratch | Extend `SubtitleGenerator.group_words_into_lines()` | Existing logic already handles punctuation breaks, duration limits, empty-word filtering |
| Clip-relative word extraction | Re-implementing time-range filtering | `SubtitleGenerator.extract_words_for_clip()` | Already implemented and tested |
| Windows path escaping | Ad-hoc string replace at call site | Dedicated `_escape_ffmpeg_filter_path()` helper | Must be tested in isolation; inline escaping is never consistent across call sites |

**Key insight:** The hard part of this phase is timestamp normalization and ASS color tagging — not the FFmpeg invocation itself, which closely mirrors the existing audiogram pattern. Build the normalization and ASS generation layers first; FFmpeg wiring is last.

---

## Common Pitfalls

### Pitfall 1: Windows FFmpeg Subtitle Filter Path Parsing

**What goes wrong:** `subtitles='C:\path\file.ass'` passes a `:` to FFmpeg's filter graph parser, which treats it as an option separator. FFmpeg exits 0 but produces a clip with no subtitles.

**Why it happens:** FFmpeg filter graph syntax uses `:` as an option separator inside filter expressions. Windows drive letters contain `:`. This is a known upstream issue (MSYS2 #11018).

**How to avoid:** Implement `_escape_ffmpeg_filter_path()` (see Pattern 5). Test with `C:\Users\evanp\projects\...` paths in unit tests before running end-to-end. Always use `subprocess.run(list_args)` not `shell=True`.

**Warning signs:** Clip renders at correct duration and correct frame size but no text is visible.

### Pitfall 2: WhisperX Word Timestamps Have Gaps, Overlaps, and Missing Words

**What goes wrong:** Consecutive words have 200-500ms gaps (visible flicker), overlapping timestamps (two words highlighted at once), and numbers/contractions with no timestamps at all (words disappear from display).

**Why it happens:** WhisperX wav2vec2 forced alignment fails on characters outside its dictionary (digits, apostrophes, attached punctuation). Gaps/overlaps are known issues partially addressed by merged PRs #816 and #999 but not fully resolved.

**How to avoid:** Implement `normalize_word_timestamps()` (see Pattern 3) and call it before any ASS generation. Test with: back-to-back unaligned words, all words missing, last word missing end time.

**Warning signs:** Subtitle display has visible flicker between words, or certain words (like numbers) disappear from the on-screen text.

### Pitfall 3: libass Silent Font Substitution on Windows

**What goes wrong:** libass cannot find the specified font via fontconfig and silently substitutes DejaVu Sans — a thin, unreadable font. FFmpeg exits 0 with no warning.

**Why it happens:** The Windows FFmpeg build ships a bundled fontconfig that does not scan `C:\Windows\Fonts` reliably. `fontsdir` helps but requires the font file to actually exist there.

**How to avoid:** Commit `Anton-Regular.ttf` (Google Fonts OFL license) to `assets/fonts/`. Pass `fontsdir=assets/fonts` in the subtitle filter. After rendering, check FFmpeg stderr for the string `substituting font` — libass logs this at warning level.

**Warning signs:** Caption text is thin and small instead of large/bold, even though `fontsize=72` and `bold=True` are specified.

### Pitfall 4: ASS Override Tag Corruption from Transcript Text

**What goes wrong:** Podcast transcripts may contain `{` or `}` characters (laughs, JSON fragments, code examples read aloud). ASS interprets these as inline override tag delimiters, producing invisible or garbled subtitles.

**Why it happens:** ASS format uses `{\tag}` syntax for inline styling. Any literal `{` in the event text line is parsed as a tag start.

**How to avoid:** Before inserting any word text into a `pysubs2.SSAEvent`, replace `{` with `\{` and `}` with `\}`. Use `pysubs2` for all ASS construction — never raw f-strings.

**Warning signs:** Subtitles randomly disappear for certain words or entire cards show no text.

### Pitfall 5: Audio Re-encoding Degrades Quality

**What goes wrong:** Subtitle burn-in re-encodes the video stream. Without `-c:a copy`, FFmpeg also re-encodes the audio (a second generation of lossy AAC compression), producing audible artifacts.

**How to avoid:** Always pass `-c:a copy` in the FFmpeg command. Verify with `ffprobe` that the output clip has the same audio codec and bitrate as the input.

### Pitfall 6: Word-Level Data Availability on Resume

**What goes wrong:** The `subtitles` checkpoint key stores SRT paths only. If the pipeline is resumed from the `subtitles` checkpoint, `ctx.transcript_data` is loaded from the JSON file on disk (set by `_run_transcribe()`). This JSON file does include `words` because `transcription.py` saves `words` to the JSON at line 113.

**Current status (CONFIRMED by code inspection):**
- `transcription.py` saves `{"text": ..., "segments": ..., "words": [...]}` to JSON at output_path
- On resume, `runner.py:_run_transcribe()` loads this JSON and sets `ctx.transcript_data` from it
- The `words` key is present in the saved JSON

**Conclusion:** Word-level data IS available on resume. No additional persistence is needed.

---

## Code Examples

### pysubs2 Style Object with Bold Large Font

```python
# Source: pysubs2 readthedocs.io — SSAStyle reference
import pysubs2

style = pysubs2.SSAStyle()
style.fontname = "Anton"
style.fontsize = 72
style.bold = True
style.primarycolor = pysubs2.Color(255, 255, 255, 0)   # white, fully opaque
style.outlinecolor = pysubs2.Color(0, 0, 0, 0)         # black outline
style.outline = 3
style.shadow = 1
style.alignment = 2     # bottom-center (numpad 2)
style.marginv = 80      # pixels from bottom edge
```

### pysubs2 SSAEvent with Accent Word Color Override

```python
# Source: pysubs2 docs — inline ASS tags in event text
# ASS color format: &HBBGGRR& (blue-green-red, no alpha in primary color tag)
# For accent color #e94560 (show red): B=00, G=45, R=e9 → &H004560e9& would be wrong
# Correct: #e94560 is R=e9, G=45, B=60 → BGR = 604560 → &H00604560& — but
# the show's standard accent is the cyan/blue #00e0ff: R=00, G=e0, B=ff → BGR = ffe000
accent_bgr = "ffe000"   # For cyan-ish accent; adjust per brand

event = pysubs2.SSAEvent(
    start=pysubs2.make_time(s=1.5),
    end=pysubs2.make_time(s=2.0),
    text=f"{{\\c&H{accent_bgr}&}}WORD{{\\c&HFFFFFF&}} OTHER WORDS",
)
```

### Card Grouping (1-3 words, Hormozi style)

```python
# Source: derived from SubtitleGenerator.group_words_into_lines() in this codebase
def _group_into_cards(words: list[dict], max_words: int = 3) -> list[list[dict]]:
    """Group normalized words into display cards of max_words each."""
    cards = []
    for i in range(0, len(words), max_words):
        cards.append(words[i : i + max_words])
    return cards
```

### FFmpeg stderr check for font substitution

```python
# Source: libass/libass issue #389
result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
if "substituting font" in result.stderr.lower():
    logger.warning(
        "libass substituted a fallback font — check assets/fonts/ and fontsdir setting"
    )
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SRT + `force_style` for clip subtitles | ASS via pysubs2 for per-word styling | Phase 6 (this phase) | Enables per-word color highlights; eliminates `force_style` limitations |
| Audiogram waveform as clip video | Branded background + burned-in subtitles | Phase 6 (this phase) | Matches Hormozi-style short-form platform expectations |
| Sentence-level SRT (5 words/line) | 1-3 word cards with word-level timing | Phase 6 (this phase) | Word-by-word reading rhythm; tracking caption effect |

**Deprecated/outdated:**

- `force_style` SRT approach for short-form clips: Replaced by ASS. The old approach remains available for the audiogram fallback path — do not remove it.
- Audiogram as the default Step 5.5 path: `USE_SUBTITLE_CLIPS=true` makes subtitle clips the default. Audiogram becomes the `USE_AUDIOGRAM=true` fallback.

---

## Open Questions

1. **Accent color hex value for CLIP-02 highlight**
   - What we know: The show's existing accent color is `0xe94560` (used in audiogram waveform)
   - What's unclear: Whether this red-pink works visually against the dark `0x1a1a2e` background for word highlights, or whether a brighter cyan/yellow is more readable
   - Recommendation: Default `SUBTITLE_ACCENT_COLOR` env var to `0x00e0ff` (bright cyan — high contrast on dark background); document that user can set to `0xe94560` to match show branding. Test both visually on a sample frame.

2. **ASS `ass=` filter vs `subtitles=` filter**
   - What we know: Both filters exist in FFmpeg. `subtitles=` accepts both SRT and ASS. `ass=` accepts only ASS but passes it directly to libass without format conversion. For ASS files generated by pysubs2, `subtitles=` with an `.ass` file is equivalent.
   - Recommendation: Use `subtitles='path.ass':fontsdir='...'` — broader compatibility, already validated in `audiogram_generator.py`.

3. **Card boundary strategy: group by word count vs group by time**
   - What we know: 1-3 words per card is the Hormozi-style standard. Grouping by word count is simpler. Grouping by time (max 1.5s per card) handles slow or fast speech better.
   - Recommendation: Group by word count (max 3 words) as the primary rule, with a time-based break if a single word spans > 2.0s. This matches what top short-form clip channels do.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing, 327 tests passing) |
| Config file | none — pytest discovers tests/ directory |
| Quick run command | `pytest tests/test_subtitle_clip_generator.py -x` |
| Full suite command | `pytest` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLIP-01 | `create_subtitle_clips()` returns MP4 paths for vertical 9:16 clips | unit (mock FFmpeg subprocess) | `pytest tests/test_subtitle_clip_generator.py::TestCreateSubtitleClips -x` | No — Wave 0 |
| CLIP-01 | FFmpeg command includes `-filter_complex` with `subtitles=` and correct dimensions | unit | `pytest tests/test_subtitle_clip_generator.py::TestBuildFfmpegCommand -x` | No — Wave 0 |
| CLIP-02 | ASS file contains accent-color `{\c}` override tag for active word | unit | `pytest tests/test_subtitle_clip_generator.py::TestGenerateAssFile -x` | No — Wave 0 |
| CLIP-02 | Surrounding words in same card are rendered white (no color override) | unit | `pytest tests/test_subtitle_clip_generator.py::TestGenerateAssFile -x` | No — Wave 0 |
| CLIP-03 | `normalize_word_timestamps()` closes gaps < 150ms | unit | `pytest tests/test_subtitle_clip_generator.py::TestNormalizeWordTimestamps -x` | No — Wave 0 |
| CLIP-03 | `normalize_word_timestamps()` resolves overlapping timestamps | unit | `pytest tests/test_subtitle_clip_generator.py::TestNormalizeWordTimestamps -x` | No — Wave 0 |
| CLIP-03 | `normalize_word_timestamps()` interpolates words with missing timestamps | unit | `pytest tests/test_subtitle_clip_generator.py::TestNormalizeWordTimestamps -x` | No — Wave 0 |
| CLIP-03 | `_escape_ffmpeg_filter_path()` converts `C:\path\file.ass` to `C\:/path/file.ass` | unit | `pytest tests/test_subtitle_clip_generator.py::TestEscapeFilterPath -x` | No — Wave 0 |
| CLIP-04 | `video_clip_paths` populated after subtitle clip generation (feed to existing uploaders) | integration (mock uploader) | `pytest tests/test_pipeline_refactor.py -x -k subtitle` | Partial — need new test |
| CLIP-04 | `dry_run()` prints subtitle clip step log entry | unit | `pytest tests/test_pipeline_refactor.py -x -k dry_run` | Partial — need new assertion |

### Sampling Rate

- **Per task commit:** `pytest tests/test_subtitle_clip_generator.py -x`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_subtitle_clip_generator.py` — covers all CLIP-01, CLIP-02, CLIP-03 unit tests listed above
- [ ] `assets/fonts/Anton-Regular.ttf` — font file for libass; download from Google Fonts and commit before end-to-end test

*(Existing test infrastructure: pytest is installed, 327 tests pass, `tests/test_audiogram_generator.py` provides the model for the new test file)*

---

## Sources

### Primary (HIGH confidence)

- pysubs2 readthedocs.io — SSAStyle, SSAEvent, SSAFile API; Color class; `make_time()` helper
- FFmpeg Filters Documentation (ffmpeg.org/ffmpeg-filters.html) — `subtitles` filter, `fontsdir` option, `ass=` filter
- MSYS2 MINGW-packages issue #11018 — Windows subtitle path colon bug confirmed
- libass/libass issue #389 — fontconfig Windows font substitution confirmed
- WhisperX PRs #816 and #999 (merged) — overlap/gap fixes in word timestamps
- WhisperX issue #1247 — word timestamp inaccuracy confirmed by maintainer
- Project codebase direct inspection: `pipeline/steps/video.py`, `pipeline/runner.py`, `pipeline/context.py`, `audiogram_generator.py`, `subtitle_generator.py`, `transcription.py`

### Secondary (MEDIUM confidence)

- Hormozi-style captions guide (Riverside) — table stakes features for short-form clips
- Word-by-word captions with Python (AngelFolio) — WhisperX to ASS per-word pattern
- FFmpeg ASS subtitle guide (Bannerbear) — burn-in filter patterns
- Burned-in subtitles quality guide (md-subs.com) — rendering quality considerations

### Tertiary (LOW confidence)

- None for Phase 6 scope. All critical claims are verified by primary sources or direct code inspection.

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — pysubs2 1.8.0 confirmed on PyPI December 2024; FFmpeg is existing validated dep; no new libraries needed for upload (all uploaders already wired)
- Architecture: HIGH — derived from direct code inspection of `pipeline/steps/video.py`, `pipeline/runner.py`, and `audiogram_generator.py`; integration pattern mirrors existing audiogram branch
- Pitfalls: HIGH — Windows FFmpeg path bug and libass font substitution confirmed by upstream issue trackers; WhisperX timestamp issues confirmed by maintainer and merged PRs; audio re-encoding is basic FFmpeg behavior

**Research date:** 2026-03-18
**Valid until:** 2026-06-18 (pysubs2 and FFmpeg are stable; WhisperX timestamp behavior is slow-moving)
