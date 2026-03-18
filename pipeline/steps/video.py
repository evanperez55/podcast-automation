"""Video step: create clips, subtitles, audiograms, thumbnails, and full-episode video."""

from __future__ import annotations

import logging
from pathlib import Path

from config import Config
from pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


def run_video(
    ctx: PipelineContext,
    components: dict,
    state=None,
) -> PipelineContext:
    """Run Steps 5, 5.1, 5.4, 5.5, 5.6: clips, approval, subtitles, video, thumbnail."""
    audio_file = ctx.audio_file
    episode_output_dir = ctx.episode_output_dir
    timestamp = ctx.timestamp
    censored_audio = ctx.censored_audio
    transcript_data = ctx.transcript_data
    analysis = ctx.analysis or {}
    episode_number = ctx.episode_number
    episode_folder = ctx.episode_folder

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
        clip_paths = components["audio_processor"].create_clips(
            censored_audio, analysis.get("best_clips", []), clip_dir
        )
        if state:
            state.complete_step(
                "create_clips", {"clip_paths": [str(p) for p in clip_paths]}
            )
    print()

    ctx.clip_paths = clip_paths

    # Step 5.1: Clip preview/approval (interactive unless auto-approve)
    print("STEP 5.1: CLIP PREVIEW/APPROVAL")
    print("-" * 60)
    best_clips = analysis.get("best_clips", [])
    if clip_paths and not ctx.auto_approve:
        clip_previewer = components["clip_previewer"]
        approved_indices = clip_previewer.preview_clips(
            [str(p) for p in clip_paths], best_clips
        )
        clip_paths, best_clips = clip_previewer.filter_clips(
            clip_paths, best_clips, approved_indices
        )
        # Update analysis with filtered clips
        analysis["best_clips"] = best_clips
        logger.info("Approved %d clips for upload", len(clip_paths))
    else:
        logger.info("Auto-approving all %d clips", len(clip_paths))
    print()

    ctx.clip_paths = clip_paths

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
            logger.info("Generated %d subtitle files", len([s for s in srt_paths if s]))
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

    ctx.srt_paths = srt_paths

    # Step 5.5: Convert clips to videos (subtitle clips, audiograms, or plain conversion)
    subtitle_clip_generator = components.get("subtitle_clip_generator")
    audiogram_generator = components.get("audiogram_generator")
    video_converter = components.get("video_converter")

    if subtitle_clip_generator and subtitle_clip_generator.enabled:
        print("STEP 5.5: CREATING SUBTITLE CLIP VIDEOS")
    elif audiogram_generator and audiogram_generator.enabled:
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
    elif subtitle_clip_generator and subtitle_clip_generator.enabled and clip_paths:
        logger.info("Creating word-by-word subtitle clips...")
        srt_list = [str(s) if s else None for s in srt_paths]
        video_clip_paths = [
            Path(p)
            for p in subtitle_clip_generator.create_subtitle_clips(
                clip_paths=[str(p) for p in clip_paths],
                srt_paths=srt_list,
                transcript_data=transcript_data,
                best_clips=analysis.get("best_clips", []),
                format_type="vertical",
            )
        ]
        logger.info("Created %d subtitle clips", len(video_clip_paths))

        # Full episode still uses static logo (not subtitle clips)
        if video_converter:
            logger.info("Creating horizontal video (16:9) for YouTube full episode...")
            full_episode_video_path = video_converter.create_episode_video(
                audio_path=str(censored_audio),
                output_path=str(
                    episode_output_dir / f"{audio_file.stem}_{timestamp}_episode.mp4"
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
    elif audiogram_generator and audiogram_generator.enabled and clip_paths:
        logger.info("Creating audiogram waveform videos for clips...")
        audiogram_srt_paths = [str(s) if s else None for s in srt_paths]
        audiogram_results = audiogram_generator.create_audiogram_clips(
            clip_paths=[str(p) for p in clip_paths],
            format_type="vertical",
            srt_paths=audiogram_srt_paths,
        )
        video_clip_paths = [Path(p) for p in audiogram_results]
        logger.info("Created %d audiogram clips", len(video_clip_paths))

        # Full episode still uses static logo (not audiogram)
        if video_converter:
            logger.info("Creating horizontal video (16:9) for YouTube full episode...")
            full_episode_video_path = video_converter.create_episode_video(
                audio_path=str(censored_audio),
                output_path=str(
                    episode_output_dir / f"{audio_file.stem}_{timestamp}_episode.mp4"
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
    elif video_converter and clip_paths:
        logger.info("Creating vertical videos (9:16) for Shorts/Reels/TikTok...")

        # Step 5.6: Convert full episode to video for YouTube (in parallel with clips)
        from concurrent.futures import ThreadPoolExecutor

        # Capture converter in closure variable before the `with` block
        vc = video_converter

        def convert_clips():
            return vc.convert_clips_to_videos(
                clip_paths=clip_paths,
                format_type="vertical",
                output_dir=str(clip_dir),
                srt_paths=srt_paths,
            )

        def convert_full_episode():
            if not vc:
                return None
            logger.info("Creating horizontal video (16:9) for YouTube...")
            return vc.create_episode_video(
                audio_path=str(censored_audio),
                output_path=str(
                    episode_output_dir / f"{audio_file.stem}_{timestamp}_episode.mp4"
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
    elif not video_converter and not (
        audiogram_generator and audiogram_generator.enabled
    ):
        logger.info("Video converter not available - skipping video creation")
    else:
        logger.info("No clips to convert")
    print()

    ctx.video_clip_paths = video_clip_paths
    ctx.full_episode_video_path = full_episode_video_path

    # Step 5.6: Generate thumbnail
    print("STEP 5.6: GENERATING THUMBNAIL")
    print("-" * 60)
    thumbnail_path = None
    episode_title = analysis.get("episode_title", f"Episode {episode_number}")
    thumbnail_generator = components.get("thumbnail_generator")
    if thumbnail_generator:
        thumb_output = (
            episode_output_dir / f"{audio_file.stem}_{timestamp}_thumbnail.png"
        )
        thumbnail_path = thumbnail_generator.generate_thumbnail(
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

    ctx.thumbnail_path = thumbnail_path

    return ctx
