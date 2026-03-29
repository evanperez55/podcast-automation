# Phase 20: Prospect Finder - Research

**Researched:** 2026-03-28
**Domain:** iTunes Search API, feedparser RSS contact extraction, YAML client scaffolding, OutreachTracker integration
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md / STATE.md)

### Locked Decisions
- [v1.5 stack]: Zero new packages — requests (iTunes), feedparser (RSS), sqlite3 (tracker)
- [v1.5 architecture]: OutreachTracker built first — data store must exist before ProspectFinder can persist discoveries
- [v1.5 consent]: Process prospect episode only after explicit consent; contact-first workflow required
- [Phase 19-outreach-tracker]: Shipped — OutreachTracker at `outreach_tracker.py`, DB at `output/outreach.db`, `add_prospect(slug, data)` method available

### Claude's Discretion
- CLI command name: `find-prospects` (confirmed in ARCHITECTURE.md)
- Genre ID set to pre-populate in YAML (Comedy=1303, True Crime=1488, Business=1321 from community sources)
- YAML `prospect:` block field names and structure

### Deferred Ideas (OUT OF SCOPE)
- Automated email sending
- Full CRM
- Podcast Index API (requires HMAC auth)
- Listen Notes API (not needed; iTunes covers same corpus for 3-5 prospects)
- Rephonic/Podchaser/ListenNotes paid APIs
- Pitch generation (Phase 21)
- Demo production workflow (Phase 22)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DISC-01 | User can search for podcasts by genre and filter by episode count range via CLI | iTunes Search API `genreId` + `trackCount` client-side filter; `find-prospects` CLI command dispatched from `_handle_client_command()` |
| DISC-02 | User can enrich a prospect with contact info extracted from their RSS feed (host email, social links) | feedparser `feed.feed.itunes_email` / `author_detail.email` + regex scan for social links; `enrich-prospect` CLI subcommand or auto-enrichment in save flow |
| DISC-03 | User can save a prospect as a client YAML config with correct genre settings pre-filled | `prospect_finder.save_prospect()` creates `clients/<slug>.yaml` via `init_client()` then appends `prospect:` block + pre-fills `content.voice_persona`, `content.scoring_profile`, `rss.categories` by genre |
</phase_requirements>

---

## Summary

Phase 20 builds `prospect_finder.py` — a `ProspectFinder` class that wraps three operations: (1) query the iTunes Search API to discover podcast shows by genre with episode count filtering, (2) enrich a selected show by parsing its RSS feed for host email and social links, and (3) scaffold a ready-to-use `clients/<slug>.yaml` with genre-appropriate content settings pre-filled, then register the prospect in the existing `OutreachTracker`.

The full stack for this phase is already in the project: `requests` (iTunes API), `feedparser` (RSS enrichment), `pyyaml` (YAML write), and `outreach_tracker.OutreachTracker` (Phase 19, shipped, 15 tests passing). Zero new packages. The new module is a standalone top-level file following the project's `self.enabled` pattern. Two CLI commands wire into the existing `_handle_client_command()` dispatch table in `main.py`.

The only meaningful ambiguity is how to handle the YAML scaffolding: the planner must decide whether to call `init_client()` (copies example-client.yaml, replaces placeholders) and then overwrite/append genre fields, or to write the YAML directly. Calling `init_client()` is safer — it guarantees the full structure is present.

**Primary recommendation:** `ProspectFinder.save_prospect()` calls `init_client(slug)` to scaffold the YAML, then uses `pyyaml` to load, merge the `prospect:` block and genre-derived content fields, and write back. This avoids duplicating the YAML structure definition.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `requests` | existing (>=2.31.0) | iTunes Search API HTTP calls | Already in project; no auth needed for iTunes |
| `feedparser` | existing (>=6.0.12) | RSS feed parsing for contact extraction | Already used in `rss_episode_fetcher.py` |
| `pyyaml` | existing (>=6.0.1) | Read/write client YAML files | Already used by `client_config.py` |
| `sqlite3` | stdlib | Register prospect in OutreachTracker | Delegated — caller is `OutreachTracker.add_prospect()` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `re` | stdlib | Regex scan for social links in RSS description | Only when feedparser fields don't contain explicit social links |
| `time` | stdlib | 2-second sleep between iTunes API batch calls | Respect Apple's ~20 req/min soft limit |
| `pathlib.Path` | stdlib | YAML file path construction | `clients/<slug>.yaml` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `requests` direct to iTunes | `python-podcastindex` | Archived library; requires HMAC auth; iTunes covers same 3-5 prospect use case |
| `feedparser` for RSS parsing | Manual `requests` + XML parse | feedparser already handles iTunes namespace normalization; no reason to rebuild |
| `init_client()` then YAML merge | Write YAML entirely from scratch | Writing from scratch risks diverging from the example-client.yaml structure; `init_client` guarantees structural completeness |

**Installation:**
```bash
# No new packages. All existing deps.
uv sync
```

---

## Architecture Patterns

### Recommended Project Structure
```
prospect_finder.py           # NEW — ProspectFinder class
tests/test_prospect_finder.py  # NEW — mock requests + mock feedparser
main.py                      # MODIFY — add find-prospects, enrich-prospect to _handle_client_command()
clients/example-client.yaml  # MODIFY — add commented prospect: block at bottom
```

### Pattern 1: iTunes Search API Call
**What:** Single `requests.get()` to `https://itunes.apple.com/search`, parse JSON, client-side filter by `trackCount`.
**When to use:** `ProspectFinder.search()` method.
**Example:**
```python
# Source: Apple iTunes Search API official docs + .planning/research/STACK.md
import requests

def search(self, term: str, genre_id: int = None,
           min_episodes: int = 20, max_episodes: int = 500,
           limit: int = 20) -> list[dict]:
    params = {
        "term": term,
        "media": "podcast",
        "limit": 200,   # fetch more, filter down client-side
    }
    if genre_id:
        params["genreId"] = genre_id
    resp = requests.get(
        "https://itunes.apple.com/search",
        params=params,
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    # Client-side episode count filter (API has no server-side filter)
    filtered = [
        r for r in results
        if min_episodes <= r.get("trackCount", 0) <= max_episodes
    ]
    return filtered[:limit]
```

### Pattern 2: RSS Contact Extraction via feedparser
**What:** Parse feed URL, extract email from iTunes namespace fields, regex-scan description for social links.
**When to use:** `ProspectFinder.enrich_from_rss()` method.
**Example:**
```python
# Source: feedparser docs + .planning/research/ARCHITECTURE.md + project rss_episode_fetcher.py
import feedparser, re

def enrich_from_rss(self, feed_url: str) -> dict:
    feed = feedparser.parse(feed_url)
    # Email: try itunes_owner first (most reliable), then author_detail
    owner = feed.feed.get("itunes_owner", {})
    email = (
        owner.get("email")
        or feed.feed.get("itunes_email")
        or (feed.feed.get("author_detail") or {}).get("email")
    )
    website = feed.feed.get("link", "")
    # Social links via regex on feed description
    desc = feed.feed.get("description", "")
    social = {}
    for pattern, key in [
        (r"twitter\.com/(\w+)", "twitter"),
        (r"instagram\.com/(\w+)", "instagram"),
    ]:
        m = re.search(pattern, desc, re.I)
        if m:
            social[key] = f"https://{pattern.split('/')[0]}.com/{m.group(1)}"

    last_pub = None
    if feed.entries:
        entry = feed.entries[0]
        if entry.get("published_parsed"):
            from datetime import datetime
            last_pub = datetime(*entry.published_parsed[:6]).date().isoformat()

    return {
        "contact_email": email,
        "website": website,
        "social_links": social,
        "last_pub_date": last_pub,
        "episode_count": len(feed.entries),
    }
```

### Pattern 3: YAML Scaffolding via init_client + pyyaml merge
**What:** Call existing `init_client(slug)` to get a full structural YAML, then `yaml.safe_load` + merge genre fields + `yaml.dump`.
**When to use:** `ProspectFinder.save_prospect()` method.
**Example:**
```python
# Source: client_config.init_client() (direct inspection) + .planning/research/ARCHITECTURE.md
import yaml
from client_config import init_client
from pathlib import Path

GENRE_DEFAULTS = {
    "comedy": {
        "voice_persona": "Write show notes with wit and dry humor. Match the show's comedic tone.",
        "blog_voice": "Conversational, punchy, self-aware. Like the show itself.",
        "compliance_style": "lenient",
        "categories": ["Comedy"],
    },
    "true-crime": {
        "voice_persona": "Write show notes in a serious, investigative tone. Respect for victims.",
        "blog_voice": "Evidence-based, measured. No speculation without sourcing.",
        "compliance_style": "strict",
        "categories": ["True Crime"],
    },
    "business": {
        "voice_persona": "Professional but warm. Write show notes for a business-minded audience.",
        "blog_voice": "Actionable insights, clear takeaways, minimal jargon.",
        "compliance_style": "standard",
        "categories": ["Business"],
    },
}

def save_prospect(self, slug: str, itunes_data: dict, rss_data: dict,
                  genre_key: str = None) -> Path:
    clients_dir = Config.BASE_DIR / "clients"
    yaml_path = clients_dir / f"{slug}.yaml"

    # Scaffold full YAML if it doesn't exist yet
    if not yaml_path.exists():
        init_client(slug)

    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

    # Inject prospect: block (not in _YAML_TO_CONFIG, silently ignored by activate_client)
    data["prospect"] = {
        "itunes_id": str(itunes_data.get("collectionId", "")),
        "feed_url": itunes_data.get("feedUrl", ""),
        "genre": itunes_data.get("primaryGenreName", ""),
        "episode_count": itunes_data.get("trackCount", 0),
        "last_pub_date": rss_data.get("last_pub_date", ""),
        "contact_email": rss_data.get("contact_email", ""),
        "website": rss_data.get("website", ""),
        "social_links": rss_data.get("social_links", {}),
        "notes": "",
    }

    # Pre-fill rss_source so --client <slug> latest works immediately
    data["episode_source"] = "rss"
    data.setdefault("rss_source", {})
    data["rss_source"]["feed_url"] = itunes_data.get("feedUrl", "")
    data["rss_source"]["episode_index"] = 0

    # Pre-fill genre-appropriate content settings
    if genre_key and genre_key in GENRE_DEFAULTS:
        defaults = GENRE_DEFAULTS[genre_key]
        data.setdefault("content", {})
        for field in ("voice_persona", "compliance_style"):
            data["content"][field] = defaults[field]
        data.setdefault("rss", {})
        data["rss"]["categories"] = defaults["categories"]

    yaml_path.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
    return yaml_path
```

### Pattern 4: OutreachTracker Registration After Save
**What:** After YAML is written, register the prospect in the outreach DB at `identified` status.
**When to use:** End of `save_prospect()`, or immediately after in the CLI handler.
**Example:**
```python
# Source: outreach_tracker.py (direct inspection — Phase 19 output)
from outreach_tracker import OutreachTracker

tracker = OutreachTracker()
tracker.add_prospect(slug, {
    "show_name": itunes_data.get("collectionName", slug),
    "genre": itunes_data.get("primaryGenreName", ""),
    "rss_feed_url": itunes_data.get("feedUrl", ""),
    "contact_email": rss_data.get("contact_email", ""),
    "social_links": rss_data.get("social_links", {}),
    "status": "identified",
})
# add_prospect is INSERT OR IGNORE — safe to call multiple times
```

### Pattern 5: CLI Command Dispatch (find-prospects)
**What:** Wire `find-prospects` into `_handle_client_command()` using `sys.argv` positional args, matching the existing `outreach` command pattern.
**When to use:** `main.py` additions.
**Example:**
```python
# Source: main.py _handle_client_command() (direct inspection)
elif cmd == "find-prospects":
    from prospect_finder import ProspectFinder
    # Parse flags: --genre, --min-episodes, --max-episodes, --limit
    # Use sys.argv scanning pattern consistent with existing flag parsing
    genre = None
    min_ep = 20
    max_ep = 500
    limit = 20
    # ... parse from sys.argv ...
    finder = ProspectFinder()
    results = finder.search(term=genre or "podcast", genre_id=genre_id,
                            min_episodes=min_ep, max_episodes=max_ep, limit=limit)
    # Print ranked table, prompt user to select slugs for saving
```

### Recommended ProspectFinder Class Interface
```python
class ProspectFinder:
    def __init__(self):
        self.enabled = True  # no credentials required

    def search(self, term: str, genre_id: int = None,
               min_episodes: int = 20, max_episodes: int = 500,
               limit: int = 20) -> list[dict]:
        """Query iTunes API, return filtered + limited results."""

    def enrich_from_rss(self, feed_url: str) -> dict:
        """Parse RSS for email, website, social links, last_pub_date, episode_count."""

    def save_prospect(self, slug: str, itunes_data: dict, rss_data: dict,
                      genre_key: str = None) -> Path:
        """Scaffold clients/<slug>.yaml with genre defaults + prospect: block.
           Register in OutreachTracker at 'identified' status.
           Returns path to YAML file."""

    def _genre_key_from_name(self, genre_name: str) -> str:
        """Map iTunes primaryGenreName to GENRE_DEFAULTS key."""
```

### Anti-Patterns to Avoid
- **Writing the full YAML from scratch in ProspectFinder:** Duplicates the example-client.yaml structure. Call `init_client()` instead to scaffold, then merge fields.
- **Fetching RSS inside save_prospect():** Keep enrichment and save as separate steps. CLI calls `enrich_from_rss()` then `save_prospect()`. Enables testing each independently.
- **Putting genre_id mapping in main.py:** Keep it in `ProspectFinder` as a `GENRE_IDS` dict constant at module level. CLI passes `--genre comedy`, finder resolves to `1303`.
- **Modifying `_YAML_TO_CONFIG` in client_config.py:** The `prospect:` block must NOT be in `_YAML_TO_CONFIG`. `activate_client()` ignores unknown keys — this is the correct behavior. No change to `client_config.py` needed.
- **Calling `activate_client()` in the find-prospects flow:** Discovery is pre-pipeline. `activate_client()` is for episode processing. Never mix these.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| iTunes podcast search | Custom scraper / Podcast Index HMAC auth | `requests.get("https://itunes.apple.com/search")` | iTunes is free, no auth, 200 results/call |
| RSS email extraction | Custom XML parser | `feedparser` (already in project) | feedparser normalizes iTunes namespace fields; handles `itunes_owner`, `managingEditor`, `author_detail` |
| YAML client scaffolding | Write full YAML from scratch | `init_client(slug)` then yaml merge | `init_client` guarantees structural completeness; avoids YAML structure drift |
| Genre-to-settings mapping | Hardcode in CLI args | `GENRE_DEFAULTS` dict at module level in `prospect_finder.py` | Centralizes defaults, testable, reusable |
| Prospect DB registration | Second sqlite3 call | `OutreachTracker.add_prospect()` | OutreachTracker owns DB; Phase 19 contract; `INSERT OR IGNORE` is already idempotent |

**Key insight:** Every hard problem in this phase is already solved by an existing project component. `ProspectFinder` is a thin orchestrator calling `requests`, `feedparser`, `init_client`, `yaml`, and `OutreachTracker`.

---

## Common Pitfalls

### Pitfall 1: iTunes Genre IDs Not in Official Apple Docs
**What goes wrong:** The `genreId` parameter is real and works, but Apple's published docs don't list genre ID values for podcasts. Using wrong IDs returns empty results silently.
**Why it happens:** Apple treats genre IDs as internal identifiers. Community-sourced IDs are the only reference.
**How to avoid:** Use the confirmed values: Comedy=1303, True Crime=1488, Business=1321, Technology=1318. Validate with a live test call during Wave 0 before shipping.
**Warning signs:** `results` list is empty even for broad `term` values.

### Pitfall 2: feedparser bozo Flag on Partially Valid Feeds
**What goes wrong:** Some RSS feeds have minor XML errors. feedparser sets `feed.bozo = True` but still parses the feed. Treating bozo as a hard failure misses valid contacts.
**Why it happens:** RSS feeds often have minor namespace issues that don't affect content. feedparser's `bozo` flag means "had parse errors" not "empty result".
**How to avoid:** Log a warning on bozo but continue parsing. Only fail if `feed.entries` is empty.
**Warning signs:** `enrich_from_rss()` always returns empty dict for feeds that load fine in a browser.

### Pitfall 3: `itunes_owner` Deprecated but Still Present
**What goes wrong:** Apple deprecated `<itunes:owner>` in their 2024 RSS spec update. Code that only checks `feed.feed.itunes_owner` misses emails stored in `<managingEditor>` or `<author>`.
**Why it happens:** Most hosting platforms (Buzzsprout, Transistor, Libsyn) still emit `<itunes:owner>` in 2026 despite deprecation. But shows on newer platforms may only have `managingEditor`.
**How to avoid:** Check in priority order: `itunes_owner.email` → `itunes_email` → `author_detail.email` → `managingEditor`. Return first non-empty value.
**Warning signs:** Contact email is None for shows that clearly list an email on their website.

### Pitfall 4: `init_client()` Prints to stdout During Tests
**What goes wrong:** `init_client()` always prints "Created client config: ..." and "Next steps:..." to stdout. Tests that call `save_prospect()` emit unexpected output.
**Why it happens:** `init_client()` has hardcoded `print()` calls (confirmed by direct inspection).
**How to avoid:** In tests, mock `init_client` entirely (`@patch("prospect_finder.init_client")`) or redirect stdout with `capsys`. Do not let the test actually call `init_client()`.
**Warning signs:** Test output is cluttered with "Created client config" messages.

### Pitfall 5: YAML dump Loses Comment Structure
**What goes wrong:** `yaml.safe_load` + `yaml.dump` round-trip strips all comments from the YAML file. The example-client.yaml has extensive inline comments documenting every field.
**Why it happens:** PyYAML's data model doesn't preserve comments.
**How to avoid:** Accept this limitation — the `prospect:` block and content fields are the important additions. The comments are for human onboarding, not for a prospect-generated YAML that will be used programmatically. Document this behavior in the method's docstring.
**Warning signs:** User complains that the generated YAML is hard to read.

### Pitfall 6: `trackCount` Proxy Isn't Episode Count
**What goes wrong:** iTunes `trackCount` is the total number of episodes in the feed, including archived/deleted ones. A show may show `trackCount=450` but only have 50 active episodes in their RSS feed.
**Why it happens:** iTunes caches episode counts at index time, not live from RSS.
**How to avoid:** Use `trackCount` for first-pass filtering only (reliable for "has > 10 episodes"). The RSS `len(feed.entries)` gives the current feed window (usually 100-300 most recent). Use the lower of the two for the actual episode count in the prospect record.
**Warning signs:** Prospect record shows 450 episodes but their RSS feed only lists 80.

---

## Code Examples

### iTunes Search API — Live Request Shape
```python
# Source: Apple official docs + STACK.md (HIGH confidence)
import requests

resp = requests.get(
    "https://itunes.apple.com/search",
    params={
        "term": "comedy",
        "media": "podcast",
        "genreId": 1303,
        "limit": 200,
    },
    timeout=10,
)
data = resp.json()
# data["resultCount"] — number of results returned
# data["results"] — list of show dicts

# Key fields on each result:
# result["collectionName"]     — show name
# result["artistName"]         — host/author name
# result["feedUrl"]            — RSS feed URL
# result["trackCount"]         — episode count (proxy)
# result["primaryGenreName"]   — genre string
# result["collectionViewUrl"]  — Apple Podcasts URL
# result["collectionId"]       — iTunes show ID (integer)
# result["releaseDate"]        — most recent episode date (ISO 8601)
```

### feedparser Contact Extraction
```python
# Source: .planning/research/ARCHITECTURE.md + feedparser docs (HIGH confidence)
import feedparser

feed = feedparser.parse("https://feeds.example.com/show.xml")

# Email — check in priority order
owner = feed.feed.get("itunes_owner", {})
email = (
    owner.get("email")                                      # <itunes:owner><itunes:email>
    or feed.feed.get("itunes_email")                        # <itunes:email> at feed level
    or (feed.feed.get("author_detail") or {}).get("email")  # <managingEditor>
)

# Website
website = feed.feed.get("link", "")

# Episode count (from current feed window)
episode_count = len(feed.entries)

# Most recent episode date
last_pub = None
if feed.entries and feed.entries[0].get("published_parsed"):
    from datetime import datetime
    last_pub = datetime(*feed.entries[0].published_parsed[:6]).date().isoformat()
```

### GENRE_IDS and GENRE_DEFAULTS Constants
```python
# Source: .planning/research/STACK.md + ARCHITECTURE.md (MEDIUM confidence — community IDs)
GENRE_IDS = {
    "comedy": 1303,
    "true-crime": 1488,
    "business": 1321,
    "technology": 1318,
    "society": 1324,
}

GENRE_DEFAULTS = {
    "comedy": {
        "voice_persona": (
            "Write show notes and social captions with wit and dry humor. "
            "Match the show's comedic tone. Lean into the absurdity."
        ),
        "compliance_style": "lenient",
        "categories": ["Comedy"],
    },
    "true-crime": {
        "voice_persona": (
            "Write show notes in a serious, investigative tone. "
            "Respect for victims is paramount. Evidence-based analysis only."
        ),
        "compliance_style": "strict",
        "categories": ["True Crime"],
    },
    "business": {
        "voice_persona": (
            "Professional but warm. Write show notes for a business-minded audience. "
            "Lead with actionable insights and clear takeaways."
        ),
        "compliance_style": "standard",
        "categories": ["Business"],
    },
}
```

### OutreachTracker Integration (Phase 19 interface)
```python
# Source: outreach_tracker.py (direct inspection — Phase 19 shipped code)
from outreach_tracker import OutreachTracker

tracker = OutreachTracker()  # defaults to output/outreach.db

# add_prospect is INSERT OR IGNORE — idempotent on duplicate slug
inserted = tracker.add_prospect("comedy-pod-name", {
    "show_name": "Comedy Pod Name",
    "genre": "Comedy",
    "rss_feed_url": "https://feeds.example.com/show.xml",
    "contact_email": "host@example.com",
    "social_links": {"twitter": "https://twitter.com/comedypod"},
    "status": "identified",
})
# Returns True if inserted (new), False if slug already existed
```

### CLI Flag Parsing Pattern (from existing main.py)
```python
# Source: main.py _handle_client_command() and _parse_flags() (direct inspection)
# find-prospects uses --genre, --min-episodes, --max-episodes, --limit flags
# Parse from sys.argv after cmd consumption:
raw_argv = sys.argv[2:]  # strip script name and cmd
genre = None
min_ep = 20
max_ep = 500
limit = 20
i = 0
while i < len(raw_argv):
    if raw_argv[i] == "--genre" and i + 1 < len(raw_argv):
        genre = raw_argv[i + 1]; i += 2
    elif raw_argv[i] == "--min-episodes" and i + 1 < len(raw_argv):
        min_ep = int(raw_argv[i + 1]); i += 2
    elif raw_argv[i] == "--max-episodes" and i + 1 < len(raw_argv):
        max_ep = int(raw_argv[i + 1]); i += 2
    elif raw_argv[i] == "--limit" and i + 1 < len(raw_argv):
        limit = int(raw_argv[i + 1]); i += 2
    else:
        i += 1
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `<itunes:owner>` for host email | Still works but deprecated by Apple | 2024 Apple RSS spec update | Must check fallback fields (`itunes_email`, `author_detail.email`) |
| `podsearch` wrapper library | Archived — do not use | February 2026 | Direct `requests` call is the only viable path |
| Podcast Index API for discovery | iTunes Search API (no auth) | N/A — iTunes always existed | iTunes sufficient for 3-5 prospects; Podcast Index overkill |

**Deprecated/outdated:**
- `podsearch` (nalgeon): Archived February 2026 — dead library, do not use
- `<itunes:owner>` as the sole email source: Deprecated 2024; still present on most feeds but not guaranteed

---

## Open Questions

1. **Genre ID Validation**
   - What we know: Community sources confirm Comedy=1303, True Crime=1488, Business=1321 (MEDIUM confidence)
   - What's unclear: Apple does not publish these in official docs; they could change without notice
   - Recommendation: Wave 0 task — make a live test call for each genre ID and confirm results are genre-appropriate before shipping

2. **YAML Comment Preservation**
   - What we know: `yaml.safe_load` + `yaml.dump` strips all comments
   - What's unclear: Whether users expect the generated YAML to have inline documentation
   - Recommendation: Accept the tradeoff; generated prospect YAMLs are programmatic configs, not human onboarding docs. Add a comment at the top of the generated file noting it was auto-generated.

3. **`enrich-prospect` as separate command vs auto-enrich in `find-prospects`**
   - What we know: DISC-02 says "user can enrich a prospect" — implies a separate step
   - What's unclear: Whether to auto-enrich during `find-prospects` display or make it explicit
   - Recommendation: Auto-enrich when saving (`save_prospect` calls `enrich_from_rss` internally). No separate `enrich-prospect` CLI command needed unless the DISC-02 requirement mandates separate invocation. Keep it simple.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (pyproject.toml testpaths = ["tests"]) |
| Config file | pyproject.toml |
| Quick run command | `uv run pytest tests/test_prospect_finder.py -q` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DISC-01 | `search()` queries iTunes API with correct params | unit | `uv run pytest tests/test_prospect_finder.py::TestProspectFinderSearch -x` | Wave 0 |
| DISC-01 | `search()` filters by episode count client-side | unit | `uv run pytest tests/test_prospect_finder.py::TestProspectFinderSearch -x` | Wave 0 |
| DISC-01 | `find-prospects` CLI prints ranked table | unit | `uv run pytest tests/test_prospect_finder.py::TestFindProspectsCLI -x` | Wave 0 |
| DISC-02 | `enrich_from_rss()` extracts email from itunes_owner | unit | `uv run pytest tests/test_prospect_finder.py::TestEnrichFromRss -x` | Wave 0 |
| DISC-02 | `enrich_from_rss()` falls back to author_detail.email | unit | `uv run pytest tests/test_prospect_finder.py::TestEnrichFromRss -x` | Wave 0 |
| DISC-02 | `enrich_from_rss()` extracts social links via regex | unit | `uv run pytest tests/test_prospect_finder.py::TestEnrichFromRss -x` | Wave 0 |
| DISC-03 | `save_prospect()` creates clients/<slug>.yaml | unit | `uv run pytest tests/test_prospect_finder.py::TestSaveProspect -x` | Wave 0 |
| DISC-03 | `save_prospect()` writes prospect: block | unit | `uv run pytest tests/test_prospect_finder.py::TestSaveProspect -x` | Wave 0 |
| DISC-03 | `save_prospect()` pre-fills genre content settings | unit | `uv run pytest tests/test_prospect_finder.py::TestSaveProspect -x` | Wave 0 |
| DISC-03 | `save_prospect()` registers prospect in OutreachTracker | unit | `uv run pytest tests/test_prospect_finder.py::TestSaveProspect -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_prospect_finder.py -q`
- **Per wave merge:** `uv run pytest -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_prospect_finder.py` — covers DISC-01, DISC-02, DISC-03 (new file, does not exist)

*(No other gaps — pytest, conftest.py, and OutreachTracker test infrastructure already in place)*

---

## Integration Points Summary

### New Files (create)
| File | What |
|------|------|
| `prospect_finder.py` | `ProspectFinder` class — iTunes search, RSS enrichment, YAML scaffold, tracker registration |
| `tests/test_prospect_finder.py` | Unit tests — mock `requests`, mock `feedparser`, mock `init_client`, real YAML with `tmp_path` |

### Modified Files (targeted additions)
| File | What changes |
|------|-------------|
| `main.py` | Add `find-prospects` branch in `_handle_client_command()` |
| `clients/example-client.yaml` | Add commented `prospect:` block at bottom (documentation only) |

### Files Unchanged
| File | Why |
|------|-----|
| `client_config.py` | `prospect:` key not in `_YAML_TO_CONFIG`; `activate_client()` ignores it silently — no change needed |
| `outreach_tracker.py` | Phase 19 output; `add_prospect()` already accepts the data shape ProspectFinder produces |
| `pipeline/runner.py` | Prospect discovery is pre-pipeline; no step changes |

---

## Sources

### Primary (HIGH confidence)
- `outreach_tracker.py` — direct inspection of Phase 19 shipped code; `add_prospect()` interface confirmed
- `main.py` — direct inspection; `_handle_client_command()` dispatch pattern confirmed
- `client_config.py` — direct inspection; `init_client()`, `_YAML_TO_CONFIG` confirmed; `prospect:` key deliberately absent
- `rss_episode_fetcher.py` — direct inspection; feedparser usage pattern confirmed
- `clients/example-client.yaml` — direct inspection; full YAML structure confirmed
- [Apple iTunes Search API Official Docs](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/index.html) — endpoint, params, no auth confirmed

### Secondary (MEDIUM confidence)
- `.planning/research/STACK.md` — genre IDs Comedy=1303, True Crime=1488, Business=1321 from community sources; `feedparser` field names from feedparser docs
- `.planning/research/ARCHITECTURE.md` — ProspectFinder class interface, YAML `prospect:` block structure, data flow
- `.planning/research/FEATURES.md` — qualification criteria, `itunes_owner` deprecation note

### Tertiary (LOW confidence)
- iTunes genre ID values (Comedy=1303, True Crime=1488, Business=1321) — community sources only; not in official Apple docs. **Validate with live test call in Wave 0.**

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies already in project; confirmed by direct file inspection
- Architecture: HIGH — ProspectFinder design derived from existing `init_client`, `OutreachTracker`, `rss_episode_fetcher` patterns; no novel patterns introduced
- Pitfalls: HIGH — feedparser bozo behavior and `itunes_owner` deprecation confirmed by official docs and project usage; YAML comment stripping is a known PyYAML limitation
- Genre IDs: MEDIUM — community sources, needs live validation

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable APIs; iTunes genre IDs are long-lived community values)
