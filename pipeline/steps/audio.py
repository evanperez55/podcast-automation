"""Audio step: transcribe, censor, normalize, and convert to MP3."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


def run_audio(
    ctx: PipelineContext,
    components: dict,
    state=None,
) -> PipelineContext:
    """Run Steps 2, 4, 4.5, 6: transcribe, censor, normalize, convert to MP3."""
    audio_file = ctx.audio_file
    episode_output_dir = ctx.episode_output_dir
    timestamp = ctx.timestamp

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
        transcript_data = components["transcriber"].transcribe(
            audio_file, transcript_path
        )
        if state:
            state.complete_step("transcribe", {"transcript_path": str(transcript_path)})
    print()

    ctx.transcript_data = transcript_data
    ctx.transcript_path = transcript_path

    # Step 4: Apply censorship
    print("STEP 4: APPLYING CENSORSHIP")
    print("-" * 60)
    analysis = ctx.analysis or {}
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
