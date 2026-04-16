# Harbor Rock Tabernacle - Outreach Pitch

**Prospect:** Harbor Rock Tabernacle
**Slug:** harbor-rock-tabernacle
**Contact:** Pastor Paul Rhoads (Lead Pastor) / **EMAIL: paul@harborrock.org**
**Contact notes:** DIRECT — lead pastor's email. Phone: 262-633-3206. Also info@harborrock.org available as fallback.
**Episode referenced:** "Why the Tomb Was Empty but the Crowd Wasn't" *(processed 2026-04-13)*
**Drive folder:** Upload from `output/harbor-rock-tabernacle/ep_773/`
**Status:** Skeleton - needs (1) episode processed, (2) contact email found, (3) Drive link before sending
**Angle chosen:** growth_seo


---

## Email

**Subject:** Made these from your "Why the Tomb Was Empty but the Crowd Wasn't" sermon - took 5 minutes

Hey there,

I listened to "Why the Tomb Was Empty but the Crowd Wasn't" this week - the part that grabbed me was "If even Jesus’ closest friends doubted his resurrection, your doubts are just part of the journey—not a failure.". That's the kind of teaching that deserves to reach people beyond Sunday morning at Harbor Rock Tabernacle.

I ran it through my automation pipeline and here's what came out in about 5 minutes - no manual editing:

[GOOGLE DRIVE LINK]

Inside you'll find:
- 5 vertical clips with burned-in subtitles (ready for YouTube Shorts / Instagram Reels)
- A devotional-style blog post with full scripture references
- Social captions written per platform (YouTube, Instagram, Facebook, Twitter)
- Chapter markers for the full sermon
- A complete searchable transcript
- Thumbnail and quote cards ready to post

The clip I'd lead with is "No Witnesses at the Greatest Moment Ever" (4:28-5:05). This clip highlights a striking and little-considered aspect of the resurrection: that no witnesses were there, underscoring the personal nature of salvation. The hook "Nobody was there when Jesus rose" works in the first 2 seconds.

Here's why this matters for Harbor Rock Tabernacle: Harbor Rock has 815 sermons on Podomatic - that is one of the deepest church podcast archives I have seen in Wisconsin. All of that teaching is currently locked inside audio files Google cannot search. Converting that archive to transcript pages + a backlog of YouTube Shorts would transform your digital presence overnight, without recording a single new sermon.

**The math:** 52 sermons/year = 52 blog posts, 260+ clips, 52 transcript pages, and hundreds of social posts. Doing this manually takes 4-6 hours per sermon. My pipeline does it in 5 minutes.

I'd like to process your next 4 sermons completely free. No strings - you keep everything. If you like the output, we talk about automating the whole thing. If not, you've got a month of free content for Harbor Rock Tabernacle.

Would it be easier to jump on a 10-minute call this week, or should I just send the next batch when it's ready?

Evan Perez
https://neurovai.org | evan@neurovai.org

---

## Follow-Up Email (send 4-5 days later if no response)

**Subject:** Re: Made these from your "Why the Tomb Was Empty but the Crowd Wasn't" sermon

Hey there,

Quick follow-up - I know church weeks are busy. Here are the clips in case the link got buried:

1. No Witnesses at the Greatest Moment Ever (0:37): [direct link]
2. Even the Closest Disciples Doubted (0:30): [direct link]
3. 5 Reasons Why People Doubt Jesus (0:27): [direct link]
4. 3 Unshakable Facts About the Resurrection (0:57): [direct link]
5. The Stone Rolled Away: A Symbol of Freedom (0:50): [direct link]

These are ready to post - just download and upload to YouTube Shorts or Instagram Reels. No editing needed.

Also: I checked, and Harbor Rock Tabernacle doesn't have searchable sermon transcripts on your website. That means Google can't index any of the teaching you've delivered. With 52 sermons a year and 815 sermons already archived, you're sitting on a major SEO opportunity that most churches miss.

Happy to walk through it on a quick call, or I can just process the next few sermons and send them over.

Evan

---

## Pre-Send Checklist

- [x] Episode processed: ep_773
- [ ] Read `output/harbor-rock-tabernacle/<ep_dir>/*_analysis.json` and pick lead clip
- [ ] Fill in all `{{}}` placeholders above using analysis output
- [x] Contact email resolved: paul@harborrock.org
- [ ] Upload clip `*_subtitle.mp4` files + blog post + thumbnail + quote cards to Google Drive
- [ ] Get shareable Drive link, replace `[GOOGLE DRIVE LINK]` above
- [ ] Get per-clip direct links, replace `[direct link]` entries in follow-up
- [ ] Update outreach tracker with email: `uv run main.py outreach update harbor-rock-tabernacle contact_email=<email>`
- [ ] Send Tue-Thu morning (10am-2pm ET for best B2B open rates)
- [ ] Mark contacted: `uv run main.py outreach update harbor-rock-tabernacle contacted`
- [ ] Calendar reminder: follow up in 4-5 days if no response

---

## Context

- **Archive size:** 815 episodes
- **RSS feed:** see `clients/harbor-rock-tabernacle.yaml`
- **Tier:** 1
- **Why this angle:** Established archive with clear SEO/YouTube upside. Framing: maximize existing investment, not fill a gap.
