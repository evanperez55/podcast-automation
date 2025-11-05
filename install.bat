@echo off
REM Podcast Automation - Windows Installation Script

echo ============================================================
echo PODCAST AUTOMATION - INSTALLATION
echo ============================================================
echo.

REM Check if Python is installed
echo [1/4] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo.
    echo Please install Python from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation!
    echo.
    pause
    exit /b 1
)
python --version
echo [OK] Python is installed
echo.

REM Upgrade pip
echo [2/4] Upgrading pip...
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo [WARNING] Could not upgrade pip, continuing anyway...
)
echo.

REM Install dependencies
echo [3/4] Installing Python packages...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] Python packages installed
echo.

REM Check FFmpeg
echo [4/4] Checking FFmpeg installation...
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] FFmpeg is not installed or not in PATH
    echo.
    echo To install FFmpeg:
    echo   Option 1: Use Chocolatey: choco install ffmpeg
    echo   Option 2: Download from: https://www.gyan.dev/ffmpeg/builds/
    echo   Option 3: Skip for now (you'll need it before processing audio)
    echo.
) else (
    echo [OK] FFmpeg is installed
)
echo.

REM Check for .env file
if not exist .env (
    echo Creating .env file from template...
    copy .env.example .env >nul
    echo [OK] .env file created
    echo.
    echo IMPORTANT: Edit .env and add your API keys!
    echo   - OPENAI_API_KEY
    echo   - ANTHROPIC_API_KEY
    echo   - DROPBOX_ACCESS_TOKEN (optional)
    echo.
) else (
    echo [OK] .env file already exists
)

echo ============================================================
echo INSTALLATION COMPLETE
echo ============================================================
echo.
echo Next steps:
echo   1. Edit .env and add your API keys
echo   2. Run: python test_setup.py
echo   3. Run: python main.py
echo.
echo For detailed setup instructions, see:
echo   - QUICK_START.md
echo   - SETUP.md
echo   - README.md
echo.
pause
