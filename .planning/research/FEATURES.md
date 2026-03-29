# Feature Landscape: Client Acquisition & Outreach Tooling

**Domain:** Podcast production service — prospect discovery, pitch, and contact tracking
**Researched:** 2026-03-28
**Milestone:** v1.5 — First Paying Client
**Confidence:** MEDIUM

---

## Context

The pipeline is fully built and the demo packager (`package-demo` command) is shipped. The gap is
entirely go-to-market: finding the right podcast prospects, qualifying them, processing a demo with
their real audio, and converting them with a credible cold outreach pitch.

This research answers:
1. Where do you find small independent podcast prospects worth pitching?
2. What criteria disqualify or qualify a show as a good target?
3. What does a cold outreach pitch need to include to convert?
4. What does lightweight contact tracking look like for a solo outreach campaign?

Existing artifacts that feed into this:
- `demo_packager.py` + `package-demo` command — produces self-contained demo folder with HTML
  summary and DEMO.md narrative
- `templates/demo_summary.html.j2` — HTML summary template
- Per-client YAML configs already support genre-specific voice personas

---

## Table Stakes

Features without which the outreach effort cannot begin or will fail.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Prospect list (3-5 shows) | You cannot pitch zero people. Every other feature depends on this | LOW (research, not code) | Use Listen Notes API (free tier: 30 results/query, genre + episode count filters). Also: manual search on Apple Podcasts, Spotify by genre + scroll for small shows with 50-500 reviews |
| Prospect qualification criteria | Not every small podcast is a good target. Need filters to avoid wasting demo cycles on shows that will never pay | LOW (criteria doc, not code) | See qualification filter list below |
| Contact extraction from RSS | The `<itunes:email>` tag in the show's RSS feed is the most reliable contact point — more reliable than website forms | LOW (Python feedparser, already in deps) | Parse RSS, extract `itunes:owner/itunes:email` or `managingEditor`. Fall back to website scrape. Already have feedparser. |
| Email pitch template | Generic outreach fails. Template must lead with their show, open with value to them, and attach a tangible demo artifact | LOW (copywriting, not code) | See pitch template section. Personalization beats volume. |
| Demo folder per prospect | Prospects cannot evaluate abstract claims. They need to hear and see the output from THEIR episode | MEDIUM (one pipeline run per prospect) | Already supported by `package-demo`. Run pipeline on a public episode of their show. Include before/after audio — this is the single fastest trust-builder. |
| Contact tracker | Even 5 prospects need a log: who was contacted, when, which email variant, reply status, follow-up due date | LOW (CSV or flat JSON, not a CRM) | See contact tracking section. Do not build software for this — use a spreadsheet or plain JSON file. |

---

## Differentiators

Features that make this outreach stand out from generic freelancer cold outreach.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Demo built from prospect's own episode | Every other editor says "here's our portfolio." This pipeline says "here's YOUR episode, processed." Personal demos convert at higher rates because they eliminate imagination from the prospect's evaluation | MEDIUM (one pipeline run per prospect; ~40 min per episode) | Process one episode per prospect before outreach. Package with `package-demo`. Send demo link or zip in initial email. |
| Estimated time-saved table in DEMO.md | Hosts understand their own time cost better than abstract quality claims. "6-11 hours saved per episode" is a number they can act on | LOW (already in DEMO.md template) | DEMO.md already has time-saved table. Verify accuracy of manual-edit time estimates against industry data (confirmed: transcription 2-3h, show notes 1-2h, clips 2-4h). |
| Cost-per-episode breakdown | "~$1-2 per episode in AI costs" is a differentiator vs. freelance editors ($50-200/ep) and SaaS tools ($29-99/mo). Positions this as something that pays for itself in two episodes | LOW (already in DEMO.md template) | Include this number in both the email and the DEMO.md. It is a competitive moat. |
| Before/after audio segment | 60 seconds of raw vs. processed audio is more persuasive than any written claim about audio quality. Duck-fade censorship, LUFS normalization, and noise reduction all show up in the listening test | MEDIUM (pipeline snapshot already shipped in v1.4) | Raw audio snapshot before censor step is already implemented. `demo_packager.py` already surfaces before/after. Confirm it is working per-client before outreach. |
| Pitch generated from demo metadata | Instead of a generic email, a pitch that names the specific episode processed, the LUFS improvement, the number of clips extracted, and one specific show note line — demonstrates that the system ran on their show | LOW (post-processing, no new infra) | See pitch generator feature below. Reads from `_analysis.json` and DEMO.md to populate a personalized email template. |
| Genre-matched content tone | Show notes and social captions that sound like the show — not a generic template — prove the system understands context, not just structure | MEDIUM (persona tuning required per show before pipeline run) | Write a genre-appropriate voice_persona in the prospect's YAML before running the pipeline. This is the highest-leverage 10-minute task before each demo run. |

---

## Anti-Features

Features that seem useful for outreach but are not worth building for a 3-5 prospect campaign.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Automated email sending (mail merge, sequences) | Campaign scale is 3-5 prospects. No automation needed at this volume. Risk of spam classification with a new sender domain. | Send manually from personal email. Use Gmail or FastMail. Personalize each one. |
| Full CRM (HubSpot, Pipedrive, Airtable) | Overkill for a 5-contact list. Setup time exceeds value at this stage. | Use a flat CSV or a JSON file in `.planning/outreach/contacts.json`. 6 fields: name, show, email, sent_date, reply_status, next_action. |
| Podcast discovery API integration in the pipeline | Finding prospects is a one-time manual task, not a recurring automated workflow (at this stage) | Research manually. Use Listen Notes free web search (no API key needed for web UI) or Apple Podcasts category pages. |
| Video outreach (Loom demo walkthrough) | High production overhead. Only worthwhile after at least one live demo validates messaging | Send the demo folder first. If no reply after 2 follow-ups, then consider a 3-minute Loom. |
| LinkedIn scraping or automated DM outreach | Podcast hosts are more reachable via email (from RSS feed) or Twitter/X DM. LinkedIn is for corporate podcasters, not indie shows | Prioritize RSS-extracted email. Fall back to Twitter/X DM or Instagram DM for indie hosts. |
| SEO / content marketing to attract inbound | Weeks to months to see results. The v1.5 milestone goal is a first client within the milestone, not a marketing funnel | Do outbound until first client. Revisit inbound at v2+. |
| Proposal generation tool | At 3-5 prospects, write proposals manually. A template doc is sufficient. | Create a single `PROPOSAL_TEMPLATE.md` in `.planning/outreach/`. Personalize per prospect. No automation. |

---

## Prospect Qualification Criteria

What makes a podcast a good target for this service. Apply these as filters before investing a
full pipeline run on a prospect's episode.

### Must-Have Qualifiers (fail any of these = skip)

| Criterion | Rationale | How to Check |
|-----------|-----------|--------------|
| Active show: published within 30 days | Inactive shows will not respond, and hosts who paused likely paused because of production burden — they need money or motivation, not a vendor | Check RSS feed for most recent publish date |
| Public RSS feed | Pipeline ingests via `rss_source` YAML key. No RSS = no demo, no pipeline run | Try to fetch `https://[show].com/feed` or look up on Apple Podcasts |
| 10-200 episodes | Too few (< 10): may be a new show that quits. Too many (> 200): likely already has a production workflow | Check episode count on ListenNotes or Apple Podcasts show page |
| Independent / self-produced (not a network show) | Network shows have in-house production teams. Indies are the target market | Hosting platform (Buzzsprout, Anchor/Spotify, Transistor, Libsyn) in RSS feed `<generator>` tag usually signals indie. NPR/iHeart/Wondery in branding = skip |
| Signs of production debt | Inconsistent audio quality, no show notes or very brief ones, missing chapters, no social clips, irregular publish schedule | Listen to 5 minutes of a recent episode. Check their Twitter/Instagram for clip posting. |
| Host handles own production | If they tweet about editing their own episodes, mention "I spent the weekend editing" — high pain, low sophistication, perfect target | Check Twitter/X for complaints about production time |

### Nice-to-Have Qualifiers (increase priority ranking)

| Criterion | Rationale |
|-----------|-----------|
| 500-5,000 estimated monthly listeners | Large enough to care about quality. Small enough that they have not yet hired an editor. ListenNotes and Rephonic both estimate reach. |
| Genre matches proven pipeline (comedy, true crime, business/interview) | Pipeline has been validated on these genres. Voice personas already exist or can be adapted quickly. |
| Guest-heavy interview format OR solo host with strong opinion content | Interview format produces consistent structure that clips and transcribes well. Monologue/opinion shows also work well. Multi-host banter without structure is harder to clip. |
| Twitter/X or Instagram account with < 5K followers | Signals they are trying to grow but have not yet broken through — production quality improvements have clear upside |
| Monetization signals (Patreon, merchandise, sponsorship mentions) | Already has some revenue. More willing to pay for services that improve production value which directly supports their monetization. |
| Positive show reviews mentioning content, not production | Listeners love the HOST but production is holding growth back. This is the most common indie podcast situation. |

### Disqualifiers (hard no)

| Criterion | Reason |
|-----------|--------|
| Network-produced (NPR, iHeart, Wondery, Audacy) | Have in-house teams. Not reachable via cold outreach. |
| No contact information findable in RSS feed, website, or social | Cannot pitch someone you cannot reach |
| Video-first show (primarily YouTube with podcast as audio export) | Production workflow is video-editing-first. Different toolchain, different pain points, not what this pipeline solves |
| Older than 12 months since last episode | Inactive shows will not convert |
| Already using a production agency (mentioned in show notes or website) | Will not switch without a compelling proof point and active dissatisfaction |

---

## Outreach Pitch Requirements

What a converting cold pitch for a podcast production service needs. Based on research across
podcast booking, B2B service, and freelancer outreach patterns.

### Email Anatomy

A cold outreach email to a podcast host must follow this structure to convert:

1. **Subject line** — Show-specific, not generic. Reference their show name or a recent episode.
   - Works: "I processed [Show Name] ep47 — here's what 6 hours of editing looks like in 38 minutes"
   - Fails: "Podcast production services for you", "Save time on your podcast"
   - Target: < 60 characters. Question format or curiosity gap works.

2. **Opening line** — About them, not you. Never start with "I". Reference their show specifically.
   - Works: "Your recent episode on [topic] had a great insight around [specific quote or moment]"
   - Fails: "I'm a podcast automation specialist with 3 years experience..."

3. **One-line value proposition** — Concrete time and cost claim, not abstract quality language.
   - Works: "I ran your episode through an automated production pipeline — saved ~8 hours of editing, costs $1-2 in AI."
   - Fails: "We offer premium podcast editing and production services"

4. **Social proof or proof point** — A tangible artifact, not a claim. Link the demo folder or HTML summary.
   - Works: "Here's what it produced from ep47: [link to demo folder or summary page]"
   - Fails: "Our clients love us and we have a great track record"

5. **Single clear ask** — One specific next step, not multiple options.
   - Works: "Worth a 20-minute call this week to walk through it?"
   - Fails: "Let me know if you'd like to learn more, or check out our website, or..."

6. **Length** — 150-200 words maximum. Prospects scan, they do not read. If it takes longer than
   30 seconds to read, it will not be read.

### Follow-Up Cadence

Research confirms: most conversions happen on follow-up, not the initial email.

| Follow-Up | Timing | Content |
|-----------|--------|---------|
| Follow-up 1 | Day 4 after no reply | One-line check-in. Add a new piece of information — one specific metric from their demo (e.g., "Your ep47 was at -24 LUFS; broadcast standard is -14. The pipeline fixed it automatically.") |
| Follow-up 2 | Day 10 after no reply | Short and graceful. Offer a different format — "Happy to send a 3-minute Loom walkthrough instead of a demo folder if that's easier." |
| Follow-up 3 | Day 20 | Final contact. Acknowledge it may not be the right time. Leave the door open: "If you ever want to run an episode through the pipeline, just say the word." |

After 3 follow-ups with no reply: mark as "dead" in tracker. Do not contact again for 90 days.

### Pitch Personalization Requirements Per Prospect

For each prospect, before sending the email, extract these from the demo run:

| Field | Source | Where Used in Email |
|-------|--------|---------------------|
| Episode number or title processed | Demo run | Subject line and opening |
| LUFS before/after values | `_analysis.json` or normalization log | Follow-up 1 metric |
| Number of clips extracted | `_analysis.json` `best_clips` length | Body of email |
| Compliance flag count | `_analysis.json` compliance section | Optional — useful if they had flags |
| Estimated time saved | DEMO.md time-saved table | Body of email (use the 6-11 hour figure) |
| One specific show note excerpt | `_analysis.json` `show_notes` field | Shows the AI matched their show's voice |

---

## Pitch Generator Feature

A lightweight script that reads an existing demo output and generates a personalized email draft.
Not a full feature — a utility script run once per prospect.

**Input:** `output/<client>/<ep>/[ep_id]_analysis.json` + `demo/<client>/<ep>/DEMO.md`
**Output:** Populated email text printed to stdout or written to `demo/<client>/<ep>/PITCH_EMAIL.txt`

**Populate:**
- Subject line variant A (statement format) and B (question format)
- Opening line using episode title
- Time saved estimate
- LUFS before/after
- Clip count
- Demo folder link placeholder
- Follow-up 1 with a specific metric

**Complexity:** LOW. 50-100 lines of Python. Reads JSON, applies a string template, writes text.
Does not require a new module — can live as `generate_pitch.py` at top level or as a CLI
subcommand `uv run main.py generate-pitch --client <name> --ep <id>`.

---

## Contact Tracking System

For 3-5 prospects, the contact tracker must take under 5 minutes to set up and zero ongoing
maintenance beyond updating a row after each interaction.

**Recommendation:** A JSON file at `.planning/outreach/contacts.json` or a CSV at
`.planning/outreach/contacts.csv`. CSV is easier to edit by hand and open in Excel/Numbers.

### Schema

| Field | Type | Example |
|-------|------|---------|
| `prospect_id` | string | `"true-crime-weekly"` |
| `show_name` | string | `"True Crime Weekly"` |
| `host_name` | string | `"Sarah Jenkins"` |
| `contact_email` | string | `"sarah@truecrimepod.com"` |
| `contact_source` | string | `"rss_itunes_email"` / `"twitter_dm"` / `"website_form"` |
| `demo_processed` | boolean | `true` |
| `demo_path` | string | `"demo/true-crime-weekly/ep47/"` |
| `email_sent_date` | date | `"2026-04-02"` |
| `email_variant` | string | `"A"` (subject line A vs B for A/B test) |
| `reply_status` | enum | `"no_reply"` / `"replied_positive"` / `"replied_negative"` / `"call_scheduled"` / `"closed_won"` / `"closed_lost"` |
| `follow_up_1_date` | date | `"2026-04-06"` |
| `follow_up_2_date` | date | `"2026-04-12"` |
| `follow_up_3_date` | date | `"2026-04-22"` |
| `next_action` | string | `"Send follow-up 1 on Apr 6"` |
| `notes` | string | `"Host mentioned on ep47 they edit themselves on weekends"` |

**Usage pattern:** Open the CSV, update the row after each interaction. Set a calendar reminder for
each next_action date. This is a 30-second-per-week maintenance task.

**Do not build a web interface or database for this.** At 3-5 prospects, that is over-engineering.
The schema above in a plain CSV file is sufficient through v1.5 and likely v2.0.

---

## Prospect Discovery Methods

Ranked by reliability and ease of extraction for this specific use case.

### Method 1: Listen Notes API — Best for Programmatic Search

Listen Notes API supports:
- `GET /search` with `type=podcast`, `genre_ids` (genre filter), `episode_count_min`, `episode_count_max`
- Free tier: 30 results per query, no rate limit specified for free plan
- Response includes estimated `total_episodes`, `listen_score` (popularity proxy), and `rss` URL

**Genre IDs to use:** Business (93), True Crime (132), Comedy (133), Society & Culture (122),
Health & Fitness (88), Education (111). Get current IDs from `GET /genres`.

**Search query approach:** Use broad genre terms ("interview" in business, "case" in true crime)
plus `episode_count_min=10&episode_count_max=200` to target active mid-stage shows.

**Confidence:** HIGH — API documentation confirms these parameters exist and the free tier supports them.

### Method 2: Apple Podcasts / Spotify Category Browse — Best for Manual Inspection

Browse category pages on Apple Podcasts (podcasts.apple.com/us/genre/podcasts-business/id1321)
and scroll past the top-ranked shows into page 3-5 territory. Shows in that range:
- Have enough listeners to care about quality
- Have not yet broken out enough to have a team

This is manual, takes 20-30 minutes per genre, but produces high-quality leads because you can
listen to 3 minutes of audio before adding to the list.

### Method 3: RSS-Extracted Contact — Best for Email Accuracy

Once a show is identified, extract contact email programmatically:

```python
import feedparser

feed = feedparser.parse(rss_url)
owner = feed.feed.get("itunes_owner", {})
email = owner.get("email") or feed.feed.get("author_detail", {}).get("email")
```

`<itunes:email>` inside `<itunes:owner>` is the most reliable contact point. Fall back to
`<managingEditor>` or the show website's contact page.

**Note:** Apple deprecated the `<itunes:owner>` tag recommendation in 2024, but most hosting
platforms (Buzzsprout, Transistor, Libsyn, Anchor) still include it. Check before assuming it
exists.

**Confidence:** HIGH — confirmed via RSS spec and podseeker.co documentation.

### Method 4: Social Media Direct Search

Search Twitter/X for `"editing my podcast" OR "spent hours editing" OR "podcast editing takes"` to
find hosts explicitly expressing the pain point in real time. These are warm leads.

Similarly, Reddit r/podcasting has posts like "How long does editing take you?" — names there are
often indie hosts who are prospects.

**Confidence:** MEDIUM — this works but requires manual effort and the signal is noisy.

---

## Feature Dependencies

```
First paying client
    └──requires──> Closed pitch (reply_status: closed_won)
                       └──requires──> Compelling demo + credible email pitch
                                          └──requires──> Demo run on prospect's episode
                                                             └──requires──> Prospect identified + qualified
                                                                                └──requires──> Prospect list (3-5 shows)

Pitch generator script
    └──reads──> _analysis.json (from pipeline run)
    └──reads──> DEMO.md (from demo_packager)
    └──outputs──> PITCH_EMAIL.txt (personalized draft)
    └──requires──> Demo has already been run per prospect

Contact tracker (CSV)
    └──no code dependencies — just a CSV file
    └──used by──> Human (manual updates)
    └──populated by──> pipeline run completion + email send event

RSS email extraction
    └──uses──> feedparser (already in deps)
    └──input──> RSS URL (from Listen Notes API search result or manual discovery)
    └──output──> contact email for each prospect
```

---

## MVP for v1.5

Minimum viable outreach that could close a first client.

### Must Ship (no client without these)

1. **Prospect list: 3-5 qualified shows** — Research, qualify against criteria above, record in CSV
   (no code required, just structured research)

2. **Demo run per prospect** — Process one episode per show using public RSS fetch. Takes ~40 min
   per episode on GPU. Run `uv run main.py --client <name> ep1` + `uv run main.py --client <name> package-demo ep1`

3. **Contact emails extracted** — Parse RSS for `itunes:email` or `managingEditor` for each
   prospect. 15 lines of feedparser code or manual inspection.

4. **Personalized pitch email per prospect** — Use template structure above. Personalize with
   episode title, LUFS delta, clip count, and one specific show note excerpt. Send manually.

5. **Contact tracker CSV** — Create `.planning/outreach/contacts.csv` with schema above. Update
   after each send and reply.

### Ship After First Reply

6. **Pitch generator script** (`generate_pitch.py` or `generate-pitch` CLI subcommand) — Reads
   demo JSON + DEMO.md, outputs personalized email draft. Worth building once the manual
   approach validates messaging.

7. **Proposal template** — A standard `.planning/outreach/PROPOSAL_TEMPLATE.md` with
   scope, pricing, and onboarding steps. Write once after first interested reply.

### Defer Until After First Client Signs

8. **Automated prospect scraping** — Not needed until you have validated the pitch and want to
   scale to 20+ prospects
9. **Full CRM** — Overkill until pipeline is serving 3+ active paying clients
10. **Inbound marketing / SEO** — Post-v1.5 concern entirely

---

## Pricing Guidance

Informed by 2025 market rates for podcast editing and production services:

| Tier | Market Rate | Notes |
|------|-------------|-------|
| Freelance editor (per episode) | $50-200/episode | Manual editing. This is the primary competition for indie hosts. |
| Mid-tier production agency (monthly) | $500-2,000/month | Full production including strategy. Too expensive for indie shows. |
| SaaS tools (Swell AI, Castmagic) | $29-99/month | Clips + show notes only. No audio mastering, no upload. |
| This pipeline (suggested entry price) | $75-150/episode OR $200-400/month | Cost: ~$1-3/episode in AI tokens. Margin is high. Entry price should be below freelance editor rates to remove friction from first client. |

**Positioning:** "Less than you pay a freelance editor, with 10x the deliverables."

The near-zero cost per episode (~$1-3 OpenAI tokens, local Whisper) means any paying client is
highly profitable. First client pricing should prioritize closing over margin optimization.

---

## Sources

- [Listen Notes API Documentation](https://www.listennotes.com/api/docs/) — HIGH confidence (official docs)
- [Listen Notes API genre/episode count filters](https://www.listennotes.com/api/announcements/) — HIGH confidence
- [Podchaser Podcast Discovery API](https://features.podchaser.com/api/) — MEDIUM confidence
- [Rephonic Podcast Database](https://rephonic.com/podcast-database) — MEDIUM confidence (25+ filters, $99-299/mo for API access)
- [Finding Podcast Contact Information via RSS](https://www.podseeker.co/blog/fastest-way-to-get-podcast-contact-information) — HIGH confidence
- [How to Pitch a Podcast: Lessons from 1,000+ Emails](https://respona.com/blog/how-to-pitch-a-podcast/) — MEDIUM confidence
- [Cold Email Conversion Rates for Podcast Outreach](https://www.smartlead.ai/blog/how-to-write-a-cold-email-podcast-template) — MEDIUM confidence (10-20% reply rate when personalized)
- [Podcast Production Pricing 2025](https://www.trevorohare.com/blog/how-much-does-professional-podcast-editing-cost-in-2025) — MEDIUM confidence
- [Podcast Production Pricing Guide 2026 — Rise25](https://rise25.com/lead-generation/podcast-production-pricing/) — MEDIUM confidence ($500-20K/month for B2B)
- [Podcast Editing Rates — SasPod](https://saspod.com/blog/post/podcast-editor-costs-and-rates-freelancers) — MEDIUM confidence ($50-200/episode for freelancers)
- [B2B Podcast Client Acquisition — Rise25](https://rise25.com/) — MEDIUM confidence
- [Top B2B Podcast Production Agencies — Content Allies](https://contentallies.com/learn/top-b2b-podcast-production-agencies) — MEDIUM confidence
- [Podcast Host Pain Points — Podium](https://hello.podium.page/blog/overcoming-common-podcasting-challenges-and-roadblocks) — MEDIUM confidence
- [Podcast Cold Email Template — WaveApps](https://www.waveapps.com/freelancing/cold-pitch-templates) — LOW confidence (general freelance templates, not podcast-specific)

---

*Feature research for: podcast production service — client acquisition and outreach tooling (v1.5 milestone)*
*Researched: 2026-03-28*
