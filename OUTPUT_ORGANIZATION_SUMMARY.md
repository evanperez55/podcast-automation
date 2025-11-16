# Output Folder Organization - Update Summary

## What Changed

Both automation scripts now automatically organize output files into episode-specific subfolders instead of dumping everything into a flat directory.

## New Folder Structure

### Output Directory (`output/`)
```
output/
├── ep_1/
│   ├── Episode #1 - Title_transcript.json
│   ├── Episode #1 - Title_analysis.json
│   ├── Episode #1 - Title_censored.wav
│   ├── Episode #1 - Title_censored.mp3
│   └── Episode #1 - Title_results.json
├── ep_2/
│   └── [same structure]
...
├── ep_25/
│   └── [same structure]
├── podcast_feed.xml
├── podcast_metadata.json
└── test_podcast_feed.xml
```

### Clips Directory (`clips/`)
```
clips/
├── ep_1/
│   ├── clip_1_start_to_end.wav
│   ├── clip_2_start_to_end.wav
│   └── clip_3_start_to_end.wav
├── ep_2/
│   └── [3 clips]
...
└── ep_25/
    └── [3 clips]
```

## Scripts Updated

### 1. `process_historical_episodes.py`
**Changes:**
- Creates `output/ep_X/` subfolder for each episode
- Saves all files (transcript, analysis, censored audio, results) into episode subfolder
- Clips already saved to `clips/ep_X/` (no change needed)

**Before:**
```python
transcript_path = Config.OUTPUT_DIR / f"{audio_file.stem}_transcript.json"
analysis_path = Config.OUTPUT_DIR / f"{audio_file.stem}_analysis.json"
```

**After:**
```python
episode_output_dir = Config.OUTPUT_DIR / episode_folder
episode_output_dir.mkdir(exist_ok=True, parents=True)

transcript_path = episode_output_dir / f"{audio_file.stem}_transcript.json"
analysis_path = episode_output_dir / f"{audio_file.stem}_analysis.json"
```

### 2. `main.py`
**Changes:**
- Creates `output/ep_X/` subfolder for each episode
- Uses episode number from filename to create organized folder structure
- Falls back to timestamped folder if episode number can't be detected
- Clips saved to `clips/ep_X/` instead of `clips/filename_timestamp/`
- Removed duplicate `episode_number` extractions for cleaner code

**Before:**
```python
transcript_path = Config.OUTPUT_DIR / f"{audio_file.stem}_{timestamp}_transcript.json"
clip_dir = Config.CLIPS_DIR / f"{audio_file.stem}_{timestamp}"
```

**After:**
```python
episode_number = self.dropbox.extract_episode_number(audio_file.name)
if episode_number:
    episode_folder = f"ep_{episode_number}"
else:
    episode_folder = f"ep_{audio_file.stem}_{timestamp}"

episode_output_dir = Config.OUTPUT_DIR / episode_folder
episode_output_dir.mkdir(exist_ok=True, parents=True)

transcript_path = episode_output_dir / f"{audio_file.stem}_{timestamp}_transcript.json"
clip_dir = Config.CLIPS_DIR / episode_folder
```

## Benefits

1. **Better Organization**: Each episode's files are grouped together
2. **Easier Navigation**: Find all files for Episode 5 in `output/ep_5/`
3. **Cleaner Root**: RSS/metadata files remain in root for easy access
4. **Consistent Structure**: Both scripts use the same organization pattern
5. **Scalable**: Works for any number of episodes

## Existing Files

Your existing files have already been organized using the `organize_output.py` script. Future runs of both automation scripts will automatically maintain this structure.

## Migration Script

The `organize_output.py` script has been created to reorganize existing output files. It can be run anytime to clean up the output directory:

```bash
python organize_output.py
```

This script:
- Groups files by episode number
- Creates `ep_X` subfolders
- Moves related files into episode folders
- Keeps RSS/metadata files in root
- Is safe to run multiple times (skips already-organized files)
