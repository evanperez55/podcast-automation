# The Crossings Church - Outreach Pitch

**Prospect:** The Crossings Church
**Slug:** the-crossings-church-collinsville
**Contact:** Pastor / Admin team / **EMAIL: admin@crossingscollinsville.com**
**Contact notes:** Site appears active despite Oct 2025 stale feed — restart angle is live. Phone: 636-442-2778.
**Episode referenced:** "Why Your Faith Can't Be Just a Feeling" *(processed 2026-04-13)*
**Drive folder:** Upload from `output/the-crossings-church-collinsville/ep_2025/`
**Status:** Skeleton - needs (1) episode processed, (2) contact email found, (3) Drive link before sending
**Angle chosen:** restart
**Flags:**
- STALE_FEED: last episode Oct 2025 - verify church is still active before sending

---

## Email

**Subject:** A few things I made from Sunday's sermon at The Crossings

Hi,

I came across The Crossings' feed while looking for teaching podcasts to listen to this week, and ended up on "Why Your Faith Can't Be Just a Feeling." The reframe that faith isn't a feeling, it's loyalty — that lands harder than a lot of the James 2 teaching that's out there.

Quick context on who I am: I'm Evan, based in Milwaukee — I built a system that takes a sermon recording and turns it into clips, a blog post, captions, and a full transcript. I've been running it for a comedy podcast I host, and it adapted well to long-form teaching. I'm reaching out to 10 churches this month to see if it's useful — no pitch past this email, the files below are yours either way.

[GOOGLE DRIVE LINK]

Inside:
- 5 short vertical clips with burned-in captions (for folks in your congregation who mostly scroll socials)
- A devotional-style blog post with verified scripture references
- Social captions written per platform
- Chapter markers for the full sermon
- A searchable transcript of the whole sermon
- Thumbnail and quote cards

The clip I'd lead with is "Faith Isn't What You Think It Is" at 8:00–8:30 — 30 seconds, self-contained, flips a cliché into a biblical counter-thesis. Hook in the first word.

One honest note: I noticed the podcast feed hasn't published since October 2025. No assumptions there — could be an intentional pause, could be capacity. Either way, the reason most churches stop publishing isn't the sermons themselves, it's the post-production pile-up. If that's the bottleneck and you want to pick it back up, I can keep doing this ongoing — transcripts people can search midweek, short clips, a weekly blog post. You may already have someone on this; if so, this is just a free asset for them. The files are yours, and I'll delete my copies after you confirm you have them if you'd rather I not keep anything.

If there's a 10-minute window sometime in the next couple weeks to talk, I'd love it. Otherwise I'll just send the next batch when it's ready — no follow-up pressure.

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
