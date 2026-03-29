# Phase 18: Demo Packaging - Research

**Researched:** 2026-03-28
**Domain:** Demo assembly — copying and presenting existing pipeline output as a prospect-ready package
**Confidence:** HIGH — based on direct inspection of all output artifacts, pipeline source, and existing utility patterns

---

<user_constraints>
## User Constraints (from CONTEXT.md / STATE.md)

### Locked Decisions
- No PDF output. WeasyPrint requires GTK+/MSYS2 on Windows 11; wkhtmltopdf archived Jan 2023. Self-contained HTML is the output format.
- Demo packager is a read-only view of existing pipeline output — it does NOT regenerate content.
- Demo folder lives at `demo/<client>/<episode>/`, NOT inside `output/` (which is ephemeral pipeline state).
- Before/after audio requires a raw audio snapshot BEFORE the censor step. The pipeline currently does NOT save this. A snapshot must be added to `pipeline/steps/audio.py` at the top of Step 4.
- DEMO.md is a markdown file — metrics extracted from `{stem}_{timestamp}_analysis.json` and the normalization log.

### Claude's Discretion
- HTML summary template design (self-contained, base64 thumbnail, no external assets)
- LUFS extraction strategy — the pipeline logs normalization metrics but does not persist them to a file; must decide whether to re-measure from the processed audio file or parse the pipeline log
- Clip selection for before/after: which `best_clips[0]` timestamp to use as the 60-second window

### Deferred Ideas (OUT OF SCOPE)
- PDF generation (WeasyPrint/wkhtmltopdf)
- Demo video walkthrough (screen recording)
- White-label output
- Client Dropbox folder handoff automation
- Proposal email generator
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DEMO-01 | User can run `package-demo` command to assemble all pipeline output into a presentable demo folder | DemoPackager class reads existing output artifacts; new CLI command in main.py; directory structure confirmed from artifact inspection |
| DEMO-02 | Demo includes a before/after audio comparison clip (raw vs processed, 60 seconds) | Requires pipeline change: snapshot raw audio at start of Step 4 in `pipeline/steps/audio.py`; FFmpeg `atrim` command for 60-second extraction; confirmed no raw snapshot currently exists |
| DEMO-03 | Demo includes a DEMO.md narrative per client (what was automated, time saved, cost, metrics) | LUFS metrics available from log; clip scores and episode summary available in analysis JSON; compliance report available as JSON |
</phase_requirements>

---

## Summary

Phase 18 is a packaging and assembly task, not a generation task. Real output already exists at `output/true-crime-client/ep_399/` and `output/business-interview-client/ep_18/`. The `DemoPackager` class reads those artifacts and copies/assembles them into `demo/<client>/<episode>/`. The only content generation is the HTML summary page (via jinja2, already in the project) and the DEMO.md (from analysis JSON + log data).

The one non-trivial implementation task is DEMO-02: before/after audio. The pipeline currently produces only a processed (`_censored.wav`) file. To create a before/after comparison, a 60-second raw audio snapshot must be saved at the start of Step 4 in `pipeline/steps/audio.py`, before `apply_censorship()` runs. The snapshot is a simple FFmpeg `atrim` + `asetpts` filter — no pydub load required for a large file, just a subprocess call.

LUFS metrics are logged by `normalize_audio()` but not persisted to a file. The simplest extraction strategy is to re-measure the processed MP3/WAV at package time using a single-pass `ffmpeg -i {file} -af loudnorm=print_format=json -f null -` call, which takes under 5 seconds for a 60-minute episode.

**Primary recommendation:** Build `demo_packager.py` as a standalone module with `DemoPackager.package_demo(client_name, episode_id)`. Add the raw audio snapshot to `pipeline/steps/audio.py`. Add `package-demo` command to `main.py`. Three tasks, linear dependency: snapshot first, packager second, CLI third.

---

## Artifact Inventory (Confirmed from Direct Inspection)

### What Exists After a Full Pipeline Run

The following artifacts exist and are locatable from the pipeline state JSON at `output/<client>/.pipeline_state/<ep_id>.json`:

| Artifact | Location | How to Find |
|----------|----------|-------------|
| Analysis JSON | `output/<client>/<ep_id>/{stem}_{ts}_analysis.json` | `pipeline_state["completed_steps"]["analyze"]["outputs"]["analysis_path"]` |
| Processed MP3 | `output/<client>/<ep_id>/{stem}_{ts}_censored.mp3` | `pipeline_state["completed_steps"]["convert_mp3"]["outputs"]["mp3_path"]` |
| Processed WAV | `output/<client>/<ep_id>/{stem}_{ts}_censored.wav` | `pipeline_state["completed_steps"]["normalize"]["outputs"]["normalized_audio"]` |
| Episode MP4 | `output/<client>/<ep_id>/{stem}_{ts}_episode.mp4` | `pipeline_state["completed_steps"]["convert_videos"]["outputs"]["full_episode_video_path"]` |
| Thumbnail PNG | `output/<client>/<ep_id>/{stem}_{ts}_thumbnail.png` | Glob `{ep_dir}/*_thumbnail.png` |
| Show notes TXT | `output/<client>/<ep_id>/{stem}_{ts}_show_notes.txt` | Glob `{ep_dir}/*_show_notes.txt` (latest) |
| Compliance JSON | `output/<client>/<ep_id>/compliance_report_{ep}_{ts}.json` | Glob `{ep_dir}/compliance_report_*.json` (latest) |
| Clip MP4s | `clips/<client>/<ep_id>/{stem}_censored_clip_0N_subtitle.mp4` | `pipeline_state["completed_steps"]["convert_videos"]["outputs"]["video_clip_paths"]` |

### What Does NOT Exist (Gaps to Fill)

| Gap | Why Missing | What Phase 18 Must Do |
|-----|-------------|----------------------|
| Raw audio snapshot (pre-censor 60s) | Pipeline never saves raw audio before Step 4 | Add snapshot to `pipeline/steps/audio.py` at start of Step 4 |
| Blog post HTML | `blog_generator.py` disabled for these clients (no `BLOG_ENABLED=true` in their YAMLs); `blog_post_path` absent from pipeline state | DemoPackager must gracefully skip blog post when absent; no fallback regeneration |
| LUFS metrics as a file | `normalize_audio()` only logs to `podcast_automation.log`; no JSON sidecar | Re-measure from processed audio at package time (single FFmpeg pass) |

**Important:** Neither `ep_399` nor `ep_18` have a blog post. The business-interview-client pipeline state JSON does not exist at all (pipeline did not reach completion — only analysis, censor, normalize steps completed; clips and videos were not run). The demo packager must handle partial runs gracefully.

---

## Standard Stack

### Core (All Already in Project)

| Library | Version | Purpose | How Used |
|---------|---------|---------|---------|
| `jinja2` | >=3.0.0 | HTML summary template rendering | `Environment(loader=FileSystemLoader(...))` — same pattern as `episode_webpage_generator.py` |
| `shutil` | stdlib | File copying into demo folder | `shutil.copy2()` for clips, thumbnail, MP3 |
| `zipfile` | stdlib | Optional ZIP archive of demo folder | `zipfile.ZipFile` for bundling |
| `subprocess` | stdlib | FFmpeg calls for raw snapshot + LUFS measurement | Already used throughout `audio_processor.py` |
| `json` | stdlib | Read analysis JSON and compliance JSON | Already used throughout pipeline |
| `pathlib.Path` | stdlib | All path manipulation | Project-wide convention |

### No New Packages Required

The v1.4 stack decision is confirmed: `feedparser` was the only new package for RSS ingest. Demo packaging needs nothing new.

---

## Architecture Patterns

### Recommended Module Structure

```
podcast-automation/
├── demo_packager.py              # NEW: DemoPackager class
├── pipeline/
│   └── steps/
│       └── audio.py             # MODIFIED: add raw snapshot at start of Step 4
├── main.py                      # MODIFIED: add package-demo command
├── templates/
│   └── demo_summary.html.j2     # NEW: jinja2 template for summary page
└── demo/
    └── <client>/
        └── <ep_id>/             # Generated output (gitignored)
```

### Pattern 1: DemoPackager as a Read-Only Assembler

**What:** `DemoPackager.package_demo(client_name, episode_id)` reads existing artifacts from `output/<client>/<ep_id>/` and `clips/<client>/<ep_id>/`, then copies them into `demo/<client>/<ep_id>/`. It never calls any pipeline component. The only new content it generates is `summary.html` and `DEMO.md`.

**Artifact discovery strategy:** Read the pipeline state JSON first. Use its checkpoint outputs to locate all artifacts with exact paths. Fall back to glob patterns when state is absent or incomplete (e.g., business-interview-client has no pipeline state file).

```python
# Source: project pattern — pipeline_state.py
from pipeline_state import PipelineState

state = PipelineState(client_name, episode_id)
if state.is_step_completed("analyze"):
    analysis_path = state.get_step_outputs("analyze")["analysis_path"]
else:
    # Fallback: glob the episode dir
    analysis_path = next(ep_dir.glob("*_analysis.json"), None)
```

**Demo folder structure:**
```
demo/<client>/<ep_id>/
    DEMO.md                    # Automation narrative + metrics
    summary.html               # Self-contained HTML (base64 thumbnail)
    processed_audio.mp3        # Copy of censored MP3
    clips/
        clip_01.mp4            # Copy of subtitle clip
        clip_02.mp4
        clip_03.mp4
    thumbnail.png              # Copy of episode thumbnail
    show_notes.txt             # Copy of show_notes.txt
    captions.txt               # Extracted from analysis.social_captions
    before_after/
        raw_60s.wav            # 60-second raw segment (pre-censor)
        processed_60s.wav      # Same timestamp, from processed WAV
    compliance_report.json     # Copy of latest compliance report JSON
```

### Pattern 2: Raw Audio Snapshot in pipeline/steps/audio.py

**What:** At the start of Step 4 (before `apply_censorship()` runs), save a 60-second clip from the raw audio using FFmpeg's `atrim` filter. The snapshot timestamp is derived from `best_clips[0]["start_seconds"]` in the analysis dict (first recommended clip). Store at `{ep_dir}/{stem}_{ts}_raw_snapshot.wav`.

**Why FFmpeg subprocess, not pydub:** The raw audio file is 1GB+ for a 90-minute episode (uncompressed WAV). Loading it into pydub (`AudioSegment.from_file`) copies the entire file into memory. A direct FFmpeg subprocess call using `atrim` extracts 60 seconds without loading the whole file.

**Implementation in pipeline/steps/audio.py:**
```python
# Add before the existing Step 4 block
# Source: FFmpeg atrim filter documentation
snapshot_start = analysis.get("best_clips", [{}])[0].get("start_seconds", 60.0)
snapshot_end = snapshot_start + 60.0
raw_snapshot_path = episode_output_dir / f"{audio_file.stem}_{timestamp}_raw_snapshot.wav"

if not (state and state.is_step_completed("censor")):
    cmd = [
        Config.FFMPEG_PATH, "-i", str(audio_file),
        "-ss", str(snapshot_start), "-to", str(snapshot_end),
        "-acodec", "pcm_s16le", "-y", str(raw_snapshot_path),
    ]
    subprocess.run(cmd, stderr=subprocess.DEVNULL, check=True)
    logger.info("Raw snapshot saved: %s", raw_snapshot_path.name)

ctx.raw_snapshot_path = raw_snapshot_path
```

**NOTE:** Snapshot is saved unconditionally (not gated by `censor` checkpoint completion check) because it must be produced from the original audio. If censor step has already run in a resumed pipeline run, skip the snapshot too — there is no original audio available once the pipeline has moved past that point.

**Checkpoint key:** The raw snapshot path should be stored in the `censor` checkpoint outputs so DemoPackager can find it via pipeline state.

### Pattern 3: LUFS Measurement at Package Time

**What:** `normalize_audio()` logs LUFS values but does not persist them. At package time, re-measure the processed MP3 using a single FFmpeg loudnorm pass (pass 1 only — measurement, no output file).

**Why re-measure vs. parse the log:** Log parsing is brittle (log file is shared across all clients and runs, 60K+ lines). A single FFmpeg measurement pass takes 2-5 seconds and returns exact values in structured JSON embedded in stderr.

```python
# Re-use the existing _parse_loudnorm_json module function from audio_processor.py
from audio_processor import _parse_loudnorm_json

def _measure_lufs(audio_path: Path) -> dict:
    """Measure LUFS via FFmpeg loudnorm pass 1. Returns stats dict."""
    cmd = [
        Config.FFMPEG_PATH, "-i", str(audio_path),
        "-af", "loudnorm=I=-16:LRA=11:TP=-1.5:print_format=json",
        "-f", "null", "-",
    ]
    result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True, check=False)
    return _parse_loudnorm_json(result.stderr)
```

### Pattern 4: Jinja2 HTML Summary (Self-Contained)

**What:** A single HTML file that embeds the thumbnail as a base64 data URI so the file is shareable without a web server or accompanying assets folder.

**Existing pattern from episode_webpage_generator.py:**
```python
from jinja2 import Environment, FileSystemLoader

templates_dir = Path(__file__).parent / "templates"
env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=True)
template = env.get_template("demo_summary.html.j2")
html = template.render(
    client_name=client_name,
    episode_title=analysis["episode_title"],
    thumbnail_b64=...,
    clips=...,
    social_captions=analysis["social_captions"],
    show_notes=analysis["show_notes"],
    chapters=analysis.get("chapters", []),
    lufs_input=lufs_stats["input_i"],
    lufs_output=lufs_stats.get("output_i", "-16"),
    compliance_critical=compliance_data.get("critical", False),
    compliance_count=len(compliance_data.get("flagged", [])),
)
```

**Base64 thumbnail embedding:**
```python
import base64
with open(thumbnail_path, "rb") as f:
    thumbnail_b64 = base64.b64encode(f.read()).decode()
# In template: <img src="data:image/png;base64,{{ thumbnail_b64 }}">
```

### Pattern 5: CLI Command in main.py

**What:** New `package-demo` command dispatched from `_handle_client_command()` in main.py. Follows existing pattern for client-scoped commands.

```python
elif cmd == "package-demo":
    from demo_packager import DemoPackager
    n = name or (sys.argv[2] if len(sys.argv) > 2 else None)
    ep = sys.argv[3] if len(sys.argv) > 3 else None
    if not n:
        print("Usage: uv run main.py package-demo <client> [ep_N]")
        return True
    DemoPackager().package_demo(n, ep)
```

### Anti-Patterns to Avoid

- **Re-generating content in the packager:** DemoPackager never calls OpenAI, Whisper, or BlogPostGenerator. If show notes are missing, they're missing in the demo. Fix the pipeline config and re-run; don't paper over it in packaging.
- **Using pydub to load the full raw WAV for snapshot:** File is 1GB+. Use FFmpeg subprocess with `atrim`. The `extract_clip()` method in `AudioProcessor` uses pydub — do not reuse it for the raw snapshot.
- **Storing demo output inside `output/`:** `output/` is ephemeral pipeline working state. Demo output belongs in `demo/`.
- **Blocking on missing artifacts:** If thumbnail or blog post is absent (business-interview-client has no full pipeline run), log a warning and continue. The packager is best-effort.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML rendering with variables | f-string concatenation | jinja2 `Template.render()` | Already in project, handles escaping, readable template |
| File copying | Open/write loops | `shutil.copy2()` | Preserves metadata, one line |
| ZIP creation | Custom archive logic | `shutil.make_archive()` or `zipfile.ZipFile` | Stdlib, well-tested |
| LUFS extraction | Log file parsing | FFmpeg loudnorm pass 1 subprocess | Structured JSON output, no brittle regex on log |
| 60-second audio extraction | pydub `AudioSegment.from_file()` + slice | FFmpeg `atrim` via subprocess | No full-file memory load for 1GB+ raw WAV |

---

## Common Pitfalls

### Pitfall 1: business-interview-client ep_18 Has No Clip Videos

**What goes wrong:** `clips/business-interview-client/ep_18/` has `.mp4` files. However, the pipeline state JSON does not exist for this client's ep_18 run. The packager must use glob discovery rather than state-based path lookup.

**Root cause:** The pipeline run for business-interview-client reached normalization but no pipeline state file was persisted (likely an older run before the state mechanism was in place for that client, or the state dir was not created).

**How to avoid:** Always fall back to glob discovery when pipeline state is absent. Priority: state JSON first, glob second.

**Confirmed clips exist at:**
`clips/business-interview-client/ep_18/default_20260328_182916_censored_clip_0{1,2,3}_subtitle.mp4`

### Pitfall 2: Multiple Analysis JSON Files in Same Episode Directory

**What goes wrong:** `output/true-crime-client/ep_399/` contains 3 analysis JSON files from different pipeline runs (`media_20260328_171743_analysis.json`, `media_20260328_173828_analysis.json`, `media_20260328_175749_analysis.json`). The packager must use the one referenced in the pipeline state, not just the latest glob match.

**How to avoid:** Read pipeline state first. If state has `analyze.outputs.analysis_path`, use that exact path. If no state, sort by mtime descending and take the newest file.

### Pitfall 3: Compliance Report Has Multiple Versions

**What goes wrong:** `output/true-crime-client/ep_399/` has 4 compliance report files from different runs. Only one corresponds to the canonical pipeline run.

**How to avoid:** Use the compliance report whose timestamp fragment matches the stem of the analysis JSON. Alternatively, glob for `compliance_report_{ep_number}_{timestamp}.json` where timestamp matches the analysis file's timestamp.

### Pitfall 4: Raw Snapshot Must Happen Before censor Step Checkpoint

**What goes wrong:** If the pipeline is resumed after the `censor` checkpoint has been written, `audio_file` (the original raw audio) is no longer used — only `censored_audio` is carried forward. The raw snapshot opportunity is gone.

**How to avoid:** In `pipeline/steps/audio.py`, generate the raw snapshot BEFORE writing the `censor` checkpoint, inside the `else` branch (i.e., when censor has not already run). Store the snapshot path in the `censor` checkpoint outputs.

### Pitfall 5: show_notes.txt vs. analysis["show_notes"]

**What goes wrong:** `{stem}_{ts}_show_notes.txt` is written by the pipeline but contains the same content as `analysis["show_notes"]`. Using the TXT file is fine but it means one more file dependency to locate.

**How to avoid:** Read `show_notes` directly from the analysis JSON — already loaded for other fields. Eliminate the TXT file dependency. Write `show_notes.txt` in the demo folder from the JSON value.

---

## Code Examples

### Find Latest Analysis JSON (Fallback to Glob)

```python
# Source: pattern from pipeline_state.py interface
from pipeline_state import PipelineState
from pathlib import Path

def _find_analysis_json(ep_dir: Path, client_name: str, ep_id: str) -> Path:
    state = PipelineState(client_name=client_name, episode_id=ep_id)
    if state.is_step_completed("analyze"):
        path = Path(state.get_step_outputs("analyze")["analysis_path"])
        if path.exists():
            return path
    # Fallback: sort by mtime, take newest
    candidates = sorted(ep_dir.glob("*_analysis.json"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        raise FileNotFoundError(f"No analysis JSON found in {ep_dir}")
    return candidates[-1]
```

### Raw Snapshot via FFmpeg atrim (No Memory Load)

```python
# Source: FFmpeg atrim filter — subprocess pattern from audio_processor.py
import subprocess
from config import Config

def _snapshot_raw_audio(audio_file: Path, start_s: float, output_path: Path) -> Path:
    """Extract 60-second clip from raw audio without loading file into memory."""
    end_s = start_s + 60.0
    cmd = [
        Config.FFMPEG_PATH, "-i", str(audio_file),
        "-ss", str(start_s), "-to", str(end_s),
        "-acodec", "pcm_s16le", "-ar", "44100", "-y", str(output_path),
    ]
    subprocess.run(cmd, stderr=subprocess.DEVNULL, check=True,
                   stdin=subprocess.DEVNULL)
    return output_path
```

### DEMO.md Template Content

```python
DEMO_MD_TEMPLATE = """# Demo: {episode_title}

**Client:** {client_name}
**Episode:** {episode_id}
**Processed:** {processed_date}

## What Was Automated

| Step | Tool | What Happened |
|------|------|---------------|
| Transcription | Whisper (local, GPU) | Full episode transcript with word-level timestamps |
| Content Analysis | GPT-4o | Episode summary, show notes, social captions, chapter markers, clip selection |
| Censorship | FFmpeg duck-fade | {censor_count} segments silenced with smooth volume duck |
| Audio Mastering | FFmpeg loudnorm EBU R128 | {lufs_input:.1f} LUFS → {lufs_output:.1f} LUFS (target: -16 LUFS) |
| Clip Extraction | pydub + FFmpeg | {clip_count} clips selected by energy scoring |
| Caption Overlays | FFmpeg + pysubs2 | Word-by-word Hormozi-style captions burned into vertical MP4s |
| Thumbnail | Pillow | 1280×720 episode thumbnail generated |
| Compliance Check | GPT-4o | {compliance_critical} critical flags, {compliance_warning} warnings |

## Estimated Time Saved

| Task | Manual (editor) | Automated |
|------|-----------------|-----------|
| Transcription | 2-3 hours | ~20 minutes (Whisper GPU) |
| Show notes + captions | 1-2 hours | ~2 minutes (GPT-4o) |
| Audio mastering | 30-60 minutes | ~5 minutes (FFmpeg) |
| Clip selection + subtitles | 2-4 hours | ~10 minutes |
| Thumbnail | 30-60 minutes | ~1 minute |
| **Total** | **6-11 hours** | **~38 minutes** |

## Cost Per Episode

- OpenAI GPT-4o: ~$0.50-1.50 (analysis + compliance)
- Local Whisper: $0 (GPU, electricity only)
- FFmpeg processing: $0
- **Total: ~$1-2 per episode**

## Before/After Audio

See `before_after/` folder:
- `raw_60s.wav` — raw recorded audio (unmastered, uncensored)
- `processed_60s.wav` — same segment after mastering

Timestamp: {snapshot_start:.0f}s – {snapshot_end:.0f}s of episode

## Audio Metrics

| Metric | Value |
|--------|-------|
| Input LUFS | {lufs_input:.1f} |
| Output LUFS | {lufs_output:.1f} |
| Gain Applied | {lufs_gain:+.1f} dB |
| Censored Segments | {censor_count} |

## Top Clips (by energy score)

{clip_list}

## Compliance Summary

{compliance_summary}

---

*Generated by Podcast Automation Pipeline*
"""
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing, 570 tests passing) |
| Config file | `pyproject.toml` — `testpaths = ["tests"]` |
| Quick run command | `uv run pytest tests/test_demo_packager.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEMO-01 | `package_demo()` creates folder with required files | unit | `uv run pytest tests/test_demo_packager.py::TestDemoPackager::test_package_creates_expected_files -x` | Wave 0 |
| DEMO-01 | `package_demo()` reads analysis JSON correctly | unit | `uv run pytest tests/test_demo_packager.py::TestDemoPackager::test_reads_analysis_json -x` | Wave 0 |
| DEMO-01 | `package_demo()` handles missing artifacts gracefully | unit | `uv run pytest tests/test_demo_packager.py::TestDemoPackager::test_handles_missing_thumbnail -x` | Wave 0 |
| DEMO-01 | `summary.html` is a valid self-contained HTML file | unit | `uv run pytest tests/test_demo_packager.py::TestSummaryHtml::test_html_contains_base64_thumbnail -x` | Wave 0 |
| DEMO-01 | `captions.txt` contains all four platform captions | unit | `uv run pytest tests/test_demo_packager.py::TestDemoPackager::test_captions_txt_content -x` | Wave 0 |
| DEMO-02 | Raw snapshot saved before `apply_censorship()` in audio step | unit | `uv run pytest tests/test_audio_step.py::TestRawSnapshot -x` | Wave 0 |
| DEMO-02 | `before_after/` folder contains both WAV files when snapshot exists | unit | `uv run pytest tests/test_demo_packager.py::TestBeforeAfter -x` | Wave 0 |
| DEMO-03 | `DEMO.md` contains episode title, LUFS metrics, clip count | unit | `uv run pytest tests/test_demo_packager.py::TestDemoMd -x` | Wave 0 |
| DEMO-03 | LUFS measurement via FFmpeg returns structured dict | unit | `uv run pytest tests/test_demo_packager.py::TestLufsMeasurement -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_demo_packager.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_demo_packager.py` — covers DEMO-01, DEMO-02, DEMO-03
- [ ] `tests/test_audio_step.py` — covers DEMO-02 raw snapshot addition (check if `tests/test_audio.py` exists first; may be adding a class to an existing file)

---

## Key Technical Facts (Confirmed by Direct Inspection)

### File Naming Conventions (Confirmed)

- Analysis JSON: `{audio_stem}_{timestamp}_analysis.json` (e.g., `media_20260328_175749_analysis.json`)
- Processed MP3: `{audio_stem}_{timestamp}_censored.mp3`
- Processed WAV: `{audio_stem}_{timestamp}_censored.wav` (same path as MP3 before conversion)
- Episode MP4: `{audio_stem}_{timestamp}_episode.mp4`
- Thumbnail: `{audio_stem}_{thumbnail_ts}_thumbnail.png` (NOTE: thumbnail has its OWN timestamp, different from analysis — see `media_20260328_181556_thumbnail.png` vs `media_20260328_175749_analysis.json`)
- Show notes: `{audio_stem}_{timestamp}_show_notes.txt`
- Compliance: `compliance_report_{episode_number}_{timestamp}.json`
- Clip WAVs: `clips/<client>/<ep_id>/{audio_stem}_censored_clip_0N.wav`
- Clip MP4s: `clips/<client>/<ep_id>/{audio_stem}_censored_clip_0N_subtitle.mp4`

### What analysis JSON Contains (Confirmed)

From actual JSON inspection — all these fields are reliably present:
- `episode_title` (string)
- `best_clips` (list of dicts with `start_seconds`, `end_seconds`, `description`, `suggested_title`, `hook_caption`, `clip_hashtags`)
- `episode_summary` (string)
- `social_captions` (dict: `youtube`, `instagram`, `twitter`, `tiktok`)
- `show_notes` (string)
- `chapters` (list of dicts with `start_timestamp`, `title`, `start_seconds`)
- `censor_timestamps` (list, may be empty)

### What compliance JSON Contains (Confirmed)

From actual JSON inspection:
- `episode_number` (int)
- `checked_at` (ISO datetime string)
- `critical` (bool)
- `flagged` (list of dicts with `start_seconds`, `end_seconds`, `text`, `category`, `severity`, `reason`)
- `warnings` (list, same structure as `flagged`)

### Clips: True Crime Client Has Full Pipeline Run; Business Client Is Partial

- `clips/true-crime-client/ep_399/` — 3 subtitle MP4s confirmed present
- `clips/business-interview-client/ep_18/` — 3 subtitle MP4s confirmed present
- `output/true-crime-client/ep_399/` — full pipeline run (has thumbnail, MP3, episode MP4)
- `output/business-interview-client/ep_18/` — partial run (has analysis, compliance, WAV, transcript; NO thumbnail, NO episode MP4, NO MP3)

**The packager must not fail if full_episode_video_path or thumbnail is absent.**

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pydub for all audio operations | FFmpeg subprocess for large file operations | v1.0 (normalize_audio) | Critical for raw snapshot — pydub loads entire file into RAM |
| Separate template files | Self-contained HTML with base64 assets | State.md decision (no-PDF ruling) | Demo is one file, shareable as email attachment |
| Log parsing for LUFS | Re-measure with FFmpeg at package time | Phase 18 design | No brittle regex, structured JSON, repeatable |

---

## Open Questions

1. **Should `package-demo` also accept `--client` flag or only positional `<client>`?**
   - What we know: All other client commands use `--client` flag OR positional. `status` uses positional as fallback. `package-demo` is similar to `status`.
   - What's unclear: User preference for call pattern.
   - Recommendation: Accept both — `uv run main.py package-demo <client> [ep]` and `uv run main.py --client <name> package-demo [ep]`. Matches existing `_handle_client_command` pattern.

2. **LUFS measurement: use MP3 or WAV?**
   - What we know: MP3 exists for true-crime ep_399 but NOT for business-interview ep_18 (partial run). WAV exists for both.
   - Recommendation: Prefer WAV when available (lossless, more accurate measurement). Fall back to MP3. Never fail if neither exists.

3. **What LUFS target to display in DEMO.md?**
   - What we know: `Config.LUFS_TARGET = -16` (confirmed from config.py). True crime actual output: -16.5 → -16.0 LUFS. Business interview actual: -12.9 → -16.0 LUFS.
   - Recommendation: Show input LUFS (from re-measurement of raw would be ideal, but raw is deleted after processing). Show processed LUFS as the delivered value. Explain the target is Spotify's standard.

---

## Sources

### Primary (HIGH confidence)

- Direct code inspection: `pipeline/steps/audio.py`, `audio_processor.py`, `subtitle_clip_generator.py`, `episode_webpage_generator.py`, `main.py`, `pipeline_state.py`
- Direct artifact inspection: `output/true-crime-client/ep_399/`, `output/business-interview-client/ep_18/`, `clips/true-crime-client/ep_399/`, `clips/business-interview-client/ep_18/`
- Direct state inspection: `output/true-crime-client/.pipeline_state/ep_399.json`
- `output/podcast_automation.log` — LUFS values confirmed (e.g., `-16.5 LUFS → -16.0 LUFS`)
- `.planning/research/ARCHITECTURE.md` — DemoPackager design patterns
- `.planning/research/STACK.md` — confirmed no new packages needed; jinja2 + stdlib
- `.planning/STATE.md` — no-PDF ruling, before/after snapshot requirement

### Secondary (MEDIUM confidence)

- `.planning/research/FEATURES.md` — competitor analysis, demo content strategy

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are existing project dependencies confirmed in pyproject.toml; no new packages
- Architecture: HIGH — based on direct code and artifact inspection; exact file paths and JSON schemas confirmed
- Pitfalls: HIGH — based on actual artifact inspection revealing partial pipeline runs, multiple analysis files, timestamp mismatches
- Validation architecture: HIGH — test framework and patterns well-established in project; 570 existing passing tests

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable codebase; only invalidated by new pipeline runs creating different artifact layouts)
