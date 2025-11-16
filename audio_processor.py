"""Audio processing for censoring content and creating clips."""

from pydub import AudioSegment
from pydub.generators import Sine
from pathlib import Path
from config import Config
import json
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
        print(f"[OK] Audio processor ready")

        # Generate or load beep sound
        self.beep_sound = self._get_beep_sound()

    def _get_beep_sound(self):
        """Get or generate the beep sound for censoring."""
        beep_path = Path(Config.BEEP_SOUND_PATH)

        if beep_path.exists():
            print(f"  Using beep sound from: {beep_path}")
            return AudioSegment.from_wav(str(beep_path))
        else:
            # Generate a 1-second beep at 1000Hz
            print(f"  Generating beep sound...")
            beep = Sine(1000).to_audio_segment(duration=1000)  # 1 second beep
            beep = beep - 10  # Reduce volume by 10dB

            # Save it for future use
            Config.ASSETS_DIR.mkdir(exist_ok=True)
            beep.export(str(beep_path), format="wav")
            print(f"  Beep sound saved to: {beep_path}")

            return beep

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

        print(f"Applying censorship to: {audio_file_path.name}")
        print(f"  Censoring {len(censor_timestamps)} items...")

        # Load audio (supports any format FFmpeg can handle)
        print(f"  Loading audio file...")
        audio = AudioSegment.from_file(str(audio_file_path))
        audio_duration = len(audio) / 1000  # Convert to seconds

        print(f"  Audio duration: {audio_duration:.1f}s")

        # Sort timestamps by time (process in order)
        sorted_timestamps = sorted(censor_timestamps, key=lambda x: x.get('seconds', 0))

        # Process each censor point
        for i, censor in enumerate(sorted_timestamps):
            timestamp = censor.get('seconds', 0)
            reason = censor.get('reason', 'unknown')

            # Estimate word duration (typically 0.3-0.5 seconds)
            # We'll beep for 0.5 seconds to be safe
            duration = 0.5

            start_ms = int(timestamp * 1000)
            end_ms = int((timestamp + duration) * 1000)

            # Make sure we don't go past the end
            end_ms = min(end_ms, len(audio))

            # Get the beep segment (adjust length if needed)
            beep = self.beep_sound[:int(duration * 1000)]

            # Replace the audio segment with beep
            audio = audio[:start_ms] + beep + audio[end_ms:]

            print(f"  [{i+1}/{len(sorted_timestamps)}] Censored at {timestamp:.1f}s: {reason}")

        # Save censored audio
        if output_path is None:
            output_path = Config.OUTPUT_DIR / f"{audio_file_path.stem}_censored.wav"
        else:
            output_path = Path(output_path)

        print(f"  Exporting censored audio...")
        audio.export(str(output_path), format="wav")

        print(f"[OK] Censored audio saved to: {output_path}")
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

        # Add fade in/out for smoother clips
        clip = clip.fade_in(100).fade_out(100)

        # Export clip
        output_path = Path(output_path)
        clip.export(str(output_path), format="wav")

        return output_path

    def create_clips(self, audio_file_path, best_clips, output_dir=None):
        """
        Create multiple clips from the audio file.

        Args:
            audio_file_path: Path to audio file
            best_clips: List of dicts with 'start_seconds', 'end_seconds', 'description'
            output_dir: Directory to save clips

        Returns:
            List of paths to created clips
        """
        audio_file_path = Path(audio_file_path)
        output_dir = Path(output_dir) if output_dir else Config.CLIPS_DIR

        print(f"Creating {len(best_clips)} clips from: {audio_file_path.name}")

        clip_paths = []

        for i, clip_info in enumerate(best_clips):
            start = clip_info.get('start_seconds', 0)
            end = clip_info.get('end_seconds', start + 30)
            description = clip_info.get('description', f'Clip {i+1}')

            # Create filename
            filename = f"{audio_file_path.stem}_clip_{i+1:02d}.wav"
            output_path = output_dir / filename

            print(f"  [{i+1}/{len(best_clips)}] Extracting clip: {start:.1f}s to {end:.1f}s")
            print(f"      {description}")

            # Extract clip
            clip_path = self.extract_clip(audio_file_path, start, end, output_path)
            clip_paths.append(clip_path)

        print(f"[OK] Created {len(clip_paths)} clips in: {output_dir}")
        return clip_paths

    def convert_to_mp3(self, wav_file_path, output_path=None, bitrate="192k"):
        """
        Convert WAV to MP3 for uploading to platforms.

        Args:
            wav_file_path: Path to WAV file
            output_path: Output path for MP3
            bitrate: Audio bitrate (default 192k)

        Returns:
            Path to MP3 file
        """
        wav_file_path = Path(wav_file_path)

        if not wav_file_path.exists():
            raise FileNotFoundError(f"WAV file not found: {wav_file_path}")

        if output_path is None:
            output_path = wav_file_path.with_suffix('.mp3')
        else:
            output_path = Path(output_path)

        print(f"Converting to MP3: {wav_file_path.name}")

        # Load and export as MP3 (supports any format FFmpeg can handle)
        audio = AudioSegment.from_file(str(wav_file_path))
        audio.export(str(output_path), format="mp3", bitrate=bitrate)

        print(f"[OK] MP3 saved to: {output_path}")
        return output_path


if __name__ == '__main__':
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
        {'seconds': 10, 'reason': 'Test beep 1'},
        {'seconds': 20, 'reason': 'Test beep 2'},
    ]

    output = processor.apply_censorship(audio_file, test_censors)
    print(f"\nTest censored file created: {output}")
