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
from video_converter import VideoConverter
from google_docs_tracker import GoogleDocsTopicTracker
from uploaders import (
    YouTubeUploader,
    InstagramUploader,
    TikTokUploader,
    TwitterUploader,
    SpotifyUploader,
    create_episode_metadata,
    create_instagram_caption,
    create_tiktok_caption,
    create_twitter_caption
)


class PodcastAutomation:
    """Main automation orchestrator."""

    def __init__(self, test_mode=False):
        """Initialize all components.

        Args:
            test_mode: If True, skip actual uploads to Dropbox and social media
        """
        self.test_mode = test_mode

        print("="*60)
        print("FAKE PROBLEMS PODCAST AUTOMATION")
        if test_mode:
            print("[TEST MODE] - Uploads disabled")
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

        # Initialize video converter (optional)
        try:
            self.video_converter = VideoConverter()
            print("[OK] Video converter initialized")
        except FileNotFoundError as e:
            print(f"[INFO] Video converter not available: {e}")
            self.video_converter = None

        # Initialize social media uploaders (optional)
        self.uploaders = self._init_uploaders()

        # Initialize Google Docs topic tracker (optional)
        try:
            self.topic_tracker = GoogleDocsTopicTracker()
            print("[OK] Google Docs topic tracker initialized")
        except (ValueError, FileNotFoundError) as e:
            print(f"[INFO] Google Docs topic tracker not available: {str(e).split(chr(10))[0]}")
            self.topic_tracker = None

        print()

    def _init_uploaders(self):
        """Initialize social media uploaders if credentials are configured."""
        uploaders = {}

        # YouTube
        try:
            uploaders['youtube'] = YouTubeUploader()
            print("[OK] YouTube uploader initialized")
        except (ValueError, FileNotFoundError) as e:
            print(f"[INFO] YouTube uploader not available: {str(e).split(chr(10))[0]}")

        # Twitter
        try:
            uploaders['twitter'] = TwitterUploader()
            print("[OK] Twitter uploader initialized")
        except ValueError as e:
            print(f"[INFO] Twitter uploader not available: {str(e).split(chr(10))[0]}")

        # Instagram
        try:
            uploaders['instagram'] = InstagramUploader()
            print("[OK] Instagram uploader initialized")
        except ValueError as e:
            print(f"[INFO] Instagram uploader not available: {str(e).split(chr(10))[0]}")

        # TikTok
        try:
            uploaders['tiktok'] = TikTokUploader()
            print("[OK] TikTok uploader initialized")
        except ValueError as e:
            print(f"[INFO] TikTok uploader not available: {str(e).split(chr(10))[0]}")

        # Spotify
        try:
            uploaders['spotify'] = SpotifyUploader()
            print("[OK] Spotify uploader initialized")
        except ValueError as e:
            print(f"[INFO] Spotify uploader not available: {str(e).split(chr(10))[0]}")

        return uploaders

    def _upload_to_social_media(
        self,
        episode_number: int,
        mp3_path: Path,
        video_clip_paths: list,
        analysis: dict
    ) -> dict:
        """
        Upload episode and clips to configured social media platforms.

        Args:
            episode_number: Episode number
            mp3_path: Path to processed MP3 file
            video_clip_paths: List of paths to video clip files
            analysis: Analysis data from Claude

        Returns:
            Dictionary with upload results for each platform
        """
        results = {}
        social_captions = analysis.get('social_captions', {})
        episode_summary = analysis.get('episode_summary', '')
        best_clips = analysis.get('best_clips', [])

        # YouTube uploads
        if 'youtube' in self.uploaders:
            print("\n[YouTube] Uploading content...")
            youtube_results = {}

            # Upload clips as Shorts
            if video_clip_paths:
                print(f"[INFO] Uploading {len(video_clip_paths)} clips as YouTube Shorts...")
                for i, video_path in enumerate(video_clip_paths[:3], 1):
                    if i - 1 < len(best_clips):
                        clip_info = best_clips[i - 1]
                        metadata = create_episode_metadata(
                            episode_number=episode_number,
                            episode_summary=episode_summary,
                            social_captions=social_captions,
                            clip_info=clip_info
                        )

                        print(f"\n[INFO] Uploading Clip {i}: {clip_info.get('title', 'Clip')}")
                        # Note: Actual upload would happen here
                        # Leaving as manual for now to avoid accidental uploads during testing
                        print(f"[INFO] Video ready: {video_path}")
                        print("[INFO] Ready to upload (upload code commented out for safety)")

            results['youtube'] = {'status': 'videos_ready', 'clips': len(video_clip_paths)}

        # Twitter posts
        if 'twitter' in self.uploaders:
            print("\n[Twitter] Posting content...")
            if self.test_mode:
                print("[TEST MODE] Skipping Twitter posts")
                print(f"[INFO] Would post: Episode {episode_number} announcement")
                if video_clip_paths:
                    print(f"[INFO] Would attach {len(video_clip_paths)} video clips")
                results['twitter'] = {'status': 'test_mode', 'skipped': True}
            else:
                try:
                    twitter_caption = create_twitter_caption(
                        clip_title=f"Episode {episode_number}",
                        social_caption=social_captions.get('twitter', episode_summary)
                    )

                    # Post episode announcement
                    twitter_result = self.uploaders['twitter'].post_episode_announcement(
                        episode_number=episode_number,
                        episode_summary=episode_summary,
                        youtube_url=None,  # Add if available
                        spotify_url=None,  # Add if available
                        clip_paths=video_clip_paths if video_clip_paths else None
                    )

                    results['twitter'] = twitter_result
                except Exception as e:
                    print(f"[ERROR] Twitter upload failed: {e}")
                    results['twitter'] = {'error': str(e)}

        # Instagram Reels
        if 'instagram' in self.uploaders:
            print("\n[Instagram] Uploading Reels...")
            if video_clip_paths:
                print(f"[INFO] {len(video_clip_paths)} vertical videos ready for Instagram Reels")
                print("[INFO] Instagram requires publicly accessible video URLs")
                print("[INFO] Upload videos to Dropbox and get public links to enable auto-upload")
                results['instagram'] = {'status': 'videos_ready', 'clips': len(video_clip_paths)}
            else:
                print("[INFO] No video clips available")
                results['instagram'] = {'status': 'no_videos'}

        # TikTok
        if 'tiktok' in self.uploaders:
            print("\n[TikTok] Uploading clips...")
            if video_clip_paths:
                print(f"[INFO] {len(video_clip_paths)} vertical videos ready for TikTok")
                print("[INFO] Videos ready for TikTok upload")
                print("[INFO] Ready to upload (upload code commented out for safety)")
                results['tiktok'] = {'status': 'videos_ready', 'clips': len(video_clip_paths)}
            else:
                print("[INFO] No video clips available")
                results['tiktok'] = {'status': 'no_videos'}

        # Spotify (RSS feed)
        if 'spotify' in self.uploaders:
            print("\n[Spotify] Updating RSS feed...")
            try:
                show_info = self.uploaders['spotify'].get_show_info()
                if show_info:
                    print(f"[OK] Connected to show: {show_info['name']}")

                # Get MP3 file info for RSS feed
                import os
                mp3_file_size = os.path.getsize(mp3_path)

                # Get episode duration from analysis
                # Assuming transcript has timing info
                duration_seconds = int(analysis.get('duration_seconds', 0))
                if duration_seconds == 0:
                    # Calculate from audio file if not in analysis
                    import wave
                    import contextlib
                    try:
                        with contextlib.closing(wave.open(str(mp3_path.with_suffix('.wav')), 'r')) as f:
                            frames = f.getnframes()
                            rate = f.getframerate()
                            duration_seconds = int(frames / float(rate))
                    except:
                        duration_seconds = 3600  # Default to 1 hour if can't determine

                # Generate shared Dropbox link for MP3
                # Note: This requires the file to be uploaded to Dropbox first
                # We'll add this step after Dropbox upload
                results['spotify'] = {
                    'status': 'rss_ready',
                    'note': 'RSS feed will be updated after Dropbox upload',
                    'duration': duration_seconds,
                    'file_size': mp3_file_size
                }

            except Exception as e:
                print(f"[ERROR] Spotify RSS preparation failed: {e}")
                results['spotify'] = {'error': str(e)}

        return results

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

        # Extract episode number for folder organization
        episode_number = self.dropbox.extract_episode_number(audio_file.name)
        if episode_number:
            episode_folder = f"ep_{episode_number}"
        else:
            episode_folder = f"ep_{audio_file.stem}_{timestamp}"

        # Create episode output subfolder
        episode_output_dir = Config.OUTPUT_DIR / episode_folder
        episode_output_dir.mkdir(exist_ok=True, parents=True)

        print()

        # Step 2: Transcribe with Whisper
        print("STEP 2: TRANSCRIBING WITH WHISPER")
        print("-" * 60)
        transcript_path = episode_output_dir / f"{audio_file.stem}_{timestamp}_transcript.json"
        transcript_data = self.transcriber.transcribe(audio_file, transcript_path)
        print()

        # Step 3: Analyze content with Claude
        print("STEP 3: ANALYZING CONTENT WITH CLAUDE")
        print("-" * 60)
        analysis = self.editor.analyze_content(transcript_data)

        # Save analysis
        analysis_path = episode_output_dir / f"{audio_file.stem}_{timestamp}_analysis.json"
        with open(analysis_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        print(f"[OK] Analysis saved to: {analysis_path}")
        print()

        # Step 3.5: Update Google Docs topic tracker
        topic_tracker_results = {}
        if self.topic_tracker and episode_number:
            # Get full transcript text for topic matching
            full_transcript = " ".join([seg.get('text', '') for seg in transcript_data.get('segments', [])])
            episode_summary = analysis.get('episode_summary', '')

            topic_tracker_results = self.topic_tracker.update_topics_for_episode(
                transcript_text=full_transcript,
                episode_summary=episode_summary,
                episode_number=episode_number
            )
        elif not self.topic_tracker:
            print("[INFO] Google Docs topic tracker not configured - skipping")
        print()

        # Step 4: Apply censorship
        print("STEP 4: APPLYING CENSORSHIP")
        print("-" * 60)
        censored_audio_path = episode_output_dir / f"{audio_file.stem}_{timestamp}_censored.wav"
        censored_audio = self.audio_processor.apply_censorship(
            audio_file,
            analysis.get('censor_timestamps', []),
            censored_audio_path
        )
        print()

        # Step 5: Create clips
        print("STEP 5: CREATING CLIPS")
        print("-" * 60)
        clip_dir = Config.CLIPS_DIR / episode_folder
        clip_dir.mkdir(exist_ok=True, parents=True)

        clip_paths = self.audio_processor.create_clips(
            censored_audio,
            analysis.get('best_clips', []),
            clip_dir
        )
        print()

        # Step 5.5: Convert clips to videos
        print("STEP 5.5: CONVERTING CLIPS TO VIDEOS")
        print("-" * 60)
        video_clip_paths = []
        if self.video_converter and clip_paths:
            print("[INFO] Creating vertical videos (1080x1920) for Shorts/Reels/TikTok...")
            video_clip_paths = self.video_converter.convert_clips_to_videos(
                clip_paths=clip_paths,
                format_type='vertical',  # For Reels, TikTok, Shorts
                output_dir=str(clip_dir)
            )
            print(f"[OK] Created {len(video_clip_paths)} video clips")
        elif not self.video_converter:
            print("[INFO] Video converter not available - skipping video creation")
        else:
            print("[INFO] No clips to convert")
        print()

        # Step 6: Convert to MP3 for uploading
        print("STEP 6: CONVERTING TO MP3")
        print("-" * 60)
        mp3_path = self.audio_processor.convert_to_mp3(censored_audio)
        print()

        # Step 7: Upload to Dropbox
        print("STEP 7: UPLOAD TO DROPBOX")
        print("-" * 60)

        if self.test_mode:
            print("[TEST MODE] Skipping Dropbox uploads")
            print(f"[INFO] Would upload: {mp3_path}")
            print(f"[INFO] Would upload {len(clip_paths)} clips")
            finished_path = None
            uploaded_clip_paths = []
        else:
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
            uploaded_clip_paths = self.dropbox.upload_clips(clip_paths, episode_folder_name=episode_folder)

            if uploaded_clip_paths:
                print(f"[OK] Uploaded {len(uploaded_clip_paths)} clips")
                for clip_path in uploaded_clip_paths:
                    print(f"   - {clip_path}")
            else:
                print("[WARNING] Failed to upload clips")

        # Step 7.5: Update RSS feed (if Spotify uploader configured and Dropbox upload succeeded)
        if not self.test_mode and finished_path and 'spotify' in self.uploaders:
            print("\nSTEP 7.5: UPDATING RSS FEED")
            print("-" * 60)

            try:
                # Get or create shared link for the MP3
                print("Creating shared link for episode...")
                audio_url = self.dropbox.get_shared_link(finished_path)

                if audio_url:
                    print(f"[OK] Shared link created: {audio_url[:60]}...")

                    # Get MP3 file info
                    import os
                    mp3_file_size = os.path.getsize(mp3_path)

                    # Get duration from transcript
                    transcript_file = transcript_path
                    with open(transcript_file, 'r', encoding='utf-8') as f:
                        transcript_data = json.load(f)
                        episode_duration = int(transcript_data.get('duration', 3600))

                    # Generate episode title and description
                    episode_summary = analysis.get('episode_summary', '')
                    episode_title = f"Episode {episode_number}"
                    if analysis.get('episode_title'):
                        episode_title = analysis.get('episode_title')

                    # Extract keywords from social captions
                    keywords = []
                    if analysis.get('social_captions'):
                        # Extract hashtags or topics if available
                        keywords = ['podcast', 'comedy', 'fake-problems']

                    # Update RSS feed
                    rss_feed_path = self.uploaders['spotify'].update_rss_feed(
                        episode_number=episode_number,
                        episode_title=episode_title,
                        episode_description=episode_summary,
                        audio_url=audio_url,
                        audio_file_size=mp3_file_size,
                        duration_seconds=episode_duration,
                        pub_date=datetime.now(),
                        keywords=keywords
                    )

                    print(f"[OK] RSS feed updated successfully!")
                    print(f"[INFO] Feed location: {rss_feed_path}")
                    print(f"[INFO] Upload this file to a public URL for Spotify to access")

                else:
                    print("[WARNING] Could not create shared link for RSS feed")

            except Exception as e:
                print(f"[ERROR] RSS feed update failed: {e}")
                import traceback
                traceback.print_exc()

        print()

        # Step 8: Social media uploading
        print("STEP 8: SOCIAL MEDIA PLATFORMS")
        print("-" * 60)

        social_media_results = {}

        if self.test_mode:
            print("[TEST MODE] Skipping social media uploads")
            social_media_results = {'test_mode': True, 'skipped': True}
        elif not self.uploaders:
            print("[INFO] No social media uploaders configured")
            print("   Set up API credentials in .env file to enable uploads")
        else:
            social_media_results = self._upload_to_social_media(
                episode_number=episode_number,
                mp3_path=mp3_path,
                video_clip_paths=video_clip_paths,
                analysis=analysis
            )

        print()

        # Prepare results
        results = {
            'original_audio': str(audio_file),
            'transcript': str(transcript_path),
            'analysis': str(analysis_path),
            'censored_audio_wav': str(censored_audio),
            'censored_audio_mp3': str(mp3_path),
            'clips': [str(p) for p in clip_paths],
            'video_clips': [str(p) for p in video_clip_paths],
            'dropbox_finished_path': finished_path,
            'dropbox_clip_paths': uploaded_clip_paths,
            'episode_summary': analysis.get('episode_summary'),
            'social_captions': analysis.get('social_captions'),
            'best_clips_info': analysis.get('best_clips'),
            'censor_count': len(analysis.get('censor_timestamps', [])),
            'social_media_results': social_media_results,
            'topic_tracker_results': topic_tracker_results
        }

        # Save results summary
        results_path = episode_output_dir / f"{audio_file.stem}_{timestamp}_results.json"
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
            try:
                print(f"   {platform.upper()}: {caption[:80]}...")
            except UnicodeEncodeError:
                # Handle Windows terminal encoding issues
                print(f"   {platform.upper()}: {caption[:80].encode('ascii', 'replace').decode('ascii')}...")
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
    # Check for test mode flag
    test_mode = '--test' in sys.argv or '--test-mode' in sys.argv
    if test_mode:
        sys.argv = [arg for arg in sys.argv if arg not in ['--test', '--test-mode']]

    automation = PodcastAutomation(test_mode=test_mode)

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
