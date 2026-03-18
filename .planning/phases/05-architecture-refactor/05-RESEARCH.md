# Phase 5: Architecture Refactor - Research

**Researched:** 2026-03-17
**Domain:** Python package decomposition, CLI shimming, pipeline orchestration
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DEBT-01 | main.py split into pipeline/ package with modular step classes and PipelineContext dataclass | Core refactor target — main.py is currently ~1870 lines; pipeline/ package with steps/ subpackage maps directly to the success criteria |
| DEBT-05 | continue_episode.py eliminated by delegating to extracted pipeline steps | continue_episode.py runs 7 steps that map 1:1 to pipeline steps already in main.py; a `run_distribute_only()` entry point on the pipeline replaces it |
</phase_requirements>

---

## Summary

main.py is a 1870-line God Object containing all pipeline logic. The `PodcastAutomation` class initializes 15+ components in `__init__`, runs 17 numbered steps inline in `process_episode()`, plus holds `dry_run_episode()`, five upload helpers, and utility methods. There is no test file for main.py at all — the entire orchestration layer is untestable because every method is deeply entangled with real components.

`continue_episode.py` duplicates 7 pipeline steps (video conversion, MP3, Dropbox, RSS, YouTube, Twitter) in isolation with its own component initialization. It exists because the main pipeline has no resumable entry point at the "distribute" phase. Eliminating it requires extracting a `run_distribute_only()` function that re-uses the same pipeline step implementations.

The refactor target is clean decomposition: a `pipeline/` package owns all orchestration, main.py becomes a thin CLI shim (~100-150 lines of argparse + delegation), and each step group is independently importable and testable. PipelineState already exists and works well; the checkpoint key names must be regression-tested to prevent silent breakage.

**Primary recommendation:** Extract a `PipelineContext` dataclass, create `pipeline/steps/` modules for each step group, create `pipeline/runner.py` as the orchestrator, and reduce main.py to argparse + `pipeline.runner.run()` dispatch.

---

## Standard Stack

### Core (already in project — no new dependencies needed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| dataclasses (stdlib) | 3.12+ | PipelineContext dataclass | Zero-dep, explicit field typing |
| pathlib (stdlib) | 3.12+ | Path handling in context | Already used project-wide |
| pytest | current | Unit tests for extracted modules | Project standard (327 tests) |
| unittest.mock | stdlib | Isolate components in step tests | Project convention |

### No new dependencies
This is a pure refactor. All runtime dependencies (pydub, mutagen, FFmpeg, uploaders, etc.) are already installed. Adding new packages would be out of scope.

---

## Architecture Patterns

### Recommended Project Structure

```
podcast-automation/
├── main.py                    # ~100-150 lines: argparse + dispatch only
├── pipeline/
│   ├── __init__.py            # exports: run(), run_distribute_only(), PipelineContext
│   ├── context.py             # PipelineContext dataclass
│   ├── runner.py              # full pipeline orchestration (extracted from PodcastAutomation)
│   └── steps/
│       ├── __init__.py
│       ├── ingest.py          # Step 1: download/find episode, extract episode_number
│       ├── audio.py           # Steps 2, 4, 4.5, 6: transcribe, censor, normalize, mp3
│       ├── analysis.py        # Step 3, 3.5: content analysis, topic tracker
│       ├── video.py           # Steps 5, 5.1, 5.4, 5.5, 5.6: clips, approval, subs, video, thumbnail
│       └── distribute.py      # Steps 7, 7.5, 8, 8.5, 9: dropbox, rss, social, blog, search index
├── pipeline_state.py          # unchanged
├── continue_episode.py        # DELETED after distribute.py exists
```

### Pattern 1: PipelineContext Dataclass

**What:** A single object carrying all pipeline state between step groups — replaces the dozens of scattered local variables in `process_episode()`.

**When to use:** Every step function receives and returns (or mutates) a PipelineContext.

**Example:**
```python
# pipeline/context.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

@dataclass
class PipelineContext:
    episode_folder: str
    episode_number: Optional[int]
    episode_output_dir: Path
    timestamp: str
    # populated as steps complete:
    audio_file: Optional[Path] = None
    transcript_path: Optional[Path] = None
    transcript_data: Optional[dict] = None
    analysis: Optional[dict] = None
    censored_audio: Optional[Path] = None
    mp3_path: Optional[Path] = None
    clip_paths: list = field(default_factory=list)
    video_clip_paths: list = field(default_factory=list)
    full_episode_video_path: Optional[str] = None
    srt_paths: list = field(default_factory=list)
    thumbnail_path: Optional[str] = None
    finished_path: Optional[str] = None
    uploaded_clip_paths: list = field(default_factory=list)
    # flags
    test_mode: bool = False
    dry_run: bool = False
    auto_approve: bool = False
    resume: bool = False
```

### Pattern 2: Step Group Functions

**What:** Each `pipeline/steps/foo.py` exposes a single `run_<group>(ctx, components)` function. Functions are pure: they read from ctx, write back to ctx, and return it.

**When to use:** Every pipeline step group.

**Example:**
```python
# pipeline/steps/audio.py
from pipeline.context import PipelineContext

def run_audio(ctx: PipelineContext, audio_processor, transcriber) -> PipelineContext:
    """Steps 2 (transcribe), 4 (censor), 4.5 (normalize), 6 (mp3)."""
    # ... extracted from PodcastAutomation.process_episode()
    return ctx
```

### Pattern 3: Thin CLI Shim

**What:** main.py becomes only argparse + instantiation + `pipeline.runner.run()` call.

**When to use:** After extraction is complete.

**Example structure (target ~120 lines):**
```python
# main.py (after refactor)
import sys
import argparse
from pipeline import run, run_distribute_only, run_upload_scheduled, run_analytics, run_search

def main():
    args = parse_args()   # ~30 lines of argparse
    if args.command == "upload-scheduled":
        run_upload_scheduled()
    elif args.command == "analytics":
        run_analytics(args.episode)
    elif args.command == "search":
        run_search(args.query)
    else:
        run(args)          # delegates all episode processing

if __name__ == "__main__":
    main()
```

### Pattern 4: run_distribute_only() Entry Point

**What:** A pipeline entry point that takes an episode_number + existing files and runs only the distribution steps (Steps 7–9). This replaces `continue_episode.py`.

**When to use:** When audio/analysis is already done and user wants to re-run distribution.

**Example:**
```python
# pipeline/__init__.py or pipeline/runner.py
def run_distribute_only(episode_number: int, skip_video: bool = False, skip_upload: bool = False):
    """Replaces continue_episode.py. Re-runs Steps 7-9 for an already-processed episode."""
    ctx = _build_context_from_existing_files(episode_number)
    components = _init_distribute_components(skip_upload=skip_upload)
    return steps.distribute.run_distribute(ctx, components)
```

### Pattern 5: Checkpoint Key Regression Test

**What:** A test that asserts the complete set of checkpoint key names in PipelineState matches a known-good hardcoded list. This catches renames during refactor.

**When to use:** Phase 5 — write it first (TDD red), then make it green.

**Example:**
```python
# tests/test_pipeline_checkpoint_keys.py
KNOWN_CHECKPOINT_KEYS = {
    "transcribe", "analyze", "censor", "normalize",
    "create_clips", "subtitles", "convert_videos",
    "convert_mp3", "blog_post"
}

def test_checkpoint_key_names_unchanged():
    """Regression: checkpoint keys must match known-good set to prevent silent resume failures."""
    from pipeline.steps import audio, analysis, video, distribute
    # collect all state.complete_step() call first-args via AST or inspection
    # assert collected == KNOWN_CHECKPOINT_KEYS
```

The simplest reliable implementation: grep all `complete_step(` calls in the step files and assert the key set. Can use `ast.parse` or a simple regex scan of the source files.

### Anti-Patterns to Avoid

- **Re-initializing all components for run_distribute_only:** `continue_episode.py` initializes everything from scratch. `run_distribute_only()` should only initialize what distribute steps need (DropboxHandler, uploaders, scheduler, etc.) — not Transcriber or AudioProcessor.
- **Moving interactive mode to pipeline/:** The interactive `input()` menu in `main()` is a CLI concern. It stays in main.py or gets deleted (it's rarely used; the named commands cover the same ground).
- **Making PipelineContext mutable without discipline:** Steps should set ctx fields, never delete them. Add a guard: fields are set-once during the run.
- **Circular imports:** `pipeline/steps/*.py` must never import from `main.py`. All shared imports come from project-level modules (config, logger, pipeline_state).
- **Changing checkpoint key names:** Any rename of `"transcribe"` → `"ingest_transcribe"` etc. will silently skip resume checkpoints for in-progress episodes. The regression test guards this.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dataclass with defaults | Custom __init__ with kwargs | `@dataclass` stdlib | Fields, defaults, repr for free |
| Checkpoint regression detection | Complex AST walker | Simple regex scan of `complete_step(` calls in source files | This is internal code, regex is reliable and readable |
| Component dependency injection | IoC container, service locator | Pass components dict or individual args to step functions | Overkill for a fixed 18-step pipeline; REQUIREMENTS.md explicitly excludes "Plugin registry / dynamic step discovery" |
| Behavior verification | End-to-end integration test running real pipeline | Pytest with monkeypatched components, assert on ctx field values after each step | No GPU, no credentials in CI |

---

## Common Pitfalls

### Pitfall 1: Spaghetti Import Order After Package Creation

**What goes wrong:** Moving code into `pipeline/steps/*.py` introduces circular import chains. E.g. `pipeline/runner.py` imports `pipeline/steps/audio.py` which imports `pipeline/context.py` which imports something that imports `pipeline`.

**Why it happens:** Python's package `__init__.py` executes on `import pipeline`, and if runner.py is imported there it triggers recursive loading.

**How to avoid:** Keep `pipeline/__init__.py` minimal — only re-export the public API (`run`, `run_distribute_only`). Let runner.py and step files import each other directly. Never import runner.py in `__init__.py` at module level without lazy imports.

**Warning signs:** `ImportError: cannot import name X from partially initialized module` on startup.

---

### Pitfall 2: Checkpoint Keys Silently Renamed

**What goes wrong:** During extraction, a developer renames `state.complete_step("convert_mp3", ...)` to `state.complete_step("mp3_conversion", ...)`. Any episode already in mid-flight (state file on disk) will re-run the MP3 conversion step unnecessarily — or worse, try to re-process a partially complete state.

**Why it happens:** No enforcement mechanism exists today. Keys are free-form strings.

**How to avoid:** Write the checkpoint key regression test FIRST (TDD red). After refactor, confirm it's green. The test in `tests/test_pipeline_checkpoint_keys.py` should assert the exact set of key names.

**Warning signs:** Resume behavior changes; steps that were completed start running again.

---

### Pitfall 3: continue_episode.py Has Diverged from main.py

**What goes wrong:** `continue_episode.py` has slightly different logic from the equivalent steps in `main.py` (e.g., it uses `create_twitter_caption` from uploaders, which main.py does not call directly; it builds `finished_filename` with different sanitization). Naively extracting distribute.py from main.py alone would drop `continue_episode.py`'s edge-case handling.

**Why it happens:** continue_episode.py was written as a standalone script and has not been kept in sync.

**How to avoid:** Before extraction, diff the relevant sections of continue_episode.py against main.py step-by-step. The distribute step module should cover both code paths.

**Warning signs:** After deletion of continue_episode.py, users who were using it for manual recovery can no longer run distribution-only.

---

### Pitfall 4: dry_run_episode() Must Move Too

**What goes wrong:** `dry_run_episode()` in main.py directly references `self.audiogram_generator.enabled`, `self.scheduler.is_scheduling_enabled()`, etc. If PodcastAutomation class is dissolved, dry-run validation either breaks or gets dropped.

**Why it happens:** It was embedded in the class.

**How to avoid:** Move `dry_run_episode()` logic to `pipeline/runner.py` as a `dry_run()` function that accepts the same components dict used by the real pipeline. The CLI shim calls `pipeline.runner.dry_run(components)`.

**Warning signs:** `python main.py --dry-run` crashes or silently skips validation after refactor.

---

### Pitfall 5: ThreadPoolExecutor in Step 5.5

**What goes wrong:** The video conversion step uses `ThreadPoolExecutor(max_workers=2)` to parallelize clip conversion and full-episode conversion. If this code is naively moved to `pipeline/steps/video.py`, the thread pool captures references to `self` (now `components` dict or similar), causing attribute errors.

**Why it happens:** The executor `submit()` calls reference `self.video_converter`, which would become a local variable in the step function.

**How to avoid:** In the extracted step function, capture the converter in the closure explicitly before the `with` block: `vc = components["video_converter"]`. Standard closure fix.

---

## Code Examples

### Current Checkpoint Keys (must not change)
```python
# All state.complete_step() first arguments in main.py process_episode():
"transcribe"        # Step 2
"analyze"           # Step 3
"censor"            # Step 4
"normalize"         # Step 4.5
"create_clips"      # Step 5
"subtitles"         # Step 5.4
"convert_videos"    # Step 5.5
"convert_mp3"       # Step 6
"blog_post"         # Step 8.5
```

### Step Group Mapping (from main.py to pipeline/steps/)

| Step(s) | Current Location | Target Module | Key Entry Point |
|---------|-----------------|---------------|-----------------|
| Step 1 (download) | process_episode() lines 830-856 | pipeline/steps/ingest.py | `run_ingest(ctx, dropbox)` |
| Steps 2+4+4.5+6 (transcribe, censor, normalize, mp3) | process_episode() lines 867-1203 | pipeline/steps/audio.py | `run_audio(ctx, components)` |
| Steps 3+3.5 (analysis, topic) | process_episode() lines 887-941 | pipeline/steps/analysis.py | `run_analysis(ctx, components)` |
| Steps 5+5.1+5.4+5.5+5.6 (clips, approval, subs, video, thumb) | process_episode() lines 976-1183 | pipeline/steps/video.py | `run_video(ctx, components)` |
| Steps 7+7.5+8+8.5+9 (dropbox, rss, social, blog, search) | process_episode() lines 1204-1427 | pipeline/steps/distribute.py | `run_distribute(ctx, components)` |
| dry_run_episode() | PodcastAutomation class | pipeline/runner.py | `dry_run(components)` |
| _process_with_notification() | module-level fn | pipeline/runner.py | `run_with_notification(args, components)` |
| _run_upload_scheduled() | module-level fn | pipeline/runner.py | `run_upload_scheduled()` |
| _run_analytics() / _run_search() | module-level fns | pipeline/runner.py | `run_analytics()`, `run_search()` |
| main() arg parsing | main() | main.py (stays) | thin CLI shim |
| continue_episode logic | continue_episode.py | pipeline/steps/distribute.py + pipeline/runner.py | `run_distribute_only()` |

### Components Dict Pattern

Instead of `PodcastAutomation` class holding `self.*`, create components in runner.py:

```python
# pipeline/runner.py
def _init_components(test_mode, dry_run, auto_approve):
    components = {
        "dropbox": DropboxHandler(),
        "transcriber": Transcriber(),
        "audio_processor": AudioProcessor(),
        "editor": ContentEditor(),
        "video_converter": _init_optional(VideoConverter),
        "uploaders": _init_uploaders(),
        "notifier": DiscordNotifier(),
        "scheduler": UploadScheduler(),
        "blog_generator": BlogPostGenerator(),
        "thumbnail_generator": ThumbnailGenerator(),
        "clip_previewer": ClipPreviewer(auto_approve=auto_approve),
        "search_index": EpisodeSearchIndex(),
        "audiogram_generator": AudiogramGenerator(),
        "chapter_generator": ChapterGenerator(),
    }
    return components
```

This dict is passed to each step group function. Steps access `components["audio_processor"]` etc. No class needed.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| God Object orchestrator | Thin CLI + pipeline package | Phase 5 (this phase) | main.py shrinks from 1870 to ~130 lines; each step group becomes independently testable |
| continue_episode.py duplicate | pipeline.run_distribute_only() | Phase 5 (this phase) | Single implementation, no drift risk |
| No main.py tests | test_pipeline_*.py per step group | Phase 5 (this phase) | Orchestration logic gains test coverage |

---

## Open Questions

1. **Interactive menu in main.py (lines 1822-1856)**
   - What we know: It's rarely used; named commands (`latest`, `ep25`, etc.) cover all cases
   - What's unclear: Whether anyone uses the numbered interactive menu
   - Recommendation: Keep it in main.py as-is (it's pure CLI glue, < 40 lines); don't move it to pipeline/

2. **PipelineContext mutability contract**
   - What we know: Dataclass fields will be set by multiple step functions
   - What's unclear: Whether to use a mutable dataclass or return new contexts from each step
   - Recommendation: Mutable dataclass with in-place mutation — simpler, matches existing checkpoint pattern; no need for immutability here

3. **Test coverage for extracted steps**
   - What we know: No test file exists for main.py today; 327 tests cover individual modules
   - What's unclear: How many integration-style tests are needed for runner.py vs. unit tests for step files
   - Recommendation: Unit tests per step module (mock components dict); one smoke test for runner.py with all components mocked

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (current project standard) |
| Config file | none (pytest auto-discovers tests/) |
| Quick run command | `pytest tests/test_pipeline_checkpoint_keys.py -x` |
| Full suite command | `pytest` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEBT-01 | main.py is under 150 lines and only does argparse + delegation | unit (line count assertion) | `pytest tests/test_pipeline_refactor.py::test_main_under_150_lines -x` | ❌ Wave 0 |
| DEBT-01 | Each pipeline/steps/*.py is independently importable | unit (import check) | `pytest tests/test_pipeline_refactor.py::test_step_modules_importable -x` | ❌ Wave 0 |
| DEBT-01 | PipelineContext dataclass exists with expected fields | unit | `pytest tests/test_pipeline_refactor.py::test_pipeline_context_fields -x` | ❌ Wave 0 |
| DEBT-01 | run_audio() step function exists and accepts ctx + components | unit | `pytest tests/test_pipeline_steps_audio.py -x` | ❌ Wave 0 |
| DEBT-01 | run_distribute() step function exists and accepts ctx + components | unit | `pytest tests/test_pipeline_steps_distribute.py -x` | ❌ Wave 0 |
| DEBT-05 | pipeline.run_distribute_only() exists and callable | unit | `pytest tests/test_pipeline_refactor.py::test_run_distribute_only_exists -x` | ❌ Wave 0 |
| DEBT-05 | run_distribute_only() calls distribute step with correct ctx fields | unit | `pytest tests/test_pipeline_steps_distribute.py::test_run_distribute_only -x` | ❌ Wave 0 |
| DEBT-01+05 | Checkpoint key names match known-good set | regression | `pytest tests/test_pipeline_checkpoint_keys.py -x` | ❌ Wave 0 |
| Both | `python main.py ep29 --auto-approve` produces same structure as before | smoke (mock all I/O) | `pytest tests/test_pipeline_smoke.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_pipeline_checkpoint_keys.py tests/test_pipeline_refactor.py -x`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_pipeline_refactor.py` — structural assertions (line count, importability, run_distribute_only existence)
- [ ] `tests/test_pipeline_checkpoint_keys.py` — checkpoint key regression (REQ DEBT-01)
- [ ] `tests/test_pipeline_steps_audio.py` — unit tests for audio step group
- [ ] `tests/test_pipeline_steps_distribute.py` — unit tests for distribute step group + run_distribute_only
- [ ] `tests/test_pipeline_smoke.py` — end-to-end smoke with mocked components

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: main.py (1870 lines, fully read) — step structure, checkpoint keys, component init
- Direct code inspection: continue_episode.py (526 lines, fully read) — duplication scope
- Direct code inspection: pipeline_state.py — checkpoint key naming confirmed
- .planning/REQUIREMENTS.md — DEBT-01, DEBT-05 requirement text
- .planning/ROADMAP.md — Phase 5 success criteria

### Secondary (MEDIUM confidence)
- Python stdlib docs (dataclasses) — standard pattern for context objects in pipelines
- Project convention (CLAUDE.md, existing tests) — flat module structure, unittest.mock patterns

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; pure Python stdlib + existing project libraries
- Architecture: HIGH — based on direct code inspection of all 1870 lines; step boundaries are clear
- Pitfalls: HIGH — identified from direct code reading (ThreadPoolExecutor closure issue, checkpoint key fragility, continue_episode.py divergence)

**Research date:** 2026-03-17
**Valid until:** Stable (pure internal refactor; no external library dependencies to track)
