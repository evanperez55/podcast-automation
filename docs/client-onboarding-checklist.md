# Client Onboarding Checklist

## Phase 1: Discovery (Before Signup)

- [ ] Client sends us their RSS feed URL
- [ ] We run `research-prospect <slug>` to gather show info, artwork, social handles
- [ ] We process 4 free episodes via `--client <slug> --test latest`
- [ ] Client reviews demo output (clips, blog, captions, thumbnail)
- [ ] Client picks a plan (Starter $49/mo, Pro $99/mo, Agency $199/mo)

## Phase 2: Client Config Setup

- [ ] Run `init-client <slug>` to scaffold YAML + credentials dir
- [ ] Fill in YAML from research:
  - `podcast_name` — exact show name
  - `rss_source.feed_url` — RSS feed URL
  - `content.words_to_censor` — any words to beep out
  - `content.names_to_remove` — host names for diarization
  - `content.num_clips` — 3 (Starter) or 5 (Pro/Agency)
  - `content.clip_min_duration` / `clip_max_duration`
  - `branding.logo_path` — downloaded during research
- [ ] Validate config: `validate-client <slug> --ping`

## Phase 3: Platform Authorization

### Starter Plan (client posts manually)
No platform auth needed. We deliver files, they post.

### Pro/Agency Plan (automated posting)

#### YouTube (HARDEST — requires OAuth consent)
- [ ] **Current:** Client creates Google Cloud project + YouTube API credentials
- [ ] **Future (Neurova OAuth app):** Client clicks authorize link, grants channel access
- [ ] Store token pickle in `clients/<slug>/youtube_token.pickle`
- [ ] Test upload: `--client <slug> --test --dry-run`

#### Instagram (requires Facebook Business)
- [ ] **Current:** Client provides long-lived access token + account ID
- [ ] **Future (Neurova Facebook app):** Client clicks "Connect Instagram"
- [ ] Store in YAML: `instagram.access_token`, `instagram.account_id`
- [ ] Note: Token expires every 60 days — need refresh automation

#### TikTok
- [ ] **Current:** Client creates TikTok developer app
- [ ] **Future (Neurova TikTok app):** Client clicks authorize
- [ ] Store in YAML: `tiktok.access_token`, `tiktok.client_key`, `tiktok.client_secret`

#### Twitter/X
- [ ] **Current:** Client applies for Twitter API access (pay-per-use ~$0.01/tweet)
- [ ] **Future (Neurova Twitter app):** Client authorizes our app via OAuth
- [ ] Store in YAML: `twitter.api_key`, `twitter.api_secret`, `twitter.access_token`, `twitter.access_secret`

#### Bluesky (EASIEST)
- [ ] Client generates an app password at bsky.app/settings
- [ ] We store handle + app password
- [ ] No OAuth, no developer app, no review process

#### Discord (notifications, optional)
- [ ] Client creates webhook in their Discord server
- [ ] Store in YAML: `discord.webhook_url`

## Phase 4: First Live Run

- [ ] Process first real episode: `--client <slug> latest`
- [ ] Verify all outputs generated correctly
- [ ] Verify uploads succeeded on each authorized platform
- [ ] Client confirms quality is acceptable
- [ ] Set up recurring schedule (if applicable)

## Phase 5: Ongoing

- [ ] Monitor upload success via Discord notifications
- [ ] Refresh Instagram token before 60-day expiry
- [ ] Check YouTube API quota usage monthly
- [ ] Respond to any content compliance flags

---

## Friction Reduction Roadmap

### Phase 1: Now (Ayrshare Middleware — days to set up)
- Sign up for Ayrshare ($99/mo for 20 clients, ~$5/client)
- Ayrshare is already approved on every platform — no reviews needed
- Client clicks ONE link to connect all their social accounts via Ayrshare's UI
- We call one API endpoint to post everywhere
- Handles token refresh, rate limits, platform quirks
- **Zero OAuth apps to create, zero platform reviews, zero token management**

### Phase 2: Month 2-4 (Direct Integrations for Key Platforms)
- Build direct Bluesky integration (free, no review, already works)
- YouTube in testing mode (free, <100 users, no audit needed)
- Submit Instagram + TikTok reviews in parallel (2-5 weeks each)
- Keep Ayrshare as fallback for platforms still in review

### Phase 3: Month 4-6 (Full Direct, Drop Ayrshare)
- Migrate to direct integrations as reviews approved
- Google OAuth production verification when 100+ users (requires $15K security audit)
- Build self-service dashboard at neurovai.org/dashboard
- Client signs up, connects platforms via OAuth buttons
- Zero manual config needed

### Cost Comparison
| Approach | Setup Time | Monthly Cost (20 clients) | Client Friction |
|----------|-----------|--------------------------|-----------------|
| Manual (current) | 0 | $0 | HIGH (hours per client) |
| Ayrshare | 1-2 days | $99 | LOW (one link, one click) |
| Direct OAuth | 2-3 months | $200 (Twitter) | LOW (click authorize per platform) |
| Direct + Google prod | 4-6 months | $200 + $15K audit | LOWEST |

---

## Platform Difficulty Ranking (for onboarding)

| Platform | Difficulty | Client Effort | Notes |
|----------|-----------|---------------|-------|
| Bluesky | Easy | 30 seconds | App password in settings |
| Twitter | Medium | 5 minutes | Apply for API, authorize |
| YouTube | Hard | 15 minutes | OAuth consent, channel access |
| Instagram | Hard | 20 minutes | Facebook Business, Graph API |
| TikTok | Hard | 15 minutes | Developer app + review |

### Recommended Onboarding Order
1. Start with Bluesky (instant win, builds confidence)
2. Twitter (quick, cheap)
3. YouTube (biggest value, worth the effort)
4. Instagram (important but painful)
5. TikTok (lowest priority for most clients)
