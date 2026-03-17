# Architecture Patterns

**Domain:** Podcast/media processing automation pipeline
**Researched:** 2026-03-16

## Current Architecture Summary

The codebase is a linear pipeline with a God Object problem. `PodcastAutomation` in `main.py` (1,802 lines) acts simultaneously as CLI entrypoint, component factory, upload coordinator, business logic owner, and dry-run validator. This creates high coupling and makes isolated testing impossible — there is no `tests/test_main.py`.

The existing module structure is actually well-decomposed at the _component_ level. `audio_processor.py`, `transcription.py`, `content_editor.py`, `uploaders/`, etc. are appropriately sized and focused. The problem is entirely in `main.py`, which owns everything else, and `continue_episode.py`, which duplicates chunks of `main.py`'s upload logic outside of it.

## Recommended Architecture

The target architecture is a **Modular Orchestrator** — keep the monolith (no microservices, no task queue), but surgically split `main.py` into three well-bounded layers:

```
CLI layer (cli.py)
     |
     v
Orchestrator (pipeline.py)
     |
     +---> PipelineContext (dataclass, carries all step outputs)
     |
     +---> Step modules (pipeline/steps/*.py, one file per step group)
                |
                v
           Component classes (existing: audio_processor.py, transcription.py, etc.)
```

**Key principle:** The component classes are already correct. Only the wiring layer (`main.py`) needs splitting. Do not refactor the component classes as part of this work — they have test coverage and working interfaces.

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `cli.py` | Argument parsing, command routing, process exit | `pipeline.py` orchestrator only |
| `pipeline.py` (new) | Step sequencing, checkpoint logic, test/dry-run guards, component initialization | All step modules and component classes |
| `pipeline/context.py` (new) | `PipelineContext` dataclass carrying all inter-step data | Passed into and returned from every step function |
| `pipeline/steps/ingest.py` (new) | Steps 1-2: Download, transcribe | `DropboxHandler`, `Transcriber` |
| `pipeline/steps/analysis.py` (new) | Steps 3-3.5: AI content analysis, topic tracking | `ContentEditor`, topic engine |
| `pipeline/steps/audio.py` (new) | Steps 4-6: Censorship, normalization, clips, approval, MP3 | `AudioProcessor`, `ClipPreviewer` |
| `pipeline/steps/video.py` (new) | Steps 5.4-5.6: Subtitles, audiograms, thumbnails, full-episode video | `SubtitleGenerator`, `AudiogramGenerator`, `VideoConverter`, `ThumbnailGenerator` |
| `pipeline/steps/distribute.py` (new) | Steps 7-9: Dropbox upload, RSS, social media, blog, search index | All uploaders, `RSSFeedGenerator`, `BlogPostGenerator`, `EpisodeSearchIndex` |
| `pipeline/uploaders.py` (new) | Uploader initialization and registry, scheduled upload execution | All `uploaders/` classes |
| Existing component classes | Domain logic (unchanged) | Infrastructure (config, logger) |

### Data Flow

```
User invokes: python main.py ep29 --auto-approve
                    |
                   cli.py
                    | resolves command → calls pipeline.run_episode(path, flags)
                    |
               pipeline.py
                    | creates PipelineContext(episode_id, flags, paths...)
                    | loads PipelineState checkpoint
                    |
        +-----------+-----------+-----------+-----------+
        |           |           |           |           |
   ingest.py   analysis.py   audio.py   video.py  distribute.py
        |           |           |           |           |
  ctx.audio_file  ctx.analysis  ctx.clips  ctx.videos  ctx.upload_results
        |           |           |           |           |
        +-----------+-----------+-----------+-----------+
                    |
              PipelineContext returned to cli.py
```

**`PipelineContext` is the single data handoff object.** Each step receives it, reads its inputs, writes its outputs back to it, and returns it. No step reaches into another step's internals. The `analysis` dict (currently the primary cross-step data carrier) becomes a field on `PipelineContext`.

### PipelineContext Shape (target)

```python
@dataclass
class PipelineContext:
    # Identity
    episode_id: str
    episode_number: str | None
    episode_folder: str

    # Flags
    test_mode: bool = False
    dry_run: bool = False
    auto_approve: bool = False
    resume: bool = False

    # Step outputs (populated as pipeline runs)
    audio_file: Path | None = None
    transcript_data: dict | None = None
    analysis: dict | None = None
    topic_context: list | None = None
    censored_audio: Path | None = None
    normalized_audio: Path | None = None
    clip_paths: list[Path] = field(default_factory=list)
    subtitle_paths: list[Path] = field(default_factory=list)
    video_paths: list[Path] = field(default_factory=list)
    full_episode_video: Path | None = None
    thumbnail_path: Path | None = None
    mp3_path: Path | None = None
    upload_results: dict = field(default_factory=dict)

    # Derived paths
    output_dir: Path | None = None
```

## Patterns to Follow

### Pattern 1: Extract Class to Pipeline Step Modules

**What:** Group related `_upload_*` and processing methods from `PodcastAutomation` into step-specific files under `pipeline/steps/`. Each step file exports a single `run(ctx: PipelineContext, components: ComponentSet) -> PipelineContext` function.

**When:** Any time a method in `main.py` maps cleanly to one pipeline phase. All `_upload_*` methods → `distribute.py`. All audio mutation steps → `audio.py`.

**Example:**
```python
# pipeline/steps/audio.py
def run(ctx: PipelineContext, components: ComponentSet) -> PipelineContext:
    if ctx.dry_run:
        ctx.censored_audio = ctx.audio_file
        return ctx
    ctx.censored_audio = components.audio_processor.apply_censorship(
        ctx.audio_file, ctx.analysis["censor_timestamps"]
    )
    ctx.normalized_audio = components.audio_processor.normalize_audio(ctx.censored_audio)
    ctx.clip_paths = components.audio_processor.create_clips(
        ctx.normalized_audio, ctx.analysis["best_clips"]
    )
    return ctx
```

**Why this order:** Start with `distribute.py` — it's the most isolated and has the most duplicate logic with `continue_episode.py`. Then `audio.py` (smallest). Then `analysis.py`. Ingest last (touches the Whisper model, highest risk).

### Pattern 2: ComponentSet (Replaces PodcastAutomation.__init__ god factory)

**What:** A simple dataclass or namedtuple holding all initialized component instances. Constructed once in `pipeline.py` and passed to each step.

**When:** Pipeline startup. Components still initialize themselves; `ComponentSet` just groups them.

**Example:**
```python
@dataclass
class ComponentSet:
    dropbox: DropboxHandler
    transcriber: Transcriber
    editor: ContentEditor
    audio_processor: AudioProcessor
    video_converter: VideoConverter | None
    uploaders: dict[str, Any]
    notifier: DiscordNotifier
    scheduler: UploadScheduler
    blog_generator: BlogPostGenerator
    thumbnail_generator: ThumbnailGenerator
    clip_previewer: ClipPreviewer
    search_index: EpisodeSearchIndex
    audiogram_generator: AudiogramGenerator
```

### Pattern 3: Checkpoint Wrapping at the Orchestrator, Not in Steps

**What:** Move all `PipelineState` checkpoint checks out of the step functions and into the orchestrator loop in `pipeline.py`. Steps are checkpoint-unaware.

**When:** Implementing `pipeline.py`. Each step is wrapped:
```python
if state and state.is_step_completed("audio"):
    ctx = state.restore_audio_context(ctx)
else:
    ctx = audio_step.run(ctx, components)
    if state:
        state.complete_step("audio", ctx.audio_outputs_dict())
```

**Why:** Checkpoint logic currently interleaved throughout `process_episode()` is the primary readability obstacle. Pulling it into a wrapper makes steps trivially testable without state machinery.

### Pattern 4: Keep `continue_episode.py` Alive by Delegating to `pipeline.py`

**What:** Rather than deleting `continue_episode.py` (used for resuming stalled uploads), refactor it to call `pipeline.run_distribute_only(episode_folder)` once `distribute.py` exists.

**When:** After `distribute.py` step is extracted. This eliminates the duplication with zero behavior change.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Step-Level Initialization

**What:** Moving component `__init__` calls into step functions (initializing Whisper inside `ingest.py`).

**Why bad:** Whisper model load (~10s, 10GB VRAM) would repeat on every resume. Current eagerly-initialized pattern is correct for a CLI pipeline.

**Instead:** Keep all component initialization in `ComponentSet` construction at pipeline startup.

### Anti-Pattern 2: Splitting Configuration

**What:** Distributing config values into per-step config files or per-step env var reading.

**Why bad:** `config.py` is already a single source of truth. Splitting it produces the same dual-source bug currently seen in `scheduler.py` (`os.getenv` vs `Config.SCHEDULE_*_DELAY_HOURS`).

**Instead:** All env var reads stay in `config.py`. Step modules import `from config import Config` like every other module.

### Anti-Pattern 3: Rebuilding the Pipeline as a Plugin Registry

**What:** Creating a decorator-based `@pipeline.step("name")` registration system where steps are discovered dynamically.

**Why bad:** This pipeline has 18 fixed, ordered steps with hard dependencies (clips require censored audio requires transcript). Discovery-based registries add complexity with no payoff when the step graph is static.

**Instead:** Explicit sequential calls in `pipeline.py`. The step order is documented, not inferred. A simple list of step functions, called in order, with checkpoint wrapping around each.

### Anti-Pattern 4: Test-Mode Branching Inside Steps

**What:** Adding `if ctx.test_mode: return ctx` at the top of every step.

**Why bad:** Scatters test/dry-run logic across all step modules, making it hard to audit what actually runs in test mode.

**Instead:** The orchestrator in `pipeline.py` is the single place that decides whether to call a step, skip it, or mock it. Steps themselves are always "real" — they just process whatever context they're given.

## Build Order (Dependencies)

The refactoring has a safe build order based on test risk and dependency direction:

```
1. pipeline/context.py
   (New dataclass — no dependencies, no behavior change)

2. pipeline/steps/distribute.py
   (Extract _upload_* methods from main.py → eliminates continue_episode.py duplication)
   → Unblocks: fixing scheduled upload stub, wiring Instagram, fixing Twitter URL bug

3. pipeline/uploaders.py
   (Extract _init_uploaders() from PodcastAutomation.__init__)
   → Unblocks: test coverage for uploader initialization

4. pipeline/steps/video.py
   (Extract SubtitleGenerator, AudiogramGenerator, VideoConverter, ThumbnailGenerator steps)
   → Low risk: all have existing test coverage

5. pipeline/steps/audio.py
   (Extract censorship, normalization, clips, approval steps)
   → Medium risk: AudioProcessor has tests but censorship is getting replaced with ducking

6. pipeline/steps/analysis.py
   (Extract ContentEditor, topic tracker integration)
   → High risk: analysis dict is the primary data handoff; any schema change propagates everywhere

7. pipeline/steps/ingest.py
   (Extract Dropbox download, Whisper transcription)
   → Highest risk: Whisper model loading, GPU dependency; do last

8. pipeline.py (orchestrator)
   (Replace PodcastAutomation.process_episode() with step-call sequence)
   → Only after all steps are extracted and individually tested

9. cli.py
   (Extract main() and command routing from main.py)
   → Last: main.py stays as a thin shim pointing to cli.py until old entry point is decommissioned

10. Delete/delegate continue_episode.py
    → Only after distribute.py and pipeline.py are validated in production
```

**Parallelizable:** Steps 2-5 can proceed in parallel (different method groups from `main.py`). Steps 6-7 must be sequential because the `analysis` dict schema must be stable before ingest changes.

## Scalability Considerations

| Concern | Now (single episode) | At 100 episodes (batch) | At multi-host |
|---------|---------------------|------------------------|---------------|
| Whisper model | Loaded once at init, fine | Explicit unload between episodes needed | One process per GPU |
| PipelineState | JSON file per episode, fine | SQLite for batch indexing | No change needed |
| Upload scheduling | Delay-based stub (broken) | Cron job calling `upload-scheduled` | No change needed |
| Step parallelism | ThreadPoolExecutor for video only | Parallel step executor for independent branches | No change needed |
| Component coupling | High (God Object) | Must be resolved before batch processing | ComponentSet pattern solves this |

## Confidence Assessment

| Claim | Confidence | Basis |
|-------|------------|-------|
| PipelineContext dataclass pattern | HIGH | Standard Python; used in Ploigos PSR, Azure ML Pipelines, and all major Python pipeline frameworks |
| Extract Class refactoring for large classes | HIGH | Documented in Refactoring.Guru, Martin Fowler; standard practice |
| Step ordering based on risk/dependency | HIGH | Derived directly from codebase dependency graph |
| Checkpoint-at-orchestrator pattern | HIGH | Separation of concerns principle; directly solves the readability problem identified in CONCERNS.md |
| Plugin registry pattern as anti-pattern here | MEDIUM | Static 18-step pipeline makes dynamic registration complexity-negative; based on code inspection |

## Sources

- [Data Pipeline Design Patterns - Coding Patterns in Python](https://www.startdataengineering.com/post/code-patterns/) — MEDIUM confidence (WebSearch verified)
- [The Elegance of Modular Data Processing with Python's Pipeline Approach](https://dkraczkowski.github.io/articles/crafting-data-processing-pipeline/) — MEDIUM confidence (WebSearch verified)
- [Extract Class Refactoring — Refactoring.Guru](https://refactoring.guru/extract-class) — HIGH confidence (official reference)
- [Large Class Code Smell — Refactoring.Guru](https://refactoring.guru/smells/large-class) — HIGH confidence (official reference)
- [I have a big class with too many methods — Breadcrumbs Collector](https://breadcrumbscollector.tech/i-have-a-big-class-with-too-many-methods-how-do-i-split-it/) — MEDIUM confidence (WebSearch)
- [Python Registry Pattern — DEV Community](https://dev.to/dentedlogic/stop-writing-giant-if-else-chains-master-the-python-registry-pattern-ldm) — LOW confidence (WebSearch only; used to inform anti-pattern reasoning)
- [Ploigos Step Runner — GitHub](https://github.com/ploigos/ploigos-step-runner) — MEDIUM confidence (real-world CLI pipeline step runner reference)
- [pypyr task-runner — GitHub](https://github.com/pypyr/pypyr) — MEDIUM confidence (reference for explicit sequential step execution pattern)

---

*Architecture research: 2026-03-16*
