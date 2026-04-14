# Metro Tab Church - Outreach Pitch

**Prospect:** Metro Tab Church
**Slug:** metro-tab-church
**Contact:** Dr. Steve Ball (via info) / **EMAIL: info@metrotab.net**
**Contact notes:** General info inbox. Phone: 423-894-3377. May need to ask for comms director by name in the email.
**Episode referenced:** "{{SERMON_TITLE}}" *(processed TBD)*
**Drive folder:** Upload from `output/metro-tab-church/{{EP_DIR}}/`
**Status:** Skeleton - needs (1) episode processed, (2) contact email found, (3) Drive link before sending
**Angle chosen:** growth_seo


---

## Email

**Subject:** Made these from your "{{SERMON_TITLE}}" sermon - took 5 minutes

Hey Steve,

I listened to "{{SERMON_TITLE}}" this week - {{SPECIFIC_MOMENT_REFERENCE}}. That's the kind of teaching that deserves to reach people beyond Sunday morning at Metro Tab Church.

I ran it through my automation pipeline and here's what came out in about 5 minutes - no manual editing:

[GOOGLE DRIVE LINK]

Inside you'll find:
- {{NUM_CLIPS}} vertical clips with burned-in subtitles (ready for YouTube Shorts / Instagram Reels)
- A devotional-style blog post with full scripture references
- Social captions written per platform (YouTube, Instagram, Facebook, Twitter)
- Chapter markers for the full sermon
- A complete searchable transcript
- Thumbnail and quote cards ready to post

The clip I'd lead with is "{{BEST_CLIP_TITLE}}" ({{CLIP_TIMESTAMP}}). {{WHY_THIS_CLIP_WORKS}}.

Here's why this matters for Metro Tab Church: Metro Tab has 315 sermons on Podbean - that is a massive content library that no one in Chattanooga knows they can search. Transcripts would turn every one of those into a Google-indexable page. YouTube Shorts from your existing library = months of new discovery with zero new recording work.

**The math:** 52 sermons/year = 52 blog posts, 260+ clips, 52 transcript pages, and hundreds of social posts. Doing this manually takes 4-6 hours per sermon. My pipeline does it in 5 minutes.

I'd like to process your next 4 sermons completely free. No strings - you keep everything. If you like the output, we talk about automating the whole thing. If not, you've got a month of free content for Metro Tab Church.

Would it be easier to jump on a 10-minute call this week, or should I just send the next batch when it's ready?

Evan Perez
https://neurovai.org | evan@neurovai.org

---

## Follow-Up Email (send 4-5 days later if no response)

**Subject:** Re: Made these from your "{{SERMON_TITLE}}" sermon

Hey Steve,

Quick follow-up - I know church weeks are busy. Here are the clips in case the link got buried:

1. {{CLIP_1_TITLE}} ({{CLIP_1_DURATION}}): [direct link]
2. {{CLIP_2_TITLE}} ({{CLIP_2_DURATION}}): [direct link]
3. {{CLIP_3_TITLE}} ({{CLIP_3_DURATION}}): [direct link]
4. {{CLIP_4_TITLE}} ({{CLIP_4_DURATION}}): [direct link]
5. {{CLIP_5_TITLE}} ({{CLIP_5_DURATION}}): [direct link]

These are ready to post - just download and upload to YouTube Shorts or Instagram Reels. No editing needed.

Also: I checked, and Metro Tab Church doesn't have searchable sermon transcripts on your website. That means Google can't index any of the teaching you've delivered. With 52 sermons a year and 315 sermons already archived, you're sitting on a major SEO opportunity that most churches miss.

Happy to walk through it on a quick call, or I can just process the next few sermons and send them over.

Evan

---

## Pre-Send Checklist

- [ ] Process latest episode: `uv run main.py --client metro-tab-church latest --auto-approve`
- [ ] Read `output/metro-tab-church/<ep_dir>/*_analysis.json` and pick lead clip
- [ ] Fill in all `{{}}` placeholders above using analysis output
- [x] Contact email resolved: info@metrotab.net (metrotab.net staff page or phone (423) 894-3377)
- [ ] Upload clip `*_subtitle.mp4` files + blog post + thumbnail + quote cards to Google Drive
- [ ] Get shareable Drive link, replace `[GOOGLE DRIVE LINK]` above
- [ ] Get per-clip direct links, replace `[direct link]` entries in follow-up
- [ ] Update outreach tracker with email: `uv run main.py outreach update metro-tab-church contact_email=<email>`
- [ ] Send Tue-Thu morning (10am-2pm ET for best B2B open rates)
- [ ] Mark contacted: `uv run main.py outreach update metro-tab-church contacted`
- [ ] Calendar reminder: follow up in 4-5 days if no response

---

## Context

- **Archive size:** 315 episodes
- **RSS feed:** see `clients/metro-tab-church.yaml`
- **Tier:** 1
- **Why this angle:** Established archive with clear SEO/YouTube upside. Framing: maximize existing investment, not fill a gap.
