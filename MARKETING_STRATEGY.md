# Fake Problems Podcast — Marketing Strategy

**Goal:** Grow from ~6 listeners to thousands using free/low-cost tactics.
**Date:** 2026-04-01

---

## 1. YouTube Shorts Optimization (Highest ROI)

YouTube Shorts is the #1 organic discovery channel for podcasts in 2026. You're already posting them — now optimize.

### 1a. Post 5-7 Shorts Per Week (Not Just 3 Per Episode)
**Why:** Algorithm rewards consistent posting. Top channels post 3-4/day.
**How:** You generate 5 clips per episode. Split each into 2-3 shorter clips (15-30 seconds is the sweet spot, not 60s). One episode = 10-15 Shorts.
**Implementation:** Update the clip generation config to create more, shorter clips. Stagger posting across the week instead of dumping all at once.

### 1b. Hook in First 3 Seconds
**Why:** 70-90% of viral Shorts retain viewers past the first 3 seconds. The algorithm tests every Short on a small seed audience — low retention = buried.
**How:** Start clips with the punchline/wildest statement, not the setup. Example: Don't clip "So we were talking about nukes and..." — clip "This bomb would have wiped out HALF the country."
**Implementation:** When selecting clips in content_editor analysis, prioritize moments that start with a bold/shocking/funny statement. Add a prompt instruction to the AI analysis to select "cold open" moments.

### 1c. Add Captions to All Shorts
**Why:** 80%+ of mobile viewers watch without sound initially.
**How:** You already generate subtitle clips — make sure every Short has burned-in captions.
**Implementation:** Already done via SubtitleClipGenerator. Verify all uploaded Shorts use the `_subtitle.mp4` versions.

### 1d. Optimize Titles and Thumbnails
**Why:** Title is the second hook after the visual. Curiosity gap drives clicks.
**How:** Use "question" or "shocking statement" format: "This Almost Destroyed America" > "Nuclear Bomb Facts"
**Implementation:** Update the AI prompt in content_editor to generate Short titles that are curiosity-driven, 5-8 words, no spoilers.

### 1e. End Screens and CTAs
**Why:** Shorts viewers need a path to the full episode.
**How:** Last frame of each Short: "Full episode — link in bio" or verbal CTA.
**Implementation:** Add a 2-second outro card to clip videos via FFmpeg overlay in SubtitleClipGenerator.

---

## 2. Spotify Discovery

### 2a. Nail the First 60 Seconds
**Why:** Spotify tracks completion rate. If listeners drop off in the first minute, algorithm deprioritizes you.
**How:** Start every episode with the wildest/funniest topic teaser, not housekeeping. "Today we're talking about — wait, did you know lobsters are basically immortal?" instead of "Hey guys, welcome back..."
**Implementation:** This is a recording habit, not automation. Brief hosts before each ep.

### 2b. Consistent Release Schedule
**Why:** Weekly/bi-weekly shows beat sporadic releases. Spotify rewards consistency.
**How:** Pick a day (e.g., every other Tuesday) and stick to it. Currently bi-weekly — keep that cadence.
**Implementation:** Already in place with content calendar.

### 2c. Keyword-Rich Episode Titles and Descriptions
**Why:** 30% of listeners find podcasts through search. Spotify and Google index your metadata.
**How:** Include searchable keywords. "Lobsters Don't Die, But We Might" is good but add description keywords like "immortality, nuclear bombs, AI horror."
**Implementation:** Update the AI analysis prompt to include 5-10 SEO keywords in show notes and episode descriptions.

---

## 3. Social Media Strategy

### 3a. Bluesky: Engage, Don't Just Post
**Why:** Bluesky is small enough that genuine engagement gets noticed. The algorithm surfaces replies and interactions.
**How:** Follow and reply to comedy/podcast accounts. Comment on trending topics with your podcast's take. Quote-post your own clips with hot takes. Join "starter packs" in your niche.
**Implementation:** Manual daily engagement (10 min/day). Automated posting is handled.

### 3b. Twitter/X: Thread Strategy
**Why:** Threads get 3x more engagement than single tweets.
**How:** Already posting threads with clips. Add a "hot take" thread format: post a controversial opinion from the episode as standalone content, not just promo.
**Implementation:** Add a "hot_take" field to the AI analysis output — a standalone controversial/funny statement from the episode that works as a tweet without needing context.

### 3c. Post Clips as Native Video (Not Just Links)
**Why:** Native video gets 10x more reach than link posts on every platform.
**How:** Upload the actual clip MP4 to Twitter/Bluesky instead of just linking to YouTube.
**Implementation:** Update twitter_uploader to attach video files for clip tweets. Bluesky supports video embeds via blob upload.

---

## 4. Cross-Promotion (Free, Highest Growth Multiplier)

### 4a. Guest Swap with Similar-Sized Podcasts
**Why:** #1 growth tactic cited by every source. A guest brings their audience to you.
**How:** Find 5-10 comedy podcasts with 100-1000 listeners. Reach out for guest swaps — you appear on theirs, they appear on yours.
**Implementation:** Use the prospect finder already built (`find-prospects`). Target podcasts in the 50-500 listener range who'd benefit from the swap equally.

### 4b. Podcast Promo Swaps (Ad Reads)
**Why:** Free — you read a 30-second ad for their show, they read one for yours.
**How:** Join podcast cross-promotion communities: r/podcastguestexchange, Podmatch.com, Podcast SOS Facebook group.
**Implementation:** Record a 30-second promo clip for Fake Problems that partner podcasts can drop into their episodes. Keep it in assets/.

### 4c. Appear on Podcasts as a Guest (Even Non-Comedy)
**Why:** You don't need to only appear on comedy shows. A comedy perspective on business/tech/culture shows is refreshing and memorable.
**How:** Pitch yourself to 5 podcasts per week. Use the pitch generator already built (`gen-pitch`).
**Implementation:** Already have outreach tooling. Execute weekly.

---

## 5. Community Building

### 5a. Create a Discord Server
**Why:** Direct relationship with listeners. They become evangelists.
**How:** Free Discord server. Channels: #episodes, #topic-suggestions, #memes, #general.
**Implementation:** Create server, add invite link to episode descriptions and social bios. You already have DiscordNotifier — post new episode alerts there.

### 5b. Listener Interaction in Episodes
**Why:** Listeners who hear their name/question on the show tell everyone they know.
**How:** "Question of the week" segment. Read listener comments/questions on air.
**Implementation:** Add a segment to the recording format. Source questions from Discord/social.

### 5c. Reddit Engagement (Manual)
**Why:** Reddit is where 38% of podcast listeners hang out. You can't auto-post, but you can engage.
**How:** Participate genuinely in r/podcasts, r/comedy, and topic-specific subreddits. When relevant, mention your episode naturally (not spam).
**Implementation:** 10 min/day manual Reddit browsing in relevant subreddits.

---

## 6. SEO and Discoverability

### 6a. Launch a Podcast Website
**Why:** Google indexes web pages. A website with full transcripts = free SEO traffic.
**How:** Simple site with episode pages containing: title, summary, full transcript, embedded player, YouTube embed.
**Implementation:** You already generate blog posts and transcripts. Deploy to GitHub Pages (episode_webpage_generator exists but needs GITHUB_PAGES_REPO configured).

### 6b. Submit to Every Podcast Directory
**Why:** Each directory is another discovery channel. Long tail adds up.
**How:** Beyond Spotify/YouTube: Apple Podcasts, Amazon Music, iHeartRadio, Podcast Index, Podchaser, Listen Notes, Goodpods, Castbox.
**Implementation:** Most just need your RSS feed URL submitted once. Do this in one afternoon.

### 6c. Podcast Trailer
**Why:** 2-3 minute "best of" trailer converts browsers to subscribers.
**How:** Compile the funniest 30-second clips from 5 episodes into a 2-3 min highlight reel.
**Implementation:** Build a "best-of" compilation from existing clips. You already have best_of_generator.

---

## 7. Guerrilla / Creative Tactics

### 7a. Clip Controversial Takes for Social Virality
**Why:** Controversy drives shares. Comedy podcast hot takes are inherently shareable.
**How:** Identify the most "wait, WHAT?" moment from each episode. Post it with a provocative caption designed to trigger comments (engagement = algorithm food).
**Implementation:** Add a "most_controversial_moment" field to AI analysis with timestamp.

### 7b. Challenge/Tag Format
**Why:** Interactive content gets shared.
**How:** End Shorts with "Tag someone who would [do this thing]" or "What would YOU do?" Questions in captions drive comments.
**Implementation:** Update clip caption generation to include engagement prompts.

### 7c. Meme Format Clips
**Why:** Meme-style content is the most shared format on every platform.
**How:** Take the funniest out-of-context quotes, overlay them on meme templates or reaction-style edits.
**Implementation:** Could automate with Pillow — generate quote cards from best lines.

### 7d. Collab Clips
**Why:** When you have guests, create clips featuring them and tag them — their audience sees it.
**How:** After guest episodes, create 3-5 clips specifically highlighting the guest, tag them on every platform.
**Implementation:** Manual tagging, but clip selection can be automated.

---

## Priority Execution Order

**Week 1-2 (Immediate, free):**
1. Post more Shorts (aim for 5-7/week, not 3)
2. Submit RSS to Apple Podcasts, Amazon Music, Podchaser, Listen Notes, Goodpods
3. Create Discord server, add link everywhere
4. Start daily 10-min engagement on Bluesky and Reddit

**Week 3-4 (Automation improvements):**
5. Update AI prompts for better hook-first clip selection
6. Add engagement CTAs to clip captions
7. Set up GitHub Pages website with transcripts
8. Generate and upload podcast trailer

**Month 2 (Growth multiplier):**
9. Start guest swap outreach (5 pitches/week)
10. Join podcast cross-promotion communities
11. Create 30-second promo clip for ad swaps
12. Add native video uploads to Twitter/Bluesky posts

**Month 3+ (Compound growth):**
13. Weekly "question of the week" from Discord
14. Meme quote cards from best lines
15. Monthly "best of" compilations
16. Track what's working, double down

---

## Key Metrics to Track

| Metric | Current | 30-Day Target | 90-Day Target |
|--------|---------|---------------|---------------|
| YouTube subscribers | ~6 | 50 | 500 |
| Spotify listeners | ~6 | 30 | 200 |
| YouTube Shorts avg views | ? | 500 | 5,000 |
| Bluesky followers | 0 | 50 | 300 |
| Episode downloads | ~6 | 30 | 200 |
| Podcast directories | 2 | 8+ | 10+ |

---

*Sources: buzzsprout.com, fame.so, vidiq.com, riverside.fm, metricool.com, podglomerate.com, socialmediatoday.com, rss.com, podcastvideos.com*
