# Phase 4: Chapter Markers - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Add auto-generated chapter markers to processed episodes. Chapters embedded in MP3 ID3 tags (readable by mp3tag/mutagen) and in the RSS feed (for Apple Podcasts and compatible apps). Scope: new chapter_generator.py module, MP3 tag writing, RSS feed chapter entries. No new platforms or distribution changes.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
User explicitly deferred all implementation decisions to Claude. The following areas are open for Claude to decide based on podcast best practices:

**Chapter Granularity:**
- How many chapters per episode (target range, not fixed)
- Whether to use GPT-4's existing `chapters` field or generate from transcript topic segmentation
- Minimum chapter duration to avoid excessive granularity

**Chapter Title Style:**
- Whether chapter titles use the show's edgy comedy voice (Phase 3 voice) or functional labels
- Recommended: match the show's voice since Phase 3 established the comedy tone throughout

**RSS Format:**
- Which RSS chapter format to use (Podcast Namespace `<podcast:chapters>`, inline timecodes, or both)
- How to integrate with the existing `rss_feed_generator.py`

**MP3 ID3 Tags:**
- Which ID3 chapter tag format to use (CHAP frames, CTOC table of contents)
- Library choice for writing chapter tags (mutagen is the standard Python choice)

**General approach:**
- Leverage the existing GPT-4 analysis which already has a `chapters` field (content_editor.py line 65)
- Chapter titles should feel like the show — Phase 3's voice persona applies here too
- Keep it simple — chapters are a navigation aid, not a feature to over-engineer

</decisions>

<specifics>
## Specific Ideas

- content_editor.py already has `analysis.setdefault("chapters", [])` — the GPT-4 analysis may already produce chapter data
- The comedy voice from Phase 3 (VOICE_PERSONA) should influence chapter titles
- Episode 29 was ~70 minutes — probably 8-12 chapters would be appropriate
- Chapter markers should work in Apple Podcasts (the main target for listener experience)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `content_editor.py:analyze_content()` — Already returns `chapters` field (may be empty list or populated by GPT-4)
- `content_editor.py:VOICE_PERSONA` — Comedy voice system prompt (Phase 3) for chapter title generation
- `rss_feed_generator.py` — Existing RSS feed generation, needs chapter entries added
- `main.py:process_episode()` — Pipeline orchestration, step 6 converts to MP3 (chapter tags go here)

### Established Patterns
- New modules follow flat structure: `chapter_generator.py` at project root
- `self.enabled` pattern gated by env vars in config.py
- Tests in `tests/test_chapter_generator.py` with `class TestChapterGenerator`

### Integration Points
- After content analysis (step 3) produces chapter data
- Before or during MP3 conversion (step 6) — ID3 tags written to the MP3 file
- During RSS feed update (step 7.5) — chapter entries added to feed XML
- `output/ep_N/` directory for any intermediate chapter data files

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-chapter-markers*
*Context gathered: 2026-03-17*
