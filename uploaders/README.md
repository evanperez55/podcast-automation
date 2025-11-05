# Social Media Uploaders

Placeholder modules for uploading podcast content to various platforms.

## 🚧 Status: Coming Soon

These modules will be implemented once API access is configured for each platform.

## 📋 Platform Upload Modules

### 1. YouTube (`youtube_uploader.py`)
- Upload full episode as video
- Add title, description, tags
- Set privacy settings
- Upload clips as Shorts

### 2. Spotify (`spotify_uploader.py`)
- Upload via Spotify for Podcasters API or RSS feed
- Set episode metadata
- Schedule publishing

### 3. Instagram (`instagram_uploader.py`)
- Post clips as Reels
- Add captions and hashtags
- Cross-post to Facebook

### 4. Twitter (`twitter_uploader.py`)
- Post episode announcement
- Share clips as videos
- Thread creation for episode highlights

### 5. TikTok (`tiktok_uploader.py`)
- Upload clips as TikTok videos
- Add trending sounds/effects
- Caption and hashtag optimization

## 🔑 API Setup Required

Before implementing these uploaders, you need to:

1. **YouTube**: Create project in Google Cloud Console, enable YouTube Data API v3
2. **Spotify**: Get access to Spotify for Podcasters API
3. **Instagram**: Set up Facebook Developer account, get Instagram Graph API access
4. **Twitter**: Create Developer account, get API v2 credentials
5. **TikTok**: Apply for TikTok Creator API access

## 📝 Implementation Priority

Recommended order:
1. ✅ YouTube (easiest, well-documented API)
2. Spotify (RSS feed might be easier than API)
3. Twitter (straightforward API)
4. Instagram (requires Facebook Graph API)
5. TikTok (may require manual review/approval)

## 🔗 API Documentation Links

- [YouTube Data API](https://developers.google.com/youtube/v3)
- [Spotify for Podcasters](https://podcasters.spotify.com/)
- [Instagram Graph API](https://developers.facebook.com/docs/instagram-api/)
- [Twitter API v2](https://developer.twitter.com/en/docs/twitter-api)
- [TikTok Creator API](https://developers.tiktok.com/)
