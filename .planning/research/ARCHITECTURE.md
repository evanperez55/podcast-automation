# Architecture Patterns: Prospect Discovery & Outreach Tooling (v1.5)

**Domain:** Prospect research, outreach template generation, contact tracking
**Researched:** 2026-03-28
**Overall confidence:** HIGH (direct codebase inspection + verified external API knowledge)

---

## Context: Existing Architecture (post-v1.4)

The pipeline as-built provides all the infrastructure these new features can reuse.
Nothing below changes any existing processing path.

```
main.py (CLI shim, 216 lines)
    _handle_client_command() — dispatch table for all non-episode commands
    |
    +-- existing commands: package-demo, process-all, init-client, list-clients,
    |                      validate-client, status, setup-client
    |
pipeline/runner.py → pipeline/steps/ (ingest, analysis, audio, video, distribute)
client_config.py    — activate_client() applies clients/<name>.yaml → Config
demo_packager.py    — reads pipeline output → demo/<client>/<ep_id>/
rss_episode_fetcher.py — feedparser-based RSS fetch (already ships)
search_index.py     — SQLite FTS5 (establishes raw-SQL, no-ORM pattern)
analytics.py        — JSON file persistence per episode (simpler pattern)
config.py + logger.py — cross-cutting, all modules import these
```

**Key structural facts:**
- `clients/<name>.yaml` is the canonical identity record for each client/prospect
- `demo/<client>/<ep_id>/` is the output of `package-demo` — already contains
  `DEMO.md`, `summary.html`, `clips/`, `captions.txt`, `show_notes.txt`
- feedparser is already a dependency (`rss_episode_fetcher.py` uses it)
- OpenAI GPT-4o is already used (`content_editor.py`, `blog_generator.py`)
- SQLite is already in the project (`search_index.py` — raw SQL, no ORM)

---

## Recommended Architecture

Three new standalone modules. Zero pipeline changes. All surface as new CLI
commands added to `main.py`'s existing dispatch table.

```
main.py
  existing: package-demo, process-all, init-client, …
  NEW: find-prospects      → prospect_finder.py
  NEW: add-prospect        → prospect_finder.py (manual add)
  NEW: gen-pitch           → pitch_generator.py
  NEW: outreach            → outreach_tracker.py (subcommands: log, list, update)

New top-level modules (flat structure — matches project convention):
  prospect_finder.py      Discover + persist prospect metadata
  pitch_generator.py      GPT-4o pitch emails/DMs from demo output
  outreach_tracker.py     SQLite contact log with status tracking

New test files:
  tests/test_prospect_finder.py
  tests/test_pitch_generator.py
  tests/test_outreach_tracker.py
```

---

## Component Boundaries

### `prospect_finder.py` — ProspectFinder

**Responsibility:** Search the iTunes Search API for podcast shows matching
genre/term criteria. Enrich results by parsing the show's RSS feed via
feedparser (already a project dependency) to extract contact signals. Write a
`prospect:` block into the client's YAML file. Register the prospect in the
outreach database.

**Communicates with:**
- iTunes Search API — free, unauthenticated, returns feedUrl + metadata
- feedparser — parse show RSS for email, website, episode recency
- `client_config.py:init_client()` — bootstraps the YAML stub if client doesn't exist yet
- `outreach_tracker.py:OutreachTracker` — inserts prospect row after discovery

**Key method signatures:**
```python
class ProspectFinder:
    def __init__(self):
        self.enabled = True  # no external credentials needed for search

    def search(self, term: str, genre_id: int = None, limit: int = 20) -> list[dict]
    # Calls: https://itunes.apple.com/search?term=<term>&media=podcast&limit=<n>
    # Returns list of raw iTunes result dicts

    def enrich_from_rss(self, feed_url: str) -> dict
    # feedparser parse of feed_url
    # Returns: {contact_email, website, last_pub_date, episode_count}

    def save_prospect(self, slug: str, itunes_data: dict, rss_data: dict) -> Path
    # Appends prospect: block to clients/<slug>.yaml
    # Returns: path to YAML file
```

**Data persisted to YAML** (`prospect:` block — ignored by `_YAML_TO_CONFIG`):
```yaml
prospect:
  itunes_id: "123456789"
  feed_url: "https://feeds.example.com/show.xml"
  genre: "True Crime"
  episode_count: 87
  last_pub_date: "2026-02-15"
  contact_email: "host@example.com"   # from itunes:email if present
  website: "https://exampleshow.com"
  notes: ""
```

The `prospect:` key is not in `_YAML_TO_CONFIG`, so `activate_client()` silently
ignores it. No changes to `client_config.py` needed.

**iTunes API facts** (HIGH confidence — official Apple docs):
- Endpoint: `https://itunes.apple.com/search?term=<q>&media=podcast`
- Returns: `collectionName`, `artistName`, `feedUrl`, `primaryGenreName`,
  `trackCount`, `releaseDate`, `artworkUrl600`, `collectionId`
- Auth: none required
- Does NOT return subscriber counts or download metrics — not available
  from any free API
- Useful proxy for "small indie show": `trackCount` 50–300 + `releaseDate`
  within 60 days = active, established, independent

**feedparser facts** (HIGH confidence — project dependency since v1.4):
- `feed.feed.itunes_email` or `feed.feed.author_detail.email` — host email
- `feed.feed.link` — podcast website
- `feed.entries[0].published` — most recent episode date
- `len(feed.entries)` — episode count (capped at feed's window, usually 100–300)

---

### `pitch_generator.py` — PitchGenerator

**Responsibility:** Read the packaged demo folder for a prospect
(`demo/<client>/<ep_id>/`) plus the client YAML's `prospect:` block, and
produce a personalized outreach email and DM-length pitch using GPT-4o.
Write output to `demo/<client>/<ep_id>/PITCH.md`.

**Communicates with:**
- `demo/<client>/<ep_id>/DEMO.md` — time-saved metrics, step list
- `output/<client>/<ep_id>/*_analysis.json` — episode title, summary
- `clients/<client>.yaml` — podcast name, host info, contact email
- OpenAI GPT-4o — same client and pattern as `content_editor.py`

**Key method signatures:**
```python
class PitchGenerator:
    def __init__(self):
        self.enabled = bool(getattr(Config, "OPENAI_API_KEY", None))

    def generate_pitch(self, client_name: str, episode_id: str) -> dict
    # Returns: {"subject": str, "email": str, "dm": str}

    def save_pitch(self, client_name: str, episode_id: str, pitch: dict) -> Path
    # Writes demo/<client>/<ep_id>/PITCH.md
    # Returns: path to written file
```

**Prompt construction** (same f-string approach as `content_editor.py`):
The system prompt establishes the role: "You are writing outreach for a podcast
production service." The user message passes structured context — podcast name,
episode title, episode summary, metrics from DEMO.md (time saved, cost per
episode, step count). The model writes the email and DM. Temperature 0.7
(slightly creative — pitch copy, not analysis).

**Cost estimate:** ~500–800 output tokens per prospect → ~$0.01–0.02 each
using GPT-4o pricing. No new API keys needed.

---

### `outreach_tracker.py` — OutreachTracker

**Responsibility:** Lightweight SQLite contact log. Tracks each prospect
(identity) and each outreach attempt (events). Follows the `search_index.py`
pattern exactly: raw SQL, no ORM, single shared DB file.

**Database location:** `output/outreach.db` — single shared file across all
prospects. Not inside any per-client output folder.

**Communicates with:** Nothing external. Pure SQLite.

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS prospects (
    client_slug   TEXT PRIMARY KEY,
    podcast_name  TEXT,
    contact_email TEXT,
    website       TEXT,
    itunes_id     TEXT,
    genre         TEXT,
    episode_count INTEGER,
    created_at    TEXT,   -- ISO 8601
    notes         TEXT
);

CREATE TABLE IF NOT EXISTS contacts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    client_slug   TEXT NOT NULL REFERENCES prospects(client_slug),
    channel       TEXT NOT NULL,   -- 'email' | 'twitter_dm' | 'instagram_dm' | 'linkedin'
    status        TEXT NOT NULL,   -- 'sent' | 'replied' | 'demo_sent' |
                                   -- 'negotiating' | 'closed_won' | 'closed_lost'
    contacted_at  TEXT NOT NULL,   -- ISO 8601
    notes         TEXT
);
```

**Key method signatures:**
```python
class OutreachTracker:
    def __init__(self, db_path: str = None):
        # db_path defaults to str(Config.OUTPUT_DIR / "outreach.db")
        self.enabled = True

    def add_prospect(self, client_slug: str, data: dict) -> None
    def log_contact(self, client_slug: str, channel: str, status: str,
                    notes: str = "") -> None
    def update_status(self, client_slug: str, status: str) -> None
    def list_prospects(self, status_filter: str = None) -> list[dict]
    def get_prospect(self, client_slug: str) -> Optional[dict]
```

---

## Data Flow

```
STEP 1 — Discover
  uv run main.py find-prospects --term "true crime" --limit 20

  ProspectFinder.search("true crime", limit=20)
    → iTunes API: https://itunes.apple.com/search?term=true+crime&media=podcast
    → returns 20 candidates with feedUrl, trackCount, releaseDate

  User reviews printed list, selects 3-5 slugs
  For each selected slug:
    ProspectFinder.enrich_from_rss(feed_url)   → contact_email, website
    ProspectFinder.save_prospect(slug, ...)    → clients/<slug>.yaml (with prospect: block)
    OutreachTracker.add_prospect(slug, ...)    → output/outreach.db


STEP 2 — Process episode (EXISTING PIPELINE — no changes)
  uv run main.py latest --client <slug>           (or rss-based if feed_url set)
  uv run main.py package-demo <slug> <ep_id>

  Output: demo/<slug>/<ep_id>/DEMO.md
          demo/<slug>/<ep_id>/summary.html
          demo/<slug>/<ep_id>/clips/
          output/<slug>/<ep_id>/*_analysis.json


STEP 3 — Generate pitch
  uv run main.py gen-pitch <slug> <ep_id>

  PitchGenerator.generate_pitch(<slug>, <ep_id>)
    → reads demo/<slug>/<ep_id>/DEMO.md           (metrics)
    → reads output/<slug>/<ep_id>/*_analysis.json (episode title + summary)
    → reads clients/<slug>.yaml (prospect: block) (podcast name, contact)
    → GPT-4o → {"subject": ..., "email": ..., "dm": ...}

  PitchGenerator.save_pitch(...)
    → writes demo/<slug>/<ep_id>/PITCH.md


STEP 4 — Track outreach (MANUAL, after sending)
  uv run main.py outreach log <slug> --channel email --status sent --notes "Sent to host@show.com"
  uv run main.py outreach list
  uv run main.py outreach list --status replied
  uv run main.py outreach update <slug> --status negotiating
```

---

## Integration Points: New vs Modified

### New files (create from scratch)

| File | What it is |
|------|-----------|
| `prospect_finder.py` | ProspectFinder class: iTunes search + feedparser enrichment + YAML write |
| `pitch_generator.py` | PitchGenerator class: GPT-4o pitch from demo output |
| `outreach_tracker.py` | OutreachTracker class: SQLite contact log |
| `tests/test_prospect_finder.py` | Unit tests — mock requests, mock feedparser |
| `tests/test_pitch_generator.py` | Unit tests — mock OpenAI, mock file reads |
| `tests/test_outreach_tracker.py` | Unit tests — real SQLite with tmp_path (search_index.py pattern) |

### Modified files (existing, targeted additions only)

| File | What changes |
|------|-------------|
| `main.py` | Add `find-prospects`, `add-prospect`, `gen-pitch`, `outreach` (with subcommands) to `_handle_client_command()` |
| `clients/example-client.yaml` | Add commented `prospect:` block with documented fields |

### Files that stay untouched

| File | Why untouched |
|------|--------------|
| `pipeline/runner.py` | Prospect tooling is pre-pipeline; no step changes needed |
| `pipeline/steps/` (all) | Discovery and outreach are outside the processing loop |
| `client_config.py` | `prospect:` keys in YAML are not in `_YAML_TO_CONFIG`; silently ignored |
| `demo_packager.py` | Already produces the input that `gen-pitch` reads |
| `rss_episode_fetcher.py` | ProspectFinder calls feedparser directly (simpler than the full fetcher) |
| `config.py` | No new env vars needed for these three modules |

---

## Build Order

Dependencies drive the order. Each phase can be tested in isolation before the next begins.

```
Phase 1 — OutreachTracker (no external deps, establishes data store)
  - SQLite schema: prospects + contacts tables
  - CRUD methods: add_prospect, log_contact, update_status, list_prospects
  - tests/test_outreach_tracker.py (real SQLite + tmp_path)
  - CLI: outreach log / list / update in main.py
  Rationale: no external API, no file dependencies — verifiable immediately

Phase 2 — ProspectFinder (depends on Phase 1 for persistence)
  - iTunes Search API call (requests, already dep)
  - feedparser RSS enrichment (already dep)
  - YAML write of prospect: block
  - Calls OutreachTracker.add_prospect() after save
  - tests/test_prospect_finder.py (mock requests + mock feedparser)
  - CLI: find-prospects and add-prospect in main.py
  Rationale: OutreachTracker must exist first; iTunes API has no auth so no setup needed

Phase 3 — PitchGenerator (depends on Phase 2 for demo output to exist)
  - GPT-4o prompt construction from DEMO.md + analysis JSON + YAML
  - PITCH.md output into demo folder
  - tests/test_pitch_generator.py (mock OpenAI, mock Path reads)
  - CLI: gen-pitch in main.py
  Rationale: requires a real packaged demo to test end-to-end; do after Phase 2
             validates that prospect YAMLs and demo output are present

Phase 4 — Manual end-to-end validation
  - Run find-prospects, select 2-3 real shows
  - Process one episode per prospect (existing pipeline)
  - package-demo per prospect
  - gen-pitch per prospect
  - Review PITCH.md quality, iterate prompt if needed
  - log outreach contacts as they're sent
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Prospect identity in a separate DB table independent of YAML
**What goes wrong:** Two sources of truth for the same entity. YAML controls
`--client <name>` activation; a separate DB with duplicate identity fields
diverges over time.
**Instead:** The `prospect:` block in `clients/<slug>.yaml` is canonical for
identity. `outreach.db` tracks *events* (contacts), not identity. ProspectFinder
writes YAML; OutreachTracker reads only the slug as a foreign key.

### Anti-Pattern 2: Putting discovery logic inside pipeline steps
**What goes wrong:** Discovery is pre-pipeline work. Pipeline steps assume a
provisioned client. Mixing them violates the invariant that steps run only after
`activate_client()` has been called and episode audio exists.
**Instead:** Standalone CLI commands only. The pipeline is untouched.

### Anti-Pattern 3: Jinja2 templates for pitch generation
**What goes wrong:** Template-with-blanks pitches feel generic. A merge field
for `{{podcast_name}}` doesn't produce a personalized pitch — it produces a
mail-merge.
**Instead:** Pass all demo metrics and episode context as structured input to
GPT-4o. Let the model write the pitch using real context. Same approach as
`content_editor.py`. The model produces better copy than any template.

### Anti-Pattern 4: Live RSS fetch inside gen-pitch
**What goes wrong:** Adds unexpected network latency and a failure point to
pitch generation. Pitch generation should be purely offline from data already
collected.
**Instead:** RSS enrichment happens once during `find-prospects` or
`add-prospect` and is cached in the `prospect:` YAML block.
`PitchGenerator.generate_pitch()` reads from YAML and local files only.

### Anti-Pattern 5: Storing outreach.db inside a per-client output directory
**What goes wrong:** The database tracks relationships across all prospects.
Putting it inside one client's folder is semantically wrong and makes
cross-prospect queries awkward.
**Instead:** `output/outreach.db` at the root output level — shared across all
prospects, same directory as the existing `podcast_automation.log`.

---

## Scalability Considerations

| Concern | 3-5 prospects (v1.5 target) | 20-50 prospects | 200+ prospects |
|---------|---------------------------|-----------------|----------------|
| Prospect storage | YAML per client — fine | YAML per client — fine | Consider DB migration |
| Contact tracking | SQLite — fine | SQLite — fine | SQLite — still fine |
| Pitch generation | Manual trigger — fine | Batch script — fine | Queue-based |
| iTunes API calls | Trivial | Fine | Fine (low volume) |

Current v1.5 target is 3-5 prospects. YAML + SQLite is correct at this scale.
No abstraction warranted.

---

## External API Notes

**iTunes Search API** (HIGH confidence — official Apple docs verified):
- Base: `https://itunes.apple.com/search?term=<q>&media=podcast&limit=<n>`
- Optional: `&genreId=<id>` for genre filtering (1488=True Crime, 1318=Technology,
  1301=Arts, 1304=Education, 1321=Business, 1316=Comedy)
- Response fields of interest: `collectionName`, `artistName`, `feedUrl`,
  `primaryGenreName`, `trackCount`, `releaseDate`, `artworkUrl600`, `collectionId`
- Auth: none. Rate limits: not published; ~20 req/min is safe in practice.
- Does not provide subscriber counts, download numbers, or listener metrics.
  `trackCount` + `releaseDate` recency is the best available proxy.

**feedparser** (HIGH confidence — already project dependency):
- `feed.feed.author_detail.email` or `feed.feed.itunes_email` — host contact
- `feed.feed.link` — podcast website
- `feed.entries[0].published` — most recent episode date
- `len(feed.entries)` — episode count visible in feed window

**OpenAI GPT-4o** (HIGH confidence — already used in project):
- Same `OPENAI_API_KEY` env var, same client pattern
- Cost: ~$0.01–0.02 per pitch (500–800 output tokens)

---

## Sources

- Direct code inspection: `main.py`, `demo_packager.py`, `client_config.py`,
  `clients/example-client.yaml`, `search_index.py`, `rss_episode_fetcher.py`,
  `pipeline/runner.py`, `pipeline/context.py`, `content_editor.py`
- iTunes Search API: https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/index.html
- iTunes Search API examples: https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/SearchExamples.html
- feedparser: project dependency, direct inspection of `rss_episode_fetcher.py`

---

*Architecture research for: v1.5 First Paying Client — Prospect Discovery & Outreach Tooling*
*Researched: 2026-03-28*
