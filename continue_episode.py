"""Continue podcast automation from manually edited files.

Usage:
    python continue_episode.py <episode_number>
    python continue_episode.py 26

This script continues the podcast automation workflow from where you have
manually edited files. It will:
1. Convert audio clips to vertical videos (for Shorts/Reels/TikTok)
2. Convert full episode to horizontal video (for YouTube)
3. Convert censored WAV to MP3
4. Upload to Dropbox
5. Update RSS feed
6. Upload to YouTube
7. Post to Twitter
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

from config import Config
from dropbox_handler import DropboxHandler
from video_converter import VideoConverter
from audio_processor import AudioProcessor
from uploaders import (
    YouTubeUploader,
    TwitterUploader,
    SpotifyUploader,
    create_episode_metadata,
    create_twitter_caption
)


def find_episode_files(episode_number):
    """Find all relevant files for an episode."""
    episode_folder = f"ep_{episode_number}"
    episode_output_dir = Config.OUTPUT_DIR / episode_folder
    clips_dir = Config.CLIPS_DIR / episode_folder

    files = {
        'episode_output_dir': episode_output_dir,
        'clips_dir': clips_dir,
        'censored_wav': None,
        'analysis': None,
        'transcript': None,
        'audio_clips': [],
        'video_clips': [],
        'mp3': None,
        'full_video': None,
    }

    if not episode_output_dir.exists():
        return files

    # Find censored WAV (look for *_censored.wav)
    censored_wavs = list(episode_output_dir.glob("*_censored.wav"))
    if censored_wavs:
        files['censored_wav'] = censored_wavs[0]

    # Find analysis JSON
    analysis_files = list(episode_output_dir.glob("*_analysis.json"))
    if analysis_files:
        files['analysis'] = analysis_files[0]

    # Find transcript JSON
    transcript_files = list(episode_output_dir.glob("*_transcript.json"))
    if transcript_files:
        files['transcript'] = transcript_files[0]

    # Find existing MP3
    mp3_files = list(episode_output_dir.glob("*.mp3"))
    if mp3_files:
        files['mp3'] = mp3_files[0]

    # Find existing full episode video
    video_files = list(episode_output_dir.glob("*_episode*.mp4"))
    if video_files:
        files['full_video'] = video_files[0]

    # Find audio clips
    if clips_dir.exists():
        files['audio_clips'] = sorted(clips_dir.glob("*.wav"))
        files['video_clips'] = sorted(clips_dir.glob("*.mp4"))

    return files


def continue_episode(episode_number, skip_video=False, skip_upload=False):
    """Continue processing an episode from manually edited files.

    Args:
        episode_number: The episode number to process
        skip_video: Skip video conversion steps
        skip_upload: Skip all upload steps (Dropbox, YouTube, Twitter)
    """

    print("="*60)
    print(f"CONTINUING EPISODE {episode_number} PROCESSING")
    print("="*60)
    print()

    # Find existing files
    files = find_episode_files(episode_number)
    episode_output_dir = files['episode_output_dir']
    clips_dir = files['clips_dir']

    # Verify essential files exist
    if not files['censored_wav']:
        print(f"[ERROR] No censored WAV found in: {episode_output_dir}")
        print(f"[INFO] Looking for files matching: *_censored.wav")
        return None

    censored_wav = files['censored_wav']
    print(f"[OK] Found censored WAV: {censored_wav.name}")
    print(f"[OK] Size: {censored_wav.stat().st_size / 1024 / 1024:.1f} MB")

    # Load analysis
    if not files['analysis']:
        print(f"[ERROR] No analysis JSON found in: {episode_output_dir}")
        return None

    with open(files['analysis'], 'r', encoding='utf-8') as f:
        analysis = json.load(f)
    print(f"[OK] Loaded analysis: {files['analysis'].name}")

    # Load transcript for duration
    episode_duration = 3600  # Default 1 hour
    if files['transcript']:
        with open(files['transcript'], 'r', encoding='utf-8') as f:
            transcript_data = json.load(f)
        episode_duration = int(transcript_data.get('duration', 3600))
        print(f"[OK] Episode duration: {episode_duration // 60} minutes")

    # Episode info
    episode_title = analysis.get('episode_title', f'Episode {episode_number}')
    print(f"\nEpisode {episode_number}: {episode_title}")
    print()

    # Get existing clip paths
    clip_paths = files['audio_clips']
    existing_video_clips = files['video_clips']
    print(f"[OK] Found {len(clip_paths)} audio clips")
    for clip in clip_paths:
        print(f"   - {clip.name}")
    if existing_video_clips:
        print(f"[OK] Found {len(existing_video_clips)} existing video clips")
    print()

    # Initialize components
    print("-" * 60)
    print("INITIALIZING COMPONENTS")
    print("-" * 60)

    audio_processor = AudioProcessor()

    try:
        video_converter = VideoConverter()
        print("[OK] Video converter initialized")
    except FileNotFoundError as e:
        print(f"[WARNING] Video converter not available: {e}")
        video_converter = None

    try:
        dropbox = DropboxHandler()
    except Exception as e:
        print(f"[WARNING] Dropbox not available: {e}")
        dropbox = None

    # Initialize uploaders
    uploaders = {}

    try:
        uploaders['youtube'] = YouTubeUploader()
        print("[OK] YouTube uploader initialized")
    except Exception as e:
        print(f"[INFO] YouTube not available: {str(e).split(chr(10))[0]}")

    try:
        uploaders['twitter'] = TwitterUploader()
        print("[OK] Twitter uploader initialized")
    except Exception as e:
        print(f"[INFO] Twitter not available: {str(e).split(chr(10))[0]}")

    try:
        uploaders['spotify'] = SpotifyUploader()
        print("[OK] Spotify uploader initialized")
    except Exception as e:
        print(f"[INFO] Spotify not available: {str(e).split(chr(10))[0]}")

    print()

    # STEP 1: Convert clips to vertical videos
    print("-" * 60)
    print("STEP 1: CONVERTING CLIPS TO VERTICAL VIDEOS")
    print("-" * 60)

    video_clip_paths = [str(p) for p in existing_video_clips]  # Use existing if available

    if skip_video:
        print("[SKIP] Video conversion skipped (--skip-video)")
    elif existing_video_clips and len(existing_video_clips) >= len(clip_paths):
        print(f"[OK] Using {len(existing_video_clips)} existing video clips")
    elif video_converter and clip_paths:
        print("[INFO] Creating vertical videos (720x1280) for Shorts/Reels/TikTok...")
        video_clip_paths = video_converter.convert_clips_to_videos(
            clip_paths=[str(p) for p in clip_paths],
            format_type='vertical',
            output_dir=str(clips_dir)
        )
        print(f"[OK] Created {len(video_clip_paths)} video clips")
    else:
        print("[SKIP] Video converter not available or no clips")
    print()

    # STEP 2: Convert full episode to video for YouTube
    print("-" * 60)
    print("STEP 2: CONVERTING FULL EPISODE TO VIDEO")
    print("-" * 60)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    full_episode_video_path = str(files['full_video']) if files['full_video'] else None

    if skip_video:
        print("[SKIP] Video conversion skipped (--skip-video)")
    elif files['full_video']:
        print(f"[OK] Using existing full episode video: {files['full_video'].name}")
    elif video_converter:
        print("[INFO] Creating horizontal video (1280x720) for YouTube...")
        print("[INFO] This may take several minutes for long episodes...")
        full_episode_video_path = video_converter.create_episode_video(
            audio_path=str(censored_wav),
            output_path=str(episode_output_dir / f"ep_{episode_number}_episode_{timestamp}.mp4"),
            format_type='horizontal'
        )
        if full_episode_video_path:
            print(f"[OK] Full episode video created: {full_episode_video_path}")
        else:
            print("[WARNING] Failed to create full episode video")
    else:
        print("[SKIP] Video converter not available")
    print()

    # STEP 3: Convert to MP3
    print("-" * 60)
    print("STEP 3: CONVERTING TO MP3")
    print("-" * 60)

    if files['mp3']:
        mp3_path = files['mp3']
        print(f"[OK] Using existing MP3: {mp3_path.name}")
    else:
        mp3_path = audio_processor.convert_to_mp3(censored_wav)
    print()

    # STEP 4: Upload to Dropbox
    print("-" * 60)
    print("STEP 4: UPLOADING TO DROPBOX")
    print("-" * 60)

    finished_path = None
    uploaded_clip_paths = []

    if skip_upload:
        print("[SKIP] Uploads skipped (--skip-upload)")
    elif dropbox:
        # Upload MP3 to finished_files
        safe_title = "".join(c for c in episode_title if c.isalnum() or c in (' ', '-', '_')).strip()
        finished_filename = f"Episode #{episode_number} - {safe_title}.mp3"

        print(f"Uploading: {finished_filename}")
        finished_path = dropbox.upload_finished_episode(mp3_path, episode_name=finished_filename)

        if finished_path:
            print(f"[OK] MP3 uploaded to: {finished_path}")
        else:
            print("[WARNING] Failed to upload MP3")

        # Upload video clips
        if video_clip_paths:
            print("\nUploading video clips...")
            uploaded_clip_paths = dropbox.upload_clips(video_clip_paths, episode_folder_name=f"ep_{episode_number}")
            print(f"[OK] Uploaded {len(uploaded_clip_paths)} video clips")
    else:
        print("[SKIP] Dropbox not available")
    print()

    # STEP 5: Update RSS feed
    print("-" * 60)
    print("STEP 5: UPDATING RSS FEED")
    print("-" * 60)

    if skip_upload:
        print("[SKIP] RSS feed update skipped (--skip-upload)")
    elif dropbox and finished_path and 'spotify' in uploaders:
        try:
            print("Creating shared link for episode...")
            audio_url = dropbox.get_shared_link(finished_path)

            if audio_url:
                print(f"[OK] Shared link: {audio_url[:60]}...")

                import os
                mp3_file_size = os.path.getsize(mp3_path)
                episode_summary = analysis.get('episode_summary', '')
                keywords = ['podcast', 'comedy', 'fake-problems']

                rss_feed_path = uploaders['spotify'].update_rss_feed(
                    episode_number=episode_number,
                    episode_title=episode_title,
                    episode_description=episode_summary,
                    audio_url=audio_url,
                    audio_file_size=mp3_file_size,
                    duration_seconds=episode_duration,
                    pub_date=datetime.now(),
                    keywords=keywords
                )

                print(f"[OK] RSS feed updated: {rss_feed_path}")

                # Upload RSS feed to Dropbox
                print("Uploading RSS feed to Dropbox...")
                rss_dropbox_path = "/podcast/podcast_feed.xml"
                dropbox.upload_file(rss_feed_path, rss_dropbox_path, overwrite=True)
                print(f"[OK] RSS feed uploaded to Dropbox: {rss_dropbox_path}")
                print(f"[INFO] Spotify will check for updates within 2-8 hours")
            else:
                print("[WARNING] Could not create shared link")
        except Exception as e:
            print(f"[ERROR] RSS feed update failed: {e}")
    else:
        print("[SKIP] RSS feed update skipped (Dropbox or Spotify not available)")
    print()

    # STEP 6: Upload to YouTube
    print("-" * 60)
    print("STEP 6: UPLOADING TO YOUTUBE")
    print("-" * 60)

    youtube_results = {'clips': [], 'full_episode': None}
    social_captions = analysis.get('social_captions', {})
    episode_summary = analysis.get('episode_summary', '')
    best_clips = analysis.get('best_clips', [])

    if skip_upload:
        print("[SKIP] YouTube upload skipped (--skip-upload)")
    elif 'youtube' in uploaders:
        # Upload full episode
        if full_episode_video_path:
            print("\n[INFO] Uploading full episode to YouTube...")
            full_title = f"Episode #{episode_number} - {episode_title}"
            full_description = f"{episode_summary}\n\n{social_captions.get('youtube', '')}"
            tags = [Config.PODCAST_NAME, 'podcast', 'comedy', f'episode{episode_number}']

            try:
                full_episode_result = uploaders['youtube'].upload_episode(
                    video_path=str(full_episode_video_path),
                    title=full_title[:100],
                    description=full_description,
                    tags=tags,
                    privacy_status='public'
                )
                if full_episode_result:
                    youtube_results['full_episode'] = full_episode_result
                    print(f"[OK] Full episode uploaded: {full_episode_result.get('video_url', 'Unknown URL')}")
                else:
                    print("[ERROR] Failed to upload full episode")
            except Exception as e:
                print(f"[ERROR] YouTube upload error: {e}")

        # Upload shorts
        if video_clip_paths:
            print(f"\n[INFO] Uploading {len(video_clip_paths)} clips as YouTube Shorts...")
            for i, video_path in enumerate(video_clip_paths[:3], 1):
                if i - 1 < len(best_clips):
                    clip_info = best_clips[i - 1]
                    metadata = create_episode_metadata(
                        episode_number=episode_number,
                        episode_summary=episode_summary,
                        social_captions=social_captions,
                        clip_info=clip_info
                    )

                    clip_title = clip_info.get('suggested_title', f'Clip {i}')
                    print(f"\n[INFO] Uploading Clip {i}: {clip_title}")

                    try:
                        upload_result = uploaders['youtube'].upload_short(
                            video_path=str(video_path),
                            title=metadata['title'],
                            description=metadata['description'],
                            tags=metadata['tags'],
                            privacy_status='public'
                        )
                        if upload_result:
                            youtube_results['clips'].append(upload_result)
                            print(f"[OK] Uploaded: {upload_result.get('video_url', 'Unknown URL')}")
                        else:
                            print(f"[ERROR] Failed to upload clip {i}")
                    except Exception as e:
                        print(f"[ERROR] YouTube upload error: {e}")
    else:
        print("[SKIP] YouTube uploader not available")
    print()

    # STEP 7: Post to Twitter
    print("-" * 60)
    print("STEP 7: POSTING TO TWITTER")
    print("-" * 60)

    twitter_results = None
    if skip_upload:
        print("[SKIP] Twitter post skipped (--skip-upload)")
    elif 'twitter' in uploaders:
        try:
            # Get YouTube URL if available (don't fail if YouTube upload failed)
            youtube_url = None
            if youtube_results and youtube_results.get('full_episode'):
                youtube_url = youtube_results['full_episode'].get('video_url')

            twitter_results = uploaders['twitter'].post_episode_announcement(
                episode_number=episode_number,
                episode_summary=episode_summary,
                youtube_url=youtube_url,
                spotify_url=None,
                clip_paths=video_clip_paths if video_clip_paths else None
            )
            print(f"[OK] Posted to Twitter")
        except Exception as e:
            print(f"[ERROR] Twitter post failed: {e}")
    else:
        print("[SKIP] Twitter uploader not available")
    print()

    # Summary
    print("="*60)
    print(f"[SUCCESS] EPISODE {episode_number} PROCESSING COMPLETE!")
    print("="*60)
    print()
    print(f"Episode {episode_number}: \"{episode_title}\"")
    print()
    print(f"Files created:")
    print(f"  - MP3: {mp3_path}")
    if full_episode_video_path:
        print(f"  - Full episode video: {full_episode_video_path}")
    print(f"  - Video clips: {len(video_clip_paths)}")
    print()

    if finished_path:
        print(f"Dropbox uploads:")
        print(f"  - MP3: {finished_path}")
        print(f"  - Clips: {len(uploaded_clip_paths)}")
    print()

    if youtube_results and youtube_results.get('full_episode'):
        print(f"YouTube:")
        print(f"  - Full episode: {youtube_results['full_episode'].get('video_url', 'Uploaded')}")
        for i, clip in enumerate(youtube_results.get('clips', []), 1):
            print(f"  - Short {i}: {clip.get('video_url', 'Uploaded')}")

    return {
        'episode_number': episode_number,
        'episode_title': episode_title,
        'mp3_path': str(mp3_path),
        'full_episode_video': full_episode_video_path,
        'video_clips': video_clip_paths,
        'dropbox_path': finished_path,
        'youtube_results': youtube_results,
        'twitter_results': twitter_results
    }


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description='Continue podcast automation from manually edited files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python continue_episode.py 26              # Process episode 26
  python continue_episode.py 26 --skip-video # Skip video conversion
  python continue_episode.py 26 --skip-upload # Only create files, no uploads
        """
    )

    parser.add_argument(
        'episode',
        type=int,
        help='Episode number to process'
    )

    parser.add_argument(
        '--skip-video',
        action='store_true',
        help='Skip video conversion steps (use existing videos if available)'
    )

    parser.add_argument(
        '--skip-upload',
        action='store_true',
        help='Skip all upload steps (Dropbox, YouTube, Twitter)'
    )

    args = parser.parse_args()

    return continue_episode(
        episode_number=args.episode,
        skip_video=args.skip_video,
        skip_upload=args.skip_upload
    )


if __name__ == '__main__':
    try:
        results = main()
    except KeyboardInterrupt:
        print("\n\n[WARNING] Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
