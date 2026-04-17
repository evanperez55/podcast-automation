# Cottonwood Church - Outreach Pitch

**Prospect:** Cottonwood Church
**Slug:** cottonwood-church
**Contact:** Pastor (via guest services — weak) / **EMAIL: guestservices@cottonwood.org**
**Contact notes:** RESIZE FLAG: Cottonwood hosts 'Answers with Bayless Conley' broadcast — this is a LARGE church/media operation, not mid-size ICP. They likely already have professional media staff and Pulpit AI. Consider deprioritizing or pitching at a higher price tier. Phone: 714-947-5300.
**Episode referenced:** "Who Am I? The Identity That Refuses 'No' as an Answer" *(processed 2026-04-13)*
**Drive folder:** Upload from `output/cottonwood-church/ep_aHR0cHM6Ly9jZG4uc3Vic3BsYXNoLmNvbS9hdWRpb3MvSDhCSlROLzRlNjViOGQ4LTA2ZDItNDc1Yi05ZmFkLTczZDcyNzU0NmFmZC9hdWRpby5tcDM_20260413_204010/`
**Status:** Skeleton - needs (1) episode processed, (2) contact email found, (3) Drive link before sending
**Angle chosen:** seo_vs_pulpit
**Flags:**
- SUBSPLASH_HOST: may already use Pulpit AI - position as complement

---

## Email

**Subject:** A few things I made from Sunday's sermon at Cottonwood

Hi,

I came across Cottonwood's feed while looking for teaching podcasts to listen to this week, and ended up on "Who Am I? The Identity That Refuses 'No' as an Answer." The line about faith unsettling your comfort zone — and treating that unsettling as the point, not a failure mode — was what stayed with me.

Quick context on who I am: I'm Evan, based in Milwaukee — I built a system that takes a sermon recording and turns it into clips, a blog post, captions, and a full transcript. I've been running it for a comedy podcast I host, and it adapted well to long-form teaching. I'm reaching out to 10 churches this month to see if it's useful — no pitch past this email, the files below are yours either way.

[GOOGLE DRIVE LINK]

Inside:
- 5 short vertical clips with burned-in captions (for folks in your congregation who mostly scroll socials)
- A devotional-style blog post with verified scripture references
- Social captions written per platform
- Chapter markers for the full sermon
- A searchable transcript of the whole sermon
- Thumbnail and quote cards

The clip I'd lead with is "You Are Who God Says You Are" at 4:41–5:28 — the "what if your worth was declared by God?" hook does its job in the first 2 seconds, and the clip carries one complete scriptural moment.

One thing worth noting: if you're already using a clip tool, no worries — the thing most of those don't produce is a searchable transcript page on your own site. Those are what put your teaching in front of someone in Orange County searching scripture questions midweek. You may already have someone on this; if so, this is just a free asset for them. The files are yours, and I'll delete my copies after you confirm you have them if you'd rather I not keep anything.

If there's a 10-minute window sometime in the next couple weeks to talk, I'd love it. Otherwise I'll just send the next batch when it's ready — no follow-up pressure.

---

## Follow-Up Email (send 4-5 days later if no response)

**Subject:** Re: Made these from your "Who Am I? The Identity That Refuses 'No' as an Answer" sermon

Hey there,

Quick follow-up - I know church weeks are busy. Here are the clips in case the link got buried:

1. You Are Who God Says You Are (0:47): [direct link]
2. God Won't Take No for an Answer (0:49): [direct link]
3. Finding Joy in Your Treasure (0:46): [direct link]
4. Brokenness Is Strength, Not Weakness (0:50): [direct link]
5. You Are a Gift — Not Just a Resource (0:35): [direct link]

These are ready to post - just download and upload to YouTube Shorts or Instagram Reels. No editing needed.

Also: I checked, and Cottonwood Church doesn't have searchable sermon transcripts on your website. That means Google can't index any of the teaching you've delivered. With 52 sermons a year and 156 sermons already archived, you're sitting on a major SEO opportunity that most churches miss.

Happy to walk through it on a quick call, or I can just process the next few sermons and send them over.

Evan

---

## Pre-Send Checklist

- [x] Episode processed: ep_aHR0cHM6Ly9jZG4uc3Vic3BsYXNoLmNvbS9hdWRpb3MvSDhCSlROLzRlNjViOGQ4LTA2ZDItNDc1Yi05ZmFkLTczZDcyNzU0NmFmZC9hdWRpby5tcDM_20260413_204010
- [ ] Read `output/cottonwood-church/<ep_dir>/*_analysis.json` and pick lead clip
- [ ] Fill in all `{{}}` placeholders above using analysis output
- [x] Contact email resolved: guestservices@cottonwood.org (church website or Apple Podcasts listing)
- [ ] Upload clip `*_subtitle.mp4` files + blog post + thumbnail + quote cards to Google Drive
- [ ] Get shareable Drive link, replace `[GOOGLE DRIVE LINK]` above
- [ ] Get per-clip direct links, replace `[direct link]` entries in follow-up
- [ ] Update outreach tracker with email: `uv run main.py outreach update cottonwood-church contact_email=<email>`
- [ ] Send Tue-Thu morning (10am-2pm ET for best B2B open rates)
- [ ] Mark contacted: `uv run main.py outreach update cottonwood-church contacted`
- [ ] Calendar reminder: follow up in 4-5 days if no response

---

## Context

- **Archive size:** 156 episodes
- **RSS feed:** see `clients/cottonwood-church.yaml`
- **Tier:** 1
- **Why this angle:** Hosted on Subsplash, may already use Pulpit AI. Pitch positions us as complement (SEO transcripts) not replacement (clips).
