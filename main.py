"""Main orchestrator for podcast automation workflow."""

import sys
import json
from pathlib import Path
from datetime import datetime

from config import Config
from dropbox_handler import DropboxHandler
from transcription import Transcriber
from content_editor import ContentEditor
from audio_processor import AudioProcessor


class PodcastAutomation:
    """Main automation orchestrator."""

    def __init__(self):
        """Initialize all components."""
        print("="*60)
        print("FAKE PROBLEMS PODCAST AUTOMATION")
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

    def process_episode(self, dropbox_path=None, local_audio_path=None):
        """
        Process a complete episode through the automation pipeline.

        Args:
            dropbox_path: Path to episode in Dropbox (optional if local_audio_path provided)
            local_audio_path: Local path to audio file (optional if dropbox_path provided)

        Returns:
            Dictionary with all output paths and metadata
        """
        print("="*60)
        print("STARTING EPISODE PROCESSING")
        print("="*60)
        print()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Step 1: Download from Dropbox (if needed)
        if local_audio_path:
            audio_file = Path(local_audio_path)
            print(f"[OK] Using local audio file: {audio_file}")
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

            print(f"Latest episode: {latest['name']}")
            audio_file = self.dropbox.download_episode(latest['path'])

        print()

        # Step 2: Transcribe with Whisper
        print("STEP 2: TRANSCRIBING WITH WHISPER")
        print("-" * 60)
        transcript_path = Config.OUTPUT_DIR / f"{audio_file.stem}_{timestamp}_transcript.json"
        transcript_data = self.transcriber.transcribe(audio_file, transcript_path)
        print()

        # Step 3: Analyze content with Claude
        print("STEP 3: ANALYZING CONTENT WITH CLAUDE")
        print("-" * 60)
        analysis = self.editor.analyze_content(transcript_data)

        # Save analysis
        analysis_path = Config.OUTPUT_DIR / f"{audio_file.stem}_{timestamp}_analysis.json"
        with open(analysis_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        print(f"[OK] Analysis saved to: {analysis_path}")
        print()

        # Step 4: Apply censorship
        print("STEP 4: APPLYING CENSORSHIP")
        print("-" * 60)
        censored_audio_path = Config.OUTPUT_DIR / f"{audio_file.stem}_{timestamp}_censored.wav"
        censored_audio = self.audio_processor.apply_censorship(
            audio_file,
            analysis.get('censor_timestamps', []),
            censored_audio_path
        )
        print()

        # Step 5: Create clips
        print("STEP 5: CREATING CLIPS")
        print("-" * 60)
        clip_dir = Config.CLIPS_DIR / f"{audio_file.stem}_{timestamp}"
        clip_dir.mkdir(exist_ok=True)

        clip_paths = self.audio_processor.create_clips(
            censored_audio,
            analysis.get('best_clips', []),
            clip_dir
        )
        print()

        # Step 6: Convert to MP3 for uploading
        print("STEP 6: CONVERTING TO MP3")
        print("-" * 60)
        mp3_path = self.audio_processor.convert_to_mp3(censored_audio)
        print()

        # Step 7: Upload to Dropbox
        print("STEP 7: UPLOAD TO DROPBOX")
        print("-" * 60)

        # Upload censored MP3 to finished_files folder
        print("Uploading censored audio to finished_files...")
        finished_path = self.dropbox.upload_finished_episode(
            mp3_path,
            episode_name=f"{audio_file.stem}_censored.mp3"
        )

        if finished_path:
            print(f"[OK] Censored audio uploaded to: {finished_path}")
        else:
            print("[WARNING] Failed to upload censored audio")

        # Upload clips to clips folder
        print("\nUploading clips to Dropbox...")
        episode_folder = f"ep_{self.dropbox.extract_episode_number(audio_file.name) or 'unknown'}"
        uploaded_clip_paths = self.dropbox.upload_clips(clip_paths, episode_folder_name=episode_folder)

        if uploaded_clip_paths:
            print(f"[OK] Uploaded {len(uploaded_clip_paths)} clips")
            for clip_path in uploaded_clip_paths:
                print(f"   - {clip_path}")
        else:
            print("[WARNING] Failed to upload clips")

        print()

        # Step 8: Social media uploading (future)
        print("STEP 8: SOCIAL MEDIA PLATFORMS")
        print("-" * 60)
        print("[INFO] Social media uploading not yet configured")
        print("   Set up API access in .env file and run uploaders separately")
        print()

        # Prepare results
        results = {
            'original_audio': str(audio_file),
            'transcript': str(transcript_path),
            'analysis': str(analysis_path),
            'censored_audio_wav': str(censored_audio),
            'censored_audio_mp3': str(mp3_path),
            'clips': [str(p) for p in clip_paths],
            'dropbox_finished_path': finished_path,
            'dropbox_clip_paths': uploaded_clip_paths,
            'episode_summary': analysis.get('episode_summary'),
            'social_captions': analysis.get('social_captions'),
            'best_clips_info': analysis.get('best_clips'),
            'censor_count': len(analysis.get('censor_timestamps', []))
        }

        # Save results summary
        results_path = Config.OUTPUT_DIR / f"{audio_file.stem}_{timestamp}_results.json"
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print("="*60)
        print("[SUCCESS] EPISODE PROCESSING COMPLETE!")
        print("="*60)
        print()
        print(f"All outputs saved to: {Config.OUTPUT_DIR}")
        print(f"Results summary: {results_path}")
        print()
        print(f"Episode Summary:")
        print(f"   {results['episode_summary']}")
        print()
        print(f"Censored items: {results['censor_count']}")
        print(f"Clips created: {len(results['clips'])}")
        print()
        print(f"Social Media Captions:")
        for platform, caption in results['social_captions'].items():
            print(f"   {platform.upper()}: {caption[:80]}...")
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
            size_mb = ep['size'] / 1024 / 1024
            modified = ep['modified'].strftime("%Y-%m-%d %H:%M")
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
            size_mb = ep['size'] / 1024 / 1024
            modified = ep['modified'].strftime("%Y-%m-%d %H:%M")

            if ep_num:
                print(f"Episode {ep_num}: {ep['name']}")
            else:
                print(f"[No Episode #]: {ep['name']}")

            print(f"   Size: {size_mb:.1f} MB | Modified: {modified}")
            print()

        return episodes_with_numbers

    def process_episode_by_number(self, episode_number):
        """Process a specific episode by its episode number."""
        print(f"Looking for Episode {episode_number}...")
        episode = self.dropbox.get_episode_by_number(episode_number)

        if not episode:
            print(f"Episode {episode_number} not found in Dropbox")
            print("\nAvailable episodes:")
            self.list_episodes_by_number()
            return None

        print(f"Found: {episode['name']}")
        print()

        return self.process_episode(dropbox_path=episode['path'])


def main():
    """Main entry point."""
    automation = PodcastAutomation()

    # Check command line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()

        if arg == 'list':
            # List available episodes sorted by number
            automation.list_episodes_by_number()
        elif arg == 'latest':
            # Process latest episode
            results = automation.process_episode()
        elif arg.startswith('ep') or arg.startswith('episode'):
            # Process specific episode by number
            # Support formats: ep25, episode25, ep 25, episode 25
            import re
            match = re.search(r'(\d+)', arg)
            if match:
                episode_num = int(match.group(1))
            elif len(sys.argv) > 2:
                episode_num = int(sys.argv[2])
            else:
                print("Usage: python main.py ep25 or python main.py episode 25")
                return

            results = automation.process_episode_by_number(episode_num)
        else:
            # Process specific file (local or dropbox path)
            file_path = sys.argv[1]
            if file_path.startswith('/'):
                # Dropbox path
                results = automation.process_episode(dropbox_path=file_path)
            else:
                # Local file
                results = automation.process_episode(local_audio_path=file_path)
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

        if choice == '1':
            results = automation.process_episode()
        elif choice == '2':
            automation.list_episodes_by_number()
            episode_num = input("\nEnter episode number: ").strip()
            try:
                results = automation.process_episode_by_number(int(episode_num))
            except ValueError:
                print("Invalid episode number")
        elif choice == '3':
            episodes = automation.list_episodes_by_number()
        elif choice == '4':
            episodes = automation.list_available_episodes()
        elif choice == '5':
            episodes = automation.list_available_episodes()
            path = input("\nEnter Dropbox path: ").strip()
            results = automation.process_episode(dropbox_path=path)
        elif choice == '6':
            path = input("Enter local audio file path: ").strip()
            results = automation.process_episode(local_audio_path=path)
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
