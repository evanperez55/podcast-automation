# ⚡ Quick Start Guide - Podcast Automation

Follow these steps to get your podcast automation system running.

## 🔧 Prerequisites Installation

### 1. Install Python (Required)

**Download and Install:**
1. Go to https://www.python.org/downloads/
2. Download Python 3.11 or higher (latest stable version)
3. Run the installer
4. ⚠️ **IMPORTANT**: Check "Add Python to PATH" during installation
5. Click "Install Now"
6. Verify installation:
   ```bash
   python --version
   ```
   Should show: `Python 3.11.x` or higher

**Alternative (Using winget on Windows 11):**
```bash
winget install Python.Python.3.11
```

### 2. Install FFmpeg (Required for Audio Processing)

**Option A: Using Chocolatey (Recommended)**
```bash
# Install Chocolatey first (if not installed)
# Run in PowerShell as Administrator
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Then install FFmpeg
choco install ffmpeg
```

**Option B: Manual Installation**
1. Download FFmpeg from https://www.gyan.dev/ffmpeg/builds/
2. Choose "ffmpeg-release-essentials.zip"
3. Extract to `C:\ffmpeg`
4. Add `C:\ffmpeg\bin` to your PATH:
   - Open "Environment Variables" in Windows
   - Edit "Path" under "User variables"
   - Click "New" and add `C:\ffmpeg\bin`
   - Click OK to save
5. Restart your terminal
6. Verify:
   ```bash
   ffmpeg -version
   ```

### 3. Get API Keys

#### OpenAI API Key (for Whisper Transcription)
1. Go to https://platform.openai.com/api-keys
2. Sign up or log in
3. Click "Create new secret key"
4. Name it "Podcast Automation"
5. Copy the key (starts with `sk-...`)
6. **Cost**: ~$0.36 per 1-hour episode

#### Anthropic Claude API Key (for Content Analysis)
1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Go to Settings → API Keys
4. Click "Create Key"
5. Copy the key (starts with `sk-ant-...`)
6. **Cost**: ~$0.01 per episode analysis

#### Dropbox Access Token
1. Go to https://www.dropbox.com/developers/apps
2. Click "Create app"
3. Choose "Scoped access" → "Full Dropbox"
4. Name it "Podcast Automation"
5. In app settings:
   - Go to "Permissions" tab
   - Enable: `files.content.read`
   - Click "Submit"
6. Go to "Settings" tab
7. Under "OAuth 2", click "Generate" access token
8. Copy the token

## 📦 Installation Steps

### 1. Open Terminal in Project Directory
```bash
cd C:\Users\evanp\projects\podcast-automation
```

### 2. Install Python Packages
```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Create Environment File
```bash
copy .env.example .env
```

### 4. Edit `.env` File

Open `.env` in a text editor and add your API keys:

```
# Required
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here

# Optional (for Dropbox integration)
DROPBOX_ACCESS_TOKEN=your-dropbox-token-here
DROPBOX_FOLDER_PATH=/Fake Problems Podcast

# Podcast Settings
PODCAST_NAME=Fake Problems Podcast
```

## ✅ Verify Setup

Run the setup test:
```bash
python test_setup.py
```

You should see all checks pass with ✅ marks.

## 🚀 Run Your First Episode

### Option 1: Interactive Mode (Recommended for First Time)
```bash
python main.py
```

Then choose:
- Option 1: Process latest episode from Dropbox
- Option 2: List episodes
- Option 4: Process a local audio file

### Option 2: Command Line Mode
```bash
# Process latest episode from Dropbox
python main.py latest

# Process a specific local file
python main.py "C:\path\to\your\episode.wav"
```

## 📁 What Gets Created

After processing, check these folders:
- `output/` - Censored audio, transcripts, analysis
- `clips/` - Short clips (15-30s) for social media
- `downloads/` - Episodes downloaded from Dropbox

## 🎯 First Run Checklist

- [ ] Python 3.11+ installed
- [ ] FFmpeg installed
- [ ] OpenAI API key added to `.env`
- [ ] Anthropic API key added to `.env`
- [ ] Dropbox token added to `.env` (optional)
- [ ] Run `python test_setup.py` successfully
- [ ] Have a WAV file ready to process

## 💡 Quick Tips

**No Dropbox?** No problem! Just run:
```bash
python main.py "C:\path\to\episode.wav"
```

**Test with a small file first** to make sure everything works before processing a full 1-hour episode.

**Cost per episode**: ~$0.37 (mostly Whisper transcription)

## ❓ Troubleshooting

**"Python not found"**
- Make sure you checked "Add Python to PATH" during installation
- Restart your terminal after installing Python

**"FFmpeg not found"**
- Verify FFmpeg is in your PATH: `ffmpeg -version`
- Restart terminal after adding to PATH

**"Missing API key"**
- Check your `.env` file has the correct keys
- No spaces around the `=` sign
- Keys should not be in quotes

**Need help?** Check:
- `README.md` for full documentation
- `SETUP.md` for detailed setup guide
- Error messages (they're usually very specific)

## 🎉 You're Ready!

Once setup passes, you're ready to automate your podcast workflow:
1. Record episode → Upload to Dropbox
2. Run `python main.py latest`
3. Get censored audio, clips, and social captions
4. Upload to platforms

**Next**: Set up social media APIs for automatic uploading (optional)
