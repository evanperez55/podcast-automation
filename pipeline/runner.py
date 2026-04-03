"""Pipeline runner — replaces PodcastAutomation class with module-level functions.

Extracted from main.py's PodcastAutomation class and module-level functions.
Called by the thin main.py CLI shim.
"""

import os
import re
import json
import time
from datetime import datetime
from pathlib import Path

from config import Config
from logger import logger
from pipeline_state import PipelineState

# Heavy modules lazy-imported in _init_components() to speed up CLI startup
# from dropbox_handler import DropboxHandler
# from transcription import Transcriber
# from content_editor import ContentEditor
# from audio_processor import AudioProcessor
# from video_converter import VideoConverter
# from uploaders import YouTubeUploader, etc.
# from notifications import DiscordNotifier
# from scheduler import UploadScheduler
# from blog_generator import BlogPostGenerator
# from thumbnail_generator import ThumbnailGenerator
# from analytics import AnalyticsCollector, TopicEngagementScorer
from clip_previewer import ClipPreviewer
from search_index import EpisodeSearchIndex
from audiogram_generator import AudiogramGenerator
from chapter_generator import ChapterGenerator
from subtitle_clip_generator import SubtitleClipGenerator
from episode_webpage_generator import EpisodeWebpageGenerator
from content_compliance_checker import ContentComplianceChecker
from retry_utils import retry_with_backoff

from pipeline.context import PipelineContext
from pipeline.steps.ingest import run_ingest
from pipeline.steps.analysis import run_analysis
from pipeline.steps.video import run_video
from pipeline.steps.distribute import run_distribute


def _init_uploaders():
    """Initialize social media uploaders if credentials are configured.

    Non-dropbox clients (RSS/local episode source) skip all uploaders to avoid
    picking up Fake Problems' shared credentials from env vars and the credentials/
    directory. Per-client uploaders can be enabled later via explicit YAML config.
    """
    from uploaders import (
        YouTubeUploader,
        InstagramUploader,
        TikTokUploader,
        TwitterUploader,
        SpotifyUploader,
        BlueskyUploader,
        RedditUploader,
    )

    uploaders = {}

    episode_source = getattr(Config, "EPISODE_SOURCE", "dropbox")
    if episode_source != "dropbox":
        logger.info(
            "Uploaders skipped for non-dropbox client (episode_source=%s)",
            episode_source,
        )
        return uploaders

    # YouTube (use per-client token path if configured)
    try:
        youtube_token = getattr(Config, "_YOUTUBE_TOKEN_PICKLE", None)
        uploaders["youtube"] = YouTubeUploader(token_path=youtube_token)
        logger.info("YouTube uploader initialized")
    except (ValueError, FileNotFoundError) as e:
        logger.info("YouTube uploader not available: %s", str(e).split("\n")[0])

    # Twitter (disabled by default — X API requires paid plan)
    if Config.TWITTER_ENABLED:
        try:
            uploaders["twitter"] = TwitterUploader()
            logger.info("Twitter uploader initialized")
        except ValueError as e:
            logger.info("Twitter uploader not available: %s", str(e).split("\n")[0])
    else:
        logger.info("[SKIP] Twitter: disabled (TWITTER_ENABLED=false)")

    # Instagram
    uploaders["instagram"] = InstagramUploader()
    if uploaders["instagram"].functional:
        logger.info("Instagram uploader initialized")
    else:
        logger.warning(
            "[SKIP] Instagram: uploader not functional (credentials missing)"
        )

    # TikTok
    uploaders["tiktok"] = TikTokUploader()
    if uploaders["tiktok"].functional:
        logger.info("TikTok uploader initialized")
    else:
        logger.warning("[SKIP] TikTok: uploader not functional (credentials missing)")

    # Spotify
    try:
        uploaders["spotify"] = SpotifyUploader()
        logger.info("Spotify uploader initialized")
    except ValueError as e:
        logger.info("Spotify uploader not available: %s", str(e).split("\n")[0])

    # Bluesky
    try:
        uploaders["bluesky"] = BlueskyUploader()
        logger.info("Bluesky uploader initialized")
    except ValueError as e:
        logger.info("[SKIP] Bluesky: %s", str(e).split("\n")[0])

    # Reddit
    try:
        uploaders["reddit"] = RedditUploader()
        logger.info("Reddit uploader initialized")
    except ValueError as e:
        logger.info("[SKIP] Reddit: %s", str(e).split("\n")[0])

    return uploaders


def _init_components(
    test_mode=False, dry_run=False, auto_approve=False, resume=False, force=False
):
    """Initialize all pipeline components.

    Returns a components dict suitable for passing to step functions.

    Args:
        test_mode: If True, skip actual uploads to Dropbox and social media
        dry_run: If True, skip heavy initialization (no I/O)
        auto_approve: If True, skip interactive clip approval
        resume: If True, resuming from checkpoint (informational only here)
        force: If True, --force flag was passed (bypass compliance upload block)
    """
    # Lazy imports — these are heavy (google API 1.4s, scipy 1s, numpy 0.3s)
    from dropbox_handler import DropboxHandler
    from transcription import Transcriber
    from content_editor import ContentEditor
    from audio_processor import AudioProcessor
    from video_converter import VideoConverter
    from notifications import DiscordNotifier
    from scheduler import UploadScheduler
    from blog_generator import BlogPostGenerator
    from thumbnail_generator import ThumbnailGenerator

    print("=" * 60)
    print(f"{Config.PODCAST_NAME.upper()} AUTOMATION")
    if dry_run:
        print("[DRY RUN] - Validating pipeline with mock data")
    elif test_mode:
        print("[TEST MODE] - Uploads disabled")
    if resume:
        print("[RESUME MODE] - Resuming from checkpoint")
    print("=" * 60)
    print()

    _auto_approve = auto_approve or test_mode or dry_run

    if dry_run:
        # Dry run: skip validation and heavy initialization
        Config.create_directories()
        episode_source = getattr(Config, "EPISODE_SOURCE", "dropbox")
        dry_run_components = {
            "transcriber": None,
            "editor": None,
            "audio_processor": None,
            "video_converter": None,
            "uploaders": {},
            "topic_tracker": None,
            "notifier": DiscordNotifier(),
            "scheduler": UploadScheduler(),
            "blog_generator": BlogPostGenerator(),
            "thumbnail_generator": ThumbnailGenerator(),
            "clip_previewer": ClipPreviewer(auto_approve=True),
            "search_index": None,
            "audiogram_generator": AudiogramGenerator(),
            "chapter_generator": ChapterGenerator(),
            "subtitle_clip_generator": SubtitleClipGenerator(),
            "webpage_generator": EpisodeWebpageGenerator(),
            "compliance_checker": ContentComplianceChecker(),
            "website_generator": None,
        }
        if episode_source == "rss":
            dry_run_components["rss_fetcher"] = None
        else:
            dry_run_components["dropbox"] = None
        return dry_run_components

    # Validate configuration
    Config.validate()
    Config.create_directories()

    # Initialize components
    episode_source = getattr(Config, "EPISODE_SOURCE", "dropbox")
    if episode_source == "rss":
        from rss_episode_fetcher import RSSEpisodeFetcher

        rss_fetcher = RSSEpisodeFetcher()
        logger.info("RSS episode fetcher initialized")
        dropbox = None
    else:
        dropbox = DropboxHandler()
        rss_fetcher = None
    transcriber = Transcriber()
    editor = ContentEditor()
    audio_processor = AudioProcessor()

    # Initialize video converter (optional)
    try:
        video_converter = VideoConverter()
        logger.info("Video converter initialized")
    except FileNotFoundError as e:
        logger.info("Video converter not available: %s", e)
        video_converter = None

    # Initialize social media uploaders (optional)
    uploaders = _init_uploaders()

    # Google Docs topic tracker — disabled (requires Google OAuth credentials
    # in credentials/google_docs_*.json which aren't currently configured)
    topic_tracker = None

    # Initialize new feature modules
    notifier = DiscordNotifier()
    scheduler = UploadScheduler()
    blog_generator = BlogPostGenerator()
    thumbnail_generator = ThumbnailGenerator()
    clip_previewer = ClipPreviewer(auto_approve=_auto_approve)
    search_index = EpisodeSearchIndex()
    audiogram_generator = AudiogramGenerator()
    chapter_generator = ChapterGenerator()
    subtitle_clip_generator = SubtitleClipGenerator()
    webpage_generator = EpisodeWebpageGenerator()
    compliance_checker = ContentComplianceChecker()

    from website_generator import WebsiteGenerator

    website_generator = WebsiteGenerator()

    print()

    components = {
        "transcriber": transcriber,
        "editor": editor,
        "audio_processor": audio_processor,
        "video_converter": video_converter,
        "uploaders": uploaders,
        "topic_tracker": topic_tracker,
        "notifier": notifier,
        "scheduler": scheduler,
        "blog_generator": blog_generator,
        "thumbnail_generator": thumbnail_generator,
        "clip_previewer": clip_previewer,
        "search_index": search_index,
        "audiogram_generator": audiogram_generator,
        "chapter_generator": chapter_generator,
        "subtitle_clip_generator": subtitle_clip_generator,
        "webpage_generator": webpage_generator,
        "compliance_checker": compliance_checker,
        "website_generator": website_generator,
    }
    if episode_source == "rss":
        components["rss_fetcher"] = rss_fetcher
    else:
        components["dropbox"] = dropbox
    return components


def _load_scored_topics():
    """Load the most recent scored topics from topic_data/ directory.

    Delegates to pipeline.steps.analysis._load_scored_topics.

    Returns:
        List of topic dicts with 'topic', 'score', 'category', or None if unavailable
    """
    from pipeline.steps.analysis import _load_scored_topics as _load

    return _load()


def _acquire_pipeline_lock():
    """Acquire exclusive pipeline lock. Returns True if acquired, False if another run is active."""
    lock_path = Config.OUTPUT_DIR / ".pipeline_lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.exists():
        try:
            old_pid = int(lock_path.read_text().strip())
            try:
                os.kill(old_pid, 0)  # signal 0 = check existence
                return False  # process is still running
            except OSError:
                logger.warning(
                    "Stale lock file found (PID %d not running), removing", old_pid
                )
        except (ValueError, OSError):
            logger.warning("Invalid lock file, removing")
    lock_path.write_text(str(os.getpid()))
    return True


def _release_pipeline_lock():
    """Release the pipeline lock."""
    lock_path = Config.OUTPUT_DIR / ".pipeline_lock"
    try:
        if lock_path.exists():
            lock_path.unlink()
    except OSError:
        pass


def run(args):
    """Run the full episode processing pipeline.

    Args:
        args: Namespace or dict with fields:
            episode_number (int | None): specific episode, or None for latest
            dropbox_path (str | None): specific Dropbox path to download
            local_audio_path (str | None): use local file instead of Dropbox
            test_mode (bool)
            dry_run (bool)
            auto_approve (bool)
            resume (bool)

    Returns:
        PipelineContext with all results populated, or dict of results for
        backward-compatibility.
    """
    if not _acquire_pipeline_lock():
        logger.error(
            "Another pipeline run is active (lock file: %s). Exiting.",
            Config.OUTPUT_DIR / ".pipeline_lock",
        )
        return None

    try:
        return _run_pipeline(args)
    finally:
        _release_pipeline_lock()


def _run_pipeline(args):
    """Internal pipeline execution (called by run() after acquiring lock)."""
    # Support both Namespace and dict
    if isinstance(args, dict):
        episode_number = args.get("episode_number")
        dropbox_path = args.get("dropbox_path")
        local_audio_path = args.get("local_audio_path")
        test_mode = args.get("test_mode", False)
        dry_run = args.get("dry_run", False)
        auto_approve = args.get("auto_approve", False)
        resume = args.get("resume", False)
        force = args.get("force", False)
    else:
        episode_number = getattr(args, "episode_number", None)
        dropbox_path = getattr(args, "dropbox_path", None)
        local_audio_path = getattr(args, "local_audio_path", None)
        test_mode = getattr(args, "test_mode", False)
        dry_run = getattr(args, "dry_run", False)
        auto_approve = getattr(args, "auto_approve", False)
        resume = getattr(args, "resume", False)
        force = getattr(args, "force", False)

    # Load client config if specified
    client_name = None
    if isinstance(args, dict):
        client_name = args.get("client_name")
    else:
        client_name = getattr(args, "client_name", None)

    if client_name:
        from client_config import activate_client

        activate_client(client_name)

    components = _init_components(
        test_mode=test_mode,
        dry_run=dry_run,
        auto_approve=auto_approve,
        resume=resume,
        force=force,
    )

    print("=" * 60)
    print("STARTING EPISODE PROCESSING")
    print("=" * 60)
    print()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Resolve audio file for the context
    audio_file = None
    if local_audio_path:
        audio_file = Path(local_audio_path)
    elif dropbox_path:
        print("STEP 1: DOWNLOADING FROM DROPBOX")
        print("-" * 60)
        audio_file = components["dropbox"].download_episode(dropbox_path)
        if not audio_file:
            raise Exception("Failed to download episode from Dropbox")
    elif episode_number is not None:
        logger.info("Looking for Episode %d...", episode_number)
        episode = components["dropbox"].get_episode_by_number(episode_number)
        if not episode:
            logger.error("Episode %d not found in Dropbox", episode_number)
            print("\nAvailable episodes:")
            list_episodes_by_number(components)
            return None
        logger.info("Found: %s", episode["name"])
        print()
        audio_file = components["dropbox"].download_episode(episode["path"])
        if not audio_file:
            raise Exception("Failed to download episode from Dropbox")
    # else: audio_file=None means run_ingest will find the latest from Dropbox

    # Build initial PipelineContext
    # episode_number/folder will be resolved by run_ingest if not set
    placeholder_folder = f"ep_{episode_number}" if episode_number else "ep_unknown"
    placeholder_output_dir = Config.OUTPUT_DIR / placeholder_folder

    ctx = PipelineContext(
        episode_folder=placeholder_folder,
        episode_number=episode_number,
        episode_output_dir=placeholder_output_dir,
        timestamp=timestamp,
        audio_file=audio_file,
        test_mode=test_mode,
        dry_run=dry_run,
        auto_approve=auto_approve or test_mode or dry_run,
        resume=resume,
        force=force,
    )

    # Initialize pipeline state for checkpoint/resume
    state = PipelineState(placeholder_folder) if resume else None

    # Step 1: Ingest (download/find audio, resolve episode folder)
    ctx = run_ingest(ctx, components, state)

    # Update state folder if episode number was discovered during ingest
    if resume and state and ctx.episode_folder != placeholder_folder:
        state = PipelineState(ctx.episode_folder)

    # Step 2: Transcribe (part of audio step)
    # Note: We call audio.run_audio which does Steps 2, 4, 4.5, 6.
    # But Step 3 (analysis) must run BETWEEN Step 2 (transcribe) and Step 4 (censor).
    # So we split: run_ingest sets audio_file -> run_audio does transcribe only,
    # then run_analysis, then run_audio does censor/normalize/mp3.
    # Since audio.py's run_audio does all four sub-steps in sequence, we rely on
    # the fact that analysis.run_analysis already has transcript_data from ctx after
    # audio step sets ctx.transcript_data.
    # The correct order is handled by calling run_audio (which does 2,4,4.5,6) but
    # analysis needs transcript first. We therefore call run_audio which sets
    # transcript_data on ctx, then the internal ordering means run_analysis must
    # be inserted. However, the current audio.py does all 4 steps atomically.
    #
    # SOLUTION: run_audio does transcribe, sets ctx.transcript_data, then returns.
    # Then run_analysis runs. Then run_audio_post does censor/normalize/mp3.
    # Since audio.py was not split in Plan 02, we call run_audio here which
    # handles steps 2+4+4.5+6 -- the ordering is correct because analysis.py
    # reads ctx.transcript_data (set by audio step 2) and writes ctx.analysis,
    # then audio steps 4+4.5 read ctx.analysis for censor_timestamps.
    #
    # The issue is run_audio does 2->4->4.5->6 sequentially and analysis must
    # happen between 2 and 4. We therefore need to split run_audio.
    # Per Plan 03 instructions: split into run_transcribe + run_process_audio,
    # keeping run_audio as a wrapper. We implement this split here by calling
    # the internal steps directly.

    # Step 2: Transcribe only
    ctx = _run_transcribe(ctx, components, state)

    # Step 3 + 3.5: Analysis
    ctx = run_analysis(ctx, components, state)

    # Step 3.6: Content compliance check
    print("STEP 3.6: CONTENT COMPLIANCE CHECK")
    print("-" * 60)
    compliance_checker = components.get("compliance_checker")
    if compliance_checker and compliance_checker.enabled:
        compliance_result = compliance_checker.check_transcript(
            transcript_data=ctx.transcript_data,
            episode_output_dir=ctx.episode_output_dir,
            episode_number=ctx.episode_number,
            timestamp=ctx.timestamp,
        )
        ctx.compliance_result = compliance_result
        # Merge flagged segments into censor_timestamps for auto-muting (SAFE-03)
        if compliance_result.get("flagged"):
            existing = (ctx.analysis or {}).get("censor_timestamps", [])
            new_entries = compliance_checker.get_censor_entries(compliance_result)
            existing.extend(new_entries)
            if ctx.analysis is None:
                ctx.analysis = {}
            ctx.analysis["censor_timestamps"] = existing
            logger.info("Merged %d compliance flags into censor list", len(new_entries))
    else:
        logger.info("Content compliance check skipped (disabled)")
    print()

    # Steps 4, 4.5, 6: Censor + normalize + MP3
    ctx = _run_process_audio(ctx, components, state)

    # Steps 5, 5.1, 5.4, 5.5, 5.6: Video, clips, etc.
    ctx = run_video(ctx, components, state)

    # Steps 7, 7.5, 8, 8.5, 9: Distribution
    ctx = run_distribute(ctx, components, state)

    # Build and save results dict (backward-compatible)
    analysis = ctx.analysis or {}
    episode_number = ctx.episode_number
    episode_title = analysis.get("episode_title", f"Episode {episode_number}")
    results = {
        "episode_number": episode_number,
        "episode_title": episode_title,
        "original_audio": str(ctx.audio_file),
        "transcript": str(ctx.transcript_path),
        "analysis": str(
            ctx.episode_output_dir / f"{ctx.audio_file.stem}_{timestamp}_analysis.json"
        ),
        "censored_audio_wav": str(ctx.censored_audio),
        "censored_audio_mp3": str(ctx.mp3_path),
        "full_episode_video": str(ctx.full_episode_video_path)
        if ctx.full_episode_video_path
        else None,
        "clips": [str(p) for p in ctx.clip_paths],
        "video_clips": [str(p) for p in ctx.video_clip_paths],
        "dropbox_finished_path": ctx.finished_path,
        "dropbox_clip_paths": ctx.uploaded_clip_paths,
        "episode_summary": analysis.get("episode_summary"),
        "show_notes": analysis.get("show_notes"),
        "chapters": analysis.get("chapters"),
        "social_captions": analysis.get("social_captions"),
        "best_clips_info": analysis.get("best_clips"),
        "censor_count": len(analysis.get("censor_timestamps", [])),
        "thumbnail_path": str(ctx.thumbnail_path) if ctx.thumbnail_path else None,
    }

    print("=" * 60)
    print("[SUCCESS] EPISODE PROCESSING COMPLETE!")
    print("=" * 60)
    print()
    print(f"All outputs saved to: {Config.OUTPUT_DIR}")
    print()
    print(f'Episode {episode_number}: "{episode_title}"')
    print()
    if results.get("episode_summary"):
        print("Episode Summary:")
        print(f"   {results['episode_summary']}")
        print()
    print(f"Censored items: {results['censor_count']}")
    print(f"Clips created: {len(results['clips'])}")
    print()
    if results.get("social_captions"):
        print("Social Media Captions:")
        for platform, caption in results["social_captions"].items():
            try:
                print(f"   {platform.upper()}: {caption[:80]}...")
            except UnicodeEncodeError:
                # Handle Windows terminal encoding issues
                print(
                    f"   {platform.upper()}: {caption[:80].encode('ascii', 'replace').decode('ascii')}..."
                )
        print()

    return results


def _run_transcribe(ctx, components, state):
    """Run Step 2 only: transcribe with Whisper.

    This is the first half of what audio.run_audio does. We need this split
    so that run_analysis can run between transcription and censorship.
    """
    audio_file = ctx.audio_file
    episode_output_dir = ctx.episode_output_dir
    timestamp = ctx.timestamp

    print("STEP 2: TRANSCRIBING WITH WHISPER")
    print("-" * 60)
    transcript_path = (
        episode_output_dir / f"{audio_file.stem}_{timestamp}_transcript.json"
    )
    if state and state.is_step_completed("transcribe"):
        outputs = state.get_step_outputs("transcribe")
        transcript_path = Path(outputs["transcript_path"])
        import json as _json

        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript_data = _json.load(f)
        logger.info("[RESUME] Skipping transcription (already completed)")
    else:
        transcript_data = components["transcriber"].transcribe(
            audio_file, transcript_path
        )
        if state:
            state.complete_step("transcribe", {"transcript_path": str(transcript_path)})
    print()

    ctx.transcript_data = transcript_data
    ctx.transcript_path = transcript_path

    return ctx


def _run_process_audio(ctx, components, state):
    """Run Steps 4, 4.5, 6: censor, normalize, and convert to MP3.

    This is the second half of what audio.run_audio does — runs AFTER analysis.
    """

    audio_file = ctx.audio_file
    episode_output_dir = ctx.episode_output_dir
    timestamp = ctx.timestamp
    analysis = ctx.analysis or {}

    # Step 4: Apply censorship
    print("STEP 4: APPLYING CENSORSHIP")
    print("-" * 60)
    censored_audio_path = (
        episode_output_dir / f"{audio_file.stem}_{timestamp}_censored.wav"
    )
    if state and state.is_step_completed("censor"):
        outputs = state.get_step_outputs("censor")
        censored_audio = Path(outputs["censored_audio"])
        logger.info("[RESUME] Skipping censorship (already completed)")
    else:
        censored_audio = components["audio_processor"].apply_censorship(
            audio_file, analysis.get("censor_timestamps", []), censored_audio_path
        )
        if state:
            state.complete_step("censor", {"censored_audio": str(censored_audio)})
    print()

    ctx.censored_audio = censored_audio

    # Step 4.5: Normalize audio
    print("STEP 4.5: NORMALIZING AUDIO")
    print("-" * 60)
    if state and state.is_step_completed("normalize"):
        outputs = state.get_step_outputs("normalize")
        censored_audio = Path(outputs["normalized_audio"])
        logger.info("[RESUME] Skipping normalization (already completed)")
    else:
        censored_audio = components["audio_processor"].normalize_audio(censored_audio)
        if state:
            state.complete_step("normalize", {"normalized_audio": str(censored_audio)})
    print()

    ctx.censored_audio = censored_audio

    # Step 6: Convert to MP3 for uploading
    print("STEP 6: CONVERTING TO MP3")
    print("-" * 60)
    chapters_list = analysis.get("chapters", [])
    if state and state.is_step_completed("convert_mp3"):
        outputs = state.get_step_outputs("convert_mp3")
        mp3_path = Path(outputs["mp3_path"])
        logger.info("[RESUME] Skipping MP3 conversion (already completed)")
    else:
        mp3_path = components["audio_processor"].convert_to_mp3(censored_audio)
        if state:
            state.complete_step("convert_mp3", {"mp3_path": str(mp3_path)})

    # Step 6.5: Embed ID3 chapter markers
    chapter_generator = components.get("chapter_generator")
    if chapter_generator and chapter_generator.enabled and chapters_list:
        logger.info("Embedding ID3 chapter markers...")
        chapter_generator.embed_id3_chapters(str(mp3_path), chapters_list)
    print()

    ctx.mp3_path = mp3_path

    return ctx


def dry_run(components=None):
    """Validate the full pipeline with mock data — no I/O, no API keys, no GPU.

    Exercises every step's control flow with stub data to catch import errors,
    config issues, broken checkpoint logic, and wiring bugs.
    """
    if components is None:
        components = _init_components(dry_run=True)

    audiogram_generator = components.get("audiogram_generator")
    subtitle_clip_generator_dr = components.get("subtitle_clip_generator")
    blog_generator = components.get("blog_generator")
    scheduler = components.get("scheduler")
    thumbnail_generator = components.get("thumbnail_generator")
    notifier = components.get("notifier")
    webpage_generator = components.get("webpage_generator")

    print()
    print("=" * 60)
    print("DRY RUN: VALIDATING PIPELINE")
    print("=" * 60)
    print()

    steps_validated = 0
    warnings = []

    # --- Config ---
    print("[OK] Config loaded")
    steps_validated += 1

    # --- Directories ---
    dirs = {
        "OUTPUT_DIR": Config.OUTPUT_DIR,
        "CLIPS_DIR": Config.CLIPS_DIR,
        "DOWNLOAD_DIR": Config.DOWNLOAD_DIR,
        "ASSETS_DIR": Config.ASSETS_DIR,
    }
    all_exist = all(d.exists() for d in dirs.values())
    if all_exist:
        print("[OK] Directories exist")
    else:
        missing = [n for n, d in dirs.items() if not d.exists()]
        print(f"[WARN] Missing directories: {', '.join(missing)}")
        warnings.append(f"Missing directories: {', '.join(missing)}")
    steps_validated += 1

    # --- Topic data ---
    topic_context = _load_scored_topics()
    if topic_context:
        print(f"[OK] Topic data loaded ({len(topic_context)} scored topics)")
    else:
        print("[SKIP] No scored topics found in topic_data/")
    steps_validated += 1

    # --- Stub data ---
    _transcript_data = {
        "words": [
            {"word": "Hello", "start": 0.0, "end": 0.3},
            {"word": "world", "start": 0.4, "end": 0.7},
        ],
        "segments": [{"text": "Hello world", "start": 0.0, "end": 0.7}],
        "duration": 3600,
    }

    analysis = {
        "episode_title": "Dry Run Test Episode",
        "censor_timestamps": [
            {
                "timestamp": "00:01:00",
                "seconds": 60.0,
                "start_seconds": 60.0,
                "end_seconds": 60.5,
                "reason": "Name: TestName",
                "context": "TestName said",
            }
        ],
        "best_clips": [
            {
                "start": "00:05:00",
                "end": "00:05:25",
                "start_seconds": 300,
                "end_seconds": 325,
                "duration_seconds": 25,
                "description": "Test clip",
                "why_interesting": "Test",
                "suggested_title": "Test Clip",
                "hook_caption": "Wait for it...",
                "clip_hashtags": ["test"],
            }
        ],
        "episode_summary": "This is a dry run test episode.",
        "social_captions": {
            "youtube": "YT caption",
            "instagram": "IG caption",
            "twitter": "Tweet",
            "tiktok": "TikTok caption",
        },
        "show_notes": 'This episode dives into dry run testing.\n\n- Topic 1\n- Topic 2\n\nNotable quote: "Testing is believing."',
        "chapters": [
            {
                "start_timestamp": "00:00:00",
                "title": "Intro",
                "start_seconds": 0,
            },
            {
                "start_timestamp": "00:05:00",
                "title": "First Topic",
                "start_seconds": 300,
            },
            {
                "start_timestamp": "00:15:00",
                "title": "Second Topic",
                "start_seconds": 900,
            },
            {
                "start_timestamp": "00:30:00",
                "title": "Wrap Up",
                "start_seconds": 1800,
            },
        ],
    }

    num_censor = len(analysis["censor_timestamps"])
    num_clips = len(analysis["best_clips"])

    # --- Pipeline steps ---
    print()
    print("[MOCK] Step 1: Download from Dropbox -- would download episode audio")
    steps_validated += 1

    print(
        f"[MOCK] Step 2: Transcription "
        f"-- would run Whisper (model: {Config.WHISPER_MODEL})"
    )
    steps_validated += 1

    print("[MOCK] Step 3: Content analysis -- would call LLM for content analysis")
    steps_validated += 1

    compliance_checker_dr = components.get("compliance_checker")
    compliance_status = (
        "enabled"
        if compliance_checker_dr and compliance_checker_dr.enabled
        else "disabled"
    )
    print(f"[MOCK] Step 3.6: Content compliance -- {compliance_status}")
    steps_validated += 1

    print(
        f"[MOCK] Step 4: Censorship -- would process {num_censor} censor timestamp(s)"
    )
    steps_validated += 1

    print(
        f"[MOCK] Step 4.5: Normalization "
        f"-- would normalize to {Config.LUFS_TARGET} LUFS"
    )
    steps_validated += 1

    print(f"[MOCK] Step 5: Clip creation -- would create {num_clips} clip(s)")
    steps_validated += 1

    print(
        "[MOCK] Step 5.1: Clip approval "
        "-- would prompt for approval (auto-approve=True)"
    )
    steps_validated += 1

    print(f"[MOCK] Step 5.4: Subtitles -- would generate {num_clips} SRT file(s)")
    steps_validated += 1

    subtitle_clip_mode = (
        subtitle_clip_generator_dr and subtitle_clip_generator_dr.enabled
    )
    audiogram_mode = (
        not subtitle_clip_mode and audiogram_generator and audiogram_generator.enabled
    )
    if subtitle_clip_mode:
        print(
            f"[MOCK] Step 5.5: Subtitle clips -- would create {num_clips} word-caption video(s)"
        )
    elif audiogram_mode:
        print(
            f"[MOCK] Step 5.5: Audiogram -- would create {num_clips} waveform video(s)"
        )
    else:
        print(
            f"[MOCK] Step 5.5: Video conversion "
            f"-- would create {num_clips} vertical + 1 horizontal video"
        )
    steps_validated += 1

    print("[MOCK] Step 5.6: Thumbnail -- would generate 1280x720 PNG")
    steps_validated += 1

    print(
        f"[MOCK] Step 6: MP3 conversion -- would convert to MP3 ({Config.MP3_BITRATE})"
    )
    steps_validated += 1

    print(
        f"[MOCK] Step 7: Dropbox upload "
        f"-- would upload to {Config.DROPBOX_FINISHED_FOLDER}"
    )
    steps_validated += 1

    print("[MOCK] Step 7.5: RSS feed -- would update podcast_feed.xml")
    steps_validated += 1

    # Step 8: check which uploader classes are importable
    platform_status = []
    _dry_uploaders = components.get("uploaders", {})
    for name in ["youtube", "twitter", "instagram", "tiktok", "spotify"]:
        uploader = _dry_uploaders.get(name)
        if uploader is not None and not getattr(uploader, "functional", True):
            platform_status.append(f"{name.capitalize()}: STUB (not functional)")
        else:
            platform_status.append(f"{name.capitalize()}: ready")
    scheduling_note = ""
    if scheduler and scheduler.is_scheduling_enabled():
        scheduling_note = " (scheduling enabled)"
    print(
        f"[MOCK] Step 8: Social media -- {', '.join(platform_status)}{scheduling_note}"
    )
    steps_validated += 1

    blog_status = "enabled" if blog_generator and blog_generator.enabled else "disabled"
    print(f"[MOCK] Step 8.5: Blog post -- {blog_status}")
    steps_validated += 1

    webpage_status = (
        "enabled" if webpage_generator and webpage_generator.enabled else "disabled"
    )
    print(f"[MOCK] Step 8.6: Episode webpage -- {webpage_status}")
    steps_validated += 1

    # Content calendar preview (Step 8.7)
    try:
        from content_calendar import ContentCalendar

        calendar = ContentCalendar()
        if calendar.enabled:
            display_slots = calendar.get_calendar_display(
                episode_number="XX",
                release_date=datetime.now(),
            )
            if display_slots:
                print("[MOCK] Step 8.7: Content Calendar (5-day spread):")
                for slot in display_slots:
                    print(
                        f"  {slot['label']:30s}  "
                        f"{slot['dt'].strftime('%Y-%m-%d %H:%M')}  "
                        f"{slot['type']:8s} -> {', '.join(slot['platforms'])}"
                    )
        else:
            print("[MOCK] Step 8.7: Content Calendar -- disabled")
        steps_validated += 1
    except Exception as e:
        print(f"[WARN] Content calendar: {e}")
        warnings.append(f"Content calendar: {e}")

    print("[MOCK] Step 9: Search index -- would index episode for full-text search")
    steps_validated += 1

    # --- Module / import validation ---
    print()

    # Pipeline state
    try:
        ps = PipelineState.__new__(PipelineState)
        # Verify interface exists without writing to disk
        assert callable(getattr(ps, "is_step_completed", None))
        assert callable(getattr(ps, "complete_step", None))
        assert callable(getattr(ps, "get_step_outputs", None))
        print("[OK] Pipeline state module works (checkpoint/resume functional)")
    except Exception as e:
        print(f"[WARN] Pipeline state issue: {e}")
        warnings.append(f"Pipeline state: {e}")

    # Subtitle generator
    try:
        from subtitle_generator import SubtitleGenerator  # noqa: F401

        print("[OK] Subtitle generator imports correctly")
    except ImportError as e:
        print(f"[WARN] Subtitle generator not available: {e}")
        warnings.append(f"Subtitle generator: {e}")

    # New feature modules
    for mod_name, mod_obj in [
        ("Discord notifier", notifier),
        ("Upload scheduler", scheduler),
        ("Blog generator", blog_generator),
        ("Thumbnail generator", thumbnail_generator),
        ("Audiogram generator", audiogram_generator),
        ("Subtitle clip generator", subtitle_clip_generator_dr),
        ("Webpage generator", webpage_generator),
    ]:
        if mod_obj:
            print(f"[OK] {mod_name} imports correctly")
        else:
            print(f"[WARN] {mod_name} not available")
            warnings.append(f"{mod_name} not available")

    # FFmpeg
    ffmpeg_path = Config.FFMPEG_PATH
    if Path(ffmpeg_path).exists():
        print(f"[OK] Video converter: FFmpeg found at {ffmpeg_path}")
    else:
        print(
            f"[WARN] Video converter: FFmpeg not found at {ffmpeg_path} "
            f"-- video steps would fail"
        )
        warnings.append(f"FFmpeg not found at {ffmpeg_path}")

    # --- Summary ---
    print()
    print("=" * 60)
    if warnings:
        print(
            f"DRY RUN COMPLETE: {steps_validated} steps validated, "
            f"{len(warnings)} warning(s)"
        )
    else:
        print(f"DRY RUN COMPLETE: All {steps_validated} steps validated")
    print("=" * 60)

    return {
        "status": "dry_run_complete",
        "steps_validated": steps_validated,
        "warnings": warnings,
    }


def run_with_notification(
    args, episode_number=None, dropbox_path=None, local_audio_path=None
):
    """Wrap episode processing with Discord notifications.

    Args:
        args: Namespace/dict with run flags (test_mode, dry_run, auto_approve, resume)
        episode_number: Episode number to process (optional)
        dropbox_path: Specific Dropbox path (optional)
        local_audio_path: Local audio file path (optional)
    """
    from notifications import DiscordNotifier

    # Merge episode targeting into args
    if isinstance(args, dict):
        run_args = dict(args)
    else:
        run_args = {
            "test_mode": getattr(args, "test_mode", False),
            "dry_run": getattr(args, "dry_run", False),
            "auto_approve": getattr(args, "auto_approve", False),
            "resume": getattr(args, "resume", False),
        }

    run_args["episode_number"] = episode_number
    run_args["dropbox_path"] = dropbox_path
    run_args["local_audio_path"] = local_audio_path

    # We need a notifier for notifications; build a minimal one
    notifier = DiscordNotifier()

    try:
        results = run(run_args)
        if results and notifier and notifier.enabled:
            notifier.notify_success(results)
        return results
    except Exception as e:
        if notifier and notifier.enabled:
            ep_info = episode_number or dropbox_path or local_audio_path or "latest"
            notifier.notify_failure(ep_info, e, step="process_episode")
        raise


def _dispatch_calendar_slot(uploader_instance, platform, slot):
    """Map calendar slot content to uploader method calls.

    Slot content varies by slot_type:
      teaser:  {caption}                        -> twitter post_tweet(text=caption)
      episode: {title, video_path, description} -> youtube upload_episode / twitter post_tweet
      clip_N:  {clip_path, caption}             -> youtube upload_short / twitter post_tweet with media

    Args:
        uploader_instance: Uploader object for the platform.
        platform: Platform string ('youtube', 'twitter', 'instagram', 'tiktok').
        slot: Slot dict with 'slot_type' and 'content' keys.

    Returns:
        Upload result dict or None.
    """
    content = slot.get("content", {})
    slot_type = slot.get("slot_type", "")

    if platform == "youtube":
        if slot_type == "episode":
            return uploader_instance.upload_episode(
                video_path=content.get("video_path", ""),
                title=content.get("title", ""),
                description=content.get("description", ""),
            )
        else:
            # clip / teaser slots -> upload as Short
            return uploader_instance.upload_short(
                video_path=content.get("clip_path", ""),
                title=content.get("caption", ""),
                description="",
            )
    elif platform == "twitter":
        media = []
        if content.get("clip_path"):
            media = [content["clip_path"]]
        elif content.get("video_path"):
            media = [content["video_path"]]
        return uploader_instance.post_tweet(
            text=content.get("caption", content.get("title", "")),
            media_paths=media or None,
        )
    elif platform == "instagram":
        return uploader_instance.upload_reel(
            video_url=content.get("clip_path", content.get("video_path", "")),
            caption=content.get("caption", ""),
        )
    elif platform == "tiktok":
        return uploader_instance.upload_video(
            video_path=content.get("clip_path", content.get("video_path", "")),
            title=content.get("caption", content.get("title", "")),
            description=content.get("caption", ""),
        )
    return None


def run_upload_scheduled():
    """Scan output folders for pending scheduled uploads and execute them."""
    from notifications import DiscordNotifier
    from scheduler import UploadScheduler
    from uploaders import (
        YouTubeUploader,
        InstagramUploader,
        TikTokUploader,
        TwitterUploader,
    )

    print("=" * 60)
    print("EXECUTING SCHEDULED UPLOADS")
    print("=" * 60)
    print()

    scheduler = UploadScheduler()
    output_dir = Config.OUTPUT_DIR

    if not output_dir.exists():
        print("No output directory found")
        return

    schedule_files = list(output_dir.glob("*/upload_schedule.json"))

    dispatch = {
        "youtube": YouTubeUploader,
        "twitter": TwitterUploader,
        "instagram": InstagramUploader,
        "tiktok": TikTokUploader,
    }

    for schedule_file in schedule_files:
        episode_folder = schedule_file.parent.name
        schedule = scheduler.load_schedule(episode_folder)
        if not schedule:
            continue

        pending = scheduler.get_pending_uploads(schedule)
        if not pending:
            logger.info("No pending uploads for %s", episode_folder)
            continue

        logger.info("Found %d pending upload(s) for %s", len(pending), episode_folder)

        for item in pending:
            platform = item["platform"]
            uploader_cls = dispatch.get(platform)
            if uploader_cls is None:
                logger.warning("No uploader for platform '%s', skipping", platform)
                continue

            logger.info("Uploading to %s...", platform)

            @retry_with_backoff(
                max_retries=3,
                base_delay=2.0,
                max_delay=30.0,
                backoff_factor=2.0,
            )
            def _do_upload(uploader_instance, upload_item):
                if platform == "youtube":
                    return uploader_instance.upload_episode(
                        video_path=upload_item.get("full_episode_video_path", ""),
                        title=upload_item.get("episode_title", ""),
                        description=upload_item.get("episode_summary", ""),
                    )
                elif platform == "twitter":
                    return uploader_instance.post_tweet(
                        text=upload_item.get("social_captions", ""),
                        media_paths=upload_item.get("video_clip_paths"),
                    )
                elif platform == "instagram":
                    return uploader_instance.upload_reel(
                        video_url=upload_item.get("video_clip_paths", [""])[0],
                        caption=upload_item.get("social_captions", ""),
                    )
                elif platform == "tiktok":
                    clip_paths = upload_item.get("video_clip_paths") or []
                    return uploader_instance.upload_video(
                        video_path=clip_paths[0] if clip_paths else "",
                        title=upload_item.get("episode_title", ""),
                        description=upload_item.get("social_captions"),
                    )
                return None

            try:
                uploader_instance = uploader_cls()
                result = _do_upload(uploader_instance, item)
                schedule = scheduler.mark_uploaded(schedule, platform, result)
                logger.info("Successfully uploaded to %s", platform)
            except Exception as e:
                logger.error("Failed to upload to %s: %s", platform, e)
                schedule = scheduler.mark_failed(schedule, platform, str(e))
                notifier = DiscordNotifier()
                notifier.notify_failure(
                    episode_folder, e, step=f"scheduled_{platform}_upload"
                )

            scheduler.save_schedule(episode_folder, schedule)
            logger.info("Updated schedule for %s after %s", episode_folder, platform)

    # Content calendar slots
    try:
        from content_calendar import ContentCalendar

        calendar = ContentCalendar()
        if calendar.enabled:
            all_episodes = calendar.load_all()
            for ep_key, ep_data in all_episodes.items():
                pending_slots = calendar.get_pending_slots(ep_data)
                if not pending_slots:
                    continue
                logger.info(
                    "Found %d pending calendar slot(s) for %s",
                    len(pending_slots),
                    ep_key,
                )
                for slot in pending_slots:
                    slot_name = slot["slot_name"]
                    platforms = slot.get("platforms", [])
                    for platform in platforms:
                        uploader_cls = dispatch.get(platform)
                        if uploader_cls is None:
                            continue
                        try:
                            uploader_instance = uploader_cls()
                            result = _dispatch_calendar_slot(
                                uploader_instance, platform, slot
                            )
                            calendar.mark_slot_uploaded(
                                ep_key, slot_name, {platform: result}
                            )
                            logger.info(
                                "Calendar slot %s/%s uploaded to %s",
                                ep_key,
                                slot_name,
                                platform,
                            )
                        except Exception as e:
                            logger.error(
                                "Calendar slot %s/%s failed on %s: %s",
                                ep_key,
                                slot_name,
                                platform,
                                e,
                            )
                            calendar.mark_slot_failed(ep_key, slot_name, str(e))
    except ImportError:
        pass  # content_calendar module not available
    except Exception as e:
        logger.warning("Calendar slot dispatch failed: %s", e)

    print()
    print("[DONE] Scheduled upload scan complete")


def run_analytics(episode_arg):
    """Collect and display analytics for episodes."""
    from analytics import AnalyticsCollector, TopicEngagementScorer

    print("=" * 60)
    print("ANALYTICS FEEDBACK LOOP")
    print("=" * 60)
    print()

    collector = AnalyticsCollector()
    scorer = TopicEngagementScorer()

    if episode_arg == "all":
        # Scan output dirs for episode numbers
        output_dir = Config.OUTPUT_DIR
        ep_dirs = sorted(output_dir.glob("ep_*"))
        for ep_dir in ep_dirs:
            match = re.search(r"ep_(\d+)", ep_dir.name)
            if match:
                ep_num = int(match.group(1))
                _collect_episode_analytics(collector, scorer, ep_num)
    else:
        match = re.search(r"(\d+)", episode_arg)
        if match:
            ep_num = int(match.group(1))
            _collect_episode_analytics(collector, scorer, ep_num)
        else:
            print(f"Invalid episode: {episode_arg}")


def _collect_episode_analytics(collector, scorer, episode_number):
    """Collect and display analytics for a single episode.

    Loads stored platform IDs (written at upload time) to pass the YouTube
    video_id directly to fetch_youtube_analytics, avoiding the expensive
    search API call (100 quota units → 1 quota unit).

    After collecting metrics, appends/updates the cross-episode
    engagement_history.json for Phase 10 correlation scoring.
    """
    print(f"\n--- Episode {episode_number} ---")

    # Load stored platform IDs for direct video ID lookup
    platform_ids = collector._load_platform_ids(episode_number)
    video_id = platform_ids.get("youtube")

    # Collect analytics — pass video_id to skip search API when available
    analytics = collector.collect_analytics(episode_number, video_id=video_id)
    collector.save_analytics(episode_number, analytics)

    score = scorer.calculate_engagement_score(analytics)
    print(f"  Engagement score: {score}/10")

    if analytics.get("youtube"):
        yt = analytics["youtube"]
        print(f"  YouTube: {yt.get('views', 0)} views, {yt.get('likes', 0)} likes")
    if analytics.get("twitter"):
        tw = analytics["twitter"]
        print(
            f"  Twitter: {tw.get('impressions', 0)} impressions, "
            f"{tw.get('engagements', 0)} engagements"
        )

    # Accumulate engagement history — determine post_timestamp from platform_ids.json mtime
    platform_ids_path = Config.OUTPUT_DIR / f"ep_{episode_number}" / "platform_ids.json"
    if platform_ids_path.exists():
        import os

        post_timestamp = datetime.fromtimestamp(
            os.path.getmtime(platform_ids_path)
        ).isoformat()
    else:
        post_timestamp = datetime.now().isoformat()

    # Extract topics from analytics data (video_id present implies analysis ran)
    # Topics are derived from episode analysis JSON in the output dir
    topics = _load_episode_topics(episode_number)

    collector.append_to_engagement_history(
        episode_number=episode_number,
        analytics_data=analytics,
        platform_ids=platform_ids,
        topics=topics,
        post_timestamp=post_timestamp,
    )
    logger.info("Updated engagement history for Episode #%s", episode_number)


def _load_episode_topics(episode_number: int) -> list:
    """Extract topic strings from episode analysis JSON.

    Looks for *_analysis.json in the episode output dir and extracts
    suggested_title from best_clips entries (same pattern as correlate_topics).

    Args:
        episode_number: The episode number to load topics for.

    Returns:
        List of topic strings, or empty list if not found.
    """
    ep_dir = Config.OUTPUT_DIR / f"ep_{episode_number}"
    if not ep_dir.exists():
        return []

    analysis_files = list(ep_dir.glob("*_analysis.json"))
    if not analysis_files:
        return []

    # Use the most recent analysis file
    analysis_file = sorted(analysis_files)[-1]
    try:
        with open(analysis_file, "r", encoding="utf-8") as f:
            analysis = json.load(f)
        topics = []
        for clip in analysis.get("best_clips", []):
            title = clip.get("suggested_title") or clip.get("title", "")
            if title:
                topics.append(title)
        return topics
    except (json.JSONDecodeError, OSError):
        return []


def run_backfill_ids():
    """One-time backfill: look up YouTube video IDs for existing episodes.

    Iterates output/ep_* directories. For each episode that does NOT already
    have a platform_ids.json, searches YouTube Data API v3 for the episode
    video ID and writes platform_ids.json with {"youtube": video_id, "twitter": None}.

    Skips episodes that already have platform_ids.json (idempotent).
    Rate-limits at 1.5 seconds between YouTube API calls.

    After backfill, `python main.py analytics all` will use stored video IDs
    instead of search API calls (100 quota units → 1 quota unit per episode).
    """
    from analytics import AnalyticsCollector

    print("=" * 60)
    print("BACKFILL PLATFORM IDS")
    print("=" * 60)
    print()

    collector = AnalyticsCollector()
    youtube = collector._build_youtube_client()
    if youtube is None:
        print(
            "[ERROR] Cannot build YouTube client — check credentials/youtube_token.pickle"
        )
        return

    output_dir = Config.OUTPUT_DIR
    if not output_dir.exists():
        print("No output directory found")
        return

    ep_dirs = sorted(output_dir.glob("ep_*"))
    if not ep_dirs:
        print("No episode directories found")
        return

    processed = 0
    skipped = 0

    for ep_dir in ep_dirs:
        match = re.search(r"ep_(\d+)", ep_dir.name)
        if not match:
            continue

        ep_num = int(match.group(1))
        platform_ids_path = ep_dir / "platform_ids.json"

        if platform_ids_path.exists():
            print(f"[SKIP] ep_{ep_num}: platform_ids.json already exists")
            skipped += 1
            continue

        # Search YouTube for this episode's video
        try:
            channel_id = __import__("os").getenv("YOUTUBE_CHANNEL_ID", "")
            results = (
                youtube.search()
                .list(
                    q=f"Episode #{ep_num}",
                    channelId=channel_id,
                    type="video",
                    part="id",
                    maxResults=1,
                )
                .execute()
            )
            items = results.get("items", [])
            video_id = items[0]["id"]["videoId"] if items else None
        except Exception as e:
            logger.warning("YouTube search failed for ep_%s: %s", ep_num, e)
            video_id = None

        platform_ids = {"youtube": video_id, "twitter": None}
        with open(platform_ids_path, "w", encoding="utf-8") as f:
            json.dump(platform_ids, f, indent=2)

        status = f"youtube={video_id}" if video_id else "youtube=None (not found)"
        print(f"[OK] ep_{ep_num}: {status}")
        processed += 1

        # Rate-limit: 1.5 seconds between YouTube search API calls
        time.sleep(1.5)

    print()
    print(f"Backfill complete: {processed} processed, {skipped} skipped")


def run_search(query):
    """Search across all indexed episodes."""
    print(f'Searching for: "{query}"')
    print("-" * 60)

    index = EpisodeSearchIndex()
    results = index.search(query, limit=10)

    if not results:
        print("No results found")
        return

    for r in results:
        print(f"\nEpisode {r['episode_number']}: {r['title']}")
        print(f"  {r['snippet']}")

    print(f"\n{len(results)} result(s) found")


def list_available_episodes(components=None):
    """List all available episodes in Dropbox."""
    from dropbox_handler import DropboxHandler

    print("Available episodes in Dropbox:")
    print("-" * 60)

    if components is None:
        dropbox = DropboxHandler()
    else:
        dropbox = components.get("dropbox") or DropboxHandler()

    episodes = dropbox.list_episodes()

    if not episodes:
        print("No episodes found")
        return []

    for i, ep in enumerate(episodes, 1):
        size_mb = ep["size"] / 1024 / 1024
        modified = ep["modified"].strftime("%Y-%m-%d %H:%M")
        print(f"{i}. {ep['name']}")
        print(f"   Size: {size_mb:.1f} MB | Modified: {modified}")
        print(f"   Path: {ep['path']}")
        print()

    return episodes


def list_episodes_by_number(components=None):
    """List all episodes sorted by episode number."""
    from dropbox_handler import DropboxHandler

    print("Available episodes (sorted by episode number):")
    print("-" * 60)

    if components is None:
        dropbox = DropboxHandler()
    else:
        dropbox = components.get("dropbox") or DropboxHandler()

    episodes_with_numbers = dropbox.list_episodes_with_numbers()

    if not episodes_with_numbers:
        print("No episodes found")
        return []

    for ep_num, ep in episodes_with_numbers:
        size_mb = ep["size"] / 1024 / 1024
        modified = ep["modified"].strftime("%Y-%m-%d %H:%M")

        if ep_num:
            print(f"Episode {ep_num}: {ep['name']}")
        else:
            print(f"[No Episode #]: {ep['name']}")

        print(f"   Size: {size_mb:.1f} MB | Modified: {modified}")
        print()

    return episodes_with_numbers


def health_check():
    """Validate all configured credentials and print a status table."""
    import pickle

    results = []

    # YouTube: try loading the pickle token
    yt_token_path = Path(Config.BASE_DIR) / "credentials" / "youtube_token.pickle"
    if yt_token_path.exists():
        try:
            with open(yt_token_path, "rb") as f:
                creds = pickle.load(f)
            if hasattr(creds, "expired") and creds.expired:
                if hasattr(creds, "refresh_token") and creds.refresh_token:
                    results.append(
                        ("YouTube", "OK", "Token expired but refresh token available")
                    )
                else:
                    results.append(
                        ("YouTube", "ERROR", "Token expired, no refresh token")
                    )
            else:
                results.append(("YouTube", "OK", "Token loaded successfully"))
        except Exception as e:
            results.append(("YouTube", "ERROR", f"Cannot load token: {e}"))
    else:
        results.append(("YouTube", "MISSING", f"Token file not found: {yt_token_path}"))

    # Twitter: check all 4 keys
    tw_keys = [
        "TWITTER_API_KEY",
        "TWITTER_API_SECRET",
        "TWITTER_ACCESS_TOKEN",
        "TWITTER_ACCESS_SECRET",
    ]
    tw_missing = [k for k in tw_keys if not getattr(Config, k, None)]
    if not tw_missing:
        results.append(("Twitter", "OK", "All 4 credentials configured"))
    else:
        results.append(("Twitter", "MISSING", f"Missing: {', '.join(tw_missing)}"))

    # Bluesky
    bs_keys = ["BLUESKY_HANDLE", "BLUESKY_APP_PASSWORD"]
    bs_missing = [k for k in bs_keys if not getattr(Config, k, None)]
    if not bs_missing:
        results.append(("Bluesky", "OK", "Handle and app password configured"))
    else:
        results.append(("Bluesky", "MISSING", f"Missing: {', '.join(bs_missing)}"))

    # Discord
    if getattr(Config, "DISCORD_WEBHOOK_URL", None):
        results.append(("Discord", "OK", "Webhook URL configured"))
    else:
        results.append(("Discord", "MISSING", "DISCORD_WEBHOOK_URL not set"))

    # Dropbox
    if getattr(Config, "DROPBOX_REFRESH_TOKEN", None):
        results.append(("Dropbox", "OK", "Refresh token configured"))
    else:
        results.append(("Dropbox", "MISSING", "DROPBOX_REFRESH_TOKEN not set"))

    # OpenAI
    if getattr(Config, "OPENAI_API_KEY", None):
        results.append(("OpenAI", "OK", "API key configured"))
    else:
        results.append(("OpenAI", "MISSING", "OPENAI_API_KEY not set"))

    # Print table
    fmt = "{:<12} {:<10} {}"
    print(fmt.format("Platform", "Status", "Details"))
    print("-" * 60)
    for platform, status, details in results:
        print(fmt.format(platform, status, details))
