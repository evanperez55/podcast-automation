# Requirements: Podcast Automation

**Defined:** 2026-03-29
**Core Value:** One command produces professional-quality, platform-ready podcast content with genre-appropriate voice and tone — without manual intervention.

## v1.5 Requirements

Requirements for First Paying Client milestone.

### Prospect Discovery

- [ ] **DISC-01**: User can search for podcasts by genre and filter by episode count range via CLI
- [ ] **DISC-02**: User can enrich a prospect with contact info extracted from their RSS feed (host email, social links)
- [ ] **DISC-03**: User can save a prospect as a client YAML config with correct genre settings pre-filled

### Outreach Tracking

- [ ] **TRACK-01**: User can add, list, and update prospect status via CLI (identified → contacted → interested → demo_sent → converted/declined)
- [ ] **TRACK-02**: User can view a summary of all prospects and their current outreach status

### Pitch Generation

- [ ] **PITCH-01**: User can generate a personalized intro message (pre-consent) from prospect metadata via GPT-4o
- [ ] **PITCH-02**: User can generate a demo pitch (post-consent) that references the processed episode's specific output

### Demo Production

- [ ] **DEMO-04**: User can process a consented prospect's episode and package the demo in one workflow

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
| DISC-01 | — | Pending |
| DISC-02 | — | Pending |
| DISC-03 | — | Pending |
| TRACK-01 | — | Pending |
| TRACK-02 | — | Pending |
| PITCH-01 | — | Pending |
| PITCH-02 | — | Pending |
| DEMO-04 | — | Pending |

**Coverage:**
- v1.5 requirements: 8 total
- Mapped to phases: 0
- Unmapped: 8 (pending roadmap)

---
*Requirements defined: 2026-03-29*
*Last updated: 2026-03-29 after initial definition*
