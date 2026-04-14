"""One-time script: generate pitch skeletons for church vertical prospects.

Reads from hardcoded PROSPECTS list and writes templated PITCH.md files.
Safe to re-run — overwrites existing skeletons.
"""
from pathlib import Path

PROSPECTS = [
    {
        "slug": "redeemer-city-church-tampa",
        "church_name": "Redeemer City Church",
        "pastor_name": "Mitch Kuhn",
        "first_name": "Mitch",
        "city": "Tampa",
        "contact_hint": "sermon.net profile, LinkedIn, or redeemertampa.com contact page",
        "ep_count": 483,
        "angle": "growth_seo",
        "positioning": "Redeemer has 483 sermons archived on Apple and Sermon.net - that is a decade of teaching that mostly lives as audio files right now. The investment is already made; what is missing is the multiplier. Transcripts on redeemertampa.com + YouTube Shorts would 7x your organic traffic without changing anything you are already doing.",
        "tier": 1,
        "flags": [],
    },
    {
        "slug": "christ-community-church-columbus",
        "church_name": "Christ Community Church",
        "pastor_name": "Kelli Wommack",
        "first_name": "Kelli",
        "city": "Columbus, GA",
        "contact_hint": "ccclive.org staff page, or Buzzsprout contact at buzzsprout.com/25550",
        "ep_count": 584,
        "angle": "growth_seo",
        "positioning": "Christ Community has 584 sermons in your Buzzsprout archive - that is an enormous back catalog and you just went through a pastoral transition. Fresh leadership + legacy content = the perfect window to relaunch the digital strategy. Every archived sermon becomes a searchable transcript page; every new Sunday becomes 5 clips.",
        "tier": 1,
        "flags": [],
    },
    {
        "slug": "metro-tab-church",
        "church_name": "Metro Tab Church",
        "pastor_name": "Dr. Steve Ball",
        "first_name": "Steve",
        "city": "Chattanooga",
        "contact_hint": "metrotab.net staff page or phone (423) 894-3377",
        "ep_count": 315,
        "angle": "growth_seo",
        "positioning": "Metro Tab has 315 sermons on Podbean - that is a massive content library that no one in Chattanooga knows they can search. Transcripts would turn every one of those into a Google-indexable page. YouTube Shorts from your existing library = months of new discovery with zero new recording work.",
        "tier": 1,
        "flags": [],
    },
    {
        "slug": "the-crossings-church-collinsville",
        "church_name": "The Crossings Church",
        "pastor_name": "Pastor",
        "first_name": "there",
        "city": "Collinsville, IL",
        "contact_hint": "crossingscollinsville.com (verify currently active) or Apple Podcasts listing contact",
        "ep_count": 79,
        "angle": "restart",
        "positioning": "I noticed your podcast feed has not published since October 2025 - I do not know if that is an intentional pause or a capacity issue, but either way this might land at a useful moment. The reason churches stop publishing is almost never lack of sermons; it is the hours of post-production work that piles up until no one has time. My pipeline makes that 5 minutes instead of 4-6 hours - so if you want to restart, the bottleneck goes away.",
        "tier": 1,
        "flags": ["STALE_FEED: last episode Oct 2025 - verify church is still active before sending"],
    },
    {
        "slug": "faith-bible-church-edmond",
        "church_name": "Faith Bible Church",
        "pastor_name": "Pastor",
        "first_name": "there",
        "city": "Edmond, OK",
        "contact_hint": "Subsplash app, church website, or Apple Podcasts listing",
        "ep_count": 1091,
        "angle": "seo_vs_pulpit",
        "positioning": "Faith Bible has 1,091 sermons on Subsplash - that is one of the deepest podcast archives of any church in Oklahoma. If you are already using Pulpit AI (Subsplash's clip tool), great - I am not here to replace it. What I do that Pulpit does not: searchable transcript pages on your website. Every sermon becomes a Google-indexable piece of content answering the exact question someone in Edmond is searching at 2am.",
        "tier": 1,
        "flags": ["SUBSPLASH_HOST: may already use Pulpit AI - position as complement (SEO/transcript), not replacement"],
    },
    {
        "slug": "life-bridge-church-green-bay",
        "church_name": "Life Bridge Church",
        "pastor_name": "Pastor",
        "first_name": "there",
        "city": "Green Bay",
        "contact_hint": "Apple Podcasts listing or church website",
        "ep_count": 100,
        "angle": "time_saving",
        "positioning": "Life Bridge launched the sermon podcast in 2024 - you are at the right stage to build a content system instead of doing this by hand. If you are like most churches this size, the social media is handled by a volunteer or the comms person as part of 10 other jobs. This pipeline takes the 4-6 hours per sermon down to 5 minutes - so no one has to choose between content and the other 10 jobs.",
        "tier": 1,
        "flags": [],
    },
    {
        "slug": "cottonwood-church",
        "church_name": "Cottonwood Church",
        "pastor_name": "Pastor",
        "first_name": "there",
        "city": "Los Alamitos (Orange County)",
        "contact_hint": "church website or Apple Podcasts listing",
        "ep_count": 156,
        "angle": "seo_vs_pulpit",
        "positioning": "Cottonwood has been on the podcast since 2010 - 156 sermons and counting. You are on Subsplash, which means you may already use Pulpit AI for clip generation. If so, great - I am not here to replace it. What I add that Pulpit does not: searchable transcript pages on your website. Every archived sermon becomes a Google-indexable piece of content - the difference between 'we have a podcast' and 'Orange County searches for Bible questions and finds Cottonwood.'",
        "tier": 1,
        "flags": ["SUBSPLASH_HOST: may already use Pulpit AI - position as complement"],
    },
    {
        "slug": "mercy-village-church",
        "church_name": "Mercy Village Church",
        "pastor_name": "Pastor",
        "first_name": "there",
        "city": "Barboursville, WV",
        "contact_hint": "church website or Apple Podcasts listing",
        "ep_count": 267,
        "angle": "stewardship_subsplash",
        "positioning": "Mercy Village describes itself as a small-town church - and small-town churches almost never have a dedicated media team, even when they have 267 sermons worth of teaching sitting on Subsplash. You are already recording every sermon and paying for Subsplash hosting; right now that investment produces one podcast episode per week. This pipeline turns the same recording into 5+ clips, a devotional blog post, a searchable transcript, and per-platform social captions - same input, 15x the output.",
        "tier": 1,
        "flags": ["SUBSPLASH_HOST: may already use Pulpit AI - position as complement"],
    },
    {
        "slug": "harbor-rock-tabernacle",
        "church_name": "Harbor Rock Tabernacle",
        "pastor_name": "Pastor",
        "first_name": "there",
        "city": "Racine, WI",
        "contact_hint": "Apple Podcasts listing or church website",
        "ep_count": 815,
        "angle": "growth_seo",
        "positioning": "Harbor Rock has 815 sermons on Podomatic - that is one of the deepest church podcast archives I have seen in Wisconsin. All of that teaching is currently locked inside audio files Google cannot search. Converting that archive to transcript pages + a backlog of YouTube Shorts would transform your digital presence overnight, without recording a single new sermon.",
        "tier": 1,
        "flags": [],
    },
    {
        "slug": "christ-community-church-johnson-city",
        "church_name": "Christ Community Church",
        "pastor_name": "Pastor",
        "first_name": "there",
        "city": "Johnson City, TN",
        "contact_hint": "Apple Podcasts listing or church website search",
        "ep_count": 565,
        "angle": "growth_seo",
        "positioning": "Christ Community has 565 sermons archived - East Tennessee churches with that kind of back catalog almost never have the media capacity to repurpose it. That is a decade of teaching that is currently invisible to anyone who did not already know your name. Transcript pages + YouTube Shorts would put your teaching in front of everyone in Johnson City searching for answers at 2am.",
        "tier": 2,
        "flags": [],
    },
]

ANGLE_RATIONALES = {
    "growth_seo": "Established archive with clear SEO/YouTube upside. Framing: maximize existing investment, not fill a gap.",
    "restart": "Podcast feed is stale - this pitch acknowledges the pause and frames automation as the unblocker rather than pretending to have missed the gap.",
    "seo_vs_pulpit": "Hosted on Subsplash, may already use Pulpit AI. Pitch positions us as complement (SEO transcripts) not replacement (clips).",
    "time_saving": "Newer podcast, likely volunteer-run. Time savings + automation speaks directly to comms bandwidth pain.",
    "stewardship_subsplash": "Self-described small-town church on Subsplash - budget/staff-constrained. Frame as stewardship of existing investment.",
}

TEMPLATE = """# {church_name} - Outreach Pitch

**Prospect:** {church_name}{tier_note}
**Slug:** {slug}
**Contact:** {pastor_name} / **EMAIL: TBD** - check: {contact_hint}
**Episode referenced:** "{{{{SERMON_TITLE}}}}" *(processed TBD)*
**Drive folder:** Upload from `output/{slug}/{{{{EP_DIR}}}}/`
**Status:** Skeleton - needs (1) episode processed, (2) contact email found, (3) Drive link before sending
**Angle chosen:** {angle}
{flags_block}

---

## Email

**Subject:** Made these from your "{{{{SERMON_TITLE}}}}" sermon - took 5 minutes

Hey {first_name},

I listened to "{{{{SERMON_TITLE}}}}" this week - {{{{SPECIFIC_MOMENT_REFERENCE}}}}. That's the kind of teaching that deserves to reach people beyond Sunday morning at {church_name}.

I ran it through my automation pipeline and here's what came out in about 5 minutes - no manual editing:

[GOOGLE DRIVE LINK]

Inside you'll find:
- {{{{NUM_CLIPS}}}} vertical clips with burned-in subtitles (ready for YouTube Shorts / Instagram Reels)
- A devotional-style blog post with full scripture references
- Social captions written per platform (YouTube, Instagram, Facebook, Twitter)
- Chapter markers for the full sermon
- A complete searchable transcript
- Thumbnail and quote cards ready to post

The clip I'd lead with is "{{{{BEST_CLIP_TITLE}}}}" ({{{{CLIP_TIMESTAMP}}}}). {{{{WHY_THIS_CLIP_WORKS}}}}.

Here's why this matters for {church_name}: {positioning}

**The math:** 52 sermons/year = 52 blog posts, 260+ clips, 52 transcript pages, and hundreds of social posts. Doing this manually takes 4-6 hours per sermon. My pipeline does it in 5 minutes.

I'd like to process your next 4 sermons completely free. No strings - you keep everything. If you like the output, we talk about automating the whole thing. If not, you've got a month of free content for {church_name}.

Would it be easier to jump on a 10-minute call this week, or should I just send the next batch when it's ready?

Evan Perez
https://neurovai.org | evan@neurovai.org

---

## Follow-Up Email (send 4-5 days later if no response)

**Subject:** Re: Made these from your "{{{{SERMON_TITLE}}}}" sermon

Hey {first_name},

Quick follow-up - I know church weeks are busy. Here are the clips in case the link got buried:

1. {{{{CLIP_1_TITLE}}}} ({{{{CLIP_1_DURATION}}}}): [direct link]
2. {{{{CLIP_2_TITLE}}}} ({{{{CLIP_2_DURATION}}}}): [direct link]
3. {{{{CLIP_3_TITLE}}}} ({{{{CLIP_3_DURATION}}}}): [direct link]
4. {{{{CLIP_4_TITLE}}}} ({{{{CLIP_4_DURATION}}}}): [direct link]
5. {{{{CLIP_5_TITLE}}}} ({{{{CLIP_5_DURATION}}}}): [direct link]

These are ready to post - just download and upload to YouTube Shorts or Instagram Reels. No editing needed.

Also: I checked, and {church_name} doesn't have searchable sermon transcripts on your website. That means Google can't index any of the teaching you've delivered. With 52 sermons a year and {ep_count} sermons already archived, you're sitting on a major SEO opportunity that most churches miss.

Happy to walk through it on a quick call, or I can just process the next few sermons and send them over.

Evan

---

## Pre-Send Checklist

- [ ] Process latest episode: `uv run main.py --client {slug} latest --auto-approve`
- [ ] Read `output/{slug}/<ep_dir>/*_analysis.json` and pick lead clip
- [ ] Fill in all `{{{{}}}}` placeholders above using analysis output
- [ ] Find {pastor_name} contact email ({contact_hint})
- [ ] Upload clip `*_subtitle.mp4` files + blog post + thumbnail + quote cards to Google Drive
- [ ] Get shareable Drive link, replace `[GOOGLE DRIVE LINK]` above
- [ ] Get per-clip direct links, replace `[direct link]` entries in follow-up
- [ ] Update outreach tracker with email: `uv run main.py outreach update {slug} contact_email=<email>`
- [ ] Send Tue-Thu morning (10am-2pm ET for best B2B open rates)
- [ ] Mark contacted: `uv run main.py outreach update {slug} contacted`
- [ ] Calendar reminder: follow up in 4-5 days if no response

---

## Context

- **Archive size:** {ep_count} episodes
- **RSS feed:** see `clients/{slug}.yaml`
- **Tier:** {tier}
- **Why this angle:** {angle_rationale}
"""


def main() -> None:
    for p in PROSPECTS:
        flags_md = ""
        if p["flags"]:
            flags_md = "**Flags:**\n" + "\n".join(f"- {f}" for f in p["flags"])
        tier_note = "" if p["tier"] == 1 else " *(Tier 2)*"
        text = TEMPLATE.format(
            church_name=p["church_name"],
            slug=p["slug"],
            pastor_name=p["pastor_name"],
            first_name=p["first_name"],
            city=p["city"],
            contact_hint=p["contact_hint"],
            ep_count=p["ep_count"],
            angle=p["angle"],
            positioning=p["positioning"],
            flags_block=flags_md,
            tier=p["tier"],
            tier_note=tier_note,
            angle_rationale=ANGLE_RATIONALES[p["angle"]],
        )
        out = Path(f"demo/church-vertical/{p['slug']}/PITCH.md")
        out.write_text(text, encoding="utf-8")
        print(f"WROTE: {out}")


if __name__ == "__main__":
    main()
