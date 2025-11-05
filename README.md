# 🎙️ Podcast Automation System

Automated production pipeline for podcast processing, including transcription, content analysis, censorship, clip creation, and distribution.

## 🌟 Features

- **Automated Transcription** - Local Whisper model with GPU acceleration
- **AI Content Analysis** - Claude AI identifies content to censor and best moments
- **Smart Censorship** - Automatic beep censorship at precise timestamps
- **Clip Generation** - Creates 30-second clips of best moments for social media
- **Dropbox Integration** - Download raw files, upload finished episodes and clips
- **Social Media Ready** - Generates captions for YouTube, Instagram, Twitter

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- NVIDIA GPU with CUDA (optional but recommended for faster transcription)
- FFmpeg installed
- Dropbox account
- Anthropic API key (Claude AI)

### Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables: `cp .env.example .env`
4. Edit .env with your API keys

### Usage

**Process latest episode:** `python main.py latest`
**Process specific episode:** `python main.py ep25`
**List available episodes:** `python main.py list`

## 📊 Performance

**With GPU (RTX 3070):** 60-minute episode in ~7 minutes
**Without GPU:** 60-minute episode in ~20-25 minutes

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for complete documentation.
