"""Process historical podcast episodes - transcribe, clip, and upload to Dropbox only."""

import sys
import json
from pathlib import Path
from datetime import datetime

from config import Config
from dropbox_handler import DropboxHandler
from transcription import Transcriber
from content_editor import ContentEditor
from audio_processor import AudioProcessor


class HistoricalEpisodeProcessor:
    """Process historical episodes without social media uploads."""

    def __init__(self):
        """Initialize all components."""
        print("="*60)
        print("HISTORICAL PODCAST EPISODE PROCESSOR")
        print("Transcribe, Clip, Upload to Dropbox (NO social media)")
        print("="*60)
        print()

        # Validate configuration
        Config.validate()
        Config.create_directories()

        # Initialize components
        self.dropbox = DropboxHandler()
        self.transcriber = Transcriber()
        self.editor = ContentEditor()
        self.audio_processor = AudioProcessor()

        print()

    def process_historical_episode(self, audio_file_path):
        """
        Process a single historical episode.

        Args:
            audio_file_path: Path to the audio file

        Returns:
            Dictionary with processing results
        """
        audio_file = Path(audio_file_path)

        if not audio_file.exists():
            print(f"[ERROR] File not found: {audio_file}")
            return None

        print("="*60)
        print(f"PROCESSING: {audio_file.name}")
        print("="*60)
        print()

        # Extract episode number from filename
        episode_number = self.dropbox.extract_episode_number(audio_file.name)
        if episode_number:
            print(f"[INFO] Detected Episode #{episode_number}")
        else:
            print(f"[WARNING] Could not detect episode number from filename")
            episode_number = 0

        episode_folder = f"ep_{episode_number}" if episode_number else "ep_unknown"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create episode output subfolder
        episode_output_dir = Config.OUTPUT_DIR / episode_folder
        episode_output_dir.mkdir(exist_ok=True, parents=True)

        # Step 1: Transcribe with Whisper
        print("\nSTEP 1: TRANSCRIBING WITH WHISPER")
        print("-" * 60)
        transcript_path = episode_output_dir / f"{audio_file.stem}_transcript.json"
        transcript_data = self.transcriber.transcribe(audio_file, transcript_path)
        print()

        # Step 2: Analyze content with Claude
        print("STEP 2: ANALYZING CONTENT WITH CLAUDE")
        print("-" * 60)
        analysis = self.editor.analyze_content(transcript_data)

        # Save analysis
        analysis_path = episode_output_dir / f"{audio_file.stem}_analysis.json"
        with open(analysis_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        print(f"[OK] Analysis saved to: {analysis_path}")
        print()

        # Step 3: Apply censorship
        print("STEP 3: APPLYING CENSORSHIP")
        print("-" * 60)
        censored_audio_path = episode_output_dir / f"{audio_file.stem}_censored.wav"
        censored_audio = self.audio_processor.apply_censorship(
            audio_file,
            analysis.get('censor_timestamps', []),
            censored_audio_path
        )
        print()

        # Step 4: Create clips
        print("STEP 4: CREATING CLIPS")
        print("-" * 60)
        clip_dir = Config.CLIPS_DIR / episode_folder
        clip_dir.mkdir(exist_ok=True, parents=True)

        clip_paths = self.audio_processor.create_clips(
            censored_audio,
            analysis.get('best_clips', []),
            clip_dir
        )
        print()

        # Step 5: Convert to MP3 for uploading
        print("STEP 5: CONVERTING TO MP3")
        print("-" * 60)
        mp3_path = self.audio_processor.convert_to_mp3(censored_audio)
        print()

        # Step 6: Upload to Dropbox
        print("STEP 6: UPLOAD TO DROPBOX")
        print("-" * 60)

        # Upload transcription
        print(f"\n[INFO] Uploading transcription to /podcast/transcriptions/{episode_folder}/")
        transcription_dropbox_path = self.dropbox.upload_transcription(
            transcript_path,
            episode_folder_name=episode_folder
        )
        if transcription_dropbox_path:
            print(f"[OK] Transcription uploaded to: {transcription_dropbox_path}")
        else:
            print("[WARNING] Failed to upload transcription")

        # Upload censored MP3 to finished_files folder
        print(f"\n[INFO] Uploading censored audio to /podcast/finished_files/")
        finished_path = self.dropbox.upload_finished_episode(
            mp3_path,
            episode_name=f"Episode_{episode_number}_{audio_file.stem}_censored.mp3"
        )

        if finished_path:
            print(f"[OK] Censored audio uploaded to: {finished_path}")
        else:
            print("[WARNING] Failed to upload censored audio")

        # Upload clips to clips folder
        print(f"\n[INFO] Uploading clips to /podcast/clips/{episode_folder}/")
        uploaded_clip_paths = self.dropbox.upload_clips(clip_paths, episode_folder_name=episode_folder)

        if uploaded_clip_paths:
            print(f"[OK] Uploaded {len(uploaded_clip_paths)} clips")
            for clip_path in uploaded_clip_paths:
                print(f"   - {clip_path}")
        else:
            print("[WARNING] Failed to upload clips")

        print()

        # Prepare results
        results = {
            'episode_number': episode_number,
            'original_audio': str(audio_file),
            'transcript': str(transcript_path),
            'analysis': str(analysis_path),
            'censored_audio_wav': str(censored_audio),
            'censored_audio_mp3': str(mp3_path),
            'clips': [str(p) for p in clip_paths],
            'dropbox_transcription_path': transcription_dropbox_path,
            'dropbox_finished_path': finished_path,
            'dropbox_clip_paths': uploaded_clip_paths,
            'episode_summary': analysis.get('episode_summary'),
            'best_clips_info': analysis.get('best_clips'),
            'censor_count': len(analysis.get('censor_timestamps', [])),
        }

        # Save results summary
        results_path = episode_output_dir / f"{audio_file.stem}_results.json"
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print("="*60)
        print(f"[SUCCESS] EPISODE {episode_number} PROCESSING COMPLETE!")
        print("="*60)
        print()
        print(f"Episode Summary: {results['episode_summary'][:100]}...")
        print(f"Censored items: {results['censor_count']}")
        print(f"Clips created: {len(results['clips'])}")
        print()

        return results

    def process_all_historical_episodes(self, folder_path="historical_ep", start_episode=None):
        """
        Process all episodes in the historical_ep folder.

        Args:
            folder_path: Path to folder containing historical episodes
            start_episode: Episode number to start from (skip episodes before this)
        """
        folder = Path(folder_path)

        if not folder.exists():
            print(f"[ERROR] Folder not found: {folder}")
            return

        # Find all audio files (mp4, m4a, wav, mp3)
        audio_extensions = ['.mp4', '.m4a', '.wav', '.mp3']
        audio_files = []
        for ext in audio_extensions:
            audio_files.extend(folder.glob(f"*{ext}"))

        if not audio_files:
            print(f"[ERROR] No audio files found in {folder}")
            return

        # Sort by episode number
        def get_episode_num(file_path):
            num = self.dropbox.extract_episode_number(file_path.name)
            return num if num else 999

        audio_files.sort(key=get_episode_num)

        print(f"\n[INFO] Found {len(audio_files)} historical episodes to process")

        # Skip episodes if start_episode is specified
        if start_episode:
            print(f"[INFO] Skipping episodes before Episode #{start_episode}")
        print()

        for i, audio_file in enumerate(audio_files, 1):
            # Skip episodes before start_episode
            episode_num = self.dropbox.extract_episode_number(audio_file.name) or 999
            if start_episode and episode_num < start_episode:
                print(f"[INFO] Skipping Episode #{episode_num} (already processed)")
                continue
            print(f"\n{'='*60}")
            print(f"PROCESSING FILE {i}/{len(audio_files)}")
            print(f"{'='*60}")

            try:
                results = self.process_historical_episode(audio_file)
                if results:
                    print(f"[OK] Successfully processed episode {results['episode_number']}")
                else:
                    print(f"[ERROR] Failed to process {audio_file.name}")
            except Exception as e:
                print(f"[ERROR] Exception processing {audio_file.name}: {e}")
                import traceback
                traceback.print_exc()

                # Auto-continue on network errors, ask on other errors
                error_str = str(e).lower()
                if 'ssl' in error_str or 'connection' in error_str or 'timeout' in error_str or 'max retries' in error_str:
                    print("[INFO] Network error detected - automatically continuing with next episode")
                    print("[INFO] You may want to manually re-process this episode later")
                    continue
                else:
                    print("[INFO] Non-network error - continuing with next episode")
                    continue

        print("\n" + "="*60)
        print("ALL HISTORICAL EPISODES PROCESSED!")
        print("="*60)


def main():
    """Main entry point."""
    processor = HistoricalEpisodeProcessor()

    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == 'all':
            # Process all historical episodes
            folder = "historical_ep"
            start_episode = None

            # Check for optional start episode (e.g., "all 5" starts from episode 5)
            if len(sys.argv) > 2:
                try:
                    start_episode = int(sys.argv[2])
                    print(f"[INFO] Starting from Episode #{start_episode}")
                except ValueError:
                    folder = sys.argv[2]

            processor.process_all_historical_episodes(folder, start_episode=start_episode)
        else:
            # Process single file
            file_path = sys.argv[1]
            processor.process_historical_episode(file_path)
    else:
        # Interactive mode
        print("Historical Episode Processor - Interactive Mode")
        print()
        print("Options:")
        print("  1. Process all episodes in historical_ep/ folder")
        print("  2. Process a single episode file")
        print()

        choice = input("Enter choice (1-2): ").strip()

        if choice == '1':
            processor.process_all_historical_episodes()
        elif choice == '2':
            file_path = input("Enter path to audio file: ").strip()
            processor.process_historical_episode(file_path)
        else:
            print("Invalid choice")


if __name__ == '__main__':
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
