# Google Docs Topic Tracker - Quick Start

Get your topic tracker running in **5 minutes**!

## What You'll Get

After setup, your automation will automatically:
- ✅ Read topics from your Google Doc
- ✅ Use AI to match topics with episodes
- ✅ Move discussed topics to a "Discussed Topics" section
- ✅ Track episode numbers and dates

## 5-Minute Setup

### 1. Get Google Credentials (2 min)

1. Go to https://console.cloud.google.com
2. Create project → Enable "Google Docs API"
3. Create OAuth credentials (Desktop app)
4. Download JSON → Save as `google_docs_credentials.json`

**Detailed instructions**: See [GOOGLE_DOCS_TOPIC_TRACKER.md](GOOGLE_DOCS_TOPIC_TRACKER.md#step-1-google-cloud-console-setup)

### 2. Add Your Doc ID (1 min)

1. Open your topics Google Doc
2. Copy ID from URL:
   ```
   https://docs.google.com/document/d/THIS_IS_YOUR_ID/edit
   ```
3. Add to `.env`:
   ```env
   GOOGLE_DOC_ID=your_doc_id_here
   ```

### 3. Run Setup (2 min)

```bash
python setup_google_docs.py
```

This will:
- Authenticate with Google
- Test access to your doc
- Save credentials

**Done!** Your automation now includes topic tracking.

## Test It

### Quick Test
```bash
python test_google_docs_integration.py
```

Shows what topics will be tracked.

### Dry Run Test
```bash
python test_google_docs_integration.py --dry-run
```

Simulates a full episode with sample data (no changes made).

### Real Usage
```bash
python main.py latest
```

Processes episode and updates your Google Doc automatically!

## Your Google Doc Format

**Before automation**:
```
Topics to Discuss:

cheese addiction
robot cafes in Japan
what if birds had arms
solar powered dating apps
```

**After processing Episode 25**:
```
Topics to Discuss:

what if birds had arms
solar powered dating apps

--- DISCUSSED TOPICS ---

• cheese addiction - Episode 25 (2025-01-19)
• robot cafes in Japan - Episode 25 (2025-01-19)
```

## Common Issues

### "GOOGLE_DOC_ID not configured"
→ Add to `.env`: `GOOGLE_DOC_ID=your_id`

### "Credentials file not found"
→ Download from Google Cloud Console as `google_docs_credentials.json`

### "Failed to fetch document"
→ Check doc ID and make sure the authenticated account has access

## Full Documentation

See [GOOGLE_DOCS_TOPIC_TRACKER.md](GOOGLE_DOCS_TOPIC_TRACKER.md) for:
- Detailed setup instructions
- How topic matching works
- Advanced configuration
- Troubleshooting guide

## Questions?

The tracker is **optional** - if not configured, automation runs normally without it.

To disable:
- Don't set `GOOGLE_DOC_ID` in `.env`, or
- Use test mode: `python main.py --test`
