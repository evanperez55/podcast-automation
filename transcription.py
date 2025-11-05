"""Audio transcription using local Whisper model."""

import whisper
from pathlib import Path
import json
from config import Config
import torch
import os


class Transcriber:
    """Handle audio transcription with local Whisper model."""

    def __init__(self, model_size="base"):
        """
        Initialize local Whisper model.

        Args:
            model_size: Model size to use. Options:
                - tiny: Fastest, least accurate (~1GB RAM)
                - base: Good balance, recommended (~1GB RAM)
                - small: Better accuracy (~2GB RAM)
                - medium: Very good accuracy (~5GB RAM)
                - large: Best accuracy, slowest (~10GB RAM)
        """
        # Ensure FFmpeg is in PATH (Whisper needs it)
        ffmpeg_dir = os.path.dirname(Config.FFMPEG_PATH)
        if ffmpeg_dir and ffmpeg_dir not in os.environ['PATH']:
            os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ['PATH']
            print(f"  Added FFmpeg to PATH: {ffmpeg_dir}")

        print(f"[OK] Loading Whisper '{model_size}' model...")

        # Check if CUDA (GPU) is available
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"  Using device: {self.device}")

        # Load the model
        self.model = whisper.load_model(model_size, device=self.device)
        print(f"[OK] Whisper model loaded and ready")

    def transcribe(self, audio_file_path, output_path=None):
        """
        Transcribe audio file using local Whisper model.

        Args:
            audio_file_path: Path to audio file (WAV, MP3, etc.)
            output_path: Optional path to save transcript JSON

        Returns:
            Dictionary with transcript data including:
            - text: Full transcript text
            - segments: List of segments with timestamps
            - language: Detected language
            - words: List of words with timestamps (if available)
        """
        audio_file_path = Path(audio_file_path)

        if not audio_file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        print(f"Transcribing: {audio_file_path.name}")
        print(f"  File size: {audio_file_path.stat().st_size / 1024 / 1024:.1f} MB")

        try:
            # Transcribe with Whisper
            print("  Processing with Whisper model...")
            print("  (This may take several minutes for long files...)")

            result = self.model.transcribe(
                str(audio_file_path),
                verbose=False,
                word_timestamps=True  # Enable word-level timestamps
            )

            # Extract words from segments (Whisper's format)
            words = []
            for segment in result.get('segments', []):
                if 'words' in segment:
                    for word_info in segment['words']:
                        words.append({
                            'word': word_info.get('word', '').strip(),
                            'start': word_info.get('start', 0),
                            'end': word_info.get('end', 0)
                        })

            # Prepare transcript data in our standard format
            transcript_data = {
                'text': result['text'],
                'language': result.get('language', 'unknown'),
                'duration': result.get('segments', [{}])[-1].get('end', 0) if result.get('segments') else 0,
                'segments': result.get('segments', []),
                'words': words
            }

            print(f"[OK] Transcription complete")
            print(f"  Language: {transcript_data['language']}")
            print(f"  Duration: {transcript_data['duration']:.1f}s")
            print(f"  Words: {len(transcript_data['words'])}")
            print(f"  Segments: {len(transcript_data['segments'])}")

            # Save transcript if output path provided
            if output_path:
                output_path = Path(output_path)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(transcript_data, f, indent=2, ensure_ascii=False)
                print(f"[OK] Transcript saved to: {output_path}")

            return transcript_data

        except Exception as e:
            print(f"[ERROR] Transcription error: {e}")
            raise

    def get_transcript_text(self, transcript_data):
        """Extract plain text from transcript data."""
        return transcript_data.get('text', '')

    def get_words_with_timestamps(self, transcript_data):
        """
        Get words with their timestamps.

        Returns:
            List of dictionaries with 'word', 'start', 'end' keys
        """
        return transcript_data.get('words', [])

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
            if word_data['word'].lower().strip('.,!?;:"\'').startswith(target_lower):
                matches.append(word_data)

        return matches


if __name__ == '__main__':
    # Test transcription
    import sys

    if len(sys.argv) < 2:
        print("Usage: python transcription.py <audio_file.wav>")
        sys.exit(1)

    audio_file = sys.argv[1]
    transcriber = Transcriber()

    output_json = Path(audio_file).stem + '_transcript.json'
    transcript = transcriber.transcribe(audio_file, output_json)

    print(f"\nTranscript preview:")
    print(transcript['text'][:500] + "...")
