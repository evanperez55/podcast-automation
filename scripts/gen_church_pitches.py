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
        "flags": [
            "STALE_FEED: last episode Oct 2025 - verify church is still active before sending"
        ],
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
        "flags": [
            "SUBSPLASH_HOST: may already use Pulpit AI - position as complement (SEO/transcript), not replacement"
        ],
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
    # ===== Batch 2 added 2026-04-27 (20 prospects for Wed/Thu sends) =====
    {
        "slug": "christ-community-franklin-tn",
        "church_name": "Christ Community Church",
        "pastor_name": "Randy Lovelace",
        "first_name": "Randy",
        "city": "Franklin, TN",
        "contact_hint": "christcommunity.org/contact, info@christcommunity.org guess, or Apple Podcasts listing id1382431493",
        "ep_count": 477,
        "angle": "seo_vs_pulpit",
        "positioning": "Christ Community has 477 sermons archived on Simplecast - a decade of careful PCA Reformed teaching with 4.8/5 reviews from listeners. Franklin is an affluent, tech-engaged demographic that searches Google before they ever walk into a church; the same back catalog could become a searchable transcript library and a year-plus of YouTube Shorts without recording a single new sermon.",
        "tier": 1,
        "flags": ["PCA_REFORMED: tech-receptive but theologically careful"],
    },
    {
        "slug": "north-village-church-austin",
        "church_name": "North Village Church",
        "pastor_name": "Michael Dennis",
        "first_name": "Michael",
        "city": "Austin, TX",
        "contact_hint": "northvillagechurch.com/contact form, address 2203 W Anderson Ln Austin TX 78757",
        "ep_count": 200,
        "angle": "time_saving",
        "positioning": "North Village launched the sermon podcast on Anchor and has been steadily publishing - exactly the stage where a content system pays back fastest. Most Austin nondenoms this size run social through a volunteer or comms-as-a-side-job. This pipeline turns 4-6 hours of post-production into 5 minutes, so whoever is currently doing this can keep doing it without burning out.",
        "tier": 1,
        "flags": [
            "EP_COUNT_ESTIMATED: not directly verified, using ~200 as anchor.fm midsize default"
        ],
    },
    {
        "slug": "doxology-bible-church",
        "church_name": "Doxology Bible Church",
        "pastor_name": "Pastor",
        "first_name": "there",
        "city": "Fort Worth, TX",
        "contact_hint": "doxology.church contact form, info@doxology.church (guess), or Buzzsprout listing 254230",
        "ep_count": 1308,
        "angle": "growth_seo",
        "positioning": "Doxology Bible has 1,308 sermons on Buzzsprout - one of the deepest podcast archives of any church in the DFW metro. The 'one church, multiple unique congregations' model means each campus is teaching the same material to different audiences; that is a content-multiplication opportunity built into how you already operate. Transcript pages on doxology.church plus a YouTube Shorts catalog from your back-catalog would put 13 years of teaching in front of every Fort Worth Google search.",
        "tier": 1,
        "flags": [
            "NEEDS_PASTOR_NAME",
            "NEEDS_EMAIL: try info@doxology.church or contact form",
        ],
    },
    {
        "slug": "park-church-denver",
        "church_name": "Park Church",
        "pastor_name": "Pastor",
        "first_name": "there",
        "city": "Denver, CO",
        "contact_hint": "renew@parkchurchdenver.org (from RSS), or parkchurch.org staff page",
        "ep_count": 1273,
        "angle": "growth_seo",
        "positioning": "Park Church has 1,273 sermons on the website - one of the deepest church podcast archives in the Mountain West. All of that teaching currently lives in audio files Google cannot search. Converting that archive to transcript pages plus a YouTube Shorts catalog from the existing recordings would put Park Church in front of every Denver-area Google search for the questions you have already answered.",
        "tier": 1,
        "flags": [],
    },
    {
        "slug": "northside-church-of-christ-wichita",
        "church_name": "Northside Church of Christ",
        "pastor_name": "Pastor",
        "first_name": "there",
        "city": "Wichita, KS",
        "contact_hint": "office@northsidecoc.org (from RSS)",
        "ep_count": 1207,
        "angle": "growth_seo",
        "positioning": "Northside has 1,207 sermons archived on Sermon.net - Churches of Christ rarely have the staff capacity to repurpose a content library that deep. Wichita is not flooded with church podcasts, so a transcript-page library on northsidecoc.org would dominate local search for almost any teaching topic. The clips and YouTube Shorts come essentially for free from the recordings already made.",
        "tier": 2,
        "flags": [
            "COC_TRADITIONAL: Church of Christ tradition may be cautious about clip strategy"
        ],
    },
    {
        "slug": "pacific-crossroads-church-la",
        "church_name": "Pacific Crossroads Church",
        "pastor_name": "Alex Watlington",
        "first_name": "Alex",
        "city": "Los Angeles, CA",
        "contact_hint": "info@pacificcrossroads.org (from RSS), pcc multi-site Santa Monica + Downtown LA",
        "ep_count": 1035,
        "angle": "growth_seo",
        "positioning": "Pacific Crossroads has 1,035 sermons on Planning Center - Reformed teaching across two LA campuses (Santa Monica + Downtown) is exactly the kind of teaching that travels well in Shorts format. That archive currently reaches the people who already know to look. Converting it to transcript pages plus a clip library from existing recordings would put thoughtful Reformed teaching in front of search-driven LA seekers who today never find it.",
        "tier": 1,
        "flags": ["PCA_REFORMED: tech-receptive but theologically careful"],
    },
    {
        "slug": "cornerstone-fellowship-bible-church",
        "church_name": "Cornerstone Fellowship Bible Church",
        "pastor_name": "Milton Vincent",
        "first_name": "Milton",
        "city": "Riverside, CA",
        "contact_hint": "jonathand@cornerstonebible.org (from RSS)",
        "ep_count": 995,
        "angle": "growth_seo",
        "positioning": "Cornerstone Fellowship has nearly 1,000 sermons in the archive - 30+ years of teaching from your pulpit. A Gospel Primer for Christians earned a national audience; the sermon library has not yet caught up to that reach. Transcript pages on cornerstonebible.org plus a clip catalog from the existing recordings would make the teaching as searchable and shareable as the book.",
        "tier": 1,
        "flags": [],
    },
    {
        "slug": "coram-deo-bible-church",
        "church_name": "Coram Deo Bible Church",
        "pastor_name": "Pastor",
        "first_name": "there",
        "city": "Carmel, IN",
        "contact_hint": "info@cdbible.org (from RSS), coramdeobible.church staff page",
        "ep_count": 981,
        "angle": "growth_seo",
        "positioning": "Coram Deo has 981 sermons archived and you are publishing every week without missing a beat. Carmel is a tech-engaged demographic that uses Google before they ever walk into a church. Right now that 981-sermon library is not searchable on Google; converting it to transcript pages plus a YouTube Shorts catalog would put your teaching in front of everyone in the Indianapolis metro searching for an answer at 2am.",
        "tier": 1,
        "flags": [],
    },
    {
        "slug": "trinity-baptist-church-nashua",
        "church_name": "Trinity Baptist Church",
        "pastor_name": "Pastor",
        "first_name": "there",
        "city": "Nashua, NH",
        "contact_hint": "admin@trinity-baptist.org (from RSS)",
        "ep_count": 934,
        "angle": "growth_seo",
        "positioning": "Trinity Baptist has 934 sermons archived - a deep teaching library for any New Hampshire church. The Northeast does not have many evangelical podcasts that come up in search; transcript pages from your existing archive plus a YouTube Shorts catalog would quietly dominate Google for every doctrinal topic you have already preached on, without recording a single new sermon.",
        "tier": 1,
        "flags": [],
    },
    {
        "slug": "go-church",
        "church_name": "GO Church",
        "pastor_name": "Pastor",
        "first_name": "there",
        "city": "Atlanta, GA",
        "contact_hint": "marketing@mygochurch.com (from RSS) - note: comms-aware church",
        "ep_count": 891,
        "angle": "growth_seo",
        "positioning": "GO Church has 891 sermons across DC and Atlanta campuses - and the marketing@ email tells me you already think about content strategy. What this pipeline adds to what you are already doing: searchable transcript pages on mygochurch.com, plus 5x the per-platform output from each Sunday. If clips and blog posts already happen, this turns 4-6 hours per sermon into 5 minutes.",
        "tier": 1,
        "flags": [
            "MARKETING_EMAIL: comms-aware church - tone must acknowledge their existing strategy, not assume they have nothing"
        ],
    },
    {
        "slug": "the-tree-church-lancaster",
        "church_name": "The Tree Church",
        "pastor_name": "Matthew Johnson",
        "first_name": "Matthew",
        "city": "Lancaster, OH",
        "contact_hint": "info@thetree.church (from RSS), formerly Lancaster Community Church",
        "ep_count": 873,
        "angle": "growth_seo",
        "positioning": "The Tree has 873 sermons archived going back to your Lancaster Community Church days - over a decade of teaching that lives mostly as audio. Lancaster is not crowded with church podcasts, so a transcript library on thetree.church would turn 'I am searching for a church in Lancaster' into 'I found a Tree Church sermon that answered my question.' Free for them, organic SEO for you.",
        "tier": 2,
        "flags": [],
    },
    {
        "slug": "high-point-church-madison",
        "church_name": "High Point Church",
        "pastor_name": "Pastor",
        "first_name": "there",
        "city": "Madison, WI",
        "contact_hint": "info@highpointchurch.org (from RSS)",
        "ep_count": 858,
        "angle": "growth_seo",
        "positioning": "High Point has 858 sermons archived and you are still publishing every week. Madison is a high-density university town where most spiritual searching happens on Google before it ever happens in a building. Right now your archive is invisible to that search; converting it to transcript pages plus a YouTube Shorts catalog would put your teaching in front of UW students answering their own questions at 2am.",
        "tier": 1,
        "flags": [],
    },
    {
        "slug": "north-wake-church",
        "church_name": "North Wake Church",
        "pastor_name": "Carson Cobb",
        "first_name": "Carson",
        "city": "Wake Forest, NC",
        "contact_hint": "tech@northwake.com (from RSS)",
        "ep_count": 855,
        "angle": "growth_seo",
        "positioning": "North Wake has 855 sermons in the archive - and the Branchcast hosting tells me y'all pay attention to platform choice. The Triangle is a tech-engaged region with strong organic search behavior; turning your archive into transcript pages on northwake.com plus a YouTube Shorts catalog would put your teaching where Wake County is actually looking. Same recordings, 5x the surface area.",
        "tier": 1,
        "flags": [],
    },
    {
        "slug": "first-family-church-ankeny",
        "church_name": "First Family Church",
        "pastor_name": "Pastor",
        "first_name": "there",
        "city": "Ankeny, IA",
        "contact_hint": "info@firstfamily.church (from RSS), 3-campus church (Ankeny, Carlisle, Lamoni)",
        "ep_count": 837,
        "angle": "growth_seo",
        "positioning": "First Family has 837 sermons across three campuses (Ankeny, Carlisle, Lamoni) - and Iowa is exactly the market where a deep, searchable teaching library wins because nothing else in the state does it. Transcript pages on firstfamily.church plus YouTube Shorts from your back-catalog would put First Family in front of every Iowa Google search for the questions you have already answered.",
        "tier": 1,
        "flags": [],
    },
    {
        "slug": "cornerstone-church-cefc",
        "church_name": "Cornerstone Church",
        "pastor_name": "Pastor",
        "first_name": "there",
        "city": "VERIFY_CITY",
        "contact_hint": "cefc@cornerstonechurches.org (from RSS) - city not yet identified, check anchor.fm/cornerstonechurches feed metadata",
        "ep_count": 798,
        "angle": "growth_seo",
        "positioning": "Cornerstone has 798 sermons on the podcast - and Anchor's free hosting suggests budget is a real constraint. That is exactly the case where automation pays back fastest: the same recordings you already produce become 5x the content output, with zero additional cost. Searchable transcripts plus a YouTube Shorts catalog without paying for new tools or new staff.",
        "tier": 2,
        "flags": [
            "NEEDS_CITY: identify location before sending - check anchor.fm/cornerstonechurches metadata or website"
        ],
    },
    {
        "slug": "denton-church-of-christ",
        "church_name": "Denton Church of Christ",
        "pastor_name": "Pastor",
        "first_name": "there",
        "city": "Denton, TX",
        "contact_hint": "podcast@dentonchurchofchrist.org (from RSS)",
        "ep_count": 795,
        "angle": "growth_seo",
        "positioning": "Denton CoC has 795 sermons archived - one of the most consistent COC podcast archives in DFW. CoC churches rarely have the media bandwidth to multiply a content library that deep, and Denton is a college town where spiritual questions land on Google first. Transcript pages on dentonchurchofchrist.org plus a YouTube Shorts catalog from your back-catalog would put your teaching where UNT students are actually searching.",
        "tier": 1,
        "flags": ["COC_TRADITIONAL"],
    },
    {
        "slug": "imago-dei-church-raleigh",
        "church_name": "Imago Dei Church",
        "pastor_name": "Tony Merida",
        "first_name": "Tony",
        "city": "Raleigh, NC",
        "contact_hint": "idcworship@gmail.com (from RSS) - note: high-profile pastor, may use staff filter",
        "ep_count": 766,
        "angle": "growth_seo",
        "positioning": "Imago Dei has 766 sermons archived from your teaching - and the Gospel Coalition audience already follows the writing. The teaching ministry has not caught up to that reach yet. Transcript pages on idcraleigh.com plus a YouTube Shorts catalog would turn the existing sermon library into the same kind of searchable, shareable resource the books already are - same teaching, where readers and seekers actually look.",
        "tier": 1,
        "flags": [
            "NOTABLE_PASTOR: Tony Merida is published author + Gospel Coalition contributor - may use staff filter, expect slower reply"
        ],
    },
    {
        "slug": "faith-baptist-church-fbcnet",
        "church_name": "Faith Baptist Church",
        "pastor_name": "Pastor",
        "first_name": "there",
        "city": "VERIFY_CITY",
        "contact_hint": "webmaster@fbcnet.org (from RSS) - location not yet confirmed, check fbcnet.org",
        "ep_count": 850,
        "angle": "seo_vs_pulpit",
        "positioning": "Faith Baptist has 850 sermons on Subsplash - which means Pulpit AI for clip generation is probably already on the table. I am not pitching a Pulpit replacement. What this adds: searchable transcript pages on the church website that Pulpit does not produce. Every sermon becomes a Google-indexable piece of content for the doctrinal questions you have already preached on.",
        "tier": 1,
        "flags": [
            "SUBSPLASH_HOST: position as SEO complement to Pulpit AI",
            "NEEDS_CITY: verify location before sending",
        ],
    },
    {
        "slug": "emergence-church-nj",
        "church_name": "Emergence Church",
        "pastor_name": "Steve Hawthorne",
        "first_name": "Steve",
        "city": "New Jersey",
        "contact_hint": "Steve.hawthorne@emergencenj.org (from RSS) - direct lead pastor email",
        "ep_count": 791,
        "angle": "seo_vs_pulpit",
        "positioning": "Emergence has 791 sermons on Subsplash - so if Pulpit AI is already in the toolkit, great; I am not pitching a replacement. What this adds: searchable transcript pages on emergencenj.org. North Jersey runs on Google searches before church visits, and right now that 791-sermon archive is invisible to those searches. Transcripts plus a YouTube Shorts catalog from existing recordings turns that around.",
        "tier": 1,
        "flags": [
            "SUBSPLASH_HOST: position as SEO complement to Pulpit AI",
            "DIRECT_PASTOR_EMAIL: Steve.hawthorne@ is the lead pastor - high-value direct contact",
        ],
    },
    {
        "slug": "park-cities-presbyterian-dallas",
        "church_name": "Park Cities Presbyterian Church",
        "pastor_name": "Pastor",
        "first_name": "there",
        "city": "Dallas, TX",
        "contact_hint": "webmaster@pcpc.org (from RSS), pcpc.org staff page for senior pastor",
        "ep_count": 1057,
        "angle": "growth_seo",
        "positioning": "Park Cities has 1,057 sermons on the podcast - and PCA Reformed teaching in the Dallas affluent demographic finds a tech-engaged audience that searches before they show up. The archive is currently invisible to that search; converting it to transcript pages on pcpc.org plus a YouTube Shorts catalog from existing recordings would put a decade of careful exposition in front of every DFW search for the doctrinal questions you have already answered.",
        "tier": 1,
        "flags": ["PCA_REFORMED: tech-receptive but theologically careful"],
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

[PREVIEW URL]

Or grab the raw files here: [GOOGLE DRIVE LINK]

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
- [ ] `outreach_prepare.py` substitutes both `[PREVIEW URL]` and `[GOOGLE DRIVE LINK]` automatically — no manual edit needed for either
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


def main(force: bool = False) -> None:
    for p in PROSPECTS:
        out = Path(f"demo/church-vertical/{p['slug']}/PITCH.md")
        if out.exists() and not force:
            print(
                f"SKIP (exists): {out} - pass --force to overwrite hand-edited content"
            )
            continue
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
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"WROTE: {out}")


if __name__ == "__main__":
    import sys

    main(force="--force" in sys.argv)
