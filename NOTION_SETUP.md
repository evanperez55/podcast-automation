## Notion Setup Guide - Fake Problems Podcast

Complete guide to set up your Notion workspace for podcast topic management.

---

## 🚀 Quick Setup (10 minutes)

### Step 1: Create Notion Integration (3 min)

1. **Go to** https://www.notion.so/my-integrations
2. **Click** "+ New integration"
3. **Fill in**:
   - Name: `Fake Problems Automation`
   - Associated workspace: [Your workspace]
   - Type: Internal integration
4. **Click** "Submit"
5. **Copy** the "Internal Integration Token"
6. **Add to `.env`**:
   ```env
   NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

### Step 2: Create Database (5 min)

1. **Open Notion** (web or app)
2. **Create new page**: "Fake Problems Topics"
3. **Type** `/database` → Select "Table - Inline"
4. **Name it**: "Topic Bank"

### Step 3: Set Up Database Properties (2 min)

**Delete default properties**, then add these:

| Property Name | Type | Options/Config |
|--------------|------|----------------|
| **Topic** | Title | (default) |
| **Score** | Number | Format: Number, 0-10 |
| **Category** | Select | Options below ⬇️ |
| **Status** | Select | Options below ⬇️ |
| **Source** | Text | - |
| **Episode** | Number | - |
| **URL** | URL | - |
| **Date Added** | Created time | (auto) |
| **Added By** | Created by | (auto) |

#### Category Options (with colors):
- 🔥 Shocking News (Red)
- 🤔 Absurd Hypothetical (Purple)
- 😬 Personal Anecdote (Yellow)
- 💔 Dating/Social (Pink)
- 🧪 Pop Science (Blue)
- 🙄 Cultural Observation (Gray)

#### Status Options (with colors):
- 📋 Backlog (Gray)
- 📝 This Episode (Blue)
- 🎙️ Recorded (Yellow)
- ✅ Published (Green)

### Step 4: Share Database with Integration

1. **Click** the `...` menu (top right of database)
2. **Click** "Connections" → "+ Add connections"
3. **Select** "Fake Problems Automation"
4. **Confirm**

### Step 5: Get Database ID

1. **Click** "Share" (top right)
2. **Copy link** - it looks like:
   ```
   https://www.notion.so/xxxxxxxxxxxxx?v=yyyyyyyyyyyy
                        ^this part^
   ```
3. **Copy just the database ID** (32 characters, the xxxxxxxxxxxxx part)
4. **Add to `.env`**:
   ```env
   NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

### Step 6: Migrate Your Topics

```bash
python notion_integration.py
```

This will:
- Load all 955 topics from Google Doc analysis
- Upload to Notion with correct statuses
- Mark discussed topics as "Published"
- Set remaining as "Backlog"

**Done!** Your Notion workspace is ready.

---

## 📊 Database Views to Create

After migration, create these views for better organization:

### View 1: "All Topics" (Table)
- **Type**: Table
- **Filter**: None
- **Sort**: Score (descending)
- **Purpose**: See everything

### View 2: "Ready to Record" (Table)
- **Type**: Table
- **Filter**:
  - Status = Backlog
  - Score ≥ 7
- **Sort**: Score (descending), Category
- **Purpose**: High-quality topics ready for episodes

### View 3: "Episode Planning" (Board/Kanban)
- **Type**: Board
- **Group by**: Status
- **Filter**: Status ≠ Published
- **Sort**: Score (descending)
- **Purpose**: Drag topics through workflow

### View 4: "By Category" (Gallery)
- **Type**: Gallery
- **Group by**: Category
- **Filter**: Status = Backlog
- **Purpose**: Browse by topic type

### View 5: "This Week" (Calendar)
- **Type**: Calendar
- **Date property**: Date Added
- **Filter**: Date Added = This week
- **Purpose**: See new topics

### View 6: "Published History" (Timeline)
- **Type**: Table
- **Filter**: Status = Published
- **Sort**: Episode (descending)
- **Purpose**: See what you've covered

---

## 🎬 How to Use Your Notion Workspace

### Weekly Workflow

**Sunday - Auto-Populate:**
```bash
python weekly_topic_refresh.py
```
→ Scrapes Reddit, scores with AI, writes to Notion
→ New topics appear in "Backlog"

**Tuesday - Plan Episode:**
1. Open "Ready to Record" view (score 7+)
2. Pick 8-12 topics:
   - 2-3 Shocking News
   - 2-3 Absurd Hypotheticals
   - 1-2 Dating/Social
   - 1-2 Pop Science
   - 1-2 Cultural
   - Add 1-2 personal stories manually
3. Change status to "This Episode"
4. Open "Episode Planning" kanban view
5. Review topics in "This Episode" column

**Wednesday - Record:**
1. Open Notion on phone/tablet
2. Reference "This Episode" topics
3. Check them off as you discuss
4. Move to "Recorded" status

**After Processing:**
```bash
python main.py latest
```
→ Automation detects discussed topics
→ Moves to "Published"
→ Links episode number

### Adding Manual Topics

**Quick Add (Desktop):**
1. Open database
2. Click "+ New" or press `Ctrl/Cmd + N`
3. Type topic
4. Select category
5. Leave status as "Backlog"

**Mobile Quick Add:**
1. Open Notion app
2. Navigate to database
3. Tap "+" button
4. Type topic in title
5. Tap properties icon
6. Set category
7. Done!

**From Template:**
Create reusable templates for common types:

**Personal Story Template:**
- Category: Personal Anecdote
- Source: [Your Name]
- Status: Backlog
- Just fill in: Topic + Notes

**Friend Suggestion Template:**
- Source: Friend Suggestion
- Status: Backlog
- Fill in: Topic + Who suggested

---

## 🔄 Integration with Automation

### Current Integration Points

**1. Weekly Topic Refresh**
```python
# topic_scraper.py → topic_scorer.py → Notion
weekly_topic_refresh.py
  └─ Writes scored topics directly to Notion
  └─ No manual copy/paste needed!
```

**2. Episode Processing**
```python
# After episode is processed
main.py latest
  └─ Detects discussed topics
  └─ Updates Notion: Backlog → Published
  └─ Adds episode number
```

### Future Enhancements (Coming Soon)

**3. Episode Planning Assistant**
```python
# Suggests balanced episode from Notion
notion_episode_planner.py
  └─ Reads topics from Notion
  └─ Suggests optimal mix by category
  └─ Auto-creates episode page
```

**4. Analytics Dashboard**
```python
# Track what's working
notion_analytics.py
  └─ Which categories you use most
  └─ Average score of picked topics
  └─ Topics aging in backlog
```

---

## 📱 Mobile Usage Tips

### iOS/Android Notion App

**Add Topics On-the-Go:**
1. Random idea hits → Open Notion app
2. Quick tap "+" in database
3. Type topic
4. Save
5. Done in 10 seconds

**During Conversations:**
Friend: "You should talk about X"
→ Pull out phone
→ Add to Notion
→ Tag with "Friend Suggestion"
→ Won't forget

**Widgets (iOS):**
Add Notion widget to home screen:
- Shows "Ready to Record" count
- Tap to open database
- Quick access

### Siri Shortcuts (iOS)

Create shortcut: "Add podcast topic"
→ Asks for topic
→ Creates in Notion
→ Hands-free entry

---

## 🎯 Advanced Features

### Formulas

**Days in Backlog:**
```
dateBetween(now(), prop("Date Added"), "days")
```
→ See how long topics have been waiting

**Should Record:**
```
and(
  prop("Status") == "Backlog",
  prop("Score") >= 7,
  prop("Days in Backlog") < 60
)
```
→ Auto-flag topics to use soon

### Relations

**Link to Episodes:**
Create separate "Episodes" database:
- Episode Number
- Title
- Date Recorded
- Topics (relation to Topic Bank)

→ Click episode to see all topics discussed
→ Click topic to see which episode it was in

### Rollups

**Category Performance:**
In Episodes database:
- Topics Count (rollup count)
- Avg Topic Score (rollup average)
→ See which categories perform best

---

## 🔧 Troubleshooting

### "Invalid API key"
→ Check NOTION_API_KEY in `.env`
→ Must start with `secret_`

### "Database not found"
→ Share database with integration
→ Check NOTION_DATABASE_ID is correct

### "Properties don't match"
→ Ensure database has all required properties
→ Names must match exactly (case-sensitive)

### Topics not appearing
→ Check filter on your view
→ Make sure status is correct

### Migration failed
→ Check error message
→ Common: Rate limits (wait 1 min, retry)
→ Check network connection

---

## 💰 Notion Pricing

**What You Need:**
- **Personal Plan**: **FREE**
  - Unlimited pages
  - Unlimited blocks
  - API access included
  - Perfect for solo podcasters

**If You Have Team:**
- **Team Plan**: $8/month per person
  - Collaboration features
  - Admin tools
  - Priority support

**For This Use Case: FREE plan is perfect!**

---

## 📊 Example Workspace Structure

```
📁 Fake Problems Podcast
  ├── 📊 Topic Bank (Database)
  │   ├── 📋 All Topics (Table)
  │   ├── ⭐ Ready to Record (Filtered Table)
  │   ├── 📌 Episode Planning (Kanban)
  │   ├── 🎨 By Category (Gallery)
  │   └── 📅 This Week (Calendar)
  │
  ├── 📊 Episodes (Database) [Optional]
  │   ├── 📋 All Episodes
  │   ├── 📊 Analytics
  │   └── 📅 Schedule
  │
  ├── 📄 Episode Templates
  │   ├── Standard Episode
  │   ├── Special Episode
  │   └── Solo Episode
  │
  └── 📄 Resources
      ├── Topic Curation Guide
      ├── Recording Checklist
      └── Distribution Checklist
```

---

## 🎓 Pro Tips

### 1. Use Templates
Create templates for:
- Episode planning
- Personal story topics
- Friend suggestions
→ One-click adding

### 2. Inline Databases
Embed database in episode pages:
- See relevant topics
- Check them off live
- No switching between pages

### 3. Linked Databases
Same database, multiple locations:
- Weekly planning page
- Recording prep page
- Always in sync

### 4. Comments & Mentions
- Comment on topics: "This is gold!"
- @mention co-hosts: "@Joey remember when..."
- Collaborate asynchronously

### 5. Archive Old Topics
- Create "Archive" status
- Move stale topics (>90 days, score <6)
- Keeps main list fresh

---

## 📈 Success Metrics

After using Notion for 1 month, you should see:

**Efficiency:**
- ✅ Episode planning: 30 min → 5 min
- ✅ Topic brainstorming: 2 hours → 0 hours
- ✅ Forgetting topics: Common → Never

**Quality:**
- ✅ Average topic score: Increased
- ✅ Category balance: Improved
- ✅ Repeated topics: Eliminated

**Growth:**
- ✅ More shareable content
- ✅ Better clip titles
- ✅ Higher engagement

---

## 🆘 Need Help?

1. **Notion Docs**: https://www.notion.so/help/guides
2. **API Docs**: https://developers.notion.com
3. **Community**: https://www.notion.so/community

---

## ✅ Setup Checklist

Before you start, make sure you have:

- [ ] Notion account created
- [ ] Integration created (got API key)
- [ ] Database created with all properties
- [ ] Database shared with integration
- [ ] Database ID copied to `.env`
- [ ] API key in `.env`
- [ ] Required views created
- [ ] Migration script tested

**Ready to migrate:** `python notion_integration.py`

---

**Your podcast just got a proper topic management system!** 🎉

No more Google Docs. No more manual tracking. Just smart, automated topic curation powered by Notion + AI.
