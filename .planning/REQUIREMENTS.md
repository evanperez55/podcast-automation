# Requirements: Podcast Automation

**Defined:** 2026-03-28
**Core Value:** One command produces professional-quality, platform-ready podcast content that sounds hand-edited and captures the show's voice — without manual intervention.

## v1.4 Requirements

Requirements for Real-World Testing & Sales Readiness milestone.

### Config Hardening

- [x] **CFG-01**: Pipeline uses only per-client config values (no Fake Problems defaults leak to other clients)
- [x] **CFG-02**: User can define genre-specific voice persona, blog voice, and scoring profile per client via YAML
- [x] **CFG-03**: User can run validate-client to see active config values after client activation (names, words, voice, scoring)

### Episode Source

- [x] **SRC-01**: User can download a podcast episode by pointing at a public RSS feed URL
- [x] **SRC-02**: Pipeline runs without Dropbox credentials when episode source is RSS or local file

### Integration Testing

- [x] **TEST-01**: User can process a real true crime episode end-to-end through the pipeline
- [x] **TEST-02**: User can process a real business/interview episode end-to-end through the pipeline
- [x] **TEST-03**: Clip scorer selects genre-appropriate moments (not just high-energy for non-comedy)
- [x] **TEST-04**: Compliance checker applies genre-appropriate sensitivity (stricter for true crime, lighter for comedy)

### Demo Packaging

- [ ] **DEMO-01**: User can run a package-demo command to assemble all pipeline output into a presentable demo folder
- [ ] **DEMO-02**: Demo includes a before/after audio comparison clip (raw vs processed)
- [ ] **DEMO-03**: Demo includes a DEMO.md narrative per client (what was automated, time saved, cost, metrics)

## Future Requirements

### Distribution Expansion

- **DIST-01**: Instagram Reels auto-upload via pipeline
- **DIST-02**: Bluesky posting via atproto SDK
- **DIST-03**: Threads posting via Meta API

### Sales Tooling

- **SALES-01**: White-label output (remove pipeline branding from generated content)
- **SALES-02**: Demo video walkthrough (screen recording + narration, 3-5 min)
- **SALES-03**: Proposal email generator from episode metadata

## Out of Scope

| Feature | Reason |
|---------|--------|
| Filler word removal | Kills comedy timing; degrades interview cadence (confirmed by user feedback) |
| Live upload demo to prospect's platforms | Requires their OAuth credentials; security risk; cannot do in a meeting |
| Real-time processing during demo meeting | 20-40 min Whisper + 5-10 min analysis; no prospect sits through that |
| Dynamic ad insertion | Requires CDN hosting; incompatible with zero-cost constraint |
| Self-serve onboarding UI | CLI-driven workflow; prospects are shown output, not the tool |
| Genre-tuned clip scoring via ML | Dataset too small; empirical tuning via YAML profiles is sufficient |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CFG-01 | Phase 15 | Complete |
| CFG-02 | Phase 15 | Complete |
| CFG-03 | Phase 15 | Complete |
| SRC-01 | Phase 16 | Complete |
| SRC-02 | Phase 16 | Complete |
| TEST-01 | Phase 17 | Complete |
| TEST-02 | Phase 17 | Complete |
| TEST-03 | Phase 17 | Complete |
| TEST-04 | Phase 17 | Complete |
| DEMO-01 | Phase 18 | Pending |
| DEMO-02 | Phase 18 | Pending |
| DEMO-03 | Phase 18 | Pending |

**Coverage:**
- v1.4 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0

---
*Requirements defined: 2026-03-28*
*Last updated: 2026-03-28 after roadmap creation*
