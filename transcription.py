"""Audio transcription using faster-whisper (CTranslate2 backend).

Uses faster-whisper for ~4x speed improvement over openai-whisper with
identical accuracy. Includes Silero VAD pre-filtering to skip silence.
"""

from pathlib import Path
import json
from config import Config
from logger import logger
import os


class Transcriber:
    """Handle audio transcription with faster-whisper model."""

    def __init__(self, model_size=None):
        """
        Initialize faster-whisper model.

        Args:
            model_size: Model size to use (defaults to Config.WHISPER_MODEL). Options:
                - tiny: Fastest, least accurate (~1GB RAM)
                - base: Good balance (~1GB RAM)
                - small: Better accuracy (~2GB RAM)
                - medium: Very good accuracy (~5GB RAM)
                - large-v3: Best accuracy (~5GB VRAM fp16)
                - distil-large-v3: Near-best accuracy, 2x faster (~2.5GB VRAM)
        """
        model_size = model_size or Config.WHISPER_MODEL

        # Ensure FFmpeg is in PATH (faster-whisper needs it)
        ffmpeg_dir = os.path.dirname(Config.FFMPEG_PATH)
        if ffmpeg_dir and ffmpeg_dir not in os.environ["PATH"]:
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ["PATH"]
            logger.debug("Added FFmpeg to PATH: %s", ffmpeg_dir)

        logger.info("Loading faster-whisper '%s' model...", model_size)

        # Lazy import: faster-whisper + torch are heavy (~2s import time)
        # Deferring to __init__ avoids paying this cost when transcription is unused
        from faster_whisper import WhisperModel
        import torch

        if torch.cuda.is_available():
            self.device = "cuda"
            self.compute_type = "float16"
        else:
            self.device = "cpu"
            self.compute_type = "int8"

        logger.info("Using device: %s (%s)", self.device, self.compute_type)

        # Load the model
        self.model = WhisperModel(
            model_size,
            device=self.device,
            compute_type=self.compute_type,
        )
        logger.info("faster-whisper model loaded and ready")

    def transcribe(self, audio_file_path, output_path=None):
        """
        Transcribe audio file using faster-whisper.

        Args:
            audio_file_path: Path to audio file (WAV, MP3, etc.)
            output_path: Optional path to save transcript JSON

        Returns:
            Dictionary with transcript data including:
            - text: Full transcript text
            - segments: List of segments with timestamps
            - language: Detected language
            - words: List of words with timestamps
        """
        audio_file_path = Path(audio_file_path)

        if not audio_file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        logger.info("Transcribing: %s", audio_file_path.name)
        logger.info("File size: %.1f MB", audio_file_path.stat().st_size / 1024 / 1024)

        try:
            # Transcribe with faster-whisper
            logger.info("Processing with faster-whisper...")
            logger.info("(This may take several minutes for long files...)")

            segments_iter, info = self.model.transcribe(
                str(audio_file_path),
                word_timestamps=True,
                vad_filter=True,  # Silero VAD pre-filters silence for 10-30% speedup
            )

            # Collect segments and words from the generator
            all_segments = []
            words = []
            full_text_parts = []

            for segment in segments_iter:
                seg_dict = {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                }

                if segment.words:
                    seg_words = []
                    for w in segment.words:
                        word_dict = {
                            "word": w.word.strip(),
                            "start": w.start,
                            "end": w.end,
                        }
                        words.append(word_dict)
                        seg_words.append(word_dict)
                    seg_dict["words"] = seg_words

                all_segments.append(seg_dict)
                full_text_parts.append(segment.text)

            duration = all_segments[-1]["end"] if all_segments else 0

            # Prepare transcript data in our standard format
            transcript_data = {
                "text": " ".join(full_text_parts),
                "language": info.language,
                "duration": duration,
                "segments": all_segments,
                "words": words,
            }

            logger.info("Transcription complete")
            logger.info(
                "Language: %s (probability: %.2f)",
                info.language,
                info.language_probability,
            )
            logger.info("Duration: %.1fs", transcript_data["duration"])
            logger.info("Words: %d", len(transcript_data["words"]))
            logger.info("Segments: %d", len(transcript_data["segments"]))

            # Save transcript if output path provided
            if output_path:
                output_path = Path(output_path)
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(transcript_data, f, indent=2, ensure_ascii=False)
                logger.info("Transcript saved to: %s", output_path)

            return transcript_data

        except Exception as e:
            logger.error("Transcription error: %s", e)
            raise

    def get_transcript_text(self, transcript_data):
        """Extract plain text from transcript data."""
        return transcript_data.get("text", "")

    def get_words_with_timestamps(self, transcript_data):
        """
        Get words with their timestamps.

        Returns:
            List of dictionaries with 'word', 'start', 'end' keys
        """
        return transcript_data.get("words", [])

    def find_word_timestamps(self, transcript_data, target_word):
        """
        Find all occurrences of a word and their timestamps.

        Args:
            transcript_data: Transcript data from transcribe()
            target_word: Word to find (case-insensitive)

        Returns:
            List of {word, start, end} dictionaries
        """
        words = self.get_words_with_timestamps(transcript_data)
        target_lower = target_word.lower()

        matches = []
        for word_data in words:
            if word_data["word"].lower().strip(".,!?;:\"'").startswith(target_lower):
                matches.append(word_data)

        return matches


if __name__ == "__main__":
    # Test transcription
    import sys

    if len(sys.argv) < 2:
        print("Usage: python transcription.py <audio_file.wav>")
        sys.exit(1)

    audio_file = sys.argv[1]
    transcriber = Transcriber()

    output_json = Path(audio_file).stem + "_transcript.json"
    transcript = transcriber.transcribe(audio_file, output_json)

    print("\nTranscript preview:")
    print(transcript["text"][:500] + "...")
