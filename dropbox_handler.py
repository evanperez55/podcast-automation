"""Dropbox file download handler."""

import dropbox
from dropbox.exceptions import ApiError
from pathlib import Path
from config import Config
from tqdm import tqdm
import re


class DropboxHandler:
    """Handle Dropbox operations for podcast episodes."""

    def __init__(self):
        """Initialize Dropbox client."""
        if not Config.DROPBOX_ACCESS_TOKEN:
            raise ValueError("DROPBOX_ACCESS_TOKEN not configured")

        self.dbx = dropbox.Dropbox(Config.DROPBOX_ACCESS_TOKEN)
        print(f"[OK] Connected to Dropbox")

    def list_episodes(self, folder_path=None):
        """
        List all WAV files in the Dropbox folder.

        Args:
            folder_path: Dropbox folder path (defaults to Config.DROPBOX_FOLDER_PATH)

        Returns:
            List of file metadata dictionaries
        """
        folder_path = folder_path or Config.DROPBOX_FOLDER_PATH

        try:
            result = self.dbx.files_list_folder(folder_path)
            episodes = []

            for entry in result.entries:
                if isinstance(entry, dropbox.files.FileMetadata):
                    if entry.name.lower().endswith('.wav'):
                        episodes.append({
                            'name': entry.name,
                            'path': entry.path_display,
                            'size': entry.size,
                            'modified': entry.client_modified
                        })

            episodes.sort(key=lambda x: x['modified'], reverse=True)
            return episodes

        except ApiError as e:
            print(f"[ERROR] Error listing Dropbox folder: {e}")
            return []

    def download_episode(self, dropbox_path, local_path=None):
        """
        Download an episode from Dropbox.

        Args:
            dropbox_path: Path to file in Dropbox
            local_path: Local destination path (optional, auto-generates if not provided)

        Returns:
            Path to downloaded file
        """
        if local_path is None:
            filename = Path(dropbox_path).name
            local_path = Config.DOWNLOAD_DIR / filename

        try:
            print(f"Downloading: {dropbox_path}")

            # Get file metadata for size
            metadata = self.dbx.files_get_metadata(dropbox_path)
            file_size = metadata.size

            # Download with progress bar
            with open(local_path, 'wb') as f:
                with tqdm(total=file_size, unit='B', unit_scale=True, desc='Download') as pbar:
                    metadata, response = self.dbx.files_download(dropbox_path)

                    for chunk in response.iter_content(chunk_size=4096):
                        f.write(chunk)
                        pbar.update(len(chunk))

            print(f"[OK] Downloaded to: {local_path}")
            return local_path

        except ApiError as e:
            print(f"[ERROR] Error downloading file: {e}")
            return None

    def get_latest_episode(self):
        """
        Get the most recently modified episode.

        Returns:
            File metadata dictionary or None
        """
        episodes = self.list_episodes()
        return episodes[0] if episodes else None

    def extract_episode_number(self, filename):
        """
        Extract episode number from filename.

        Supports formats like:
        - "Episode 25 - Title.wav"
        - "Ep 25 - Title.wav"
        - "25 - Title.wav"
        - "Fake Problems Podcast Episode 25.wav"

        Args:
            filename: Episode filename

        Returns:
            Episode number as integer or None if not found
        """
        # Try different patterns
        patterns = [
            r'[Ee]pisode\s*(\d+)',  # Episode 25
            r'[Ee]p[_\s]*(\d+)',     # Ep 25, ep_25, ep25
            r'^(\d+)\s*[-_]',        # 25 - Title
            r'#(\d+)',               # #25
        ]

        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                return int(match.group(1))

        return None

    def get_episode_by_number(self, episode_number):
        """
        Find episode by episode number.

        Args:
            episode_number: Episode number to find

        Returns:
            File metadata dictionary or None if not found
        """
        episodes = self.list_episodes()

        for episode in episodes:
            ep_num = self.extract_episode_number(episode['name'])
            if ep_num == episode_number:
                return episode

        return None

    def list_episodes_with_numbers(self):
        """
        List all episodes with extracted episode numbers.

        Returns:
            List of tuples (episode_number, episode_metadata)
        """
        episodes = self.list_episodes()
        episodes_with_numbers = []

        for episode in episodes:
            ep_num = self.extract_episode_number(episode['name'])
            episodes_with_numbers.append((ep_num, episode))

        # Sort by episode number (None values go to end)
        episodes_with_numbers.sort(key=lambda x: (x[0] is None, x[0] or 0))

        return episodes_with_numbers

    def upload_file(self, local_path, dropbox_path, overwrite=False):
        """
        Upload a file to Dropbox.

        Args:
            local_path: Path to local file
            dropbox_path: Destination path in Dropbox (including filename)
            overwrite: Whether to overwrite if file exists

        Returns:
            Dropbox file metadata or None on failure
        """
        local_path = Path(local_path)

        if not local_path.exists():
            print(f"[ERROR] Local file not found: {local_path}")
            return None

        try:
            print(f"Uploading: {local_path.name} -> {dropbox_path}")

            file_size = local_path.stat().st_size
            mode = dropbox.files.WriteMode.overwrite if overwrite else dropbox.files.WriteMode.add

            # Upload with progress bar
            with open(local_path, 'rb') as f:
                with tqdm(total=file_size, unit='B', unit_scale=True, desc='Upload') as pbar:
                    # For files larger than 150MB, use upload sessions
                    if file_size > 150 * 1024 * 1024:
                        # Large file upload
                        upload_session_start_result = self.dbx.files_upload_session_start(f.read(4 * 1024 * 1024))
                        pbar.update(4 * 1024 * 1024)
                        cursor = dropbox.files.UploadSessionCursor(
                            session_id=upload_session_start_result.session_id,
                            offset=f.tell()
                        )

                        commit = dropbox.files.CommitInfo(path=dropbox_path, mode=mode)

                        while f.tell() < file_size:
                            chunk_size = min(4 * 1024 * 1024, file_size - f.tell())
                            if chunk_size <= 4 * 1024 * 1024 and f.tell() + chunk_size == file_size:
                                # Last chunk
                                metadata = self.dbx.files_upload_session_finish(
                                    f.read(chunk_size),
                                    cursor,
                                    commit
                                )
                                pbar.update(chunk_size)
                            else:
                                # Continue session
                                self.dbx.files_upload_session_append_v2(
                                    f.read(chunk_size),
                                    cursor
                                )
                                pbar.update(chunk_size)
                                cursor.offset = f.tell()
                    else:
                        # Small file upload (< 150MB)
                        data = f.read()
                        metadata = self.dbx.files_upload(data, dropbox_path, mode=mode)
                        pbar.update(file_size)

            print(f"[OK] Uploaded to: {dropbox_path}")
            return metadata

        except ApiError as e:
            print(f"[ERROR] Error uploading file: {e}")
            return None

    def upload_finished_episode(self, local_audio_path, episode_name=None):
        """
        Upload finished/censored episode to the finished_files folder.

        Args:
            local_audio_path: Path to censored audio file (MP3 or WAV)
            episode_name: Optional custom name (defaults to original filename)

        Returns:
            Dropbox path or None on failure
        """
        local_path = Path(local_audio_path)
        filename = episode_name or local_path.name
        dropbox_path = f"{Config.DROPBOX_FINISHED_FOLDER}/{filename}"

        metadata = self.upload_file(local_path, dropbox_path, overwrite=True)
        return dropbox_path if metadata else None

    def upload_clips(self, clip_paths, episode_folder_name=None):
        """
        Upload clip files to Dropbox clips folder.

        Args:
            clip_paths: List of local clip file paths
            episode_folder_name: Optional folder name for organizing clips

        Returns:
            List of Dropbox paths for uploaded clips
        """
        uploaded_paths = []

        # Create clips folder structure
        if episode_folder_name:
            clips_folder = f"/podcast/clips/{episode_folder_name}"
        else:
            clips_folder = "/podcast/clips"

        for clip_path in clip_paths:
            clip_path = Path(clip_path)
            dropbox_path = f"{clips_folder}/{clip_path.name}"

            metadata = self.upload_file(clip_path, dropbox_path, overwrite=True)
            if metadata:
                uploaded_paths.append(dropbox_path)

        return uploaded_paths

    def get_shared_link(self, dropbox_path: str) -> Optional[str]:
        """
        Get or create a shared link for a Dropbox file.

        Args:
            dropbox_path: Dropbox file path

        Returns:
            Public shared link URL, or None on failure
        """
        try:
            # Try to get existing shared links
            links = self.dbx.sharing_list_shared_links(path=dropbox_path)

            if links.links:
                # Use existing link
                url = links.links[0].url
                # Convert to direct download URL (replace ?dl=0 with ?dl=1)
                if '?dl=0' in url:
                    url = url.replace('?dl=0', '?dl=1')
                elif '?dl=1' not in url:
                    url = url + '?dl=1'
                return url
            else:
                # Create new shared link
                settings = dropbox.sharing.SharedLinkSettings(requested_visibility=dropbox.sharing.RequestedVisibility.public)
                link = self.dbx.sharing_create_shared_link_with_settings(dropbox_path, settings)
                url = link.url
                # Convert to direct download URL
                if '?dl=0' in url:
                    url = url.replace('?dl=0', '?dl=1')
                elif '?dl=1' not in url:
                    url = url + '?dl=1'
                return url

        except ApiError as e:
            # Check if error is because shared link already exists
            if hasattr(e.error, 'shared_link_already_exists'):
                # Try to list links again
                try:
                    links = self.dbx.sharing_list_shared_links(path=dropbox_path)
                    if links.links:
                        url = links.links[0].url
                        if '?dl=0' in url:
                            url = url.replace('?dl=0', '?dl=1')
                        elif '?dl=1' not in url:
                            url = url + '?dl=1'
                        return url
                except:
                    pass

            print(f"[ERROR] Failed to get shared link: {e}")
            return None


if __name__ == '__main__':
    # Test the Dropbox handler
    handler = DropboxHandler()
    episodes = handler.list_episodes()

    print(f"\nFound {len(episodes)} episodes:")
    for ep in episodes[:5]:  # Show first 5
        print(f"  - {ep['name']} ({ep['size'] / 1024 / 1024:.1f} MB)")
