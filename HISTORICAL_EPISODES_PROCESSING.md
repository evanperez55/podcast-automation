# Historical Episode Processing Summary

## Overview

This document tracks the processing of 24 historical podcast episodes for the Fake Problems Podcast.

## What's Being Processed

All episodes from the `historical_ep/` folder:
- Episodes #1 through #24
- Various formats: MP4, M4A, WAV
- No social media uploads (Dropbox only)

## Processing Steps for Each Episode

1. **Transcription** - Whisper AI transcribes the full episode
2. **Content Analysis** - Claude AI analyzes content and identifies:
   - Items to censor (names, sensitive content)
   - Best clip moments (3 clips per episode)
   - Episode summary
3. **Censorship** - Apply beep sounds over flagged content
4. **Clip Creation** - Extract 3 best clips (30 seconds each)
5. **MP3 Conversion** - Convert censored audio to MP3
6. **Dropbox Upload**:
   - Transcriptions → `/podcast/transcriptions/ep_XX/`
   - Clips → `/podcast/clips/ep_XX/`
   - Full episode → `/podcast/finished_files/`

## Dropbox Folder Structure

After processing, your Dropbox will have:

```
/podcast/
├── transcriptions/
│   ├── ep_1/
│   │   └── Episode #1 - CTE Can't Hurt Me_transcript.json
│   ├── ep_2/
│   │   └── Episode #2 - Top Gun Ego Death_transcript.json
│   └── ... (ep_3 through ep_24)
│
├── clips/
│   ├── ep_1/
│   │   ├── clip_1_520.0_to_550.0.wav
│   │   ├── clip_2_2400.0_to_2430.0.wav
│   │   └── clip_3_4420.0_to_4450.0.wav
│   ├── ep_2/
│   └── ... (ep_3 through ep_24)
│
└── finished_files/
    ├── Episode_1_Episode #1 - CTE Can't Hurt Me_censored.mp3
    ├── Episode_2_Episode #2 - Top Gun Ego Death_censored.mp3
    └── ... (episodes 3 through 24)
```

## Local Output Files

All processing artifacts are saved to `output/` directory:

- `Episode #X - Title_transcript.json` - Full transcription with timestamps
- `Episode #X - Title_analysis.json` - Claude's content analysis
- `Episode #X - Title_censored.wav` - Censored audio (WAV)
- `Episode #X - Title_censored.mp3` - Censored audio (MP3)
- `Episode #X - Title_results.json` - Processing summary

Clips are saved to `clips/ep_X/` directory.

## Running the Script

### Process All Historical Episodes
```bash
python process_historical_episodes.py all
```

### Process Single Episode
```bash
python process_historical_episodes.py "historical_ep/Episode #1 - CTE Can't Hurt Me.mp4"
```

### Interactive Mode
```bash
python process_historical_episodes.py
```

## Estimated Processing Time

- **Per episode**: ~10-15 minutes (depending on episode length)
- **All 24 episodes**: ~4-6 hours total

Breakdown per episode:
- Transcription: 5-8 minutes (longest step)
- Analysis: 1-2 minutes
- Censorship: 30 seconds
- Clip creation: 30 seconds
- Upload: 1-2 minutes

## Error Handling

The script will:
- Show detailed progress for each step
- Ask if you want to continue after errors
- Save all successful processing even if later episodes fail
- Skip social media uploads (as requested)

## What's NOT Being Done

❌ YouTube uploads (Shorts)
❌ Twitter/X posts
❌ Instagram Reels
❌ TikTok videos
❌ Spotify RSS updates

Only Dropbox uploads are performed.

## After Processing

Once all 24 episodes are processed, you'll have:

- ✅ 24 transcriptions in Dropbox
- ✅ ~72 clips (3 per episode) in Dropbox
- ✅ 24 censored MP3 files in Dropbox
- ✅ All local files in `output/` and `clips/` folders

You can then:
1. Use clips for social media manually
2. Share full episodes
3. Review transcriptions
4. Use analysis data for show notes

## Monitoring Progress

The script shows real-time progress:
- Which file is being processed (X/24)
- Current step (transcription, analysis, etc.)
- Upload status and paths

Check the terminal output to see current status.

## Next Steps After Completion

1. Review any errors or warnings
2. Verify uploads in Dropbox
3. Optionally post clips to social media manually
4. Set up automatic token refresh (see DROPBOX_TOKEN_SETUP.md)

---

**Status**: Processing started at background process ID: 953d5f
**Command**: `python process_historical_episodes.py all`
