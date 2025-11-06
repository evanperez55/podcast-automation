# Fake Problems Podcast Automation - Project Status

**Last Updated:** November 5, 2025
**Current Status:** ✅ FULLY AUTOMATED - Complete pipeline with social media distribution

---

## 🎯 Project Overview

Automated podcast production pipeline for "Fake Problems Podcast" that handles:
- Downloading episodes from Dropbox
- Transcription with local Whisper (GPU-accelerated)
- Content analysis and censorship with Claude AI
- Creating social media clips
- Uploading finished files back to Dropbox

---

## ✅ Completed Features

### 1. Dropbox Integration (✓ COMPLETE)
- **Download** episodes from `/podcast/new_raw_files/`
- **Upload** censored episodes to `/podcast/finished_files/`
- **Upload** clips to `/podcast/clips/{episode_number}/`
- Episode number extraction from filenames
- Progress bars for large file transfers
- Supports files > 150MB with chunked uploads

**Files:** `dropbox_handler.py`, `.env`

### 2. Audio Transcription (✓ COMPLETE)
- **Local Whisper model** (no API limits!)
- GPU acceleration with CUDA (RTX 3070)
- Word-level timestamps for precise censorship
- Base model loaded (~1GB RAM)
- ~3-4 minutes for 60-minute episode

**Files:** `transcription.py`

**Performance:**
- CPU: 15-20 minutes per hour of audio
- GPU (RTX 3070): 3-4 minutes per hour of audio

### 3. Content Analysis (✓ COMPLETE)
- **Claude AI (Anthropic)** analyzes transcripts
- Identifies content to censor:
  - Names: Joey, Evan, Dom
  - Slurs: homophobic, ableist terms
  - Other inappropriate content
- Finds best moments for clips (30 seconds each)
- Generates episode summary
- Creates social media captions (YouTube, Instagram, Twitter)

**Files:** `content_editor.py`

### 4. Audio Processing (✓ COMPLETE)
- Applies beep censorship at precise timestamps
- Creates 30-second clips of best moments
- Converts WAV to MP3 for distribution
- FFmpeg integration

**Files:** `audio_processor.py`, `config.py`

### 5. Main Orchestrator (✓ COMPLETE)
- Command-line interface
- Episode selection by number: `python main.py ep25`
- List episodes: `python main.py list`
- Process latest: `python main.py latest`
- Interactive mode: `python main.py`
- Full end-to-end automation

**Files:** `main.py`

---

## 📊 Test Results (Episode 25)

**Processed:** November 4, 2025

### Input:
- File: `ep_25_raw.WAV` (647 MB)
- Duration: 61 minutes (3,666 seconds)

### Output:
- **Transcript:** 10,694 words, 1,420 segments
- **Censored:** 4 items (1 slur, 2 names, 1 ableist term)
- **Clips:** 3 clips (30 seconds each)
  1. "The Godfather Dilemma" (11:12-11:42)
  2. "9 Pounds of Cheese" (47:06-47:36)
  3. "I'm Humbled Makes No Sense" (58:57-59:27)

### Processing Time:
- Download: ~15 seconds
- Transcription (GPU): ~3-4 minutes
- Claude Analysis: ~30 seconds
- Audio Censorship: ~30 seconds
- Clip Creation: ~10 seconds
- MP3 Conversion: ~20 seconds
- Upload to Dropbox: ~1 minute 20 seconds
- **Total: ~7 minutes**

### Files Created:
```
output/
  ep_25_raw_20251104_225120_transcript.json
  ep_25_raw_20251104_225120_analysis.json
  ep_25_raw_20251104_225120_censored.wav
  ep_25_raw_20251104_225120_censored.mp3
  ep_25_raw_20251104_225120_results.json

clips/ep_25_raw_20251104_225120/
  ep_25_raw_20251104_225120_censored_clip_01.wav
  ep_25_raw_20251104_225120_censored_clip_02.wav
  ep_25_raw_20251104_225120_censored_clip_03.wav
```

### Uploaded to Dropbox:
```
/podcast/finished_files/ep_25_censored.mp3 (88 MB)
/podcast/clips/ep_25/
  ep_25_raw_20251104_225120_censored_clip_01.wav (5.29 MB)
  ep_25_raw_20251104_225120_censored_clip_02.wav (5.29 MB)
  ep_25_raw_20251104_225120_censored_clip_03.wav (5.29 MB)
```

---

## 🔧 Technical Setup

### Environment:
- **Python:** 3.12
- **GPU:** NVIDIA RTX 3070
- **CUDA:** Enabled and working
- **FFmpeg:** C:\ffmpeg\bin\ffmpeg.exe

### Key Dependencies:
```
openai-whisper==20231117
torch==2.1.0 (CUDA-enabled)
torchaudio==2.1.0 (CUDA-enabled)
anthropic==0.72.0
dropbox==12.0.2
pydub==0.25.1
ffmpeg-python==0.2.0
```

### Configuration (.env):
```bash
# Working API Keys
ANTHROPIC_API_KEY=sk-ant-api03-128PZTY... (configured)
DROPBOX_ACCESS_TOKEN=sl.u.AGFXWUo-ys42... (configured with write permissions)

# Dropbox Paths
DROPBOX_FOLDER_PATH=/podcast/new_raw_files
DROPBOX_FINISHED_FOLDER=/podcast/finished_files

# Podcast Settings
PODCAST_NAME=Fake Problems Podcast
BEEP_SOUND_PATH=./assets/beep.wav

# Social Media (NOT YET CONFIGURED)
YOUTUBE_CLIENT_ID=your_youtube_client_id_here
YOUTUBE_CLIENT_SECRET=your_youtube_client_secret_here
SPOTIFY_CLIENT_ID=your_spotify_client_id_here
TWITTER_API_KEY=your_twitter_api_key_here
INSTAGRAM_ACCESS_TOKEN=your_instagram_access_token_here
TIKTOK_CLIENT_KEY=your_tiktok_client_key_here
```

### 6. Video Conversion (✓ COMPLETE)
- Converts audio clips to vertical videos (1080x1920)
- Adds static podcast logo as background
- Perfect for YouTube Shorts, Instagram Reels, TikTok
- FFmpeg-based conversion with high-quality output

**Files:** `video_converter.py`

### 7. Social Media Integration (✓ COMPLETE)

#### Twitter/X (✓ CONFIGURED)
- Automatic episode announcements
- Thread creation with episode info
- Can attach video clips
- **Status:** Active and posting

**Files:** `uploaders/twitter_uploader.py`

#### YouTube (✓ CONFIGURED)
- Full episode upload capability
- YouTube Shorts support
- Custom thumbnails and metadata
- OAuth2 authentication configured
- **Status:** Ready (upload code commented out for safety)

**Files:** `uploaders/youtube_uploader.py`

#### Spotify (✅ FULLY AUTOMATED VIA RSS)
- **Automatic distribution via RSS feed**
- No manual uploads required
- Episodes appear on Spotify in 2-8 hours automatically
- Also works with Apple Podcasts, Google Podcasts, and ALL podcast apps
- **Cost:** $0 (uses existing Dropbox storage)
- **Status:** Fully implemented and tested

**Files:** `uploaders/spotify_uploader.py`, `rss_feed_generator.py`
**Setup:** See `QUICKSTART_RSS.md` or `RSS_FEED_SETUP.md`

#### Instagram (⏳ WAITING)
- Instagram Reels integration ready
- Waiting for Facebook account approval
- **Status:** Code ready, account pending

**Files:** `uploaders/instagram_uploader.py`

#### TikTok (❌ NOT CONFIGURED)
- TikTok Content Posting API integration ready
- Requires business verification (weeks-long process)
- **Status:** Code ready, API not configured

**Files:** `uploaders/tiktok_uploader.py`

---

## 🎉 What's Automated Now

When you run `python main.py ep26`:

1. ✅ Downloads/loads episode from Dropbox
2. ✅ Transcribes with Whisper (GPU-accelerated, ~3-4 minutes)
3. ✅ Analyzes content with Claude AI
4. ✅ Applies censorship (beeps out names/slurs)
5. ✅ Creates 3x 30-second highlight clips
6. ✅ Converts clips to vertical videos (Shorts/Reels/TikTok format)
7. ✅ Converts episode to MP3
8. ✅ Uploads MP3 + clips to Dropbox
9. ✅ Creates Dropbox shared link for MP3
10. ✅ **Updates RSS feed with new episode**
11. ✅ **Spotify automatically pulls new episode (2-8 hours)**
12. ✅ Posts episode announcement to Twitter
13. ✅ Prepares YouTube videos (ready to upload)
14. ✅ Creates vertical videos for TikTok/Reels

**Your work:** Run one command
**Automation does:** Everything else

---

## 📋 Next Steps: Social Media Automation

### Priority 1: RSS Feed Setup (15 minutes)
- [ ] Set up YouTube Data API v3 credentials
- [ ] Create `youtube_uploader.py` module
- [ ] Upload full episode with metadata
- [ ] Upload clips as Shorts
- [ ] Generate thumbnails
- [ ] Add timestamps to description

**API Setup:**
1. Go to https://console.cloud.google.com
2. Create project "Fake Problems Automation"
3. Enable YouTube Data API v3
4. Create OAuth 2.0 credentials
5. Add to `.env` file

**Resources:**
- YouTube API Docs: https://developers.google.com/youtube/v3
- Python Client: `google-api-python-client`

### Priority 2: Instagram Upload
- [ ] Set up Instagram Graph API credentials
- [ ] Create `instagram_uploader.py` module
- [ ] Upload clips as Reels
- [ ] Add captions and hashtags
- [ ] Schedule posts

**API Setup:**
1. Create Facebook App at https://developers.facebook.com
2. Add Instagram Basic Display
3. Get Instagram Business Account access token
4. Add to `.env` file

**Resources:**
- Instagram API: https://developers.facebook.com/docs/instagram-api
- Reels API: https://developers.facebook.com/docs/instagram-api/guides/reels

### Priority 3: TikTok Upload
- [ ] Set up TikTok Developer account
- [ ] Create `tiktok_uploader.py` module
- [ ] Upload clips
- [ ] Add captions and hashtags
- [ ] Handle video requirements (vertical format)

**Note:** May need to convert clips to vertical format (9:16 ratio)

### Priority 4: Twitter/X Upload
- [ ] Set up Twitter API v2 credentials
- [ ] Create `twitter_uploader.py` module
- [ ] Post episode announcement
- [ ] Post clips with captions
- [ ] Thread for multiple clips

**API Setup:**
- Twitter API: https://developer.twitter.com
- Elevated access needed for media uploads

### Priority 5: Spotify for Podcasters
- [ ] Research Spotify Podcasters API
- [ ] Investigate RSS feed vs API upload
- [ ] Create `spotify_uploader.py` module
- [ ] Upload episode with metadata

**Note:** May use Anchor/Spotify for Podcasters RSS feed instead

---

## 📁 Project Structure

```
podcast-automation/
├── main.py                    # Main orchestrator
├── config.py                  # Configuration and paths
├── dropbox_handler.py         # Dropbox download/upload
├── transcription.py           # Whisper transcription
├── content_editor.py          # Claude AI analysis
├── audio_processor.py         # Audio censorship & clips
├── requirements.txt           # Python dependencies
├── .env                       # API keys and config
├── test_upload.py            # Test script for uploads
├── PROJECT_STATUS.md         # This file
│
├── assets/
│   └── beep.wav              # Censorship beep sound
│
├── downloads/                # Downloaded episodes
│   └── ep_25_raw.WAV
│
├── output/                   # Processed files
│   ├── *_transcript.json
│   ├── *_analysis.json
│   ├── *_censored.wav
│   ├── *_censored.mp3
│   └── *_results.json
│
└── clips/                    # Generated clips
    └── ep_25_raw_20251104_225120/
        ├── *_clip_01.wav
        ├── *_clip_02.wav
        └── *_clip_03.wav
```

---

## 🚀 Usage

### Process Latest Episode:
```bash
python main.py latest
```

### Process Specific Episode:
```bash
python main.py ep25
python main.py episode 26
```

### List Available Episodes:
```bash
python main.py list
```

### Interactive Mode:
```bash
python main.py
```

---

## 🐛 Known Issues

1. **Unicode Encoding (Minor):** Windows terminal can't display some Unicode characters in social media captions. Files are created correctly, just can't print to console.

2. **CUDA Toolkit Warning (Minor):** Full CUDA toolkit not installed, falls back to alternative implementation. GPU still works, just slightly slower than optimal.

---

## 💡 Future Enhancements

### Content Improvements:
- [ ] AI-generated thumbnails for YouTube/social media
- [ ] Automatic chapter markers based on transcript
- [ ] Sentiment analysis for clip selection
- [ ] Automatic hashtag generation
- [ ] Speaker diarization (identify who's speaking)

### Automation:
- [ ] Automatic scheduling (process new episodes daily)
- [ ] Email notifications when processing complete
- [ ] Webhook integration for episode drops
- [ ] Dashboard for monitoring status

### Quality:
- [ ] Audio normalization (leveling)
- [ ] Noise reduction
- [ ] Intro/outro music insertion
- [ ] Multiple quality exports (HD, SD, audio-only)

### Distribution:
- [ ] Apple Podcasts upload
- [ ] Google Podcasts
- [ ] RSS feed generation
- [ ] Cross-posting to Reddit/Discord

---

## 📞 API Credentials Needed

### Currently Have:
- ✅ Anthropic API (Claude AI)
- ✅ Dropbox API (with write permissions)

### Need to Set Up:
- ⏳ YouTube Data API v3
- ⏳ Instagram Graph API
- ⏳ Twitter API v2
- ⏳ TikTok Developer API
- ⏳ Spotify for Podcasters

---

## 📝 Notes

### Whisper Model Options:
- `tiny`: Fastest, least accurate (~1GB RAM)
- `base`: **Currently using** - Good balance (~1GB RAM)
- `small`: Better accuracy (~2GB RAM)
- `medium`: Very good accuracy (~5GB RAM)
- `large`: Best accuracy, slowest (~10GB RAM)

Can upgrade model in `main.py` line 31:
```python
self.transcriber = Transcriber(model_size="small")  # or "medium", "large"
```

### Censorship Configuration:
Edit `content_editor.py` line 63 to customize what gets censored:
```python
NAMES_TO_CENSOR = ["joey", "evan", "dom", "other_name"]
```

### Clip Duration:
Edit `content_editor.py` line 124 to change clip length:
```python
"duration_seconds": 30,  # Change to 60 for 1-minute clips
```

---

## 🎓 Learning Resources

### APIs Used:
- **Whisper:** https://github.com/openai/whisper
- **Claude AI:** https://docs.anthropic.com/
- **Dropbox:** https://www.dropbox.com/developers/documentation
- **FFmpeg:** https://ffmpeg.org/documentation.html

### Python Libraries:
- **pydub:** https://github.com/jiaaro/pydub
- **torch:** https://pytorch.org/docs/
- **anthropic:** https://github.com/anthropics/anthropic-sdk-python

---

**Ready to continue with social media automation tomorrow!** 🚀
