# Social Media Integration Setup Guide

Complete guide for setting up all social media platform integrations for automated podcast distribution.

---

## Table of Contents

1. [YouTube](#youtube)
2. [Twitter/X](#twitterx)
3. [Instagram](#instagram)
4. [TikTok](#tiktok)
5. [Spotify](#spotify)
6. [Testing](#testing)

---

## YouTube

### Prerequisites
- Google account
- YouTube channel

### Setup Steps

1. **Create Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project: "Fake Problems Automation" (or your podcast name)
   - Wait for project creation to complete

2. **Enable YouTube Data API v3**
   - In your project, go to "APIs & Services" > "Library"
   - Search for "YouTube Data API v3"
   - Click "Enable"

3. **Create OAuth 2.0 Credentials**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - If prompted, configure the OAuth consent screen:
     - User Type: External (unless you have a Google Workspace)
     - App name: Your podcast name
     - User support email: Your email
     - Add your email to test users
   - Application type: Desktop app
   - Name: "Podcast Automation"
   - Click "Create"

4. **Download Credentials**
   - Click the download button (⬇) next to your OAuth client
   - Save the JSON file as `credentials/youtube_credentials.json` in your project

5. **First Run Authentication**
   - Run your podcast automation with YouTube enabled
   - A browser window will open for authorization
   - Sign in to your Google account
   - Grant permissions to the app
   - The token will be saved to `credentials/youtube_token.pickle`

### API Quotas
- Default quota: 10,000 units per day
- Video upload cost: 1,600 units
- ~6 uploads per day with default quota
- Request quota increase if needed

### Notes
- Supports full episode uploads and Shorts
- Videos must be in video format (not just audio)
- Consider creating static image videos from audio files

---

## Twitter/X

### Prerequisites
- Twitter/X account
- Elevated API access (required for media uploads)

### Setup Steps

1. **Apply for Developer Access**
   - Go to [Twitter Developer Portal](https://developer.twitter.com)
   - Sign in with your Twitter account
   - Click "Sign up" for developer access
   - Fill out the application form
   - Explain your use case: "Automated podcast distribution and episode announcements"
   - Wait for approval (usually 1-2 days)

2. **Create a Project and App**
   - Once approved, go to the Developer Portal
   - Create a new Project
   - Create an App within the project

3. **Request Elevated Access**
   - In your app settings, request "Elevated" access
   - Required for media uploads (videos, images)
   - Fill out the additional use case form
   - Wait for approval

4. **Generate Keys and Tokens**
   - Go to your app's "Keys and Tokens" tab
   - Regenerate API Key and Secret (Consumer Keys)
   - Generate Access Token and Secret
   - Copy all four values

5. **Add to .env**
   ```bash
   TWITTER_API_KEY=your_api_key_here
   TWITTER_API_SECRET=your_api_secret_here
   TWITTER_ACCESS_TOKEN=your_access_token_here
   TWITTER_ACCESS_SECRET=your_access_secret_here
   ```

### API Limits
- Tweet character limit: 280 (4000 for Premium)
- Media per tweet: Up to 4 images OR 1 video
- Video max size: 512MB
- Video max length: 2 minutes 20 seconds

### Features
- Post episode announcements
- Create Twitter threads
- Upload video clips
- Auto-generated captions from Claude

---

## Instagram

### Prerequisites
- Instagram Business or Creator account
- Facebook Page linked to Instagram account
- Facebook Developer account

### Setup Steps

1. **Convert to Business Account**
   - Open Instagram app
   - Go to Settings > Account
   - Switch to Professional Account
   - Choose Business or Creator
   - Link to a Facebook Page

2. **Create Facebook App**
   - Go to [Facebook Developers](https://developers.facebook.com)
   - Click "My Apps" > "Create App"
   - Use case: "Business"
   - App type: "Business"
   - Fill in app details

3. **Add Instagram Graph API**
   - In your app dashboard
   - Click "Add Product"
   - Find "Instagram Graph API" and click "Set Up"

4. **Get Access Token**
   - Go to "Instagram Graph API" > "Tools"
   - Click "User Token Generator"
   - Grant permissions:
     - `instagram_basic`
     - `instagram_content_publish`
     - `pages_read_engagement`
   - Copy the generated token

5. **Exchange for Long-Lived Token**
   ```bash
   https://graph.facebook.com/v18.0/oauth/access_token?
     grant_type=fb_exchange_token&
     client_id=YOUR_APP_ID&
     client_secret=YOUR_APP_SECRET&
     fb_exchange_token=YOUR_SHORT_LIVED_TOKEN
   ```

6. **Get Instagram Account ID**
   ```bash
   https://graph.facebook.com/v18.0/me/accounts?
     access_token=YOUR_ACCESS_TOKEN
   ```
   Then:
   ```bash
   https://graph.facebook.com/v18.0/PAGE_ID?
     fields=instagram_business_account&
     access_token=YOUR_ACCESS_TOKEN
   ```

7. **Add to .env**
   ```bash
   INSTAGRAM_ACCESS_TOKEN=your_long_lived_token_here
   INSTAGRAM_ACCOUNT_ID=your_instagram_account_id_here
   ```

### API Requirements
- Videos must be publicly accessible URLs
- Upload clips to Dropbox with public links
- Replace `dl=0` with `dl=1` in Dropbox URLs

### Reel Requirements
- Duration: 3-90 seconds
- Aspect ratio: 9:16 (vertical) recommended
- Resolution: Minimum 500x888 pixels
- File size: Maximum 1GB
- Format: MP4

---

## TikTok

### Prerequisites
- TikTok account
- Business verification (required for API access)

### Setup Steps

1. **Apply for Developer Access**
   - Go to [TikTok Developers](https://developers.tiktok.com)
   - Click "Register" and create developer account
   - Complete business verification process
   - This can take several days to weeks

2. **Create an App**
   - Once verified, go to "Manage Apps"
   - Click "Create App"
   - Fill in app details
   - Select "Content Posting API" in products

3. **Request Content Posting API Access**
   - In your app, request access to Content Posting API
   - Provide detailed use case description
   - Wait for approval (can take weeks)

4. **Get Client Credentials**
   - Once approved, go to app settings
   - Copy Client Key and Client Secret

5. **Complete OAuth Flow**
   - Implement OAuth 2.0 flow to get user access token
   - Scopes needed: `video.upload`, `video.publish`
   - This requires user authentication

6. **Add to .env**
   ```bash
   TIKTOK_CLIENT_KEY=your_client_key_here
   TIKTOK_CLIENT_SECRET=your_client_secret_here
   TIKTOK_ACCESS_TOKEN=your_access_token_here
   ```

### API Requirements
- Business account verification required
- Approval process is lengthy
- Consider manual uploads as alternative

### Video Requirements
- Duration: 3 seconds to 10 minutes
- Aspect ratio: 9:16 (vertical) recommended
- Resolution: Minimum 720p, recommended 1080p
- File size: Maximum 4GB
- Format: MP4 or WebM

### Notes
- TikTok API access is the most restrictive
- Many podcasters use manual uploads
- Consider third-party tools if API access denied

---

## Spotify

### Prerequisites
- Spotify for Podcasters account (formerly Anchor)
- Spotify Developer account (for API)

### Setup Steps

#### Option 1: RSS Feed (Recommended)

1. **Create RSS Feed**
   - Use the built-in RSS generator in this project
   - Host RSS feed on a public URL

2. **Submit to Spotify**
   - Go to [Spotify for Podcasters](https://podcasters.spotify.com)
   - Click "Get Started"
   - Choose "Import an existing podcast"
   - Enter your RSS feed URL
   - Complete verification

3. **Automatic Updates**
   - Spotify checks RSS feed periodically
   - New episodes appear automatically
   - No API calls needed

#### Option 2: Spotify API (Advanced)

1. **Create Spotify Developer App**
   - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   - Create an app
   - Get Client ID and Client Secret

2. **Get Show ID**
   - Find your show on Spotify
   - Copy the ID from the URL: `spotify:show:SHOW_ID`

3. **Add to .env**
   ```bash
   SPOTIFY_CLIENT_ID=your_client_id_here
   SPOTIFY_CLIENT_SECRET=your_client_secret_here
   SPOTIFY_SHOW_ID=your_show_id_here
   ```

### Notes
- RSS feed is the standard approach
- API is read-only for most features
- Use Spotify for Podcasters dashboard for uploads
- API useful for analytics and show information

---

## Testing

### Run Test Suite

```bash
# Install test dependencies
pip install pytest pytest-cov pytest-mock

# Run all tests
pytest tests/

# Run specific uploader tests
pytest tests/test_youtube_uploader.py
pytest tests/test_instagram_uploader.py
pytest tests/test_tiktok_uploader.py
pytest tests/test_twitter_uploader.py
pytest tests/test_spotify_uploader.py

# Run with coverage
pytest --cov=uploaders tests/

# Run with verbose output
pytest -v tests/
```

### Manual Testing

1. **Test YouTube Upload**
   ```python
   from uploaders import YouTubeUploader

   uploader = YouTubeUploader()
   result = uploader.upload_episode(
       video_path='test_video.mp4',
       title='Test Episode',
       description='Test description',
       privacy_status='private'  # Use private for testing
   )
   print(result)
   ```

2. **Test Twitter Post**
   ```python
   from uploaders import TwitterUploader

   uploader = TwitterUploader()
   result = uploader.post_tweet('Test tweet from automation')
   print(result)
   ```

3. **Test Instagram Reel**
   ```python
   from uploaders import InstagramUploader

   uploader = InstagramUploader()
   # Note: Requires public video URL
   result = uploader.upload_reel(
       video_url='https://example.com/video.mp4',
       caption='Test reel'
   )
   print(result)
   ```

---

## Troubleshooting

### YouTube

**Error: Credentials file not found**
- Ensure `credentials/youtube_credentials.json` exists
- Download from Google Cloud Console
- Check file path and permissions

**Error: Quota exceeded**
- Default quota is 10,000 units/day
- Video upload costs 1,600 units
- Request quota increase in Google Cloud Console

### Twitter

**Error: Forbidden (403)**
- Ensure you have Elevated access
- Check API keys are correct
- Verify app has write permissions

**Error: Media upload failed**
- Check file size (max 512MB for video)
- Ensure file format is supported
- Verify Elevated access is granted

### Instagram

**Error: Invalid access token**
- Token may have expired
- Generate new long-lived token
- Tokens last 60 days, refresh before expiry

**Error: Video URL not accessible**
- Instagram requires public URLs
- Use Dropbox shared links
- Change `dl=0` to `dl=1` in URL

### TikTok

**Error: Insufficient permissions**
- Ensure Content Posting API is approved
- Check access token has correct scopes
- Verify business account status

**Error: Video processing failed**
- Check video meets requirements (vertical, 720p+)
- Ensure file size under 4GB
- Verify MP4 format

### Spotify

**Error: Authentication failed**
- Check client credentials
- Ensure app has correct scopes
- Verify client secret is correct

**RSS Feed Issues**
- Ensure feed is publicly accessible
- Validate RSS XML format
- Check all required iTunes tags present

---

## Best Practices

### Security
- Never commit `.env` file to version control
- Use environment variables for all secrets
- Rotate API keys periodically
- Use minimum required API scopes

### Rate Limiting
- Respect platform rate limits
- Implement exponential backoff
- Monitor API quota usage
- Consider queueing uploads

### Content
- Use consistent branding across platforms
- Optimize video format for each platform
- Test with private/unlisted posts first
- Monitor analytics to optimize timing

### Automation
- Start with manual testing
- Gradually enable automation
- Monitor error logs
- Have fallback manual process

---

## Support Resources

- **YouTube**: [YouTube Data API Docs](https://developers.google.com/youtube/v3)
- **Twitter**: [Twitter API Docs](https://developer.twitter.com/en/docs)
- **Instagram**: [Instagram Graph API Docs](https://developers.facebook.com/docs/instagram-api)
- **TikTok**: [TikTok Developer Docs](https://developers.tiktok.com/doc)
- **Spotify**: [Spotify for Podcasters](https://support.spotify.com/us/podcasters/)

---

## Next Steps

1. Choose which platforms to integrate
2. Follow setup instructions for each platform
3. Add credentials to `.env`
4. Run test uploads
5. Enable in production
6. Monitor results and adjust

Good luck with your podcast automation! 🎙️
