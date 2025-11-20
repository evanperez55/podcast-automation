# Google Docs Topic Tracker

Automatically track and mark discussed podcast topics in a Google Doc.

## Overview

The Google Docs Topic Tracker integrates with your podcast automation to:

1. **Read topics** from your Google Doc
2. **Analyze transcripts** using Claude AI to find discussed topics
3. **Automatically move** discussed topics to a "Discussed Topics" section
4. **Track episode numbers** and dates for each discussed topic

This eliminates the manual work of tracking which topics you've already covered!

## How It Works

### Workflow

```
Episode Processing
    ↓
Transcript Created
    ↓
Claude Analyzes Content
    ↓
[NEW STEP] Topic Tracker Activates
    ↓
1. Fetches topics from Google Doc
2. Claude matches topics with transcript (semantic matching)
3. Moves matched topics to "Discussed Topics" section
4. Adds episode number and date
    ↓
Continue with normal automation...
```

### Smart Topic Matching

The tracker uses Claude AI for intelligent matching:

- **Semantic understanding**: Detects topics even if wording differs
  - Doc says: "cheese addiction"
  - Episode discusses: "eating too much cheese daily"
  - Result: ✓ MATCH

- **Context awareness**: Only matches when topic was actually discussed
  - Brief mention in passing: ✗ No match
  - Main story/discussion: ✓ Match

- **Confidence scoring**: Only moves topics with >60% confidence

## Setup Instructions

### Step 1: Google Cloud Console Setup

1. **Go to [Google Cloud Console](https://console.cloud.google.com)**

2. **Create a new project** (or select existing)
   - Click the project dropdown at the top
   - Click "New Project"
   - Name it something like "Podcast Automation"

3. **Enable Google Docs API**
   - In the left sidebar, go to "APIs & Services" > "Library"
   - Search for "Google Docs API"
   - Click on it and press "Enable"

4. **Create OAuth 2.0 Credentials**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - If prompted, configure the OAuth consent screen:
     - Choose "External" (unless you have a Google Workspace)
     - Fill in app name: "Podcast Topic Tracker"
     - Add your email as a test user
     - Save
   - Back at Create OAuth client ID:
     - Choose "Desktop application"
     - Name it "Podcast Automation"
     - Click "Create"

5. **Download credentials**
   - Click the download button next to your new credential
   - Save the JSON file as `google_docs_credentials.json` in your project folder

### Step 2: Get Your Google Doc ID

1. **Open your podcast topics Google Doc**

2. **Copy the document ID from the URL**:
   ```
   https://docs.google.com/document/d/1AbCdEfGhIjKlMnOpQrStUvWxYz/edit
                                      ↑
                              This is your DOC_ID
   ```

3. **Add to your `.env` file**:
   ```env
   GOOGLE_DOC_ID=1AbCdEfGhIjKlMnOpQrStUvWxYz
   ```

### Step 3: Run Setup Script

```bash
python setup_google_docs.py
```

This will:
- Check for credentials file
- Open your browser for authorization
- Save authentication token
- Test access to your Google Doc

**Note**: You only need to do this once! The token is saved and will be reused.

### Step 4: Organize Your Google Doc

Your Google Doc should have your topics listed as simple bullet points or lines:

```
Topics to Discuss:

cheese addiction
robot cafes in Japan
what if you could only eat one color of food
dating apps but for finding enemies
solar powered toasters
```

The automation will automatically create a "Discussed Topics" section at the bottom when it finds matches.

## Using the Tracker

### Automatic Mode

Once set up, the tracker runs automatically during episode processing:

```bash
python main.py latest
```

**Output example**:
```
STEP 3: ANALYZING CONTENT WITH CLAUDE
----------------------------------------------------------
[OK] Content analysis complete
  Items to censor: 4
  Best clips identified: 3
[OK] Analysis saved to: output/ep_25/analysis.json

============================================================
UPDATING GOOGLE DOCS TOPIC TRACKER
============================================================
[INFO] Fetching Google Doc...
[INFO] Extracting topics from document...
[OK] Found 47 active topics

[INFO] Analyzing 47 topics against transcript...
[OK] Found 2 discussed topics

[INFO] Topics to move to 'Discussed' section:
  • cheese addiction (95% confidence)
    Reason: Main story about extreme cheese consumption and health effects
  • robot cafes in Japan (78% confidence)
    Reason: Discussed as example of unique dining experiences
[OK] Moved 2 topics to 'Discussed Topics' section
============================================================
```

### After Processing

Your Google Doc will now have:

**At the top** (active topics):
```
Topics to Discuss:

what if you could only eat one color of food
dating apps but for finding enemies
solar powered toasters
```

**At the bottom** (discussed topics):
```
--- DISCUSSED TOPICS ---

• cheese addiction - Episode 25 (2025-01-19)
• robot cafes in Japan - Episode 25 (2025-01-19)
• space therapy - Episode 21 (2025-01-15)
• drunk persistence - Episode 24 (2025-01-18)
```

## Configuration

### Optional: Disable for Testing

To run the automation without topic tracking:

1. **Option 1**: Don't set `GOOGLE_DOC_ID` in `.env`
   - Tracker will skip silently

2. **Option 2**: Use test mode:
   ```bash
   python main.py --test latest
   ```

### Topic Matching Sensitivity

The tracker uses Claude with these settings:

- **Confidence threshold**: 60% (topics below this won't be moved)
- **Temperature**: 0.1 (consistent, deterministic matching)
- **Model**: Claude Sonnet 4 (latest)

To adjust confidence threshold, edit `google_docs_tracker.py`:

```python
# Line ~210
if match.get('discussed', False) and match.get('confidence', 0) > 0.6:
                                                                    ↑
                                                            Change this value
```

## Troubleshooting

### "GOOGLE_DOC_ID not configured"

**Solution**: Add your doc ID to `.env`:
```env
GOOGLE_DOC_ID=your_actual_doc_id_here
```

### "Failed to fetch document: 404"

**Possible causes**:
- Wrong document ID
- Document doesn't exist
- You don't have access to the document

**Solution**: Double-check the document ID and make sure the Google account you authenticated with has access to the doc.

### "Credentials file not found"

**Solution**: Download OAuth credentials from Google Cloud Console and save as:
```
google_docs_credentials.json
```

### "Google Docs topic tracker not available"

This is normal if you haven't set it up yet. The automation will continue without it.

To enable:
1. Follow setup instructions above
2. Restart the automation

### "No topics found to check"

**Possible causes**:
- All topics are already in "Discussed Topics" section
- Document is empty
- Topics are formatted in an unexpected way

**Solution**: Make sure you have topics listed as simple text (bullet points or separate lines).

## Advanced Usage

### Manual Testing

Test the tracker without processing a full episode:

```bash
python google_docs_tracker.py
```

This runs with fake data to verify authentication and document access.

### Integration with Existing Code

You can use the tracker in your own scripts:

```python
from google_docs_tracker import GoogleDocsTopicTracker

tracker = GoogleDocsTopicTracker()

result = tracker.update_topics_for_episode(
    transcript_text="Full transcript here...",
    episode_summary="Summary from Claude",
    episode_number=25
)

print(f"Moved {result['topics_moved']} topics")
```

### Multiple Google Docs

To track topics in multiple documents:

1. Create separate `.env` variables:
   ```env
   GOOGLE_DOC_ID_MAIN=doc_id_1
   GOOGLE_DOC_ID_BACKUP=doc_id_2
   ```

2. Modify `config.py` to add the second ID

3. Create multiple tracker instances in `main.py`

## Privacy & Permissions

### What Can the Automation Access?

The OAuth token grants access to:
- **Read** your Google Docs
- **Edit** your Google Docs

**Scope**: `https://www.googleapis.com/auth/documents`

### Data Storage

- **Credentials**: Stored locally in `google_docs_credentials.json`
- **Token**: Stored locally in `google_docs_token.json`
- **Never shared**: All authentication is local, credentials never leave your machine

### Revoking Access

To revoke access:
1. Go to [Google Account Permissions](https://myaccount.google.com/permissions)
2. Find "Podcast Automation" (or whatever you named it)
3. Click "Remove Access"
4. Delete `google_docs_token.json` from your project

## Example Workflow

### Complete Example

1. **You have a Google Doc**:
   ```
   Podcast Topics:
   - AI becoming sentient but only for customer service
   - cheese addiction
   - what if birds had arms
   ```

2. **Record Episode 25** about cheese addiction

3. **Run automation**:
   ```bash
   python main.py ep25
   ```

4. **Automation processes**:
   - Transcribes audio
   - Claude analyzes: "Episode discusses extreme cheese consumption..."
   - Topic tracker matches "cheese addiction" (92% confidence)
   - Moves to "Discussed Topics" section

5. **Your Google Doc now shows**:
   ```
   Podcast Topics:
   - AI becoming sentient but only for customer service
   - what if birds had arms

   --- DISCUSSED TOPICS ---
   • cheese addiction - Episode 25 (2025-01-19)
   ```

6. **Next time you open the doc**, you immediately see:
   - ✓ What topics are still available
   - ✓ What you've already covered
   - ✓ When each topic was discussed

No more duplicate topics!

## Benefits

### Before Topic Tracker

❌ Manually mark topics after recording
❌ Forget which topics were discussed
❌ Accidentally repeat topics
❌ Hard to remember when you covered something

### After Topic Tracker

✅ Automatic topic tracking
✅ Always know what's been covered
✅ Never repeat topics
✅ Full history with episode numbers and dates

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Verify your setup with `python setup_google_docs.py`
3. Test authentication with `python google_docs_tracker.py`
4. Check that Google Docs API is enabled in your project

## Requirements

**Python packages** (auto-installed):
```bash
pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

**Already included in** `requirements.txt`
