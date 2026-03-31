"""Audio processing for censoring content and creating clips."""

from pydub import AudioSegment
from pydub.generators import Sine
from pathlib import Path
from config import Config
from logger import logger
import os
import subprocess
import json
import re

# Configure FFmpeg paths for pydub (Windows compatibility)
if os.path.exists(Config.FFMPEG_PATH):
    AudioSegment.converter = Config.FFMPEG_PATH
    AudioSegment.ffmpeg = Config.FFMPEG_PATH
    AudioSegment.ffprobe = Config.FFPROBE_PATH


def _parse_loudnorm_json(stderr_text: str) -> dict:
    """Extract loudnorm measurement JSON from ffmpeg stderr output.

    FFmpeg embeds the JSON block in stderr mixed with progress lines.
    Scan the full stderr string for the first {...} block.
    """
    match = re.search(r"\{[^{}]+\}", stderr_text, re.DOTALL)
    if not match:
        raise ValueError(
            f"Could not find loudnorm JSON in ffmpeg output. "
            f"stderr (last 500 chars): {stderr_text[-500:]}"
        )
    return json.loads(match.group())


class AudioProcessor:
    """Process audio files to apply censorship and extract clips."""

    def __init__(self):
        """Initialize audio processor."""
        logger.info("Audio processor ready")

        # TODO: beep_sound kept for backward compat; no longer used by apply_censorship (Phase 2)
        self.beep_sound = self._get_beep_sound()

    def _get_beep_sound(self):
        """Get or generate the beep sound for censoring."""
        beep_path = Path(Config.BEEP_SOUND_PATH)

        if beep_path.exists():
            logger.debug("Using beep sound from: %s", beep_path)
            return AudioSegment.from_wav(str(beep_path))
        else:
            # Generate a 1-second beep at 1000Hz
            logger.debug("Generating beep sound...")
            beep = Sine(1000).to_audio_segment(duration=1000)  # 1 second beep
            beep = beep - 10  # Reduce volume by 10dB

            # Save it for future use
            Config.ASSETS_DIR.mkdir(exist_ok=True)
            beep.export(str(beep_path), format="wav")
            logger.debug("Beep sound saved to: %s", beep_path)

            return beep

    def _apply_duck_segment(
        self, audio: AudioSegment, start_ms: int, end_ms: int
    ) -> AudioSegment:
        """Replace segment with smooth volume duck (radio-style dip).

        Extracts the segment, reduces its volume to near-silence (-40 dB),
        applies 50ms fade-in and fade-out at the edges, then splices it back.
        Cap fade duration to half the segment length to handle very short segments.
        """
        DUCK_GAIN_DB = -40  # Near-silence — clearly intentional, not a cut
        FADE_MS = 50  # 50ms fade-in and fade-out (shorter than 50ms padding)

        segment = audio[start_ms:end_ms]
        segment_len = end_ms - start_ms
        actual_fade = min(FADE_MS, segment_len // 2)  # Cap for very short segments

        ducked = segment.apply_gain(DUCK_GAIN_DB)
        ducked = ducked.fade_in(actual_fade).fade_out(actual_fade)
        return audio[:start_ms] + ducked + audio[end_ms:]

    def _parse_loudnorm_json(self, stderr_text: str) -> dict:
        """Extract loudnorm measurement JSON from ffmpeg stderr output.

        Delegates to the module-level _parse_loudnorm_json function.
        """
        return _parse_loudnorm_json(stderr_text)

    def normalize_audio(self, audio_path, output_path=None):
        """
        Normalize audio to EBU R128 target LUFS using FFmpeg two-pass loudnorm.

        Pass 1 measures the input loudness; Pass 2 applies linear normalization
        using the measured values. Logs input LUFS, output LUFS, gain applied,
        and LRA. Warns (does not raise) if FFmpeg falls back to AGC (dynamic) mode.

        Args:
            audio_path: Path to audio file
            output_path: Output path (defaults to overwriting input)

        Returns:
            Path to normalized audio file
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        in_place = output_path is None
        if in_place:
            output_path = audio_path.with_suffix(".norm" + audio_path.suffix)
        else:
            output_path = Path(output_path)

        logger.info("Normalizing audio: %s", audio_path.name)

        # --- Pass 1: measure loudness ---
        pass1_cmd = [
            Config.FFMPEG_PATH,
            "-i",
            str(audio_path),
            "-af",
            f"loudnorm=I={Config.LUFS_TARGET}:LRA=11:TP=-1.5:print_format=json",
            "-f",
            "null",
            "-",
        ]
        result1 = subprocess.run(
            pass1_cmd,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        if result1.returncode != 0:
            raise RuntimeError(
                f"FFmpeg loudnorm pass 1 failed (rc={result1.returncode}). "
                f"stderr: {result1.stderr[-500:]}"
            )

        stats = self._parse_loudnorm_json(result1.stderr)

        # Warn (do not raise) if FFmpeg fell back to AGC/dynamic mode
        if stats.get("normalization_type") == "dynamic":
            logger.warning(
                "Normalization fell back to AGC (dynamic) mode — "
                "linear normalization not possible with current true peak "
                "(measured_TP=%s dBTP, target_TP=-1.5 dBTP). "
                "Audio normalized but dynamic compression was applied.",
                stats.get("input_tp", "unknown"),
            )

        # --- Pass 2: apply normalization ---
        pass2_cmd = [
            Config.FFMPEG_PATH,
            "-i",
            str(audio_path),
            "-af",
            (
                f"loudnorm=I={Config.LUFS_TARGET}:LRA=11:TP=-1.5:linear=true:"
                f"measured_I={stats['input_i']}:measured_LRA={stats['input_lra']}:"
                f"measured_TP={stats['input_tp']}:measured_thresh={stats['input_thresh']}:"
                f"offset={stats['target_offset']}"
            ),
            "-ar",
            "44100",
            "-y",
            str(output_path),
        ]
        result2 = subprocess.run(
            pass2_cmd,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        if result2.returncode != 0:
            raise RuntimeError(
                f"FFmpeg loudnorm pass 2 failed (rc={result2.returncode}). "
                f"stderr: {result2.stderr[-500:]}"
            )

        # Extract pass-2 output measurements; fall back to approximations if absent
        try:
            stats2 = _parse_loudnorm_json(result2.stderr)
            output_lufs = float(stats2.get("output_i", Config.LUFS_TARGET))
            output_lra = float(stats2.get("output_lra", stats.get("input_lra", "0")))
        except (ValueError, KeyError):
            output_lufs = float(Config.LUFS_TARGET)
            output_lra = float(stats.get("input_lra", "0"))

        # If normalizing in-place, replace original with normalized file
        if in_place:
            output_path.replace(audio_path)
            output_path = audio_path

        # Log normalization metrics
        gain_db = output_lufs - float(stats["input_i"])
        logger.info(
            "Normalization complete — input: %.1f LUFS, output: %.1f LUFS, "
            "gain: %.1f dB, LRA: %.1f LU",
            float(stats["input_i"]),
            output_lufs,
            gain_db,
            output_lra,
        )

        return output_path

    def apply_censorship(self, audio_file_path, censor_timestamps, output_path=None):
        """
        Apply beep censorship to audio at specified timestamps.

        Args:
            audio_file_path: Path to original audio file
            censor_timestamps: List of dicts with 'seconds', 'reason' keys
            output_path: Output path for censored audio

        Returns:
            Path to censored audio file
        """
        audio_file_path = Path(audio_file_path)

        if not audio_file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        logger.info("Applying censorship to: %s", audio_file_path.name)
        logger.info("Censoring %d items...", len(censor_timestamps))

        # Load audio (supports any format FFmpeg can handle)
        logger.debug("Loading audio file...")
        audio = AudioSegment.from_file(str(audio_file_path))
        audio_duration = len(audio) / 1000  # Convert to seconds

        logger.debug("Audio duration: %.1fs", audio_duration)

        # Sort timestamps by time (process in order)
        # Use start_seconds if available (refined timestamps), otherwise fall back to seconds
        sorted_timestamps = sorted(
            censor_timestamps, key=lambda x: x.get("start_seconds", x.get("seconds", 0))
        )

        # Process each censor point
        for i, censor in enumerate(sorted_timestamps):
            reason = censor.get("reason", "unknown")

            # Use word-level boundaries if available (from refined timestamps)
            # Otherwise fall back to segment timestamp with estimated duration
            if "start_seconds" in censor and "end_seconds" in censor:
                # Use exact word boundaries from Whisper
                start_seconds = censor["start_seconds"]
                end_seconds = censor["end_seconds"]
                duration = end_seconds - start_seconds

                # Add small padding (50ms) to ensure complete coverage
                start_seconds = max(0, start_seconds - 0.05)
                end_seconds = end_seconds + 0.05
                duration = end_seconds - start_seconds
            else:
                # Fallback: use segment timestamp with estimated duration
                start_seconds = censor.get("seconds", 0)
                duration = 0.5
                end_seconds = start_seconds + duration

            start_ms = int(start_seconds * 1000)
            end_ms = int(end_seconds * 1000)

            # Make sure we don't go past the end
            end_ms = min(end_ms, len(audio))

            # Duck the censored segment (smooth volume fade — no beep)
            audio = self._apply_duck_segment(audio, start_ms, end_ms)

            logger.info(
                "[%d/%d] Ducked %.2fs-%.2fs (%.2fs): %s",
                i + 1,
                len(sorted_timestamps),
                start_seconds,
                end_seconds,
                duration,
                reason,
            )

        # Save censored audio
        if output_path is None:
            output_path = Config.OUTPUT_DIR / f"{audio_file_path.stem}_censored.wav"
        else:
            output_path = Path(output_path)

        logger.debug("Exporting censored audio...")
        audio.export(str(output_path), format="wav")

        logger.info("Censored audio saved to: %s", output_path)
        return output_path

    def extract_clip(
        self, audio_file_path, start_seconds, end_seconds, output_path, _audio=None
    ):
        """
        Extract a clip from the audio file.

        Args:
            audio_file_path: Path to audio file
            start_seconds: Start time in seconds
            end_seconds: End time in seconds
            output_path: Output path for clip
            _audio: Pre-loaded AudioSegment to avoid redundant disk reads

        Returns:
            Path to extracted clip
        """
        audio_file_path = Path(audio_file_path)

        if not audio_file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        # Use pre-loaded audio if provided, otherwise load from disk
        audio = (
            _audio
            if _audio is not None
            else AudioSegment.from_file(str(audio_file_path))
        )

        # Extract clip
        start_ms = int(start_seconds * 1000)
        end_ms = int(end_seconds * 1000)

        clip = audio[start_ms:end_ms]

        # Add fade in/out using configurable fade duration
        fade_ms = Config.CLIP_FADE_MS
        clip = clip.fade_in(fade_ms).fade_out(fade_ms)

        # Export clip
        output_path = Path(output_path)
        clip.export(str(output_path), format="wav")

        return output_path

    def create_clips(
        self, audio_file_path, best_clips, output_dir=None, base_name=None
    ):
        """
        Create multiple clips from the audio file.

        Args:
            audio_file_path: Path to audio file
            best_clips: List of dicts with 'start_seconds', 'end_seconds', 'description'
            output_dir: Directory to save clips
            base_name: Optional base name for clip files (default: audio file stem)

        Returns:
            List of paths to created clips
        """
        audio_file_path = Path(audio_file_path)
        output_dir = Path(output_dir) if output_dir else Config.CLIPS_DIR
        file_base = base_name if base_name else audio_file_path.stem

        logger.info("Creating %d clips from: %s", len(best_clips), audio_file_path.name)

        # Load audio once — avoids redundant disk reads in extract_clip loop
        audio = AudioSegment.from_file(str(audio_file_path))

        clip_paths = []

        for i, clip_info in enumerate(best_clips):
            start = clip_info.get("start_seconds", 0)
            end = clip_info.get("end_seconds", start + 30)
            description = clip_info.get("description", f"Clip {i + 1}")

            # Clip duration validation
            duration = end - start
            if duration < Config.CLIP_MIN_DURATION:
                logger.warning(
                    "Clip %d is %.1fs (min %ds), extending end time",
                    i + 1,
                    duration,
                    Config.CLIP_MIN_DURATION,
                )
                end = start + Config.CLIP_MIN_DURATION
            elif duration > Config.CLIP_MAX_DURATION:
                logger.warning(
                    "Clip %d is %.1fs (max %ds), trimming",
                    i + 1,
                    duration,
                    Config.CLIP_MAX_DURATION,
                )
                end = start + Config.CLIP_MAX_DURATION

            # Create filename
            filename = f"{file_base}_clip_{i + 1:02d}.wav"
            output_path = output_dir / filename

            logger.info(
                "[%d/%d] Extracting clip: %.1fs to %.1fs",
                i + 1,
                len(best_clips),
                start,
                end,
            )
            logger.debug("  %s", description)

            # Extract clip (pass cached audio to avoid reloading from disk)
            clip_path = self.extract_clip(
                audio_file_path, start, end, output_path, _audio=audio
            )
            clip_paths.append(clip_path)

        logger.info("Created %d clips in: %s", len(clip_paths), output_dir)
        return clip_paths

    def convert_to_mp3(
        self, wav_file_path, output_path=None, bitrate=None, _audio=None
    ):
        """
        Convert WAV to MP3 for uploading to platforms.

        Args:
            wav_file_path: Path to WAV file
            output_path: Output path for MP3
            bitrate: Audio bitrate (default from Config.MP3_BITRATE)
            _audio: Pre-loaded AudioSegment to avoid redundant disk reads

        Returns:
            Path to MP3 file
        """
        wav_file_path = Path(wav_file_path)
        bitrate = bitrate or Config.MP3_BITRATE

        if not wav_file_path.exists():
            raise FileNotFoundError(f"WAV file not found: {wav_file_path}")

        if output_path is None:
            output_path = wav_file_path.with_suffix(".mp3")
        else:
            output_path = Path(output_path)

        logger.info("Converting to MP3: %s", wav_file_path.name)

        if _audio is not None:
            # Pre-loaded audio — use pydub export (data already in memory)
            _audio.export(str(output_path), format="mp3", bitrate=bitrate)
        else:
            # No pre-loaded audio — use FFmpeg directly (skip pydub decode overhead)
            cmd = [
                Config.FFMPEG_PATH,
                "-i",
                str(wav_file_path),
                "-codec:a",
                "libmp3lame",
                "-b:a",
                bitrate,
                "-y",
                str(output_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode != 0:
                raise RuntimeError(
                    f"FFmpeg MP3 conversion failed (rc={result.returncode}): "
                    f"{result.stderr[-300:]}"
                )

        logger.info("MP3 saved to: %s", output_path)
        return output_path


if __name__ == "__main__":
    # Test audio processing
    import sys

    if len(sys.argv) < 2:
        print("Usage: python audio_processor.py <audio_file.wav>")
        sys.exit(1)

    audio_file = sys.argv[1]
    processor = AudioProcessor()

    # Test beep generation
    print("\nBeep sound loaded successfully")

    # You can test with sample timestamps:
    test_censors = [
        {"seconds": 10, "reason": "Test beep 1"},
        {"seconds": 20, "reason": "Test beep 2"},
    ]

    output = processor.apply_censorship(audio_file, test_censors)
    print(f"\nTest censored file created: {output}")
