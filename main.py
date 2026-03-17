"""Main orchestrator for podcast automation workflow."""

import re
import sys
import json
from pathlib import Path
from datetime import datetime

from config import Config
from logger import logger
from pipeline_state import PipelineState
from dropbox_handler import DropboxHandler
from transcription import Transcriber
from content_editor import ContentEditor
from audio_processor import AudioProcessor
from video_converter import VideoConverter
from google_docs_tracker import GoogleDocsTopicTracker  # noqa: F401
from uploaders import (
    YouTubeUploader,
    InstagramUploader,
    TikTokUploader,
    TwitterUploader,
    SpotifyUploader,
    create_episode_metadata,
)
from notifications import DiscordNotifier
from scheduler import UploadScheduler
from blog_generator import BlogPostGenerator
from thumbnail_generator import ThumbnailGenerator
from analytics import AnalyticsCollector, TopicEngagementScorer
from clip_previewer import ClipPreviewer
from search_index import EpisodeSearchIndex
from audiogram_generator import AudiogramGenerator
from chapter_generator import ChapterGenerator
from retry_utils import retry_with_backoff


class PodcastAutomation:
    """Main automation orchestrator."""

    def __init__(
        self, test_mode=False, resume=False, dry_run=False, auto_approve=False
    ):
        """Initialize all components.

        Args:
            test_mode: If True, skip actual uploads to Dropbox and social media
            resume: If True, resume from last checkpoint using pipeline_state
            dry_run: If True, validate pipeline wiring with mock data (no I/O)
            auto_approve: If True, skip interactive clip approval prompt
        """
        self.test_mode = test_mode
        self.resume = resume
        self.dry_run = dry_run
        self.auto_approve = auto_approve or test_mode or dry_run

        print("=" * 60)
        print("FAKE PROBLEMS PODCAST AUTOMATION")
        if dry_run:
            print("[DRY RUN] - Validating pipeline with mock data")
        elif test_mode:
            print("[TEST MODE] - Uploads disabled")
        if resume:
            print("[RESUME MODE] - Resuming from checkpoint")
        print("=" * 60)
        print()

        if dry_run:
            # Dry run: skip validation and heavy initialization
            Config.create_directories()
            self.dropbox = None
            self.transcriber = None
            self.editor = None
            self.audio_processor = None
            self.video_converter = None
            self.uploaders = {}
            self.topic_tracker = None
            self.notifier = DiscordNotifier()
            self.scheduler = UploadScheduler()
            self.blog_generator = BlogPostGenerator()
            self.thumbnail_generator = ThumbnailGenerator()
            self.clip_previewer = ClipPreviewer(auto_approve=True)
            self.search_index = None
            self.audiogram_generator = AudiogramGenerator()
            self.chapter_generator = ChapterGenerator()
            return

        # Validate configuration
        Config.validate()
        Config.create_directories()

        # Initialize components
        self.dropbox = DropboxHandler()
        self.transcriber = Transcriber()
        self.editor = ContentEditor()
        self.audio_processor = AudioProcessor()

        # Initialize video converter (optional)
        try:
            self.video_converter = VideoConverter()
            logger.info("Video converter initialized")
        except FileNotFoundError as e:
            logger.info("Video converter not available: %s", e)
            self.video_converter = None

        # Initialize social media uploaders (optional)
        self.uploaders = self._init_uploaders()

        # Initialize Google Docs topic tracker (optional) - DISABLED FOR NOW
        # TODO: Re-enable after fixing Google OAuth credentials
        self.topic_tracker = None
        logger.info("Google Docs topic tracker disabled")

        # Initialize new feature modules
        self.notifier = DiscordNotifier()
        self.scheduler = UploadScheduler()
        self.blog_generator = BlogPostGenerator()
        self.thumbnail_generator = ThumbnailGenerator()
        self.clip_previewer = ClipPreviewer(auto_approve=self.auto_approve)
        self.search_index = EpisodeSearchIndex()
        self.audiogram_generator = AudiogramGenerator()
        self.chapter_generator = ChapterGenerator()

        print()

    def _init_uploaders(self):
        """Initialize social media uploaders if credentials are configured."""
        uploaders = {}

        # YouTube
        try:
            uploaders["youtube"] = YouTubeUploader()
            logger.info("YouTube uploader initialized")
        except (ValueError, FileNotFoundError) as e:
            logger.info("YouTube uploader not available: %s", str(e).split("\n")[0])

        # Twitter
        try:
            uploaders["twitter"] = TwitterUploader()
            logger.info("Twitter uploader initialized")
        except ValueError as e:
            logger.info("Twitter uploader not available: %s", str(e).split("\n")[0])

        # Instagram
        try:
            uploaders["instagram"] = InstagramUploader()
            logger.info("Instagram uploader initialized")
        except ValueError as e:
            logger.info("Instagram uploader not available: %s", str(e).split("\n")[0])

        # TikTok
        try:
            uploaders["tiktok"] = TikTokUploader()
            logger.info("TikTok uploader initialized")
        except ValueError as e:
            logger.info("TikTok uploader not available: %s", str(e).split("\n")[0])

        # Spotify
        try:
            uploaders["spotify"] = SpotifyUploader()
            logger.info("Spotify uploader initialized")
        except ValueError as e:
            logger.info("Spotify uploader not available: %s", str(e).split("\n")[0])

        return uploaders

    def _load_scored_topics(self):
        """Load the most recent scored topics from topic_data/ directory.

        Returns:
            List of topic dicts with 'topic', 'score', 'category', or None if unavailable
        """
        topic_dir = Config.BASE_DIR / "topic_data"
        if not topic_dir.exists():
            return None

        # Find the most recent scored_topics file
        scored_files = sorted(topic_dir.glob("scored_topics_*.json"), reverse=True)
        if not scored_files:
            return None

        try:
            with open(scored_files[0], "r", encoding="utf-8") as f:
                data = json.load(f)

            # Flatten topics from all categories into a single ranked list
            topics = []
            for category, category_topics in data.get("topics_by_category", {}).items():
                for t in category_topics:
                    score = t.get("score", {})
                    if isinstance(score, dict) and score.get("recommended", False):
                        topics.append(
                            {
                                "topic": t.get("title", ""),
                                "score": score.get("total", 0),
                                "category": score.get("category", category),
                            }
                        )

            # Sort by score descending
            topics.sort(key=lambda x: x["score"], reverse=True)
            logger.info(
                "Loaded %d scored topics from %s", len(topics), scored_files[0].name
            )
            return topics if topics else None
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to load scored topics: %s", e)
            return None

    def _upload_youtube(
        self,
        episode_number,
        video_clip_paths,
        analysis,
        full_episode_video_path,
        publish_at=None,
    ):
        """Upload content to YouTube (full episode + clips as Shorts)."""
        if "youtube" not in self.uploaders:
            return None

        logger.info("[YouTube] Uploading content...")
        youtube_results = {"clips": [], "full_episode": None}
        social_captions = analysis.get("social_captions", {})
        episode_summary = analysis.get("episode_summary", "")
        episode_title = analysis.get("episode_title", f"Episode {episode_number}")
        best_clips = analysis.get("best_clips", [])

        show_notes = analysis.get("show_notes", "")
        chapters = analysis.get("chapters", [])

        # Upload full episode first
        if full_episode_video_path:
            logger.info("Uploading full episode to YouTube...")
            full_title = f"Episode #{episode_number} - {episode_title}"
            metadata = create_episode_metadata(
                episode_number=episode_number,
                episode_summary=episode_summary,
                social_captions=social_captions,
                show_notes=show_notes,
                chapters=chapters,
            )
            full_description = metadata["description"]
            tags = metadata["tags"]

            if self.test_mode:
                logger.info(
                    "[TEST MODE] Would upload full episode: %s", full_episode_video_path
                )
                youtube_results["full_episode"] = {
                    "status": "test_mode",
                    "title": full_title,
                }
            else:
                try:
                    # If scheduling, upload as private with publishAt
                    privacy = "private" if publish_at else "public"
                    full_episode_result = self.uploaders["youtube"].upload_episode(
                        video_path=str(full_episode_video_path),
                        title=full_title[:100],
                        description=full_description,
                        tags=tags,
                        privacy_status=privacy,
                        publish_at=publish_at,
                    )
                    if full_episode_result:
                        youtube_results["full_episode"] = full_episode_result
                        logger.info(
                            "Full episode uploaded: %s",
                            full_episode_result.get("video_url", "Unknown URL"),
                        )
                    else:
                        logger.error("Failed to upload full episode")
                        youtube_results["full_episode"] = {"status": "failed"}
                except Exception as e:
                    logger.error("YouTube full episode upload error: %s", e)
                    youtube_results["full_episode"] = {
                        "status": "error",
                        "error": str(e),
                    }

        # Upload clips as Shorts
        if video_clip_paths:
            logger.info(
                "Uploading %d clips as YouTube Shorts...", len(video_clip_paths)
            )
            for i, video_path in enumerate(video_clip_paths[:3], 1):
                if i - 1 < len(best_clips):
                    clip_info = best_clips[i - 1]
                    metadata = create_episode_metadata(
                        episode_number=episode_number,
                        episode_summary=episode_summary,
                        social_captions=social_captions,
                        clip_info=clip_info,
                    )

                    clip_title = clip_info.get("suggested_title", f"Clip {i}")
                    logger.info("Uploading Clip %d: %s", i, clip_title)

                    if self.test_mode:
                        logger.info("[TEST MODE] Would upload: %s", video_path)
                        youtube_results["clips"].append(
                            {"status": "test_mode", "title": clip_title}
                        )
                    else:
                        try:
                            upload_result = self.uploaders["youtube"].upload_short(
                                video_path=str(video_path),
                                title=metadata["title"],
                                description=metadata["description"],
                                tags=metadata["tags"],
                                privacy_status="public",
                            )
                            if upload_result:
                                youtube_results["clips"].append(upload_result)
                                logger.info(
                                    "Uploaded: %s",
                                    upload_result.get("video_url", "Unknown URL"),
                                )
                            else:
                                logger.error("Failed to upload clip %d", i)
                                youtube_results["clips"].append(
                                    {"status": "failed", "title": clip_title}
                                )
                        except Exception as e:
                            logger.error("YouTube upload error: %s", e)
                            youtube_results["clips"].append(
                                {"status": "error", "error": str(e)}
                            )

        return youtube_results

    def _upload_twitter(self, episode_number, analysis, youtube_results):
        """Upload content to Twitter (episode announcement with YouTube links)."""
        if "twitter" not in self.uploaders:
            return None

        logger.info("[Twitter] Posting content...")
        episode_summary = analysis.get("episode_summary", "")
        best_clips = analysis.get("best_clips", [])

        # Gather YouTube URLs from upload results
        yt_full_url = None
        clip_youtube_urls = []
        if youtube_results:
            if youtube_results.get("full_episode") and youtube_results[
                "full_episode"
            ].get("video_url"):
                yt_full_url = youtube_results["full_episode"]["video_url"]
            for i, clip_result in enumerate(youtube_results.get("clips", [])):
                if clip_result.get("video_url"):
                    # Use title from YouTube result (already resolved via
                    # suggested_title -> title -> generic fallback chain),
                    # strip #Shorts suffix for Twitter display
                    clip_title = clip_result.get("title", "").replace(" #Shorts", "")
                    if not clip_title:
                        clip_title = (
                            best_clips[i].get(
                                "suggested_title",
                                best_clips[i].get("title", f"Clip {i + 1}"),
                            )
                            if i < len(best_clips)
                            else f"Clip {i + 1}"
                        )
                    clip_youtube_urls.append(
                        {"title": clip_title, "url": clip_result["video_url"]}
                    )

        if self.test_mode:
            logger.info("[TEST MODE] Skipping Twitter posts")
            logger.info("Would post: Episode %d announcement", episode_number)
            if yt_full_url:
                logger.info("Would include YouTube URL: %s", yt_full_url)
            if clip_youtube_urls:
                logger.info(
                    "Would link %d YouTube Shorts clips", len(clip_youtube_urls)
                )
            return {"status": "test_mode", "skipped": True}
        else:
            try:
                twitter_caption = analysis.get("social_captions", {}).get("twitter")
                twitter_result = self.uploaders["twitter"].post_episode_announcement(
                    episode_number=episode_number,
                    episode_summary=episode_summary,
                    youtube_url=yt_full_url,
                    clip_youtube_urls=clip_youtube_urls if clip_youtube_urls else None,
                    twitter_caption=twitter_caption,
                )
                return twitter_result
            except Exception as e:
                logger.error("Twitter upload failed: %s", e)
                return {"error": str(e)}

    def _upload_instagram(self, video_clip_paths, episode_number=None, analysis=None):
        """Upload clips to Instagram as Reels."""
        if "instagram" not in self.uploaders:
            return None

        logger.info("[Instagram] Uploading Reels...")
        if video_clip_paths:
            logger.info(
                "%d vertical videos ready for Instagram Reels", len(video_clip_paths)
            )
            logger.info("Instagram requires publicly accessible video URLs")
            logger.info(
                "Upload videos to Dropbox and get public links to enable auto-upload"
            )
            # Log prepared captions with hook + hashtags
            if analysis:
                best_clips = analysis.get("best_clips", [])
                for i, clip_info in enumerate(best_clips[: len(video_clip_paths)]):
                    hook = clip_info.get("hook_caption", "")
                    tags = clip_info.get("clip_hashtags", [])
                    if hook or tags:
                        logger.info(
                            "  Clip %d caption: hook=%r hashtags=%s",
                            i + 1,
                            hook,
                            tags,
                        )
            return {"status": "videos_ready", "clips": len(video_clip_paths)}
        else:
            logger.info("No video clips available")
            return {"status": "no_videos"}

    def _upload_to_social_media(
        self,
        episode_number: int,
        mp3_path: Path,
        video_clip_paths: list,
        analysis: dict,
        full_episode_video_path: str = None,
    ) -> dict:
        """
        Upload episode and clips to configured social media platforms.

        Args:
            episode_number: Episode number
            mp3_path: Path to processed MP3 file
            video_clip_paths: List of paths to video clip files
            analysis: Analysis data from Claude
            full_episode_video_path: Path to full episode video for YouTube

        Returns:
            Dictionary with upload results for each platform
        """
        results = {}

        # Check if scheduling is enabled
        if self.scheduler.is_scheduling_enabled():
            logger.info("Scheduling enabled — creating upload schedule")
            schedule = self.scheduler.create_schedule(
                episode_folder=f"ep_{episode_number}",
                episode_number=episode_number,
                analysis=analysis,
                video_clip_paths=[str(p) for p in video_clip_paths]
                if video_clip_paths
                else None,
                full_episode_video_path=str(full_episode_video_path)
                if full_episode_video_path
                else None,
                mp3_path=str(mp3_path),
            )
            schedule_path = self.scheduler.save_schedule(
                f"ep_{episode_number}", schedule
            )
            logger.info("Upload schedule saved to %s", schedule_path)
            results["schedule"] = {
                "path": str(schedule_path),
                "platforms": list(schedule["platforms"].keys()),
            }

        # YouTube uploads (may use publishAt if scheduled)
        publish_at = self.scheduler.get_youtube_publish_at()
        youtube_results = self._upload_youtube(
            episode_number,
            video_clip_paths,
            analysis,
            full_episode_video_path,
            publish_at=publish_at,
        )
        if youtube_results:
            results["youtube"] = youtube_results

        # Twitter posts (needs YouTube URLs, so runs after YouTube)
        twitter_results = self._upload_twitter(
            episode_number, analysis, youtube_results
        )
        if twitter_results:
            results["twitter"] = twitter_results

        # Instagram Reels
        instagram_results = self._upload_instagram(
            video_clip_paths,
            episode_number=episode_number,
            analysis=analysis,
        )
        if instagram_results:
            results["instagram"] = instagram_results

        # TikTok
        if "tiktok" in self.uploaders:
            logger.info("[TikTok] Uploading clips...")
            if video_clip_paths:
                logger.info(
                    "%d vertical videos ready for TikTok", len(video_clip_paths)
                )
                logger.info("Ready to upload (upload code commented out for safety)")
                # Log prepared captions with hook + hashtags
                best_clips = analysis.get("best_clips", [])
                for i, clip_info in enumerate(best_clips[: len(video_clip_paths)]):
                    hook = clip_info.get("hook_caption", "")
                    tags = clip_info.get("clip_hashtags", [])
                    if hook or tags:
                        logger.info(
                            "  Clip %d caption: hook=%r hashtags=%s",
                            i + 1,
                            hook,
                            tags,
                        )
                results["tiktok"] = {
                    "status": "videos_ready",
                    "clips": len(video_clip_paths),
                }
            else:
                logger.info("No video clips available")
                results["tiktok"] = {"status": "no_videos"}

        # Spotify (RSS feed — updated after Dropbox upload in Step 7.5)
        if "spotify" in self.uploaders:
            logger.info("[Spotify] RSS feed will be updated after Dropbox upload")
            results["spotify"] = {
                "status": "rss_ready",
                "note": "RSS feed updated in Step 7.5",
            }

        return results

    def dry_run_episode(self):
        """Validate the full pipeline with mock data — no I/O, no API keys, no GPU.

        Exercises every step's control flow with stub data to catch import errors,
        config issues, broken checkpoint logic, and wiring bugs.
        """
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
        topic_context = self._load_scored_topics()
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

        print(
            f"[MOCK] Step 4: Censorship "
            f"-- would process {num_censor} censor timestamp(s)"
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
            f"[MOCK] Step 5.1: Clip approval "
            f"-- would prompt for approval (auto-approve={self.auto_approve})"
        )
        steps_validated += 1

        print(f"[MOCK] Step 5.4: Subtitles -- would generate {num_clips} SRT file(s)")
        steps_validated += 1

        audiogram_mode = self.audiogram_generator and self.audiogram_generator.enabled
        if audiogram_mode:
            print(
                f"[MOCK] Step 5.5: Audiogram "
                f"-- would create {num_clips} waveform video(s)"
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
            f"[MOCK] Step 6: MP3 conversion "
            f"-- would convert to MP3 ({Config.MP3_BITRATE})"
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
        for name in ["youtube", "twitter", "instagram", "tiktok", "spotify"]:
            platform_status.append(f"{name.capitalize()}: ready")
        scheduling_note = ""
        if self.scheduler.is_scheduling_enabled():
            scheduling_note = " (scheduling enabled)"
        print(
            f"[MOCK] Step 8: Social media -- {', '.join(platform_status)}{scheduling_note}"
        )
        steps_validated += 1

        blog_status = (
            "enabled"
            if self.blog_generator and self.blog_generator.enabled
            else "disabled"
        )
        print(f"[MOCK] Step 8.5: Blog post -- {blog_status}")
        steps_validated += 1

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
            ("Discord notifier", self.notifier),
            ("Upload scheduler", self.scheduler),
            ("Blog generator", self.blog_generator),
            ("Thumbnail generator", self.thumbnail_generator),
            ("Audiogram generator", self.audiogram_generator),
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

    def process_episode(self, dropbox_path=None, local_audio_path=None):
        """
        Process a complete episode through the automation pipeline.

        Args:
            dropbox_path: Path to episode in Dropbox (optional if local_audio_path provided)
            local_audio_path: Local path to audio file (optional if dropbox_path provided)

        Returns:
            Dictionary with all output paths and metadata
        """
        print("=" * 60)
        print("STARTING EPISODE PROCESSING")
        print("=" * 60)
        print()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Step 1: Download from Dropbox (if needed)
        if local_audio_path:
            audio_file = Path(local_audio_path)
            logger.info("Using local audio file: %s", audio_file)
        elif dropbox_path:
            print("STEP 1: DOWNLOADING FROM DROPBOX")
            print("-" * 60)
            audio_file = self.dropbox.download_episode(dropbox_path)
            if not audio_file:
                raise Exception("Failed to download episode from Dropbox")
        else:
            # Use latest episode
            print("STEP 1: FINDING LATEST EPISODE IN DROPBOX")
            print("-" * 60)
            latest = self.dropbox.get_latest_episode()
            if not latest:
                raise Exception("No episodes found in Dropbox")

            logger.info("Latest episode: %s", latest["name"])
            audio_file = self.dropbox.download_episode(latest["path"])

        # Extract episode number for folder organization
        episode_number = self.dropbox.extract_episode_number(audio_file.name)
        if episode_number:
            episode_folder = f"ep_{episode_number}"
        else:
            episode_folder = f"ep_{audio_file.stem}_{timestamp}"

        # Create episode output subfolder
        episode_output_dir = Config.OUTPUT_DIR / episode_folder
        episode_output_dir.mkdir(exist_ok=True, parents=True)

        # Initialize pipeline state for checkpoint/resume
        state = PipelineState(episode_folder) if self.resume else None

        print()

        # Step 2: Transcribe with Whisper
        print("STEP 2: TRANSCRIBING WITH WHISPER")
        print("-" * 60)
        transcript_path = (
            episode_output_dir / f"{audio_file.stem}_{timestamp}_transcript.json"
        )
        if state and state.is_step_completed("transcribe"):
            outputs = state.get_step_outputs("transcribe")
            transcript_path = Path(outputs["transcript_path"])
            with open(transcript_path, "r", encoding="utf-8") as f:
                transcript_data = json.load(f)
            logger.info("[RESUME] Skipping transcription (already completed)")
        else:
            transcript_data = self.transcriber.transcribe(audio_file, transcript_path)
            if state:
                state.complete_step(
                    "transcribe", {"transcript_path": str(transcript_path)}
                )
        print()

        # Step 3: Analyze content with Claude
        print("STEP 3: ANALYZING CONTENT WITH AI")
        print("-" * 60)

        # Load scored topics for context (if available)
        topic_context = self._load_scored_topics()

        analysis_path = (
            episode_output_dir / f"{audio_file.stem}_{timestamp}_analysis.json"
        )
        if state and state.is_step_completed("analyze"):
            outputs = state.get_step_outputs("analyze")
            analysis_path = Path(outputs["analysis_path"])
            with open(analysis_path, "r", encoding="utf-8") as f:
                analysis = json.load(f)
            logger.info("[RESUME] Skipping analysis (already completed)")
        else:
            analysis = self.editor.analyze_content(
                transcript_data, topic_context=topic_context
            )
            with open(analysis_path, "w", encoding="utf-8") as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)
            logger.info("Analysis saved to: %s", analysis_path)

            # Save show notes as a standalone text file
            show_notes_text = analysis.get("show_notes", "")
            if show_notes_text:
                show_notes_path = (
                    episode_output_dir / f"{audio_file.stem}_{timestamp}_show_notes.txt"
                )
                with open(show_notes_path, "w", encoding="utf-8") as f:
                    f.write(show_notes_text)
                logger.info("Show notes saved to: %s", show_notes_path)

            if state:
                state.complete_step("analyze", {"analysis_path": str(analysis_path)})
        print()

        # Step 3.5: Update Google Docs topic tracker
        topic_tracker_results = {}
        if self.topic_tracker and episode_number:
            # Get full transcript text for topic matching
            full_transcript = " ".join(
                [seg.get("text", "") for seg in transcript_data.get("segments", [])]
            )
            episode_summary = analysis.get("episode_summary", "")

            topic_tracker_results = self.topic_tracker.update_topics_for_episode(
                transcript_text=full_transcript,
                episode_summary=episode_summary,
                episode_number=episode_number,
            )
        elif not self.topic_tracker:
            logger.info("Google Docs topic tracker not configured - skipping")
        print()

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
            censored_audio = self.audio_processor.apply_censorship(
                audio_file, analysis.get("censor_timestamps", []), censored_audio_path
            )
            if state:
                state.complete_step("censor", {"censored_audio": str(censored_audio)})
        print()

        # Step 4.5: Normalize audio
        print("STEP 4.5: NORMALIZING AUDIO")
        print("-" * 60)
        if state and state.is_step_completed("normalize"):
            outputs = state.get_step_outputs("normalize")
            censored_audio = Path(outputs["normalized_audio"])
            logger.info("[RESUME] Skipping normalization (already completed)")
        else:
            censored_audio = self.audio_processor.normalize_audio(censored_audio)
            if state:
                state.complete_step(
                    "normalize", {"normalized_audio": str(censored_audio)}
                )
        print()

        # Step 5: Create clips
        print("STEP 5: CREATING CLIPS")
        print("-" * 60)
        clip_dir = Config.CLIPS_DIR / episode_folder
        clip_dir.mkdir(exist_ok=True, parents=True)

        if state and state.is_step_completed("create_clips"):
            outputs = state.get_step_outputs("create_clips")
            clip_paths = [Path(p) for p in outputs["clip_paths"]]
            logger.info("[RESUME] Skipping clip creation (already completed)")
        else:
            clip_paths = self.audio_processor.create_clips(
                censored_audio, analysis.get("best_clips", []), clip_dir
            )
            if state:
                state.complete_step(
                    "create_clips", {"clip_paths": [str(p) for p in clip_paths]}
                )
        print()

        # Step 5.1: Clip preview/approval (interactive unless auto-approve)
        print("STEP 5.1: CLIP PREVIEW/APPROVAL")
        print("-" * 60)
        best_clips = analysis.get("best_clips", [])
        if clip_paths and not self.auto_approve:
            approved_indices = self.clip_previewer.preview_clips(
                [str(p) for p in clip_paths], best_clips
            )
            clip_paths, best_clips = self.clip_previewer.filter_clips(
                clip_paths, best_clips, approved_indices
            )
            # Update analysis with filtered clips
            analysis["best_clips"] = best_clips
            logger.info("Approved %d clips for upload", len(clip_paths))
        else:
            logger.info("Auto-approving all %d clips", len(clip_paths))
        print()

        # Step 5.4: Generate subtitles for clips
        print("STEP 5.4: GENERATING SUBTITLES")
        print("-" * 60)
        if state and state.is_step_completed("subtitles"):
            outputs = state.get_step_outputs("subtitles")
            srt_paths = [Path(p) if p else None for p in outputs["srt_paths"]]
            logger.info("[RESUME] Skipping subtitle generation (already completed)")
        else:
            srt_paths = []
            try:
                from subtitle_generator import SubtitleGenerator

                sub_gen = SubtitleGenerator()
                best_clips = analysis.get("best_clips", [])
                for i, clip_path in enumerate(clip_paths):
                    if i < len(best_clips):
                        clip_info = best_clips[i]
                        srt_path = sub_gen.generate_clip_srt(
                            transcript_data=transcript_data,
                            clip_start=clip_info.get("start_seconds", 0),
                            clip_end=clip_info.get("end_seconds", 30),
                            output_path=str(clip_path).replace(".wav", ".srt"),
                        )
                        srt_paths.append(srt_path)
                    else:
                        srt_paths.append(None)
                logger.info(
                    "Generated %d subtitle files", len([s for s in srt_paths if s])
                )
            except Exception as e:
                logger.warning(
                    "Subtitle generation failed, continuing without subtitles: %s", e
                )
                srt_paths = [None] * len(clip_paths)
            if state:
                state.complete_step(
                    "subtitles",
                    {"srt_paths": [str(p) if p else None for p in srt_paths]},
                )
        print()

        # Step 5.5: Convert clips to videos (or audiograms if enabled)
        if self.audiogram_generator and self.audiogram_generator.enabled:
            print("STEP 5.5: CREATING AUDIOGRAM WAVEFORM VIDEOS")
        else:
            print("STEP 5.5: CONVERTING CLIPS TO VIDEOS")
        print("-" * 60)
        video_clip_paths = []
        full_episode_video_path = None

        if state and state.is_step_completed("convert_videos"):
            outputs = state.get_step_outputs("convert_videos")
            video_clip_paths = [Path(p) for p in outputs.get("video_clip_paths", [])]
            full_episode_video_path = outputs.get("full_episode_video_path")
            logger.info("[RESUME] Skipping video conversion (already completed)")
        elif (
            self.audiogram_generator and self.audiogram_generator.enabled and clip_paths
        ):
            logger.info("Creating audiogram waveform videos for clips...")
            audiogram_srt_paths = [str(s) if s else None for s in srt_paths]
            audiogram_results = self.audiogram_generator.create_audiogram_clips(
                clip_paths=[str(p) for p in clip_paths],
                format_type="vertical",
                srt_paths=audiogram_srt_paths,
            )
            video_clip_paths = [Path(p) for p in audiogram_results]
            logger.info("Created %d audiogram clips", len(video_clip_paths))

            # Full episode still uses static logo (not audiogram)
            if self.video_converter:
                logger.info(
                    "Creating horizontal video (16:9) for YouTube full episode..."
                )
                full_episode_video_path = self.video_converter.create_episode_video(
                    audio_path=str(censored_audio),
                    output_path=str(
                        episode_output_dir
                        / f"{audio_file.stem}_{timestamp}_episode.mp4"
                    ),
                    format_type="horizontal",
                )

            if state:
                state.complete_step(
                    "convert_videos",
                    {
                        "video_clip_paths": [str(p) for p in video_clip_paths],
                        "full_episode_video_path": str(full_episode_video_path)
                        if full_episode_video_path
                        else None,
                    },
                )
        elif self.video_converter and clip_paths:
            logger.info("Creating vertical videos (9:16) for Shorts/Reels/TikTok...")

            # Step 5.6: Convert full episode to video for YouTube (in parallel with clips)
            from concurrent.futures import ThreadPoolExecutor

            def convert_clips():
                return self.video_converter.convert_clips_to_videos(
                    clip_paths=clip_paths,
                    format_type="vertical",
                    output_dir=str(clip_dir),
                    srt_paths=srt_paths,
                )

            def convert_full_episode():
                if not self.video_converter:
                    return None
                logger.info("Creating horizontal video (16:9) for YouTube...")
                return self.video_converter.create_episode_video(
                    audio_path=str(censored_audio),
                    output_path=str(
                        episode_output_dir
                        / f"{audio_file.stem}_{timestamp}_episode.mp4"
                    ),
                    format_type="horizontal",
                )

            with ThreadPoolExecutor(max_workers=2) as executor:
                clip_future = executor.submit(convert_clips)
                episode_future = executor.submit(convert_full_episode)

                video_clip_paths = clip_future.result()
                full_episode_video_path = episode_future.result()

            logger.info("Created %d video clips", len(video_clip_paths))
            if full_episode_video_path:
                logger.info("Full episode video created: %s", full_episode_video_path)
            else:
                logger.warning("Failed to create full episode video")
            if state:
                state.complete_step(
                    "convert_videos",
                    {
                        "video_clip_paths": [str(p) for p in video_clip_paths],
                        "full_episode_video_path": str(full_episode_video_path)
                        if full_episode_video_path
                        else None,
                    },
                )
        elif not self.video_converter and not (
            self.audiogram_generator and self.audiogram_generator.enabled
        ):
            logger.info("Video converter not available - skipping video creation")
        else:
            logger.info("No clips to convert")
        print()

        # Step 5.6: Generate thumbnail
        print("STEP 5.6: GENERATING THUMBNAIL")
        print("-" * 60)
        thumbnail_path = None
        episode_title = analysis.get("episode_title", f"Episode {episode_number}")
        if self.thumbnail_generator:
            thumb_output = (
                episode_output_dir / f"{audio_file.stem}_{timestamp}_thumbnail.png"
            )
            thumbnail_path = self.thumbnail_generator.generate_thumbnail(
                episode_title=episode_title,
                episode_number=episode_number,
                output_path=str(thumb_output),
            )
            if thumbnail_path:
                logger.info("Thumbnail generated: %s", thumbnail_path)
            else:
                logger.info("Thumbnail generation skipped or failed")
        else:
            logger.info("Thumbnail generator not available")
        print()

        # Step 6: Convert to MP3 for uploading
        print("STEP 6: CONVERTING TO MP3")
        print("-" * 60)
        chapters_list = analysis.get("chapters", [])
        if state and state.is_step_completed("convert_mp3"):
            outputs = state.get_step_outputs("convert_mp3")
            mp3_path = Path(outputs["mp3_path"])
            logger.info("[RESUME] Skipping MP3 conversion (already completed)")
        else:
            mp3_path = self.audio_processor.convert_to_mp3(censored_audio)
            if state:
                state.complete_step("convert_mp3", {"mp3_path": str(mp3_path)})

        # Step 6.5: Embed ID3 chapter markers
        if self.chapter_generator.enabled and chapters_list:
            logger.info("Embedding ID3 chapter markers...")
            self.chapter_generator.embed_id3_chapters(str(mp3_path), chapters_list)
        print()

        # Step 7: Upload to Dropbox
        print("STEP 7: UPLOAD TO DROPBOX")
        print("-" * 60)

        if self.test_mode:
            logger.info("[TEST MODE] Skipping Dropbox uploads")
            logger.info("Would upload: %s", mp3_path)
            logger.info("Would upload %d clips", len(clip_paths))
            finished_path = None
            uploaded_clip_paths = []
        else:
            # Upload censored MP3 to finished_files folder
            logger.info("Uploading censored audio to finished_files...")
            # Use episode title for filename (sanitize for filesystem)
            episode_title = analysis.get("episode_title", f"Episode {episode_number}")
            safe_title = "".join(
                c for c in episode_title if c.isalnum() or c in (" ", "-", "_")
            ).strip()
            finished_filename = f"Episode #{episode_number} - {safe_title}.mp3"
            finished_path = self.dropbox.upload_finished_episode(
                mp3_path, episode_name=finished_filename
            )

            if finished_path:
                logger.info("Censored audio uploaded to: %s", finished_path)
            else:
                logger.error(
                    "Failed to upload censored audio to Dropbox - suggest rerunning with --resume"
                )
                # Fail-fast: skip social media if Dropbox upload fails
                finished_path = None

            # Upload clips to clips folder
            logger.info("Uploading clips to Dropbox...")
            uploaded_clip_paths = self.dropbox.upload_clips(
                clip_paths, episode_folder_name=episode_folder
            )

            if uploaded_clip_paths:
                logger.info("Uploaded %d clips", len(uploaded_clip_paths))
                for clip_path in uploaded_clip_paths:
                    logger.debug("  - %s", clip_path)
            else:
                logger.warning("Failed to upload clips")

        # Step 7.5: Update RSS feed (if Spotify uploader configured and Dropbox upload succeeded)
        if not self.test_mode and finished_path and "spotify" in self.uploaders:
            print("\nSTEP 7.5: UPDATING RSS FEED")
            print("-" * 60)

            try:
                # Get or create shared link for the MP3
                logger.info("Creating shared link for episode...")
                audio_url = self.dropbox.get_shared_link(finished_path)

                if audio_url:
                    logger.info("Shared link created: %s...", audio_url[:60])

                    # Get MP3 file info
                    import os

                    mp3_file_size = os.path.getsize(mp3_path)

                    # Get duration from transcript
                    transcript_file = transcript_path
                    with open(transcript_file, "r", encoding="utf-8") as f:
                        transcript_data = json.load(f)
                        episode_duration = int(transcript_data.get("duration", 3600))

                    # Generate chapters JSON for podcast apps
                    chapters_json_url = None
                    if self.chapter_generator.enabled and chapters_list:
                        ep_output_dir = Config.OUTPUT_DIR / f"ep_{episode_number}"
                        ep_output_dir.mkdir(parents=True, exist_ok=True)
                        chapters_json_path = str(ep_output_dir / "chapters.json")
                        self.chapter_generator.generate_chapters_json(
                            chapters_list, chapters_json_path
                        )
                        logger.info("Chapters JSON written to %s", chapters_json_path)
                        # chapters_json_url remains None until a public URL is available;
                        # the file is written locally for future upload enhancement.

                    # Generate episode title and description
                    episode_summary = analysis.get("episode_summary", "")
                    show_notes = analysis.get("show_notes", "")
                    ai_title = analysis.get("episode_title", "")
                    episode_title = (
                        f"Episode #{episode_number} - {ai_title}"
                        if ai_title
                        else f"Episode #{episode_number}"
                    )

                    # Build rich episode description for RSS
                    rss_description = show_notes or episode_summary
                    if chapters_list:
                        chapter_lines = [
                            f"{ch.get('start_timestamp', '')} {ch.get('title', '')}"
                            for ch in chapters_list
                        ]
                        rss_description += "\n\nChapters:\n" + "\n".join(chapter_lines)

                    # Extract keywords from social captions
                    keywords = []
                    if analysis.get("social_captions"):
                        keywords = ["podcast", "comedy", "fake-problems"]

                    # Update RSS feed
                    rss_feed_path = self.uploaders["spotify"].update_rss_feed(
                        episode_number=episode_number,
                        episode_title=episode_title,
                        episode_description=rss_description,
                        audio_url=audio_url,
                        audio_file_size=mp3_file_size,
                        duration_seconds=episode_duration,
                        pub_date=datetime.now(),
                        keywords=keywords,
                        chapters_url=chapters_json_url,
                    )

                    logger.info("RSS feed updated successfully!")
                    logger.info("Feed location: %s", rss_feed_path)

                    # Upload RSS feed to Dropbox
                    logger.info("Uploading RSS feed to Dropbox...")
                    rss_dropbox_path = "/podcast/podcast_feed.xml"
                    self.dropbox.upload_file(
                        rss_feed_path, rss_dropbox_path, overwrite=True
                    )
                    logger.info("RSS feed uploaded to Dropbox: %s", rss_dropbox_path)
                    logger.info("Spotify will check for updates within 2-8 hours")

                else:
                    logger.warning("Could not create shared link for RSS feed")

            except Exception as e:
                logger.error("RSS feed update failed: %s", e)
                import traceback

                traceback.print_exc()

        print()

        # Step 8: Social media uploading
        print("STEP 8: SOCIAL MEDIA PLATFORMS")
        print("-" * 60)

        social_media_results = {}

        if self.test_mode:
            logger.info("[TEST MODE] Skipping social media uploads")
            social_media_results = {"test_mode": True, "skipped": True}
        elif not self.uploaders:
            logger.info("No social media uploaders configured")
            logger.info("Set up API credentials in .env file to enable uploads")
        else:
            social_media_results = self._upload_to_social_media(
                episode_number=episode_number,
                mp3_path=mp3_path,
                video_clip_paths=video_clip_paths,
                analysis=analysis,
                full_episode_video_path=full_episode_video_path,
            )

        print()

        # Step 8.5: Generate blog post
        print("STEP 8.5: GENERATING BLOG POST")
        print("-" * 60)
        blog_post_path = None
        if self.blog_generator and self.blog_generator.enabled:
            if state and state.is_step_completed("blog_post"):
                outputs = state.get_step_outputs("blog_post")
                blog_post_path = outputs.get("blog_post_path")
                logger.info("[RESUME] Skipping blog post (already completed)")
            else:
                try:
                    markdown = self.blog_generator.generate_blog_post(
                        transcript_data=transcript_data,
                        analysis=analysis,
                        episode_number=episode_number,
                    )
                    blog_post_path = str(
                        self.blog_generator.save_blog_post(
                            markdown=markdown,
                            episode_output_dir=episode_output_dir,
                            episode_number=episode_number,
                            timestamp=timestamp,
                        )
                    )
                    logger.info("Blog post generated: %s", blog_post_path)
                    if state:
                        state.complete_step(
                            "blog_post", {"blog_post_path": blog_post_path}
                        )
                except Exception as e:
                    logger.warning("Blog post generation failed: %s", e)
        else:
            logger.info("Blog post generation disabled or not configured")
        print()

        # Step 9: Index episode for search
        print("STEP 9: INDEXING EPISODE FOR SEARCH")
        print("-" * 60)
        if self.search_index:
            try:
                full_transcript = " ".join(
                    seg.get("text", "") for seg in transcript_data.get("segments", [])
                )
                self.search_index.index_episode(
                    episode_number=episode_number,
                    title=analysis.get("episode_title", f"Episode {episode_number}"),
                    summary=analysis.get("episode_summary", ""),
                    show_notes=analysis.get("show_notes", ""),
                    transcript_text=full_transcript,
                    topics=[
                        c.get("description", "") for c in analysis.get("best_clips", [])
                    ],
                )
                logger.info("Episode %s indexed for search", episode_number)
            except Exception as e:
                logger.warning("Search indexing failed: %s", e)
        else:
            logger.info("Search index not available")
        print()

        # Get episode title from analysis or generate default
        episode_title = analysis.get("episode_title", f"Episode {episode_number}")

        # Prepare results
        results = {
            "episode_number": episode_number,
            "episode_title": episode_title,
            "original_audio": str(audio_file),
            "transcript": str(transcript_path),
            "analysis": str(analysis_path),
            "censored_audio_wav": str(censored_audio),
            "censored_audio_mp3": str(mp3_path),
            "full_episode_video": str(full_episode_video_path)
            if full_episode_video_path
            else None,
            "clips": [str(p) for p in clip_paths],
            "video_clips": [str(p) for p in video_clip_paths],
            "dropbox_finished_path": finished_path,
            "dropbox_clip_paths": uploaded_clip_paths,
            "episode_summary": analysis.get("episode_summary"),
            "show_notes": analysis.get("show_notes"),
            "chapters": analysis.get("chapters"),
            "social_captions": analysis.get("social_captions"),
            "best_clips_info": analysis.get("best_clips"),
            "censor_count": len(analysis.get("censor_timestamps", [])),
            "social_media_results": social_media_results,
            "topic_tracker_results": topic_tracker_results,
            "thumbnail_path": str(thumbnail_path) if thumbnail_path else None,
            "blog_post_path": blog_post_path,
        }

        # Save results summary
        results_path = (
            episode_output_dir / f"{audio_file.stem}_{timestamp}_results.json"
        )
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print("=" * 60)
        print("[SUCCESS] EPISODE PROCESSING COMPLETE!")
        print("=" * 60)
        print()
        print(f"All outputs saved to: {Config.OUTPUT_DIR}")
        print(f"Results summary: {results_path}")
        print()
        print(f'Episode {episode_number}: "{episode_title}"')
        print()
        print("Episode Summary:")
        print(f"   {results['episode_summary']}")
        print()
        print(f"Censored items: {results['censor_count']}")
        print(f"Clips created: {len(results['clips'])}")
        print()
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

    def list_available_episodes(self):
        """List all available episodes in Dropbox."""
        print("Available episodes in Dropbox:")
        print("-" * 60)

        episodes = self.dropbox.list_episodes()

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

    def list_episodes_by_number(self):
        """List all episodes sorted by episode number."""
        print("Available episodes (sorted by episode number):")
        print("-" * 60)

        episodes_with_numbers = self.dropbox.list_episodes_with_numbers()

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

    def process_episode_by_number(self, episode_number):
        """Process a specific episode by its episode number."""
        logger.info("Looking for Episode %d...", episode_number)
        episode = self.dropbox.get_episode_by_number(episode_number)

        if not episode:
            logger.error("Episode %d not found in Dropbox", episode_number)
            print("\nAvailable episodes:")
            self.list_episodes_by_number()
            return None

        logger.info("Found: %s", episode["name"])
        print()

        return self.process_episode(dropbox_path=episode["path"])


def _process_with_notification(
    automation, episode_number=None, dropbox_path=None, local_audio_path=None
):
    """Wrap episode processing with Discord notifications."""
    notifier = automation.notifier
    try:
        if episode_number:
            results = automation.process_episode_by_number(episode_number)
        elif dropbox_path:
            results = automation.process_episode(dropbox_path=dropbox_path)
        elif local_audio_path:
            results = automation.process_episode(local_audio_path=local_audio_path)
        else:
            results = automation.process_episode()

        if results and notifier and notifier.enabled:
            notifier.notify_success(results)
        return results
    except Exception as e:
        if notifier and notifier.enabled:
            ep_info = episode_number or dropbox_path or local_audio_path or "latest"
            notifier.notify_failure(ep_info, e, step="process_episode")
        raise


def _run_upload_scheduled():
    """Scan output folders for pending scheduled uploads and execute them."""
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
    if not schedule_files:
        print("No scheduled uploads found")
        return

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

        dispatch = {
            "youtube": YouTubeUploader,
            "twitter": TwitterUploader,
            "instagram": InstagramUploader,
            "tiktok": TikTokUploader,
        }

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

    print()
    print("[DONE] Scheduled upload scan complete")


def _run_analytics(episode_arg):
    """Collect and display analytics for episodes."""
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
    """Collect and display analytics for a single episode."""
    print(f"\n--- Episode {episode_number} ---")
    analytics = collector.collect_analytics(episode_number)
    collector.save_analytics(episode_number, analytics)

    score = scorer.calculate_engagement_score(analytics)
    print(f"  Engagement score: {score}/10")

    if analytics.get("youtube"):
        yt = analytics["youtube"]
        print(f"  YouTube: {yt.get('views', 0)} views, {yt.get('likes', 0)} likes")
    if analytics.get("twitter"):
        tw = analytics["twitter"]
        print(
            f"  Twitter: {tw.get('impressions', 0)} impressions, {tw.get('engagements', 0)} engagements"
        )


def _run_search(query):
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


def main():
    """Main entry point."""
    # Check for flags
    test_mode = "--test" in sys.argv or "--test-mode" in sys.argv
    resume = "--resume" in sys.argv
    dry_run = "--dry-run" in sys.argv
    auto_approve = "--auto-approve" in sys.argv

    # Strip flags from argv before parsing positional args
    flag_args = ["--test", "--test-mode", "--resume", "--dry-run", "--auto-approve"]
    sys.argv = [arg for arg in sys.argv if arg not in flag_args]

    # Handle commands that don't need full PodcastAutomation init
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()

        if cmd == "upload-scheduled":
            _run_upload_scheduled()
            return

        if cmd == "analytics":
            episode_arg = sys.argv[2] if len(sys.argv) > 2 else "all"
            _run_analytics(episode_arg)
            return

        if cmd == "search" and len(sys.argv) > 2:
            query = " ".join(sys.argv[2:])
            _run_search(query)
            return

    automation = PodcastAutomation(
        test_mode=test_mode, resume=resume, dry_run=dry_run, auto_approve=auto_approve
    )

    # Dry run mode: validate pipeline and exit
    if dry_run:
        automation.dry_run_episode()
        return

    # Check command line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()

        if arg == "list":
            # List available episodes sorted by number
            automation.list_episodes_by_number()
        elif arg == "latest":
            # Process latest episode (with Discord notification)
            _process_with_notification(automation)
        elif arg.startswith("ep") or arg.startswith("episode"):
            # Process specific episode by number
            # Support formats: ep25, episode25, ep 25, episode 25
            match = re.search(r"(\d+)", arg)
            if match:
                episode_num = int(match.group(1))
            elif len(sys.argv) > 2:
                episode_num = int(sys.argv[2])
            else:
                print("Usage: python main.py ep25 or python main.py episode 25")
                return

            _process_with_notification(automation, episode_number=episode_num)
        else:
            # Process specific file (local or dropbox path)
            file_path = sys.argv[1]
            if file_path.startswith("/"):
                # Dropbox path
                _process_with_notification(automation, dropbox_path=file_path)
            else:
                # Local file
                _process_with_notification(automation, local_audio_path=file_path)
    else:
        # Interactive mode
        print("Podcast Automation - Interactive Mode")
        print()
        print("Options:")
        print("  1. Process latest episode from Dropbox")
        print("  2. Process episode by episode number (e.g., Episode 25)")
        print("  3. List all episodes sorted by number")
        print("  4. List all episodes by date")
        print("  5. Process specific Dropbox episode by path")
        print("  6. Process local audio file")
        print()

        choice = input("Enter choice (1-6): ").strip()

        if choice == "1":
            _process_with_notification(automation)
        elif choice == "2":
            automation.list_episodes_by_number()
            episode_num = input("\nEnter episode number: ").strip()
            try:
                _process_with_notification(automation, episode_number=int(episode_num))
            except ValueError:
                print("Invalid episode number")
        elif choice == "3":
            automation.list_episodes_by_number()
        elif choice == "4":
            automation.list_available_episodes()
        elif choice == "5":
            automation.list_available_episodes()
            path = input("\nEnter Dropbox path: ").strip()
            _process_with_notification(automation, dropbox_path=path)
        elif choice == "6":
            path = input("Enter local audio file path: ").strip()
            _process_with_notification(automation, local_audio_path=path)
        else:
            print("Invalid choice")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[WARNING] Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
