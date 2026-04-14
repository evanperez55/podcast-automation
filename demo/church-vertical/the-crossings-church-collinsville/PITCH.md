# The Crossings Church - Outreach Pitch

**Prospect:** The Crossings Church
**Slug:** the-crossings-church-collinsville
**Contact:** Pastor / Admin team / **EMAIL: admin@crossingscollinsville.com**
**Contact notes:** Site appears active despite Oct 2025 stale feed — restart angle is live. Phone: 636-442-2778.
**Episode referenced:** "Why Your Faith Can't Be Just a Feeling" *(processed TBD)*
**Drive folder:** Upload from `output/the-crossings-church-collinsville/ep_2025/`
**Status:** Skeleton - needs (1) episode processed, (2) contact email found, (3) Drive link before sending
**Angle chosen:** restart
**Flags:**
- STALE_FEED: last episode Oct 2025 - verify church is still active before sending

---

## Email

**Subject:** Made these from your "Why Your Faith Can't Be Just a Feeling" sermon - took 5 minutes

Hey there,

I listened to "Why Your Faith Can't Be Just a Feeling" this week - the reframe that faith isn't a feeling, it's loyalty — that lands harder than 90% of the James chapter 2 teaching that's out there. That's the kind of teaching that deserves to reach people beyond Sunday morning at The Crossings Church.

I ran it through my automation pipeline and here's what came out in about 5 minutes - no manual editing:

[GOOGLE DRIVE LINK]

Inside you'll find:
- 5 vertical clips with burned-in subtitles (ready for YouTube Shorts / Instagram Reels)
- A devotional-style blog post with full scripture references
- Social captions written per platform (YouTube, Instagram, Facebook, Twitter)
- Chapter markers for the full sermon
- A complete searchable transcript
- Thumbnail and quote cards ready to post

The clip I'd lead with is "Faith Isn't What You Think It Is" (8:00-8:30). It's 30 seconds, self-contained, and flips a cliché ('faith is just a feeling') into a Biblical counter-thesis. Perfect Shorts material — hook in the first word, payoff in under 30 seconds.

Here's why this matters for The Crossings Church: I noticed your podcast feed has not published since October 2025 - I do not know if that is an intentional pause or a capacity issue, but either way this might land at a useful moment. The reason churches stop publishing is almost never lack of sermons; it is the hours of post-production work that piles up until no one has time. My pipeline makes that 5 minutes instead of 4-6 hours - so if you want to restart, the bottleneck goes away.

**The math:** 52 sermons/year = 52 blog posts, 260+ clips, 52 transcript pages, and hundreds of social posts. Doing this manually takes 4-6 hours per sermon. My pipeline does it in 5 minutes.

I'd like to process your next 4 sermons completely free. No strings - you keep everything. If you like the output, we talk about automating the whole thing. If not, you've got a month of free content for The Crossings Church.

Would it be easier to jump on a 10-minute call this week, or should I just send the next batch when it's ready?

Evan Perez
https://neurovai.org | evan@neurovai.org

---

## Follow-Up Email (send 4-5 days later if no response)

**Subject:** Re: Made these from your "Why Your Faith Can't Be Just a Feeling" sermon

Hey there,

Quick follow-up - I know church weeks are busy. Here are the clips in case the link got buried:

1. Faith Isn't What You Think It Is (0:30): [direct link]
2. You Can't Serve Two Masters (0:45): [direct link]
3. Faith and Works: Both Matter (0:30): [direct link]
4. Faith Is Not Meant To Be Private (0:30): [direct link]
5. Why You Need To Focus On The Eternal (0:30): [direct link]

These are ready to post - just download and upload to YouTube Shorts or Instagram Reels. No editing needed.

Also: I checked, and The Crossings Church doesn't have searchable sermon transcripts on your website. That means Google can't index any of the teaching you've delivered. With 52 sermons a year and 79 sermons already archived, you're sitting on a major SEO opportunity that most churches miss.

Happy to walk through it on a quick call, or I can just process the next few sermons and send them over.

Evan

---

## Pre-Send Checklist

- [x] Episode processed: ep_2025
- [ ] Read `output/the-crossings-church-collinsville/<ep_dir>/*_analysis.json` and pick lead clip
- [ ] Fill in all `{{}}` placeholders above using analysis output
- [x] Contact email resolved: admin@crossingscollinsville.com or Apple Podcasts listing contact)
- [ ] Upload clip `*_subtitle.mp4` files + blog post + thumbnail + quote cards to Google Drive
- [ ] Get shareable Drive link, replace `[GOOGLE DRIVE LINK]` above
- [ ] Get per-clip direct links, replace `[direct link]` entries in follow-up
- [ ] Update outreach tracker with email: `uv run main.py outreach update the-crossings-church-collinsville contact_email=<email>`
- [ ] Send Tue-Thu morning (10am-2pm ET for best B2B open rates)
- [ ] Mark contacted: `uv run main.py outreach update the-crossings-church-collinsville contacted`
- [ ] Calendar reminder: follow up in 4-5 days if no response

---

## Context

- **Archive size:** 79 episodes
- **RSS feed:** see `clients/the-crossings-church-collinsville.yaml`
- **Tier:** 1
- **Why this angle:** Podcast feed is stale - this pitch acknowledges the pause and frames automation as the unblocker rather than pretending to have missed the gap.
