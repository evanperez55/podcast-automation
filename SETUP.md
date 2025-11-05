# 🚀 Setup Guide

Step-by-step guide to get your podcast automation system running.

## ✅ Step 1: Install Python

Make sure you have Python 3.9 or higher installed:

```bash
python --version
```

If not installed, download from https://www.python.org/downloads/

## ✅ Step 2: Install FFmpeg

FFmpeg is required for audio processing.

### Windows
1. Download from https://ffmpeg.org/download.html
2. Extract to `C:\ffmpeg`
3. Add `C:\ffmpeg\bin` to your PATH environment variable
4. Verify: `ffmpeg -version`

### Mac
```bash
brew install ffmpeg
```

### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

## ✅ Step 3: Install Python Dependencies

```bash
cd podcast-automation
pip install -r requirements.txt
```

## ✅ Step 4: Set Up API Keys

### OpenAI API (for Whisper transcription)

1. Go to https://platform.openai.com/api-keys
2. Sign up or log in
3. Click "Create new secret key"
4. Name it "Podcast Automation"
5. Copy the key (starts with `sk-...`)
6. Save it somewhere safe

**Cost**: ~$0.36 per 1-hour episode

### Anthropic Claude API (for content analysis)

1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Go to Settings > API Keys
4. Click "Create Key"
5. Copy the key (starts with `sk-ant-...`)

**Cost**: ~$0.01 per episode

### Dropbox API

1. Go to https://www.dropbox.com/developers/apps
2. Click "Create app"
3. Choose "Scoped access"
4. Choose "Full Dropbox" access
5. Name your app (e.g., "Podcast Automation")
6. Click "Create app"
7. In the app settings, go to "Permissions" tab
8. Enable: `files.content.read`
9. Go to "Settings" tab
10. Under "OAuth 2", click "Generate" access token
11. Copy the token

## ✅ Step 5: Configure Environment

1. Copy the example environment file:
   ```bash
   copy .env.example .env
   ```

2. Edit `.env` and add your API keys:
   ```
   OPENAI_API_KEY=sk-your-key-here
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   DROPBOX_ACCESS_TOKEN=your-dropbox-token-here
   DROPBOX_FOLDER_PATH=/Fake Problems Podcast
   ```

3. Update the Dropbox folder path to match where you store your episodes

## ✅ Step 6: Test the Setup

Run the setup test:

```bash
python -c "from config import Config; Config.validate(); print('✓ Configuration valid!')"
```

If you see `✓ Configuration valid!`, you're ready!

## ✅ Step 7: First Run

### Option A: Interactive Mode
```bash
python main.py
```

Choose option 1 to process the latest episode from Dropbox.

### Option B: Command Line
```bash
python main.py latest
```

## 📊 What Happens During Processing

1. **Downloads** episode from Dropbox (if needed)
2. **Transcribes** with Whisper (~5-10 minutes for 1-hour episode)
3. **Analyzes** content with Claude (~30 seconds)
4. **Censors** problematic content with beeps
5. **Creates** 3 clips of best moments (15-30s each)
6. **Converts** to MP3 for uploading
7. **Saves** all outputs to `output/` directory

## 📁 Check Your Results

After processing, look in:
- `output/` - Censored audio, transcripts, analysis
- `clips/` - Short clips for social media

## ⚠️ Troubleshooting

### "ModuleNotFoundError"
```bash
pip install -r requirements.txt
```

### "FFmpeg not found"
Make sure FFmpeg is installed and in your PATH. Test with:
```bash
ffmpeg -version
```

### "OPENAI_API_KEY not configured"
- Check your `.env` file exists
- Make sure there are no spaces around the `=` sign
- Verify your API key is correct

### "Dropbox access denied"
- Verify your Dropbox access token
- Check the folder path is correct (case-sensitive)
- Make sure the folder exists in your Dropbox

### "Audio file too large"
- Whisper API has a 25MB file size limit
- Consider compressing your audio before uploading
- Or split very long episodes into parts

## 🎉 Next Steps

1. Process a few test episodes
2. Review the censorship and clips
3. Adjust settings in `config.py` if needed
4. Set up social media API access (optional)
5. Automate with scheduling (cron job)

## 📞 Need Help?

Check the README.md for more detailed documentation, or review the error messages carefully - they usually tell you exactly what's wrong!
