"""Generate 'Best Of' compilation videos from existing episode clips."""

import json
import os
import subprocess
from pathlib import Path
from typing import Optional

from config import Config
from logger import logger
from video_utils import get_h264_encoder_args


class CompilationGenerator:
    """Build a compilation video from the best clips across episodes."""

    def __init__(self):
        """Initialize compilation generator with enabled gating."""
        self.enabled = os.getenv("COMPILATION_ENABLED", "true").lower() == "true"
        self.ffmpeg_path = Config.FFMPEG_PATH
        self.crossfade_ms = 500

    def generate_best_of(
        self, max_clips: int = 10, output_dir: Optional[str] = None
    ) -> Optional[str]:
        """Generate a Best Of compilation from top-rated episode clips.

        Scans output directories for clip WAV files, ranks them using
        analysis metadata, concatenates the top N with crossfades, and
        converts to MP4 video.

        Args:
            max_clips: Maximum number of clips to include (default 10).
            output_dir: Directory for output files (default Config.OUTPUT_DIR).

        Returns:
            Path to the generated MP4 file, or None on failure.
        """
        if not self.enabled:
            logger.warning("Compilation generator disabled")
            return None

        output_path = Path(output_dir) if output_dir else Config.OUTPUT_DIR
        output_path.mkdir(parents=True, exist_ok=True)

        # Discover clips and their metadata
        scored_clips = self._discover_and_score_clips()
        if not scored_clips:
            logger.warning("No clips found for compilation")
            return None

        # Pick top N
        scored_clips.sort(key=lambda c: c["score"], reverse=True)
        selected = scored_clips[:max_clips]
        logger.info(
            "Selected %d clips for compilation from %d candidates",
            len(selected),
            len(scored_clips),
        )

        # Concatenate audio with crossfades
        wav_path = output_path / "best_of_compilation.wav"
        if not self._concatenate_clips(selected, wav_path):
            return None

        # Convert to MP4
        mp4_path = output_path / "best_of_compilation.mp4"
        if not self._convert_to_video(wav_path, mp4_path):
            return None

        # Write metadata sidecar
        self._write_metadata(selected, output_path)

        logger.info("Best Of compilation complete: %s", mp4_path)
        return str(mp4_path)

    def _discover_and_score_clips(self) -> list:
        """Scan episode directories for clips and score them.

        Returns:
            List of dicts with keys: path, score, episode_id, clip_meta.
        """
        results = []
        output_dir = Config.OUTPUT_DIR

        for ep_dir in sorted(output_dir.iterdir()):
            if not ep_dir.is_dir() or not ep_dir.name.startswith("ep"):
                continue

            clips_dir = ep_dir / "clips"
            if not clips_dir.is_dir():
                continue

            # Load analysis for this episode
            analysis = self._load_analysis(ep_dir)
            best_clips_meta = (
                {i: clip for i, clip in enumerate(analysis.get("best_clips", []))}
                if analysis
                else {}
            )

            for clip_file in sorted(clips_dir.glob("*.wav")):
                clip_index = self._parse_clip_index(clip_file.name)
                meta = best_clips_meta.get(clip_index, {})
                score = self._score_clip(meta)

                results.append(
                    {
                        "path": clip_file,
                        "score": score,
                        "episode_id": ep_dir.name,
                        "clip_meta": meta,
                    }
                )

        return results

    def _load_analysis(self, ep_dir: Path) -> Optional[dict]:
        """Load the analysis JSON for an episode directory.

        Args:
            ep_dir: Episode output directory (e.g. output/ep_25/).

        Returns:
            Parsed analysis dict, or None if not found.
        """
        for f in ep_dir.iterdir():
            if f.name.endswith("_analysis.json"):
                try:
                    return json.loads(f.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning("Failed to load analysis %s: %s", f.name, e)
                    return None
        return None

    def _parse_clip_index(self, filename: str) -> int:
        """Extract zero-based clip index from filename like 'ep25_clip_03.wav'.

        Args:
            filename: Clip WAV filename.

        Returns:
            Zero-based clip index, or -1 if unparseable.
        """
        # Expected pattern: *_clip_NN.wav
        stem = Path(filename).stem
        parts = stem.rsplit("_", 1)
        if len(parts) == 2:
            try:
                return int(parts[1]) - 1  # filenames are 1-based
            except ValueError:
                pass
        return -1

    def _score_clip(self, meta: dict) -> float:
        """Score a clip based on its analysis metadata.

        Clips with richer metadata (hook_caption, description,
        why_interesting) score higher.

        Args:
            meta: Clip metadata dict from analysis JSON.

        Returns:
            Numeric score (higher is better).
        """
        score = 0.0

        # Presence of key fields
        if meta.get("hook_caption"):
            score += 3.0
        if meta.get("why_interesting"):
            score += 2.0
        if meta.get("description"):
            score += 1.0
        if meta.get("suggested_title"):
            score += 1.0

        # Longer descriptions suggest more interesting content
        desc_len = len(meta.get("description", ""))
        score += min(desc_len / 100.0, 2.0)

        hook_len = len(meta.get("hook_caption", ""))
        score += min(hook_len / 50.0, 1.0)

        return score

    def _concatenate_clips(self, clips: list, output_path: Path) -> bool:
        """Concatenate clip WAV files with crossfade transitions.

        Args:
            clips: List of clip dicts (must have 'path' key).
            output_path: Path for the combined WAV output.

        Returns:
            True on success, False on failure.
        """
        from pydub import AudioSegment

        try:
            combined = AudioSegment.from_file(str(clips[0]["path"]))

            for clip_info in clips[1:]:
                next_clip = AudioSegment.from_file(str(clip_info["path"]))
                combined = combined.append(next_clip, crossfade=self.crossfade_ms)

            combined.export(str(output_path), format="wav")
            logger.info(
                "Combined %d clips into %.1fs WAV: %s",
                len(clips),
                combined.duration_seconds,
                output_path.name,
            )
            return True
        except Exception as e:
            logger.warning("Failed to concatenate clips: %s", e)
            return False

    def _convert_to_video(self, wav_path: Path, mp4_path: Path) -> bool:
        """Convert WAV to MP4 video with a static background.

        Uses FFmpeg with the podcast logo as the video frame.

        Args:
            wav_path: Path to input WAV file.
            mp4_path: Path for output MP4 file.

        Returns:
            True on success, False on failure.
        """
        # Resolve logo path
        logo_path = Config.ASSETS_DIR / "podcast_logo.jpg"
        if Config.CLIENT_LOGO_PATH and Path(Config.CLIENT_LOGO_PATH).exists():
            logo_path = Path(Config.CLIENT_LOGO_PATH)

        if not logo_path.exists():
            logger.warning("Logo not found at %s, skipping video", logo_path)
            return False

        width, height = Config.HORIZONTAL_RESOLUTION
        encoder_args = get_h264_encoder_args(preset="medium", crf=18, profile="high")

        command = [
            self.ffmpeg_path,
            "-loop",
            "1",
            "-i",
            str(logo_path),
            "-i",
            str(wav_path),
            *encoder_args,
        ]
        if not Config.USE_NVENC:
            command.extend(["-tune", "stillimage"])
        command.extend(
            [
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-vf",
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
                "-shortest",
                "-movflags",
                "+faststart",
                "-y",
                str(mp4_path),
            ]
        )

        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=3600
            )
            if result.returncode == 0 and mp4_path.exists():
                logger.info("Compilation video created: %s", mp4_path)
                return True
            logger.error("FFmpeg failed (rc=%d): %s", result.returncode, result.stderr)
            return False
        except subprocess.TimeoutExpired:
            logger.error("Compilation video conversion timed out")
            return False
        except Exception as e:
            logger.error("Compilation video conversion failed: %s", e)
            return False

    def _write_metadata(self, clips: list, output_dir: Path) -> None:
        """Write compilation metadata JSON with title and clip listing.

        Args:
            clips: Selected clip dicts with episode_id and clip_meta.
            output_dir: Directory to write the metadata file.
        """
        clip_entries = []
        for i, clip_info in enumerate(clips, 1):
            meta = clip_info.get("clip_meta", {})
            clip_entries.append(
                {
                    "position": i,
                    "episode": clip_info["episode_id"],
                    "title": meta.get("suggested_title", f"Clip {i}"),
                    "description": meta.get("description", ""),
                    "why_interesting": meta.get("why_interesting", ""),
                }
            )

        metadata = {
            "title": f"{Config.PODCAST_NAME} \u2014 Best Moments",
            "description": (
                f"A compilation of the {len(clips)} best moments from "
                f"{Config.PODCAST_NAME}."
            ),
            "clips": clip_entries,
        }

        meta_path = output_dir / "best_of_metadata.json"
        meta_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info("Compilation metadata written: %s", meta_path)
