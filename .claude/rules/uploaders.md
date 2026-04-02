---
paths:
  - "uploaders/**"
---

- Instagram and TikTok uploaders are stubs — they log but don't actually upload
- All uploaders must handle `--dry-run` mode (log intent, skip actual upload)
- Test with `unittest.mock`, never hit real platform APIs
- Each uploader follows the pattern: `__init__` checks credentials → `upload()` returns success/failure
- YouTube uploader uses OAuth (credentials/youtube_token.pickle)
- Twitter uploader uses tweepy with API keys from Config
