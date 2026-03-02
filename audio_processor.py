"""Audio processing for censoring content and creating clips."""

from pydub import AudioSegment
from pydub.generators import Sine
from pathlib import Path
from config import Config
from logger import logger
import os

# Configure FFmpeg paths for pydub (Windows compatibility)
if os.path.exists(Config.FFMPEG_PATH):
    AudioSegment.converter = Config.FFMPEG_PATH
    AudioSegment.ffmpeg = Config.FFMPEG_PATH
    AudioSegment.ffprobe = Config.FFPROBE_PATH


class AudioProcessor:
    """Process audio files to apply censorship and extract clips."""

    def __init__(self):
        """Initialize audio processor."""
        logger.info("Audio processor ready")

        # Generate or load beep sound
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

    def normalize_audio(self, audio_path, output_path=None):
        """
        Normalize audio to target LUFS level using pydub dBFS measurement.

        Args:
            audio_path: Path to audio file
            output_path: Output path (defaults to overwriting input)

        Returns:
            Path to normalized audio file
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        if output_path is None:
            output_path = audio_path
        else:
            output_path = Path(output_path)

        logger.info("Normalizing audio: %s", audio_path.name)
        audio = AudioSegment.from_file(str(audio_path))

        current_dbfs = audio.dBFS
        target_dbfs = Config.LUFS_TARGET
        change_in_dbfs = target_dbfs - current_dbfs

        logger.debug(
            "Current dBFS: %.1f, Target: %.1f, Adjustment: %.1f dB",
            current_dbfs,
            target_dbfs,
            change_in_dbfs,
        )

        if abs(change_in_dbfs) > 0.5:
            normalized = audio.apply_gain(change_in_dbfs)
            normalized.export(
                str(output_path), format=output_path.suffix.lstrip(".") or "wav"
            )
            logger.info("Audio normalized (%.1f dB adjustment)", change_in_dbfs)
        else:
            logger.info("Audio already near target level, skipping normalization")
            if output_path != audio_path:
                audio.export(
                    str(output_path), format=output_path.suffix.lstrip(".") or "wav"
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

            # Get the beep segment (adjust length to match duration)
            beep_duration_ms = int(duration * 1000)
            if beep_duration_ms > len(self.beep_sound):
                # Repeat beep if needed
                beep = self.beep_sound * (beep_duration_ms // len(self.beep_sound) + 1)
                beep = beep[:beep_duration_ms]
            else:
                beep = self.beep_sound[:beep_duration_ms]

            # Replace the audio segment with beep
            audio = audio[:start_ms] + beep + audio[end_ms:]

            logger.info(
                "[%d/%d] Censored %.2fs-%.2fs (%.2fs): %s",
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

    def extract_clip(self, audio_file_path, start_seconds, end_seconds, output_path):
        """
        Extract a clip from the audio file.

        Args:
            audio_file_path: Path to audio file
            start_seconds: Start time in seconds
            end_seconds: End time in seconds
            output_path: Output path for clip

        Returns:
            Path to extracted clip
        """
        audio_file_path = Path(audio_file_path)

        if not audio_file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        # Load audio (supports any format FFmpeg can handle)
        audio = AudioSegment.from_file(str(audio_file_path))

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

            # Extract clip
            clip_path = self.extract_clip(audio_file_path, start, end, output_path)
            clip_paths.append(clip_path)

        logger.info("Created %d clips in: %s", len(clip_paths), output_dir)
        return clip_paths

    def convert_to_mp3(self, wav_file_path, output_path=None, bitrate=None):
        """
        Convert WAV to MP3 for uploading to platforms.

        Args:
            wav_file_path: Path to WAV file
            output_path: Output path for MP3
            bitrate: Audio bitrate (default from Config.MP3_BITRATE)

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

        # Load and export as MP3 (supports any format FFmpeg can handle)
        audio = AudioSegment.from_file(str(wav_file_path))
        audio.export(str(output_path), format="mp3", bitrate=bitrate)

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
