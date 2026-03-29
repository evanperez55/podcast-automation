# Domain Pitfalls

**Domain:** Podcast production service — go-to-market, cold outreach, and first paying client acquisition
**Researched:** 2026-03-28
**Confidence:** MEDIUM-HIGH (sales pitfalls from practitioner sources; legal section MEDIUM — not legal advice)

---

## Critical Pitfalls

### Pitfall 1: Processing Someone's Episode for a Demo Without Permission Creates Legal and Reputational Exposure

**What goes wrong:**
You process a prospect's public podcast episode through the pipeline and send them the output as a sales demo. The prospect feels their content was used without consent. Even though the episode was publicly available via RSS, the act of running it through transcription, AI analysis, content alteration (censorship, clips), and packaging it for commercial solicitation goes beyond the purpose for which it was published.

**Why it happens:**
"It's public" feels like permission. It is not. Copyright protects a work regardless of accessibility. The four-factor fair use test weighs heavily against commercial use — you're creating derivative works (clips, subtitles, blog post) from someone else's content to sell a service. Under GDPR, voice recordings are classified as personal data even when published publicly, and processing them for a new commercial purpose requires a separate lawful basis.

The spec-work analogy applies here too: the design industry fought this battle for decades. Unsolicited redesigns sent to prospects are widely considered presumptuous and manipulative ("look what I did to your stuff, now pay me"). Podcast hosts who share this reaction publicly can damage your reputation in a small, interconnected community.

**Consequences:**
- Prospect responds with hostility, shares the pitch in podcasting communities as a cautionary tale
- Copyright infringement claim (low probability but non-zero, especially if output is redistributed)
- GDPR exposure if the prospect is EU-based and you processed their voice data without a lawful basis
- Lost deal and word-of-mouth damage in the exact niche you're targeting

**Prevention:**
Get permission before processing. A simple DM or email: "I'd love to run your latest episode through my pipeline as a free demo — would you be open to that? I'll send you everything and you can use it or not." This converts a legal risk into a warm lead.

If you want to build demos without prior contact, use your own content (Fake Problems) as the demo artifact, or use shows you've explicitly been given permission to process. Show prospects what the output looks like without using their content.

**Detection:**
Any prospect response that includes words like "permission," "consent," or "didn't ask" is a signal you've triggered this reaction.

**Phase to address:**
Prospect research phase (before any processing). Establish a consent-first policy before the first episode is processed.

---

### Pitfall 2: Targeting the Wrong Size or Stage of Podcast

**What goes wrong:**
You pitch shows that are either too large (don't need you, have production teams) or too small (can't afford you, processing their episodes produces near-zero ROI for them). The sweet spot is independent shows with 1,000–20,000 downloads per episode that are releasing regularly but have no post-production workflow.

**Why it happens:**
It's tempting to pitch well-known shows for validation, or to cast a wide net. Large shows (100K+ downloads) have established production pipelines and staff — they'll evaluate your pitch against professional agencies, not as a scrappy automation tool. Very small shows (under 500 downloads) may not be generating revenue and cannot justify any production spend, no matter how low.

**Consequences:**
- Wasted demo effort on shows that can't convert
- Large shows may be dismissive in ways that demoralize outreach momentum
- Very small shows may love the demo but have no budget, leading to tire-kickers and scope negotiation that goes nowhere

**Prevention:**
Screen prospects using public signals before investing in a demo:
- Listen to Chartable, Rephonic, or Podchaser for download estimates
- Signs of monetization: sponsor reads, Patreon links, "this show is supported by" language in episodes
- Signs of growth intent: regular release cadence, improving audio quality over time, active social promotion
- Signs they need help: no clips on social, no transcripts on site, no chapters in RSS feed, inconsistent release schedule

Target: solo hosts or 2-person shows, releasing bi-weekly or weekly, with some monetization signal, who are not currently using a production service.

**Detection:**
If prospects consistently respond with "we already have someone" or no response at all, you may be pitching too large. If they respond with enthusiasm but stall on pricing, you may be pitching too small.

**Phase to address:**
Prospect identification phase. Define an ICP checklist before building the prospect list.

---

### Pitfall 3: Pricing Based on Your Costs, Not the Value You Deliver

**What goes wrong:**
Your marginal cost per episode is near zero (GPU electricity + ~$0.50–0.80 OpenAI API calls). If you price based on cost-plus, you might charge $50–100/episode, which is below market rate and signals low value. Worse, you leave significant money on the table because what you're actually delivering — 3 social clips, subtitles, a blog post, YouTube upload, RSS update — would take a professional editor 4–8 hours at $75–150/hour.

**Why it happens:**
Low-cost automation tempts operators to compete on price. "I can undercut everyone because my costs are low" is a race to the bottom that commoditizes your service and attracts clients who will churn the moment they find something cheaper.

**Consequences:**
- Pricing at $50/episode signals a hobbyist tool, not a professional service
- Clients who buy on price leave on price — highest churn segment
- You're leaving 5–10x revenue on the table relative to what the market will bear

**Prevention:**
Market rates in 2026 for full-service podcast production:
- Basic editing only: $200–500/episode
- Full production (edit + clips + social + SEO): $500–2,000/episode
- Monthly retainer (4 episodes + distribution): $1,500–5,000/month

Position on outcomes (saved time, professional distribution, consistent publishing) not on the automation that enables it. Prospects don't care that it's AI — they care that their show sounds professional and gets published on time.

Start with a per-episode price in the $300–600 range for small shows. Move to monthly retainers as quickly as possible — retainers create predictable revenue and lower churn.

**Detection:**
If your first instinct is "what does it cost me" rather than "what is it worth to them," you're pricing from the wrong direction.

**Phase to address:**
Outreach template phase (before any pricing is communicated to prospects).

---

### Pitfall 4: The Demo Doesn't Match the Show's Brand or Tone

**What goes wrong:**
The pipeline's AI-generated content — episode title, social captions, blog post, chapter titles — reflects the voice persona in the client YAML config. If you process a prospect's episode using the wrong voice persona (or the Fake Problems fallback), the demo output reads as off-brand. A serious true crime show gets captions with dark comedy framing. A professional B2B interview show gets irreverent chapter titles. The prospect sees output that sounds nothing like their show and concludes the tool doesn't work.

**Why it happens:**
The pipeline defaults to the Fake Problems voice. Processing a new show's episode requires explicitly setting up a client YAML with an appropriate voice persona before running. Under time pressure, it's easy to skip this step.

**Consequences:**
- Prospect dismisses the demo as "not what we'd want" even if the technical quality is excellent
- You've invested 30–60 minutes of processing time on a demo that can't be used
- Worse, if you send a demo with comedy framing to a true crime host, it may read as mockery of their serious subject matter

**Prevention:**
Before processing any demo episode, spend 20–30 minutes listening to the show and writing a voice persona description in the client YAML. Use their actual episode descriptions and social posts as style references. Run the pipeline with this persona set, then manually review AI-generated output before packaging the demo.

Never send a demo without reading the blog post and social captions first. These are the outputs prospects will evaluate most critically.

**Detection:**
Review the demo output before sending. If the blog post or captions don't sound like the show you listened to, the voice persona is wrong.

**Phase to address:**
Demo production phase. Add a mandatory pre-send review step in the outreach workflow.

---

## Moderate Pitfalls

### Pitfall 5: Over-Automating Outreach Triggers Spam Filters and Kills Deliverability

**What goes wrong:**
Tempted by the automation capabilities of the pipeline, you build an automated outreach sequence — auto-generated pitch emails, automated follow-ups, bulk sending. Google's spam policies (hard enforcement since November 2025) reject messages from domains without DMARC/DKIM/SPF. Safe sending limits are 50–100 cold emails per day per mailbox. Above this threshold, spam filters engage and domain reputation degrades — which means future legitimate emails also land in spam.

For a service that sells to a small community (independent podcasters), spam reports are especially damaging. Podcasters are an interconnected community. One host who marks your email as spam and posts about it in a community Slack or Discord can dry up a segment of your prospect pool.

**Prevention:**
Send cold outreach manually or with minimal automation. At 3–5 prospects, no automation is needed. Configure DMARC/DKIM/SPF before sending any cold email from your domain. Personalize each pitch — reference a specific episode, a specific problem visible in their current distribution (no clips, no transcript, sporadic schedule). The goal is 3–5 prospects, not 300.

**Detection:**
Bounce rates above 5% or open rates below 20% on cold outreach suggest deliverability problems. If your email platform flags your domain reputation, stop sending immediately.

**Phase to address:**
Outreach execution phase. Keep volume at manually manageable levels (under 10 per day).

---

### Pitfall 6: Overpromising What the Pipeline Can Do

**What goes wrong:**
The pipeline is impressive on paper: transcription, AI analysis, clips, subtitles, blog post, YouTube upload, RSS update. In the pitch, these become "fully automated end-to-end podcast production." The prospect signs up expecting hands-off delivery. Reality: the pipeline requires a working Dropbox setup, proper client YAML configuration, GPU hardware, occasional manual clip approval, and review of AI output before distribution. When the client encounters friction — a file format issue, a voice persona that needs tuning, a compliance flag requiring human judgment — the gap between "fully automated" and "requires your involvement sometimes" creates disappointment and distrust.

**Prevention:**
Describe what the pipeline does accurately: "I run your raw audio through a production pipeline that handles editing, clips, subtitles, and distribution. You review and approve before anything goes live." The approval step is a feature, not a limitation — it's quality control that protects their brand.

Be explicit about what requires their involvement: providing the raw audio file, reviewing the output once per episode, and approving clips before distribution. This is still dramatically less work than manual production.

**Detection:**
If your pitch uses the phrase "fully automated" or "zero effort," you've probably overpromised.

**Phase to address:**
Outreach template phase. Review pitch language for accuracy before sending.

---

### Pitfall 7: Pitching the Tool Instead of the Outcome

**What goes wrong:**
The pitch focuses on the technology: "I built a Python pipeline with Whisper transcription, GPT-4o analysis, and automated YouTube upload." The prospect doesn't care about the implementation. They care about the outcome: consistent publishing, professional clips for social, time saved.

**Prevention:**
Lead with the problem the prospect has, not the solution you built. Example framing: "I noticed your show hasn't released a clip to Instagram in three months. I can produce 3 ready-to-post clips per episode, plus a blog post and YouTube upload, starting this week." Then show the demo as evidence, not as the pitch.

**Detection:**
Read your pitch email. If the first mention of "what you get" comes after a technical description of how it works, restructure it.

**Phase to address:**
Outreach template phase. Write outcome-first templates before any pitching.

---

### Pitfall 8: Sending Generic Pitches That Don't Reference the Specific Show

**What goes wrong:**
83% of podcast hosts reject pitches that don't demonstrate familiarity with their show. A pitch email with "Hi [Name]" merged in but no specific show knowledge reads as a template blast. Getting the podcast name wrong, referencing a topic they covered years ago, or sending the same pitch to a comedy show and a true crime show signals you haven't listened.

**Prevention:**
For each prospect: listen to at least one episode, note one specific episode detail you can reference, and customize the first paragraph of the pitch. Reference the specific episode you processed for the demo. The personalization effort also forces the minimum research required to set the voice persona correctly.

**Detection:**
If you can copy-paste your pitch to a different prospect without changing any content detail, it's too generic.

**Phase to address:**
Outreach template phase. Templates should have explicit [PERSONALIZATION REQUIRED] placeholders.

---

## Minor Pitfalls

### Pitfall 9: No Contact Tracking Leads to Duplicate Outreach

**What goes wrong:**
Without tracking who has been contacted, when, and what response they gave, you risk following up too aggressively (damaging the relationship) or losing warm leads who responded positively but weren't ready to commit.

**Prevention:**
Even a simple spreadsheet with: prospect name, show name, contact date, channel (email/DM), response, follow-up date. For 3–5 prospects, this is a 10-minute setup.

**Phase to address:**
Outreach tooling phase.

---

### Pitfall 10: Failing to Get Permission for Demo Use = Demos You Can't Share

**What goes wrong:**
Even if you process a prospect's episode with their permission, you cannot later use that demo as a public portfolio piece or reference without separate permission. Clients may not want their content used in your marketing.

**Prevention:**
When asking for demo consent, ask explicitly: "May I use this as an example in my portfolio?" Keep separate from "may I process your episode." Most will say yes, but don't assume.

**Phase to address:**
Demo production phase.

---

### Pitfall 11: Pricing Conversation Before Demo Delivery Kills Deals

**What goes wrong:**
Mentioning pricing in the initial cold outreach (or in the same message as the demo offer) frames the demo as a sales attempt rather than a gift. Prospects disengage before seeing the output.

**Prevention:**
Lead with the free demo offer. No pricing in cold outreach. Pricing conversation happens after the prospect has seen the output and expressed interest.

**Phase to address:**
Outreach template phase.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Prospect identification | Targeting shows too large or too small | Define ICP criteria (1K–20K downloads, monetization signal, no current production service) before building list |
| Demo production | Processing without permission | DM/email for consent before running pipeline; use Fake Problems as fallback demo |
| Demo production | Wrong voice persona in output | Listen to show, write persona before processing; review all AI output before packaging |
| Demo production | Pipeline defaults to Fake Problems config | Always pass `--client <prospect-name>` with a configured YAML; never use default client |
| Outreach templates | Pitch sounds like a template | Write outcome-first; include specific show reference in paragraph 1 |
| Outreach execution | Over-automation, spam risk | Manual sending only at 3–5 prospect scale; configure DMARC/DKIM/SPF first |
| Pricing conversation | Under-pricing based on cost | Price on value delivered ($300–600/episode entry point); lead with retainer framing |
| Expectation setting | Overpromising automation | Use "I handle production, you review and approve" framing — never "fully automated" |
| Follow-up | No tracking, duplicate contact | Build simple contact log before first outreach |

---

## Legal Considerations Summary

The following are practical risk assessments, not legal advice.

| Action | Risk Level | Notes |
|--------|------------|-------|
| Processing public episode without consent for private demo use | MEDIUM | Fair use likely does not apply for commercial derivative works; voice is personal data under GDPR |
| Processing public episode with explicit prospect consent | LOW | Consent resolves both copyright and GDPR concerns |
| Using Fake Problems episodes as demo of capabilities | LOW | You own the content |
| Distributing processed output publicly without permission | HIGH | Do not do this |
| Transcribing and processing an episode, then deleting all outputs | LOW | Transient processing with no distribution has minimal exposure |
| Using processed demo as portfolio without permission | MEDIUM | Requires separate explicit permission from the prospect |

---

## Sources

- [Podcasting Copyright Laws - async.com](https://async.com/blog/podcasting-copyright-laws/)
- [Podcasting Legal Guide - Creative Commons](https://wiki.creativecommons.org/wiki/Podcasting_Legal_Guide)
- [How to Avoid Copyright Infringement on a Podcast - Copyright Alliance](https://copyrightalliance.org/how-to-avoid-copyright-infringement-on-podcasts/)
- [How do the rules on audio recording change under GDPR? - IAPP](https://iapp.org/news/a/how-do-the-rules-on-audio-recording-change-under-the-gdpr)
- [GDPR Compliance for Voice-to-Text Services - GDPR Advisor](https://www.gdpr-advisor.com/gdpr-compliance-for-voice-to-text-services-and-transcription-platforms/)
- [Podcast Production Pricing Guide 2026 - Rise25](https://rise25.com/lead-generation/podcast-production-pricing/)
- [Podcast Editing Pricing Models - PricingLink](https://pricinglink.com/knowledge-base/podcast-production-marketing-services/podcast-editing-pricing-models/)
- [6 cold outreach mistakes to avoid in 2026 - Outsource Accelerator](https://www.outsourceaccelerator.com/articles/cold-outreach/)
- [Cold Email Outreach Best Practices 2025-26 - Cleverly](https://www.cleverly.co/blog/cold-email-outreach-best-practices)
- [Common mistakes choosing the right podcast to pitch - PR Daily](https://www.prdaily.com/common-mistakes-in-choosing-the-right-podcast-for-your-media-relations-pitch/)
- [What Google's Spam Changes Mean for B2B Cold Email - Outbound Republic](https://outboundrepublic.com/blog/what-googles-spam-changes-mean-for-b2b-cold-email-in-2025/)
- [Cold Email Sending Limits 2025 - Topo](https://www.topo.io/blog/safe-sending-limits-cold-email)
- [Setting Realistic Expectations for AI Projects - PMI](https://www.pmi.org/blog/setting-realistic-expectations-ai-projects)
- [ALP 279: Setting client expectations in the AI era - FIR Podcast Network](https://www.firpodcastnetwork.com/alp-279-setting-client-expectations-in-the-ai-era/)
- [Are Your Reps Pitch Slapping Their Prospects? - LinkedIn](https://www.linkedin.com/pulse/pitch-slapping-linkedin-why-bad-news-sellers-buyers-peter)
- Existing codebase pitfalls (technical): `.planning/research/PITFALLS.md` prior version (2026-03-28)

---

## Note on Prior Pitfalls File

This file replaces the previous `PITFALLS.md` which covered **technical/pipeline pitfalls** for v1.4 (cross-genre testing). Those findings remain valid and are documented in the git history. The v1.5 milestone is a go-to-market milestone — the primary risks are no longer in the code.

---

*Pitfalls research for: v1.5 First Paying Client — sales, outreach, and demo delivery*
*Researched: 2026-03-28*
