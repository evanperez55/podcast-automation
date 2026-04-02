# Fake Problems Podcast — Growth Strategy Scenarios

**Date:** 2026-03-31
**Seed:** Comedy podcast with 30+ episodes, full automation, no audience traction
**Domain:** Marketing | **Depth:** Deep | **Focus:** Edge-cases/unconventional

---

## THE CORE PROBLEM

You've built an incredible production machine. But production ≠ distribution ≠ discovery. Right now your funnel looks like:

```
[Content] → [Automated posting] → [Void] → [???] → [Audience]
                                    ^^^^^
                              You are here
```

The missing piece is **demand generation** — giving people a reason to seek you out. Below are 50 scenarios organized from highest-impact to experimental.

---

## TIER 1: HIGH-IMPACT, DO THIS WEEK

### S01: The Clip-First Strategy (TikTok/Reels/Shorts)

**Current state:** You're auto-posting clips, but clips need to be **optimized for discovery**, not just cut from the episode.

**What to change:**
1. **Hook in first 1-2 seconds.** Your clips start at the "interesting moment" — but TikTok needs the hook BEFORE the content. Add a text overlay: "Why are lobsters basically immortal?" then cut to the hosts riffing.
2. **Trending audio.** TikTok's algorithm pushes content using trending sounds. Overlay a trending sound at low volume behind your clip, or use the platform's native tools to add it.
3. **Post 3-5 clips per episode, not just the "best" ones.** Volume matters on short-form. Your automation already creates them — post more.
4. **Clip length: 15-30s is too safe.** TikTok rewards 45-90s videos now. Extend `CLIP_MAX_DURATION` to 60s.
5. **Reply to viral videos** with your clips. TikTok "reply" and "stitch" features put your content in front of existing audiences.

**Expected outcome:** 1-2 clips go semi-viral (10K+ views) within 2-3 weeks of consistent posting
**Severity:** CRITICAL — this is your #1 growth lever

### S02: YouTube SEO — Titles & Thumbnails Are Everything

**Current state:** Your episode titles are funny ("Lobsters Are Basically Immortal") but not searchable. Nobody is searching for that.

**What to change:**
1. **Dual-purpose titles.** Format: `[Searchable topic] | [Your funny angle]`. Example: "Are Lobsters Immortal? | Fake Problems Podcast ep32"
2. **Custom thumbnails.** Your auto-generated 1280x720 thumbnails need expressive faces, large text, bright colors. Static logos don't get clicks.
3. **YouTube Shorts descriptions.** Include 3-5 hashtags: #comedy #podcast #shorts #[topic]. Your automation generates `clip_hashtags` — make sure they're in the Shorts description.
4. **Chapters.** You're already generating them — great. YouTube surfaces chaptered content in search results.
5. **End screens + cards.** Link to your best-performing video from every new upload.

**Expected outcome:** YouTube impressions increase 2-5x within a month
**Severity:** CRITICAL

### S03: Spotify Optimization

**Current state:** RSS feed published, Spotify picks it up automatically.

**What to change:**
1. **Claim your Spotify for Podcasters profile.** Add category (Comedy), cover art, description.
2. **Episode descriptions matter for Spotify search.** Your show_notes are good — make sure they include searchable keywords.
3. **Submit episodes to Spotify editorial playlists.** Spotify has a "submit to playlist" feature for podcasters — use it for every episode.
4. **Spotify Q&A and polls.** Engage listeners directly in the Spotify app.

**Expected outcome:** Spotify listens increase 50%+ from baseline
**Severity:** HIGH

---

## TIER 2: COMMUNITY INFILTRATION (DO THIS MONTH)

### S04: Reddit — Your Secret Weapon

**Actors:** Hosts, Reddit communities
**Trigger:** Post authentically in relevant subreddits

**Strategy:**
1. **Don't spam your podcast link.** Reddit hates self-promotion. Instead, participate genuinely in subreddits related to your episode topics.
2. **After building karma, post clips as native video.** r/funny, r/standupcomedy, r/podcasts, r/ContagiousLaughter — whichever fits.
3. **AMA in r/podcasts.** "We're 3 friends who built an AI-powered podcast production pipeline, AMA" — that's genuinely interesting to that community.
4. **Topic-specific subreddits.** If you discussed lobster immortality, post in r/todayilearned with the fact. Don't even mention the podcast. Just build presence.

**Expected outcome:** 1-2 Reddit posts gain traction, driving 50-200 new listeners
**Severity:** HIGH

### S05: Discord & Community Servers

**Strategy:**
1. **Join podcast-related Discord servers.** Share clips, participate in feedback channels.
2. **Create your own Discord.** Even with 10 members, a Discord creates a core fan community who will share your content.
3. **Live listening parties.** Drop new episodes in Discord, react together in real-time.

**Expected outcome:** 10-30 engaged community members within a month
**Severity:** MEDIUM

### S06: Twitter/X Engagement Strategy

**Current state:** Auto-posting episode announcements.

**What's missing:** Announcements to nobody are just noise. You need **engagement**.
1. **Quote-tweet other comedy podcasters.** Add your take. Build relationships.
2. **Thread your best bits.** Turn episode highlights into a Twitter thread: "5 things we learned about lobster immortality (thread)" — link to full episode at the end.
3. **Engage in trending topics.** When a topic you've covered trends, reply with your take + clip.
4. **Post polls.** "Do lobsters deserve immortality? Yes / Absolutely yes" — drives engagement, no link needed.

**Expected outcome:** Tweet impressions 5-10x, follower growth
**Severity:** MEDIUM

---

## TIER 3: COLLABORATION (BIGGEST UNLOCK)

### S07: Guest on Other Podcasts

**This is the single highest-ROI activity for podcast growth.**

**Strategy:**
1. **Find comedy podcasts with 500-5000 listeners** (your tier, not Joe Rogan). Use ListenNotes, Podchaser, or your own `prospect_finder.py`.
2. **Pitch yourself as a guest.** "We run a comedy podcast about fake problems — we'd love to come riff with you for an episode."
3. **Cross-promote.** When you guest on their show, their listeners discover you. When they guest on yours, vice versa.
4. **Target 1-2 guest appearances per month.**

**Expected outcome:** Each guest appearance brings 20-100 new listeners who already like the format
**Severity:** CRITICAL — this is the #1 proven podcast growth strategy

### S08: Invite Guests to Your Show

**Strategy:**
1. **Micro-influencers** in your niche (comedy Twitter, TikTok creators with 5K-50K followers).
2. **The guest promotes the episode to THEIR audience.** This is the growth mechanism.
3. **Make it easy for guests to share.** Send them pre-made clips of their best moments.

**Expected outcome:** Guest's audience discovers your show; 10-50 new subscribers per guest
**Severity:** HIGH

### S09: Podcast Swap / Trailer Exchange

**Strategy:**
1. Find 3-5 podcasts in adjacent niches (comedy, pop culture, debate shows).
2. Record a 60-second promo for each other's shows.
3. Run the promo as a mid-roll or post-roll.
4. Your automation already handles the audio pipeline — injecting a promo trailer is trivial.

**Expected outcome:** Free advertising to an already-engaged podcast audience
**Severity:** HIGH

---

## TIER 4: CONTENT STRATEGY SHIFTS

### S10: The "Clip that Explains the Show" — Pin It Everywhere

**Problem:** New visitors don't know what your show is. Your best clip should be pinned on every platform profile as a "start here" intro.

**Action:** Create a 60-second "best of" highlight reel. Pin it on TikTok, Instagram, Twitter, YouTube channel trailer.

### S11: Topical Episodes — Ride the News Cycle

**Strategy:** When something absurd happens in the news, record a quick response episode or bonus clip. Timeliness + comedy = shareability.

**Example:** If "lobster rights" trends on Twitter, you should have a clip ready within hours, not days.

### S12: Episode Titles as Hooks, Not Descriptions

**Current titles (good voice but low search):**
- "Lobsters Are Basically Immortal and Honestly Good for Them"

**Better for discovery:**
- "The Animal That Can't Die (And Why Scientists Are Confused)"
- "Why Lobsters Live Forever | Fake Problems Podcast"

The title's job is to get CLICKS from people who don't know you yet. The funny voice comes through in the content.

### S13: Create a "Best Of" Compilation

**Strategy:** Compile your funniest 10 minutes across 30 episodes into one video. Title it "Fake Problems Podcast — Best Moments (30 Episodes)". This is your most shareable piece of content.

### S14: Consistent Release Schedule + Pre-Announcement

**Strategy:** 
1. Pick a day (e.g., every Thursday).
2. Announce it: "New episode every Thursday" in bio, outro, everywhere.
3. Post a teaser clip the day before: "Tomorrow's episode: [hook]"
4. Your content_calendar already supports staggered posting — use the teaser slot.

### S15: Cold Open Hook

**Strategy:** Start every episode with the funniest 15-second moment from later in the episode, THEN do the intro. This is standard in successful comedy podcasts and TV. It immediately hooks listeners who sample your show.

---

## TIER 5: PLATFORM-SPECIFIC EDGE CASES

### S16: YouTube Shorts → Full Episode Funnel

**The strategy:** Shorts are discovery. Full episodes are retention. Connect them.
1. Every Short should end with: "Full episode linked above" (pinned comment with link)
2. Use YouTube's "clip" feature to link Shorts to the timestamp in the full episode
3. End screen on Shorts pointing to full episode

### S17: TikTok Series Feature

**Strategy:** TikTok lets you create "series" — organize your clips by episode or topic. "Fake Problems: Animals" series, "Fake Problems: Healthcare" series. Makes your profile browseable.

### S18: Instagram Carousels

**Strategy:** Turn your best quotes into carousel posts (text on colorful backgrounds). These get way more reach than video on Instagram's feed algorithm. Your blog_generator already extracts quotes — repurpose them.

### S19: Spotify Video Podcasts

**Strategy:** Spotify now supports video podcasts. Upload your full episode MP4 to Spotify for Podcasters. Video podcasts get preferential placement in Spotify's browse.

### S20: Apple Podcasts — Don't Ignore It

**Strategy:** Your RSS feed works on Apple Podcasts automatically, but:
1. Claim your show on Apple Podcasts Connect
2. Set the right category (Comedy > Comedy Interviews or Stand-Up)
3. Ask listeners to rate & review — Apple's algorithm heavily weights ratings

---

## TIER 6: UNCONVENTIONAL / GUERRILLA

### S21: The "Overheard" Strategy

**Strategy:** Post your funniest quotes as text-only posts on Twitter, Reddit, and Instagram — without mentioning the podcast. Just the quote. Let it go viral on its own. When people ask "where is this from?" — that's your hook.

**Example post:** "turns out immortality is real, it just only applies to lobsters" — no link, no promo, just the line. Bio links to podcast.

### S22: Make a Meme Account

**Strategy:** Create a separate meme account that posts comedy memes in your niche. Build followers on memes (easy growth). Occasionally cross-promote: "we also have a podcast btw."

### S23: The "Episode Title" A/B Test

**Strategy:** Post the same clip twice with different titles/hooks on TikTok. See which performs better. Use the winner's style for future titles. Your automation makes this trivial — just post the same clip with two different captions.

### S24: Newsletter / Email List

**Strategy:** Start a simple email list (free Substack or Buttondown). Send a weekly email with:
- This week's episode + best clip
- A funny one-liner about next week's topic
- A "fake problem of the week" from listeners

Email is the only channel you OWN. Algorithms can't take it away.

### S25: The "Fake Problem of the Day" Social Content

**Strategy:** Post a daily "fake problem" on Twitter/Instagram that's NOT from the podcast — just a funny observation. Build a brand around the concept, not just the show. When the brand grows, the show grows.

**Examples:**
- "Fake Problem: My ice cream melted before I finished my existential crisis"
- "Fake Problem: I can't find a parking spot at the gym so I guess I'll stay unhealthy"

### S26: TikTok Live

**Strategy:** Go live on TikTok and riff on fake problems with the chat. TikTok pushes live streams to followers aggressively. Even 5 viewers creates engagement.

### S27: Submit to Podcast Awards / Lists

**Strategy:** Submit to:
- Apple Podcasts "New & Noteworthy" (automatic for new shows, but claim your profile)
- Podcast Awards (podcastawards.com)
- "Best Comedy Podcasts" listicles — email the authors and pitch your show
- Podchaser lists

### S28: Cross-Post Full Episodes to YouTube as Podcast

**Strategy:** YouTube has a dedicated Podcasts section. Tag your uploads as podcast content (YouTube Studio → Content → Podcast). This gets you into YouTube's podcast discovery feed.

### S29: Leverage Your Tech Story

**Strategy:** Your automated production pipeline is genuinely interesting. Write about it:
- Post on Hacker News: "I built an AI-powered podcast production pipeline"
- Write a dev.to or Medium article
- Post on r/SideProject, r/Python, r/MachineLearning

This gets tech-audience attention, and tech people listen to podcasts.

### S30: The "One Perfect Clip" Strategy

**Strategy:** Instead of posting 3 mediocre clips, invest in making ONE clip per episode absolutely perfect:
- Custom hook text overlay
- Perfect cut timing (start mid-laugh, end on punchline)
- Engaging caption written by a human, not AI
- Post it at peak hours (7-9 PM your timezone)

One viral clip > 10 invisible ones.

---

## TIER 7: GROWTH MULTIPLIERS (AFTER TIER 1-3 WORKING)

### S31-S35: Paid Growth (When Ready)

- **S31:** Boost your best-performing TikTok/Reel ($5-10 gets 1000+ views)
- **S32:** Reddit ads targeting podcast subreddits ($20/day test)
- **S33:** Overcast ads (podcast-specific ad network, pay per listen)
- **S34:** Sponsor a newsletter in your niche
- **S35:** Instagram story ads with your best clip

### S36-S40: Listener Activation

- **S36:** "Share this episode" CTA at the end of every episode — most podcasts forget this
- **S37:** Listener voicemail segment — play listener-submitted fake problems
- **S38:** Referral rewards — "Tell a friend, we'll shout you out"
- **S39:** Clip contest — "Make a clip from our episode, best one gets featured"
- **S40:** Merch (even free stickers) — physical brand presence

### S41-S45: SEO & Long-Tail

- **S41:** Blog posts are already generated — optimize them for SEO keywords
- **S42:** Create a YouTube playlist per topic ("Animals", "Healthcare", "Tech")
- **S43:** Transcripts on your website (you already have them — publish them for Google indexing)
- **S44:** Answer Quora questions related to your episode topics, link to episode
- **S45:** Wikipedia-style "Fake Problems" page on your site — Google loves reference content

### S46-S50: Experimental

- **S46:** AI-generated animated clips (use your transcript to generate simple animations)
- **S47:** Podcast network — join a small comedy podcast network for cross-promotion
- **S48:** Live show — even a small venue or Twitch stream creates content + community
- **S49:** "React to our podcast" — send clips to reaction YouTubers
- **S50:** Seasonal special — holiday-themed fake problems episode for discoverability
