# 🎬 FFmpeg Manual Installation Guide (Windows)

## Quick Steps (5 minutes)

### 1. Download FFmpeg

Go to: https://www.gyan.dev/ffmpeg/builds/

Click on: **"ffmpeg-release-essentials.zip"** (~80 MB)

### 2. Extract the Files

1. Once downloaded, right-click the ZIP file → "Extract All"
2. Choose to extract to `C:\` (you'll get `C:\ffmpeg-...`)
3. Rename the folder to just `C:\ffmpeg` for simplicity

You should now have:
```
C:\ffmpeg\
  ├── bin\
  │   ├── ffmpeg.exe  ← This is what we need
  │   ├── ffplay.exe
  │   └── ffprobe.exe
  ├── doc\
  └── presets\
```

### 3. Add FFmpeg to PATH

**Method A: Using Windows Settings (Recommended)**

1. Press `Windows Key + X`
2. Click "System"
3. Scroll down and click "Advanced system settings"
4. Click "Environment Variables..." button
5. Under "User variables for [your name]", find and click on "Path"
6. Click "Edit..."
7. Click "New"
8. Type: `C:\ffmpeg\bin`
9. Click OK on all windows

**Method B: Using PowerShell (Quick)**

Open PowerShell and run:
```powershell
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\ffmpeg\bin", "User")
```

### 4. Verify Installation

1. **Close any open terminals/PowerShell windows**
2. Open a **NEW** PowerShell or Command Prompt
3. Run:
   ```bash
   ffmpeg -version
   ```

You should see something like:
```
ffmpeg version 2024.11.10-full_build-www.gyan.dev
...
```

### 5. Done! ✅

FFmpeg is now installed and ready to use.

---

## Troubleshooting

### "ffmpeg is not recognized..."

**Problem:** Path not updated or terminal not restarted

**Solution:**
1. Make sure you added `C:\ffmpeg\bin` (with `\bin` at the end!)
2. Close ALL terminal windows
3. Open a NEW terminal
4. Try `ffmpeg -version` again

### "Cannot find C:\ffmpeg\bin"

**Problem:** FFmpeg not in the right location

**Solution:**
1. Check where you extracted FFmpeg
2. Look for the `ffmpeg.exe` file
3. Add the folder containing `ffmpeg.exe` to your PATH

### Still not working?

Quick test - navigate directly:
```bash
cd C:\ffmpeg\bin
ffmpeg.exe -version
```

If this works, then it's just a PATH issue. Make sure you:
1. Added the correct path to Environment Variables
2. Restarted your terminal

---

## Alternative: Winget (Windows 11 Only)

If you're on Windows 11, you can use:
```bash
winget install Gyan.FFmpeg
```

This will automatically add it to PATH.

---

## Need Help?

If you're stuck, you can:
1. Skip FFmpeg for now
2. Set up Python and API keys first
3. Come back to FFmpeg when ready to process audio

The automation system will work fine without FFmpeg until you actually need to process audio files.
