# Phase 1: Foundations - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix silent production bugs and dependency hygiene issues before any feature work begins. Scope: openai SDK dependency, scheduler stub, credential file locations, and naming artifact cleanup. No new features — purely stabilization.

</domain>

<decisions>
## Implementation Decisions

### Scheduler Fix
- Wire real platform uploaders (YouTubeUploader, TwitterUploader, etc.) into `_run_upload_scheduled()` so it actually executes uploads
- On failure: retry 3 times, then mark as failed and send Discord notification via existing `notifications.py`
- Never silently mark uploads as complete — either succeed or fail loudly
- Use existing `retry_utils.py` patterns for retry logic

### Credentials Migration
- Move `google_docs_credentials.json` and `google_docs_token.json` from project root to `credentials/` directory
- Update all code references to use new paths

### Naming Cleanup
- Fix the 3 known items: rename `_parse_claude_response` → `_parse_llm_response`, fix duplicate config reads in `scheduler.py`, move inline `re` imports to module top in `main.py`
- Also fix any other obviously wrong naming encountered during the work, but don't do an exhaustive hunt
- Run ruff check/format on touched files to ensure consistency

### Claude's Discretion
- Whether to also migrate `youtube_token.pickle` to JSON-based storage (assess risk vs. scope)
- Whether to move `NAMES_TO_REMOVE` from `config.py` to `.env` (assess based on repo visibility risk)
- Exact retry count and backoff strategy for scheduler (3 retries is the guideline, Claude picks the implementation)
- Any additional obvious cleanup wins encountered during the work

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. The user wants these fixes done correctly but doesn't have strong opinions on implementation details beyond the decisions captured above.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `retry_utils.py`: Existing retry decorator/utility — use for scheduler retry logic
- `notifications.py` (DiscordNotifier): Already sends webhook notifications — use for scheduler failure alerts
- `credentials/` directory: Already exists with `youtube_credentials.json` and `youtube_token.pickle`

### Established Patterns
- Every module uses `self.enabled` gated by env vars in `config.py` — scheduler fix should follow this pattern
- Pre-commit hook enforces ruff lint + ruff format on staged files
- Test convention: `tests/test_<module>.py` with `class Test<ClassName>` grouping

### Integration Points
- `_run_upload_scheduled()` in `main.py:1559-1606` — the stub to be fixed
- `scheduler.py:17-20` — duplicate env reads to fix (use Config.SCHEDULE_*_DELAY_HOURS instead)
- `content_editor.py:61,263` — `_parse_claude_response` rename locations
- `main.py:1624,1631,1732` — inline `re` import locations

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundations*
*Context gathered: 2026-03-16*
