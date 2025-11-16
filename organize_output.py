"""Organize output files into episode subfolders."""

import os
import shutil
from pathlib import Path
import re


def organize_output_folder():
    """Organize output files by episode number into subfolders."""

    output_dir = Path("output")

    if not output_dir.exists():
        print("[ERROR] Output directory not found")
        return

    # Get all files in output directory
    files = [f for f in output_dir.iterdir() if f.is_file()]

    # Group files by episode
    episode_files = {}
    other_files = []

    for file in files:
        # Skip RSS/metadata files
        if file.name in ['podcast_feed.xml', 'test_podcast_feed.xml', 'podcast_metadata.json']:
            other_files.append(file)
            continue

        # Extract episode number from filename
        # Pattern: "Episode #X - Title" or "ep_X_raw_..."
        match = re.search(r'Episode #(\d+)', file.name)
        if match:
            episode_num = int(match.group(1))
            episode_key = f"ep_{episode_num}"
        else:
            # Check for ep_25_raw pattern
            match = re.search(r'ep_(\d+)_raw', file.name)
            if match:
                episode_num = int(match.group(1))
                episode_key = f"ep_{episode_num}"
            else:
                other_files.append(file)
                continue

        if episode_key not in episode_files:
            episode_files[episode_key] = []
        episode_files[episode_key].append(file)

    # Create subfolders and move files
    print(f"\n[INFO] Found {len(episode_files)} episodes to organize")
    print(f"[INFO] Found {len(other_files)} other files (will keep in root)")
    print()

    for episode_key, files in sorted(episode_files.items()):
        # Create episode subfolder
        episode_folder = output_dir / episode_key
        episode_folder.mkdir(exist_ok=True)

        print(f"[INFO] Organizing {episode_key}...")

        # Move files into subfolder
        for file in files:
            dest = episode_folder / file.name
            if dest.exists():
                print(f"  [SKIP] {file.name} already exists in {episode_key}")
            else:
                shutil.move(str(file), str(dest))
                print(f"  [MOVED] {file.name} -> {episode_key}/")

    print()
    print("[SUCCESS] Output folder organized!")
    print()
    print("Files kept in root:")
    for file in other_files:
        print(f"  - {file.name}")


if __name__ == '__main__':
    organize_output_folder()
