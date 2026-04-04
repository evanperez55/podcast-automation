# Preschool AI — Deep Dive: Improvements for AI Chat Experience

**Date:** 2026-04-03
**Scope:** RAG pipeline, frontend UX, admin/analytics, performance

---

## Priority Matrix (34 improvements found)

### P0 — Fix These First (broken or actively hurting UX)

| # | Area | Improvement | Why It Matters | Effort |
|---|------|-------------|----------------|--------|
| 1 | **RAG** | **Add conversation history (3 prior turns)** | Every follow-up question is context-free. "What about at bedtime?" after discussing tantrums gets a generic bedtime answer. The LLM receives zero conversation context. | Medium |
| 2 | **Frontend** | **Fix typing animation** (lines 2105-2137) | `typeText()` writes `innerHTML` char-by-char, showing broken HTML tags (`<stro`) mid-render. O(n^2) DOM work. 1000-char response = 15 seconds of garbled output. | Low |
| 3 | **Frontend** | **Add `aria-live` region to chat** | Screen readers miss 100% of responses. Zero accessibility for blind users. | Trivial |
| 4 | **RAG** | **Add safety guardrail to system prompt** | No instruction to redirect medical/developmental concerns to professionals. A parent asking about autism signs gets book advice instead of "consult a pediatrician." | Trivial |

### P1 — High Impact (significantly improve experience)

| # | Area | Improvement | Why It Matters | Effort |
|---|------|-------------|----------------|--------|
| 5 | **RAG** | **Raise similarity threshold to 0.45** | At 0.35, marginally relevant chunks pollute context. Higher bar = more grounded advice. Tune via `SIMILARITY_THRESHOLD` env var, monitor "not covered" rate. | Trivial |
| 6 | **RAG** | **Add hybrid search (BM25 + semantic)** | Pure semantic search fails on exact terminology ("all-powerful self", "loving regulation"). Add `tsvector` column + RRF merge for best of both worlds. | Medium |
| 7 | **RAG** | **Fix age prefix injection** | `[Child age: 4 years]` is embedded WITH the query, polluting the embedding vector. Strip before embedding, inject into system prompt separately. | Low |
| 8 | **Frontend** | **Complete markdown rendering** | Only bold + line breaks work. Bullet lists, headers, italic, links render as raw syntax. Add marked.js (~8KB) or extend regex set. | Low |
| 9 | **Frontend** | **Add Escape key + focus trap to modals** | Keyboard users can't dismiss modals. Tab navigates behind the overlay. | Low |
| 10 | **Frontend** | **Fix comment modal X = submit bug** | X button submits feedback including typed comment. Users clicking X to cancel accidentally submit. Make X = cancel, "Done" = submit. | Trivial |
| 11 | **Admin** | **Content gap detection endpoint** | "Not covered" queries (0 chunks retrieved) are invisible to admins. Every failed query is a signal about what book/topic to add next. Simple SQL: `WHERE retrieved_chunks = 0 GROUP BY user_query`. | Low |
| 12 | **Admin** | **Feedback trends over time** | Current stats are a single aggregate. No way to see if a prompt change helped or hurt. One SQL query + chart. | Low |

### P2 — Medium Impact (polish and depth)

| # | Area | Improvement | Why It Matters | Effort |
|---|------|-------------|----------------|--------|
| 13 | **RAG** | **Increase max_tokens to 1800** | 1200 tokens cuts responses mid-sentence on complex topics (discipline, separation anxiety). Cost difference: ~$0.0005/response. | Trivial |
| 14 | **RAG** | **Switch pgvector index from ivfflat to HNSW** | HNSW has 99%+ recall vs ~90% for ivfflat. No probe tuning needed. `CREATE INDEX ... USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)` | Low |
| 15 | **RAG** | **Add LRU cache for embeddings** | Same common queries ("how to handle tantrums") re-embed every time. 500-entry LRU with 24h TTL saves 200-400ms latency per cache hit. | Low |
| 16 | **RAG** | **Add response structure instruction to prompt** | No guidance on answer structure. Add: "(1) validate concern, (2) explain Smart Love perspective, (3) practical steps, (4) what to expect." | Trivial |
| 17 | **RAG** | **Add conflicting-chunk instruction to prompt** | When chunks from different age ranges retrieved, model may blend inappropriately. Add: "prioritize chunks relevant to the child's stated age." | Trivial |
| 18 | **RAG** | **Query expansion via gpt-4o-mini** | Short queries like "kid won't eat" miss book-language chunks about "food refusal." Lightweight LLM call to generate 2-3 search variants. Adds ~200ms + ~$0.0001. | Medium |
| 19 | **Frontend** | **LLM-generated follow-up suggestions** | Current follow-ups use static templates from 4 keyword categories. Have backend return contextual follow-ups as part of the SSE `done` event. | Medium |
| 20 | **Frontend** | **Section feedback: replace blur-to-submit** | 200ms setTimeout on blur auto-submits partial comments when user tabs away. Replace with explicit submit button (HTML already exists but hidden). | Trivial |
| 21 | **Frontend** | **Feedback confirmation toast** | Success/error silently swallowed (line 1972). Users don't know if feedback saved. Brief "Thanks for your feedback!" toast. | Low |
| 22 | **Frontend** | **"Not covered" visual distinction** | Refusal responses look identical to normal answers. Add amber border or icon so users immediately understand the boundary. | Trivial |
| 23 | **Admin** | **Source/book quality scoring** | Join `chat_feedback.sources` with ratings to find which book chapters produce the most thumbs-down. `SELECT unnest(sources), COUNT(*) FILTER (WHERE rating = 'thumbs_down')` | Low |
| 24 | **Admin** | **Response latency monitoring** | No timing data captured. Add `response_time_ms` column, show avg + p95 on dashboard. Essential for production. | Low |
| 25 | **Admin** | **Quality drop alerting** | No notification when thumbs-down rate spikes. Compare 24h rate vs 7-day average, email/webhook on 2x threshold. | Low |

### P3 — Nice to Have (incremental improvements)

| # | Area | Improvement | Why It Matters | Effort |
|---|------|-------------|----------------|--------|
| 26 | **RAG** | **Prepend chapter name to chunk text before embedding** | Improves retrieval for "what does the discipline chapter say about..." queries. Requires re-ingestion. | Medium |
| 27 | **RAG** | **Increase chunk target size to 1200** | 800 chars splits multi-paragraph explanations. Larger chunks preserve reasoning chains. Test empirically. | Low (re-ingest) |
| 28 | **Frontend** | **Conversation search** | No way to search past conversations. Sidebar just lists them all. | Medium |
| 29 | **Frontend** | **Age selector: allow deselect + visual indicator** | Once selected, can't clear. No badge showing active age context near input. | Low |
| 30 | **Frontend** | **Fix export: says PDF, produces .txt, hidden on mobile** | Misleading label. | Trivial |
| 31 | **Frontend** | **Debounce visualViewport resize handler** | Fires rapidly during keyboard animation, causes layout thrashing. | Trivial |
| 32 | **Frontend** | **Split index.html (2959 lines) into separate files** | CSS (~1500 lines), auth.js, chat.js, feedback.js, sidebar.js, utils.js. | Medium |
| 33 | **Admin** | **User engagement metrics** | Session depth, return visit rate, queries per session. `session_id` column already exists. | Low |
| 34 | **Admin** | **Metadata enrichment during ingestion** | Add topic tags + age ranges per chunk via LLM. Enables filtered retrieval and better analytics. | High |

---

## Deep Dive: Top 5 Improvements

### 1. Conversation History (P0 — currently zero multi-turn support)

**Current state:** `ragService.query()` sends only system prompt + single user message to gpt-4o. No prior exchanges included. `sessionId` is accepted and stored but never used for context retrieval.

**Implementation:**
```javascript
// In ragService.query(), before generateResponse():
const history = await pool.query(
  `SELECT user_query, ai_response FROM chat_feedback
   WHERE session_id = $1 ORDER BY created_at DESC LIMIT 3`,
  [sessionId]
);

const messages = [
  { role: 'system', content: systemPrompt },
  ...history.rows.reverse().flatMap(h => [
    { role: 'user', content: h.user_query },
    { role: 'assistant', content: h.ai_response }
  ]),
  { role: 'user', content: query }
];
```

**Why 3 turns:** At ~1200 tokens/response, 3 prior exchanges add ~5000 tokens. Combined with system prompt (~800) + context chunks (~2000), stays well within gpt-4o's window.

**Files to change:** `ragService.js` (query method + generateResponse/generateResponseStream to accept messages array)

---

### 2. Typing Animation Fix (P0 — broken HTML rendering)

**Current:** `typeText()` iterates HTML string char-by-char, setting `innerHTML` on every character. Users see partial tags like `<stro` as literal text.

**Fix:** Remove `typeText()` entirely. The streaming path already provides real-time token display without jank. For the non-streaming fallback, display the full formatted response instantly (no animation) or animate at the word level after full HTML formatting.

**File:** `frontend/index.html:2105-2137`

---

### 3. Hybrid Search (P1 — catches exact terminology misses)

**Current:** Pure semantic search via pgvector cosine similarity.

**Add BM25 full-text search:**
```sql
ALTER TABLE book_chunks ADD COLUMN tsv tsvector
  GENERATED ALWAYS AS (to_tsvector('english', text)) STORED;
CREATE INDEX idx_book_chunks_tsv ON book_chunks USING gin(tsv);
```

**Merge with Reciprocal Rank Fusion:** Run both queries (top 20 each), combine scores: `1/(60+rank_vector) + 1/(60+rank_bm25)`, take top 8.

**File:** `ragService.js:findSimilarChunks()`

---

### 4. Content Gap Detection (P1 — invisible failed queries)

**Current:** Zero-chunk queries return canned "not covered" response, stored with `retrieved_chunks = 0`, but no admin visibility.

**Add:**
```sql
-- New endpoint: GET /api/admin/content-gaps
SELECT user_query, COUNT(*) AS times_asked, MAX(created_at) AS last_asked
FROM chat_feedback WHERE retrieved_chunks = 0
GROUP BY user_query ORDER BY times_asked DESC LIMIT 50
```

Plus a "Content Gaps" tab in admin dashboard. Every failed query = direct signal about what book/topic to add next.

**File:** `adminRoutes.js` (new endpoint), `admin.html` (new tab)

---

### 5. Safety Guardrail (P0 — missing medical redirect)

**Current system prompt has no instruction about medical/developmental concerns.**

**Add to ragService.js _buildSystemPrompt():**
```
- If the question involves medical symptoms, developmental screening, mental health crises,
  or child safety concerns, always recommend consulting a pediatrician or licensed
  professional. Do not diagnose or prescribe. You can still share relevant Smart Love
  perspectives alongside the professional recommendation.
```

**File:** `ragService.js:53-100`

---

## Implementation Roadmap

**Week 1 (quick wins):**
- Items 2, 3, 4, 5, 10, 13, 16, 17, 20, 21, 22 (all Trivial-Low effort, 11 items)
- Estimated: ~2-3 hours of focused work

**Week 2 (core improvements):**
- Items 1, 7, 8, 9, 11, 12, 14, 15 (Low-Medium effort, 8 items)
- Estimated: ~6-8 hours

**Week 3+ (deeper work):**
- Items 6, 18, 19, 23, 24, 25 (Medium effort)
- Then P3 items as time allows
