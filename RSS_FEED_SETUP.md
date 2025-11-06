# RSS Feed Setup Guide
## Automatic Spotify Distribution via RSS Feed

This guide will help you set up automatic podcast distribution to Spotify using an RSS feed. Once configured, Spotify will automatically pull new episodes from your RSS feed every few hours - **no manual uploads required!**

---

## Why Use RSS Feed?

**Benefits:**
- ✅ **Completely Automatic**: New episodes appear on Spotify without manual upload
- ✅ **Zero Cost**: Uses your existing Dropbox storage
- ✅ **Industry Standard**: Works with Spotify, Apple Podcasts, Google Podcasts, and all podcast apps
- ✅ **One-Time Setup**: Configure once, works forever
- ✅ **Already Integrated**: Your automation updates the RSS feed automatically

**How It Works:**
1. You run `python main.py ep26`
2. Automation uploads MP3 to Dropbox
3. Automation updates RSS feed with episode info + Dropbox link
4. Automation uploads RSS feed to Dropbox
5. Spotify checks your RSS feed every few hours
6. Spotify automatically adds new episode to your show
7. **Done!** Episode appears on Spotify without any manual work

---

## Prerequisites

Before starting, make sure you have:
- ✅ Podcast automation already working (`python main.py` runs successfully)
- ✅ Dropbox connected and uploading files
- ✅ Spotify uploader configured (`test_spotify.py` passes)
- ✅ Your podcast logo image (1400x1400 to 3000x3000 pixels, JPG/PNG)

---

## Step 1: Set Up Podcast Metadata (One-Time)

Your RSS feed needs basic information about your podcast. Run this setup script once:

### Create Setup Script

Create a file called `setup_rss_metadata.py`:

```python
"""One-time setup script for RSS feed metadata."""

from uploaders.spotify_uploader import SpotifyUploader

# Initialize Spotify uploader
uploader = SpotifyUploader()

# Configure your podcast metadata
uploader.setup_podcast_metadata(
    title="Fake Problems Podcast",  # Your podcast name
    description="A podcast about fake problems and real laughs",  # Your podcast description
    author="Fake Problems Team",  # Host names
    email="podcast@fakeproblems.com",  # Contact email
    website_url="https://www.fakeproblems.com",  # Your website (or social media link)
    categories=["Comedy", "Society & Culture"],  # iTunes categories
    artwork_url=None,  # Will be filled in Step 2
    explicit=False  # Set to True if your podcast contains explicit content
)

print("✓ Podcast metadata configured!")
print("✓ Next: Upload podcast logo to get artwork URL")
```

### Run Setup

```bash
python setup_rss_metadata.py
```

This saves your podcast information to `output/podcast_metadata.json`.

---

## Step 2: Upload Podcast Logo

Your RSS feed needs a publicly accessible URL for your podcast logo.

### Option A: Upload to Dropbox (Recommended)

1. Copy your podcast logo to Dropbox:
   ```bash
   # Copy logo to your Dropbox podcast folder
   cp fake_problems_logo.jpg ~/Dropbox/podcast/artwork/
   ```

2. Get a shared link:
   - Open Dropbox website or app
   - Navigate to `/podcast/artwork/fake_problems_logo.jpg`
   - Right-click → "Share" → "Copy link"
   - **Important**: Replace `?dl=0` with `?dl=1` at the end of the URL
   - Example: `https://www.dropbox.com/s/abc123/logo.jpg?dl=1`

3. Update metadata with artwork URL:
   ```bash
   python -c "
   from uploaders.spotify_uploader import SpotifyUploader
   import json
   from pathlib import Path

   # Load metadata
   metadata_path = Path('output/podcast_metadata.json')
   with open(metadata_path, 'r') as f:
       metadata = json.load(f)

   # Update artwork URL
   metadata['artwork_url'] = 'YOUR_DROPBOX_LINK_HERE'  # Paste your ?dl=1 link

   # Save
   with open(metadata_path, 'w') as f:
       json.dump(metadata, f, indent=2)

   print('✓ Artwork URL updated!')
   "
   ```

### Option B: Use Existing URL

If your logo is already hosted somewhere (your website, imgur, etc.):
- Just use that URL
- Make sure it's publicly accessible (not behind a login)
- Update metadata with that URL using the script above

---

## Step 3: Generate Your First RSS Feed

Run the automation on an existing episode to generate the RSS feed:

```bash
python main.py ep25
```

This will:
1. Process the episode (or load existing data)
2. Upload MP3 to Dropbox
3. Create shared link for the MP3
4. **Generate/update RSS feed at `output/podcast_feed.xml`**

Check that it worked:
```bash
ls -lh output/podcast_feed.xml
```

You should see an XML file. You can open it in a text editor to verify it looks correct.

---

## Step 4: Host Your RSS Feed

Spotify needs to access your RSS feed from a public URL. You have several options:

### Option A: Dropbox Public Link (Easiest, Free)

1. Upload RSS feed to Dropbox:
   ```bash
   cp output/podcast_feed.xml ~/Dropbox/Public/
   # Or if Public folder doesn't exist:
   cp output/podcast_feed.xml ~/Dropbox/podcast/
   ```

2. Get shared link:
   - Open Dropbox website
   - Navigate to `podcast_feed.xml`
   - Right-click → "Share" → "Copy link"
   - **Important**: Replace `?dl=0` with `?raw=1` at the end
   - Example: `https://www.dropbox.com/s/xyz789/podcast_feed.xml?raw=1`
   - **Note**: Use `?raw=1` for XML files (not `?dl=1`)

3. Test the link:
   - Open the link in your browser
   - You should see raw XML content
   - If it downloads instead, you used `?dl=1` instead of `?raw=1`

### Option B: GitHub Pages (Free, More Reliable)

1. Create a GitHub repository (e.g., `fake-problems-rss`)
2. Upload `podcast_feed.xml` to the repo
3. Enable GitHub Pages in Settings
4. Your RSS URL will be: `https://yourusername.github.io/fake-problems-rss/podcast_feed.xml`

### Option C: Your Own Website

If you have a website, just upload `podcast_feed.xml` to your web server:
- URL: `https://yourwebsite.com/podcast_feed.xml`
- Make sure it's publicly accessible

---

## Step 5: Submit RSS Feed to Spotify

### First Time Setup

1. Go to [Spotify for Podcasters](https://podcasters.spotify.com)
2. Click "Get Started" or "Add Your Podcast"
3. **Enter your RSS feed URL** (from Step 4)
4. Click "Next"
5. Spotify will validate your feed
6. Complete verification (you may need to add a code to your feed or website)
7. Once verified, your podcast is live on Spotify!

### Important Notes

- Spotify checks your RSS feed every **2-8 hours** for new episodes
- New episodes appear automatically (no manual upload needed)
- You can see status at [podcasters.spotify.com](https://podcasters.spotify.com)
- First sync can take up to 24 hours

---

## Step 6: Automate RSS Feed Upload

Now make your automation update the RSS feed automatically:

### Option 1: Dropbox Auto-Upload (Recommended)

Edit your automation to upload the RSS feed to Dropbox after every episode:

1. Open `main.py`
2. Find the RSS feed generation section (Step 7.5)
3. Add after RSS feed is saved:

```python
# Upload RSS feed to Dropbox
print("[INFO] Uploading RSS feed to Dropbox...")
rss_dropbox_path = "/podcast/podcast_feed.xml"
self.dropbox.upload_file(rss_feed_path, rss_dropbox_path, overwrite=True)
print(f"[OK] RSS feed uploaded: {rss_dropbox_path}")
print("[INFO] Spotify will check for updates within 2-8 hours")
```

Now every time you run `python main.py ep26`, the RSS feed is automatically updated and uploaded!

### Option 2: Manual Upload (Simple)

After running automation:
```bash
# Copy updated feed to Dropbox
cp output/podcast_feed.xml ~/Dropbox/podcast/
```

Spotify will pick up changes within a few hours.

---

## How to Use

### For Each New Episode:

1. **Run automation** (same as always):
   ```bash
   python main.py ep26
   ```

2. **That's it!** The automation:
   - Uploads MP3 to Dropbox
   - Gets shared link
   - Updates RSS feed with episode info
   - Uploads RSS feed to Dropbox
   - **Episode appears on Spotify in 2-8 hours automatically**

You never have to manually upload to Spotify again!

---

## Validation & Troubleshooting

### Validate Your RSS Feed

Check if your RSS feed is valid:

```python
from uploaders.spotify_uploader import SpotifyUploader

uploader = SpotifyUploader()
results = uploader.validate_rss_feed()

if results['valid']:
    print(f"✓ RSS feed is valid!")
    print(f"✓ {results['episode_count']} episodes in feed")
else:
    print("✗ RSS feed has issues:")
    for warning in results['warnings']:
        print(f"  - {warning}")
```

### Common Issues

**Issue**: "Spotify isn't picking up new episodes"
- **Solution**: Check your RSS feed URL is accessible (open in browser)
- **Solution**: Make sure MP3 Dropbox links use `?dl=1`
- **Solution**: Wait 8-12 hours (Spotify checks every 2-8 hours, but can be delayed)
- **Solution**: Go to Spotify for Podcasters and click "Check for new episodes"

**Issue**: "RSS feed shows wrong information"
- **Solution**: Edit `output/podcast_metadata.json` and re-run automation
- **Solution**: Check your podcast logo URL is accessible

**Issue**: "Episodes have no audio / won't play"
- **Solution**: Make sure Dropbox shared links end with `?dl=1` (direct download)
- **Solution**: Test the MP3 link directly in a browser - it should download, not show a Dropbox page

**Issue**: "RSS feed file not found"
- **Solution**: Run `python main.py ep25` to generate initial feed
- **Solution**: Check `output/podcast_feed.xml` exists

---

## Advanced: Multiple Seasons

To organize episodes into seasons:

1. Edit `output/podcast_metadata.json`
2. Add `"season": 1` to episode metadata
3. When calling `update_rss_feed()`, pass `season_number=1`

---

## Testing the Complete Flow

Test everything works:

```bash
# 1. Run automation in test mode
python main.py ep25 --test

# 2. Check RSS feed was created
cat output/podcast_feed.xml | head -50

# 3. Validate feed
python -c "from uploaders.spotify_uploader import SpotifyUploader; print(SpotifyUploader().validate_rss_feed())"

# 4. Upload to Dropbox
cp output/podcast_feed.xml ~/Dropbox/podcast/

# 5. Get shared link and test in browser
# (Should show XML content)

# 6. Submit to Spotify for Podcasters

# 7. Wait 2-24 hours for first sync

# 8. Check Spotify app - your episode should appear!
```

---

## What Gets Automated

When you run `python main.py ep26`:

| Step | What Happens | Automated? |
|------|-------------|-----------|
| Transcribe audio | Whisper transcription | ✅ Yes |
| Analyze content | Claude AI analysis | ✅ Yes |
| Censor audio | Beep out names/slurs | ✅ Yes |
| Create clips | 3x 30-second clips | ✅ Yes |
| Convert to video | Create MP4 with logo | ✅ Yes |
| Convert to MP3 | Episode audio to MP3 | ✅ Yes |
| Upload to Dropbox | MP3 + clips uploaded | ✅ Yes |
| Create shared links | Public Dropbox URLs | ✅ Yes |
| **Update RSS feed** | **Add episode to feed** | ✅ **Yes** |
| **Upload RSS feed** | **Upload to Dropbox** | ✅ **Yes** |
| **Spotify distribution** | **Auto-pull from RSS** | ✅ **Yes** |

**Total manual work: Just run `python main.py ep26`**

---

## Cost

**Completely Free!**
- RSS feed: Free (just an XML file)
- Hosting: Free (use Dropbox you already have)
- Spotify distribution: Free
- **Total: $0/month**

---

## Support

If you run into issues:

1. Check that Spotify uploader is configured:
   ```bash
   python test_spotify.py
   ```

2. Validate your RSS feed:
   ```bash
   python -c "from uploaders.spotify_uploader import SpotifyUploader; print(SpotifyUploader().validate_rss_feed())"
   ```

3. Check that Dropbox links work:
   - Open MP3 link in browser - should download file
   - Open RSS feed link in browser - should show XML

4. Test RSS feed with a validator:
   - Go to https://podba.se/validate/
   - Paste your RSS feed URL
   - Fix any errors shown

---

## Summary

**One-Time Setup** (15 minutes):
1. Run `setup_rss_metadata.py` to configure podcast info
2. Upload podcast logo and get public URL
3. Generate initial RSS feed with `python main.py ep25`
4. Upload RSS feed to Dropbox and get public URL
5. Submit RSS feed URL to Spotify for Podcasters

**Every Episode After** (0 minutes):
1. Run `python main.py ep26`
2. Episode automatically appears on Spotify in 2-8 hours

**No more manual Spotify uploads!** 🎉
