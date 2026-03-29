# Technology Stack — v1.5 New Capabilities Only

**Project:** Podcast Automation (v1.5 — First Paying Client)
**Researched:** 2026-03-28
**Scope:** NEW capabilities only — podcast prospect discovery, outreach copy generation, contact tracking.
         Existing stack is not repeated; see prior milestone STACK for v1.4 and below.

---

## What Already Covers the New Capabilities

Before adding anything, these existing dependencies already cover all three v1.5 areas:

| Existing Dep | Version | Covers |
|---|---|---|
| `requests>=2.31.0` | existing | iTunes Search API calls (no auth required) |
| `feedparser>=6.0.12` | existing (added v1.4) | RSS feed parsing for prospect show metadata + contact extraction |
| `openai>=1.0.0` | existing | GPT-4o for personalized pitch copy generation |
| `jinja2>=3.0.0` | existing | Email/DM template rendering |
| `pyyaml>=6.0.1` | existing | Prospect config files if needed |
| `sqlite3` | stdlib | Contact/prospect CRM database — no new dep needed |

**Result: Zero new packages for v1.5.** All three capability areas build on the existing stack.

---

## Podcast Discovery

### iTunes Search API — raw `requests`, no wrapper library

**Why this over a wrapper library:**
The iTunes Search API requires no API key, no registration, and no SDK. A single `requests.get()` call is all that is needed. The archived `podsearch` library (v0.3.1, last commit 2021, archived February 2026) and similar wrappers add nothing over 10 lines of code with `requests`.

**Confidence:** HIGH — Apple official docs confirm: public endpoint, no auth, 200 results per call.

**Endpoint:**
```
GET https://itunes.apple.com/search?term={query}&media=podcast&genreId={id}&limit=200
```

**Genre IDs for target prospect segments (confirmed from community sources, not in official docs):**

| Genre | genreId | Use |
|---|---|---|
| Comedy | 1303 | Fake Problems-adjacent prospects |
| True Crime | 1488 | Casefile-adjacent prospects |
| Business | 1321 | HIBT-adjacent prospects |
| Technology | 1318 | Future expansion |
| Society & Culture | 1324 | Future expansion |

**Response fields that matter:**
- `collectionName` — show name
- `artistName` — host name(s)
- `feedUrl` — RSS feed URL (pass to feedparser for contact extraction)
- `trackCount` — episode count (proxy for "established but small" show)
- `primaryGenreName` — genre label
- `collectionViewUrl` — Apple Podcasts page URL
- `artworkUrl600` — show artwork

**Size filter heuristic:** No API-level listener count filtering exists. Use `trackCount` between 20–200 to target shows that have traction but are not already at scale. Review count (visible on iTunes show page, not in API response) requires a second lookup or manual check.

**Rate limit:** Apple documents ~20 calls/minute as a soft guideline. Inserting a 2-second sleep between calls is sufficient for a batch of 3-5 genre queries.

### RSS Contact Extraction — existing `feedparser`

**Why feedparser covers this:** Podcast RSS feeds routinely embed host contact info in iTunes extension fields. `feedparser` already normalizes these.

Fields to check in order:
1. `feed.author_detail.email` — from `<managingEditor>` or `<itunes:email>`
2. `feed.feed.get('tags', [])` — some feeds encode social links as categories
3. Regex scan on `feed.feed.description` for `mailto:`, `twitter.com/`, `instagram.com/` patterns

No new library needed. A helper function of ~30 lines covers this completely.

### Why NOT Podcast Index API for v1.5

The Podcast Index API (podcastindex.org) is free but requires HMAC-SHA1 authentication (API key + secret, HMAC header per request). The `python-podcastindex==1.15.0` library wraps this, but:

1. For finding 3-5 prospects, the iTunes API returns the same catalog.
2. Registration + credential management adds setup friction that is not justified for the v1.5 goal.
3. The Podcast Index is a better fit for a batch prospecting tool processing hundreds of shows. That is not v1.5.

**Defer `python-podcastindex` to a future "batch prospecting" milestone** if outreach scales beyond manual targeting.

---

## Outreach Copy Generation

### GPT-4o via existing `openai` SDK — no new package

**Pattern:** New `PitchGenerator` class (`pitch_generator.py`) following the project's `self.enabled` convention. Takes a dict of demo metadata (episode title, clip count, highlight topics from analysis, show summary) plus prospect context (show name, host name, genre, episode count). Returns structured dict with `email_subject`, `email_body`, `twitter_dm`, and optionally `instagram_dm`.

**Two-layer approach:**
1. **Jinja2** (existing) renders the structural skeleton: greeting with host name, sign-off with sender name, CTA linking to demo package, subject line formula.
2. **GPT-4o at temperature 0.7** generates the personalized hook paragraph that references the specific episode processed. This is the part that cannot be templated — "I ran your episode about [topic] through the pipeline and pulled three clips..." requires reading the actual analysis output.

**Why not pure templates:** The prospect has 3-5 outreach messages. Quality beats volume. A form letter referencing no specific episode content is immediately recognizable as mass email and will not convert. GPT-4o costs ~$0.01-0.02 per pitch at this temperature and length, which is acceptable.

**Why not Ollama/Llama3 locally:** The quality gap between Llama 3.1 and GPT-4o is material for persuasive writing. Local inference is the right choice for bulk analytical tasks (topic scoring); GPT-4o is the right choice for high-stakes one-shot copy.

**Confidence:** HIGH — openai SDK already integrated in pipeline, same calling pattern as `ContentEditor`.

---

## Contact Tracking

### stdlib `sqlite3` — no new package

**Why not a CRM library or framework:** Tracking 3-5 contacts does not justify Django-CRM, creme-crm, or any framework. The project already uses `sqlite3` for `EpisodeSearchIndex` (FTS5). The same pattern works here.

**Module:** `prospect_tracker.py` with a `ProspectTracker` class.

**Schema:**

```sql
CREATE TABLE IF NOT EXISTS prospects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    show_name TEXT NOT NULL UNIQUE,
    host_name TEXT,
    rss_url TEXT,
    itunes_url TEXT,
    genre TEXT,
    episode_count INTEGER,
    contact_email TEXT,
    contact_twitter TEXT,
    contact_instagram TEXT,
    status TEXT DEFAULT 'identified',
    demo_path TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS outreach_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER REFERENCES prospects(id),
    channel TEXT,
    subject TEXT,
    body TEXT,
    sent_at TEXT,
    response_received INTEGER DEFAULT 0,
    response_notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
```

**Status lifecycle (stored as TEXT, validated in Python):**
```
identified → demo_processed → demo_packaged → contacted → replied → call_scheduled → client | declined
```

**Storage:** `output/prospects.db` — consistent with `output/` convention for all generated artifacts.

**CLI surface** (new `prospect` subcommand group in `main.py`):
- `uv run main.py prospect search --genre comedy --limit 20`
- `uv run main.py prospect list [--status contacted]`
- `uv run main.py prospect add --show "Show Name" --rss https://...`
- `uv run main.py prospect demo <show-name>` — triggers `package-demo` for that prospect
- `uv run main.py prospect pitch <show-name>` — generates email + DM copy
- `uv run main.py prospect status <show-name> contacted`

**Confidence:** HIGH — exact same sqlite3 pattern as `EpisodeSearchIndex` in `search_index.py`.

---

## New Modules Summary

Three new modules, zero new packages:

| Module | Class | Purpose |
|---|---|---|
| `prospect_finder.py` | `ProspectFinder` | iTunes Search API queries, RSS contact extraction |
| `prospect_tracker.py` | `ProspectTracker` | SQLite CRM — status tracking, outreach log |
| `pitch_generator.py` | `PitchGenerator` | GPT-4o + Jinja2 personalized email/DM generation |

All three follow project conventions: `self.enabled` pattern, `from config import Config`, `from logger import logger`, error handling returns `None` on API failures, raises `ValueError` on missing credentials.

**Test files:** `tests/test_prospect_finder.py`, `tests/test_prospect_tracker.py`, `tests/test_pitch_generator.py`. iTunes API and OpenAI calls mocked; SQLite uses `tmp_path` for real round-trip tests (same pattern as `test_search_index.py`).

---

## Installation (v1.5 diff)

```bash
# No new packages. Verify existing deps are installed:
uv sync
```

---

## What NOT to Add

| Avoid | Why | Use Instead |
|---|---|---|
| `python-podcastindex` | Requires HMAC auth setup; iTunes API covers same corpus for 3-5 prospects | `requests` to iTunes Search API |
| `podsearch` (nalgeon) | Archived February 2026 — dead library | Direct `requests` call (10 lines) |
| `smtplib` / `sendgrid` / `mailchimp` | v1.5 generates copy only; sending is intentionally manual to allow review before sending | Copy written to stdout/file |
| `pandas` or `sqlalchemy` | ORM/DataFrame overhead for a 5-row table | stdlib `sqlite3` directly |
| Rephonic / Podchaser / ListenNotes API | Paid APIs — explicitly out of scope per PROJECT.md constraints | iTunes API + manual review |
| `scrapy` / `playwright` | Web scraping is not needed; iTunes API returns RSS URLs directly | `feedparser` on the RSS URL |
| `aiohttp` | No async needed; pipeline is sequential | `requests` (already present) |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|---|---|---|---|
| Podcast discovery | `requests` to iTunes Search API | `python-podcastindex` | Requires auth setup; iTunes covers same catalog; overkill for 3-5 prospects |
| Contact extraction | `feedparser` fields + regex | Scraping Apple Podcasts show page | RSS feed has the same data without scraping; feedparser already in stack |
| Outreach copy | GPT-4o via `openai` | Pure Jinja2 templates | Templates produce recognizable form emails; GPT-4o generates episode-specific hooks |
| Outreach copy | GPT-4o via `openai` | Ollama/Llama3 locally | Quality gap matters for persuasive writing; cost is ~$0.02/pitch |
| Contact tracking | stdlib `sqlite3` | YAML file | Status mutations and log appends are relational; SQLite is the right tool |
| Contact tracking | stdlib `sqlite3` | Django-CRM / creme-crm | Heavyweight frameworks for a 5-row table |

---

## Sources

- [iTunes Search API Official Docs](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/index.html) — no auth required, 200 limit, genreId parameter confirmed (HIGH confidence)
- [iTunes Search API Examples](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/SearchExamples.html) — parameter structure confirmed (HIGH confidence)
- [iTunes genre IDs community reference](https://publicapis.io/i-tunes-search-api) — genreId values for Comedy (1303), True Crime (1488), Business (1321) confirmed by multiple community sources (MEDIUM confidence — not in official Apple docs)
- [python-podcastindex 1.15.0 on PyPI](https://pypi.org/project/python-podcastindex/) — version and maintenance status confirmed (HIGH confidence), deferred
- [Podcast Index API](https://podcastindex.org/) — free, HMAC auth required, confirmed (HIGH confidence), deferred
- [podsearch-py archived Feb 2026](https://github.com/nalgeon/podsearch-py) — confirmed abandoned, do not use (HIGH confidence)
- [feedparser RSS iTunes namespace docs](https://feedparser.readthedocs.io/en/latest/introduction/) — `author_detail.email` and iTunes tag normalization confirmed (HIGH confidence)
- [Jinja2 email template patterns](https://frankcorso.dev/email-html-templates-jinja-python.html) — existing dep sufficient for template rendering (HIGH confidence)
- [EpisodeSearchIndex sqlite3 pattern](../codebase/ARCHITECTURE.md) — confirmed as the project's precedent for sqlite3 CRM-style storage (HIGH confidence)

---

*Stack research for: v1.5 prospect discovery, outreach generation, contact tracking*
*Researched: 2026-03-28*
