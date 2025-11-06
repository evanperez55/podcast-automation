# Quick Start: Automatic Spotify Distribution

## What This Does

Makes Spotify uploads **completely automatic** at **$0 cost** using RSS feeds.

**Before:** Manual 10-minute upload to Spotify for each episode
**After:** Episodes appear on Spotify automatically (zero manual work)

---

## 3-Step Quick Setup (15 minutes)

### Step 1: Configure Podcast Info (5 min)

```bash
python setup_rss_metadata.py
```

Answer the prompts with your podcast information.

### Step 2: Add Podcast Logo URL (5 min)

1. Upload your podcast logo to Dropbox
2. Get shared link, change `?dl=0` to `?dl=1`
3. Edit `output/podcast_metadata.json` and add the URL to `artwork_url`

### Step 3: Submit to Spotify (5 min)

1. Run automation to generate RSS feed:
   ```bash
   python main.py ep25
   ```

2. Upload `output/podcast_feed.xml` to Dropbox

3. Get Dropbox shared link for the XML file, change `?dl=0` to `?raw=1`

4. Go to [Spotify for Podcasters](https://podcasters.spotify.com)

5. Click "Add Your Podcast" and enter your RSS feed URL

6. Complete verification

**Done!** Spotify will now automatically check your RSS feed every 2-8 hours for new episodes.

---

## Daily Usage (After Setup)

For every new episode:

```bash
python main.py ep26
```

That's it! Episode appears on Spotify automatically in 2-8 hours.

---

## What You Need

- ✅ Working podcast automation
- ✅ Dropbox account
- ✅ Podcast logo image (1400x1400+)
- ✅ Basic podcast info (title, description, host names)
- ✅ 15 minutes for one-time setup

---

## Need Help?

See detailed guide: `RSS_FEED_SETUP.md`

Test RSS generation:
```bash
python test_rss_feed.py
```

Validate your feed:
```bash
python -c "from uploaders.spotify_uploader import SpotifyUploader; print(SpotifyUploader().validate_rss_feed())"
```

---

## What This Costs

**$0 per month**

Uses your existing Dropbox storage (which you're already using for episodes).

---

## Summary

- **Setup time:** 15 minutes (one-time)
- **Per episode:** 0 minutes (automatic)
- **Cost:** $0
- **Platforms:** Works with Spotify, Apple Podcasts, Google Podcasts, and ALL podcast apps

Your command: `python main.py ep26`
Result: Episode on Spotify + Apple Podcasts + Google Podcasts + everywhere else automatically! 🎉
