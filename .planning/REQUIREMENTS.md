# Requirements: Podcast Automation

**Defined:** 2026-03-29
**Core Value:** One command produces professional-quality, platform-ready podcast content with genre-appropriate voice and tone — without manual intervention.

## v1.5 Requirements

Requirements for First Paying Client milestone.

### Prospect Discovery

- [x] **DISC-01**: User can search for podcasts by genre and filter by episode count range via CLI
- [x] **DISC-02**: User can enrich a prospect with contact info extracted from their RSS feed (host email, social links)
- [x] **DISC-03**: User can save a prospect as a client YAML config with correct genre settings pre-filled

### Outreach Tracking

- [x] **TRACK-01**: User can add, list, and update prospect status via CLI (identified → contacted → interested → demo_sent → converted/declined)
- [x] **TRACK-02**: User can view a summary of all prospects and their current outreach status

### Pitch Generation

- [x] **PITCH-01**: User can generate a personalized intro message (pre-consent) from prospect metadata via GPT-4o
- [x] **PITCH-02**: User can generate a demo pitch (post-consent) that references the processed episode's specific output

### Demo Production

- [x] **DEMO-04**: User can process a consented prospect's episode and package the demo in one workflow

## v1.6 Requirements

Requirements for Production Quality & Operations milestone.

### Demo Output Quality

- [ ] **DEMO-05**: Pipeline produces clips ranked by a composite quality score (audio energy + content relevance + hook strength)
- [ ] **DEMO-06**: Subtitle clips use genre-appropriate styling (font size, color, animation timing) tuned via autoresearch
- [ ] **DEMO-07**: Thumbnails use contrast-optimized text placement and genre-appropriate color palettes

### Monitoring & Alerting

- [ ] **MON-01**: Pipeline sends Discord alert with error details when any step fails
- [ ] **MON-02**: Pipeline sends Discord summary notification after each successful run (episode name, duration, clip count, platforms uploaded)

### Client Onboarding

- [ ] **ONBOARD-01**: ONBOARDING.md checklist documents every piece of info needed from a new client
- [ ] **ONBOARD-02**: Example client YAML template with inline comments explaining every field

### Clip Selection Optimization

- [ ] **CLIP-05**: AudioClipScorer weights are tunable via client YAML config (energy_weight, content_weight, hook_weight)
- [ ] **CLIP-06**: Scorer weights optimized against historical engagement data using autoresearch iteration

## Future Requirements

### Distribution Expansion

- **DIST-01**: Instagram Reels auto-upload via pipeline
- **DIST-02**: Bluesky posting via atproto SDK
- **DIST-03**: Threads posting via Meta API

### Client Management

- **CLIENT-01**: Web dashboard for client self-service
- **CLIENT-02**: Automated billing/invoicing

## Out of Scope

| Feature | Reason |
|---------|--------|
| Automated mass email sending | Spam risk at 3-5 prospects; manual outreach is correct |
| Paid podcast directory APIs (Rephonic, etc.) | iTunes free tier is sufficient for 3-5 prospects |
| Full CRM system | Over-engineering for 3-5 contacts; SQLite tracker is enough |
| Processing episodes without consent | Legal/ethical risk; consent-first workflow required |
| Filler word removal | Kills comedy timing; degrades interview cadence |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DISC-01 | Phase 20 | Complete |
| DISC-02 | Phase 20 | Complete |
| DISC-03 | Phase 20 | Complete |
| TRACK-01 | Phase 19 | Complete |
| TRACK-02 | Phase 19 | Complete |
| PITCH-01 | Phase 21 | Complete |
| PITCH-02 | Phase 21 | Complete |
| DEMO-04 | Phase 22 | Complete |
| MON-01 | Phase 23 | Pending |
| MON-02 | Phase 23 | Pending |
| ONBOARD-01 | Phase 24 | Pending |
| ONBOARD-02 | Phase 24 | Pending |
| DEMO-05 | Phase 25 | Pending |
| CLIP-05 | Phase 25 | Pending |
| DEMO-06 | Phase 26 | Pending |
| DEMO-07 | Phase 26 | Pending |
| CLIP-06 | Phase 27 | Pending |

**Coverage:**
- v1.5 requirements: 8 total
- v1.5 mapped to phases: 8
- v1.5 unmapped: 0
- v1.6 requirements: 9 total
- v1.6 mapped to phases: 9
- v1.6 unmapped: 0

---
*Requirements defined: 2026-03-29*
*Last updated: 2026-04-06 — v1.6 traceability added after roadmap creation*
