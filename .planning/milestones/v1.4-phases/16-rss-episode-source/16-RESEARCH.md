# Phase 16: RSS Episode Source - Research

**Researched:** 2026-03-28
**Domain:** RSS feed parsing, episode download, ingest decoupling from Dropbox
**Confidence:** HIGH — based on direct codebase inspection + verified library research

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SRC-01 | User can download a podcast episode by pointing at a public RSS feed URL | feedparser 6.0.12 parses enclosures; requests streaming downloads audio; new `rss_episode_fetcher.py` module handles both |
| SRC-02 | Pipeline runs without Dropbox credentials when episode source is RSS or local file | Confirmed: `DropboxHandler.__init__()` raises `ValueError` when no credentials — must be moved inside a conditional branch in `runner.py`; `ingest.py` must branch on `Config.EPISODE_SOURCE` |

</phase_requirements>

---

## Summary

Phase 16 adds RSS as an episode source alongside Dropbox. The work is narrower than it might appear: feedparser handles all RSS/Atom/iTunes namespace parsing in one library call, and the existing `requests` + `tqdm` streaming download pattern from `dropbox_handler.py` is reusable verbatim. The real engineering effort is in the ingest decoupling.

The critical blocker identified in STATE.md is confirmed by code inspection: `runner.py:_init_components()` unconditionally calls `DropboxHandler()` at line 150, and `DropboxHandler.__init__()` raises `ValueError` when `DROPBOX_REFRESH_TOKEN`, `DROPBOX_APP_KEY`, or `DROPBOX_APP_SECRET` are absent (dropbox_handler.py line 39). This means any client without Dropbox credentials fails before ingest begins. This must be fixed in the same phase as RSS support.

A secondary blocker is in `ingest.py` line 45: even when a local file is pre-set and Dropbox is skipped in the if-branch, the code falls through to `dropbox = components["dropbox"]` unconditionally for episode number extraction. This must be refactored so Dropbox is only accessed when the dropbox source is active.

**Primary recommendation:** Build `rss_episode_fetcher.py` first (standalone, easily testable), then fix `runner.py` and `ingest.py` as a paired change to decouple Dropbox initialization from the default path.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| feedparser | >=6.0.12 | Parse RSS/Atom feeds, extract enclosures and iTunes metadata | Only new dependency; handles all RSS 2.0 + iTunes namespace variants without custom XML parsing |
| requests | >=2.31.0 (existing) | HTTP streaming download of audio enclosure | Already in pyproject.toml; `stream=True` + `iter_content()` is the standard pattern |
| tqdm | >=4.66.1 (existing) | Progress bar during audio download | Already used in dropbox_handler.py for Dropbox downloads |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| dataclasses (stdlib) | 3.7+ | `EpisodeMeta` return type from fetcher | Clean, typed handoff between fetcher and ingest step |
| datetime (stdlib) | built-in | Convert `feedparser.entries[n].published_parsed` (time.struct_time) to datetime | feedparser normalizes dates to time.struct_time; convert with `datetime.fromtimestamp(time.mktime(...))` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| feedparser | podcastparser 0.6.11 | podcastparser is lighter but has a more limited API and fewer namespace extensions; feedparser handles all RSS variants and iTunes tags |
| feedparser | xml.etree.ElementTree | Manual XML parsing works but RSS 2.0 has numerous namespace variations (iTunes, Google, Podcastindex 2.0); feedparser normalizes all of them — hand-rolling is weeks of edge-case work |
| requests streaming | httpx (async) | Pipeline is synchronous; requests is already present |

**Installation:**
```bash
uv add feedparser
# requests, tqdm already in pyproject.toml — no change needed
```

---

## Architecture Patterns

### Recommended Project Structure
```
podcast-automation/
├── rss_episode_fetcher.py       # NEW: feedparser + requests download, EpisodeMeta dataclass
├── config.py                   # MODIFIED: add EPISODE_SOURCE, RSS_FEED_URL defaults
├── client_config.py            # MODIFIED: map episode_source and rss.feed_url YAML keys
├── clients/example-client.yaml # MODIFIED: add commented episode_source and rss sections
├── pipeline/
│   └── steps/
│       └── ingest.py           # MODIFIED: branch on EPISODE_SOURCE, fix unconditional dropbox ref
├── pipeline/runner.py          # MODIFIED: conditional DropboxHandler construction
└── tests/
    └── test_rss_episode_fetcher.py  # NEW
```

### Pattern 1: Episode Source Branch in runner.py
**What:** Gate `DropboxHandler` construction behind an `EPISODE_SOURCE == "dropbox"` check. This is the fix for the SRC-02 blocker.
**When to use:** Always — replaces the unconditional line 150 `dropbox = DropboxHandler()`.

```python
# Source: direct inspection of runner.py lines 149-150, dropbox_handler.py lines 38-42
episode_source = getattr(Config, "EPISODE_SOURCE", "dropbox")

if episode_source == "rss":
    from rss_episode_fetcher import RSSEpisodeFetcher
    components["rss_fetcher"] = RSSEpisodeFetcher()
else:
    # dropbox (default) or local
    components["dropbox"] = DropboxHandler()  # existing behavior preserved
```

The dry-run branch at runner.py line 123-143 must also be updated: it currently sets `"dropbox": None` unconditionally. For RSS clients in dry-run mode, set `"rss_fetcher": None` instead.

### Pattern 2: Ingest Step Source Routing
**What:** `ingest.py` currently has two problems: (1) the else branch accesses `components["dropbox"]` for actual download; (2) line 45 unconditionally accesses `components["dropbox"]` for episode number extraction even after a local file bypass. Both must be fixed.

```python
# Source: direct inspection of ingest.py lines 27-46
episode_source = getattr(Config, "EPISODE_SOURCE", "dropbox")

if ctx.audio_file and ctx.audio_file.exists():
    audio_file = ctx.audio_file
    # Extract episode number without Dropbox:
    episode_number = _extract_episode_number_from_filename(audio_file.name)
elif episode_source == "rss":
    fetcher = components["rss_fetcher"]
    meta = fetcher.fetch_latest(Config.RSS_FEED_URL)
    audio_file = fetcher.download_audio(meta.audio_url, Config.DOWNLOAD_DIR)
    episode_number = meta.episode_number  # from iTunes tag or filename fallback
    ctx.episode_meta = meta
else:
    # dropbox (existing behavior)
    dropbox = components["dropbox"]
    latest = dropbox.get_latest_episode()
    audio_file = dropbox.download_episode(latest["path"])
    episode_number = dropbox.extract_episode_number(audio_file.name)
```

The episode number extraction from filenames is already implemented in `DropboxHandler.extract_episode_number()` — extract that regex to a module-level helper so both paths can call it.

### Pattern 3: RSSEpisodeFetcher Module
**What:** New standalone module at project root, peer to `dropbox_handler.py`. Follows the project's flat module structure and `self.enabled` pattern.

```python
# Follows project convention from CONVENTIONS.md
from dataclasses import dataclass
from typing import Optional
import feedparser
import requests
from tqdm import tqdm
from config import Config
from logger import logger

@dataclass
class EpisodeMeta:
    title: str
    audio_url: str
    pub_date: Optional[datetime]
    episode_number: Optional[int]
    duration_seconds: Optional[int]
    description: Optional[str]

class RSSEpisodeFetcher:
    """Fetch and download podcast episodes from a public RSS feed."""

    def __init__(self):
        self.enabled = True  # no credentials required

    def fetch_latest(self, rss_url: str) -> EpisodeMeta:
        """Fetch metadata for the most recent episode."""
        ...

    def fetch_episode(self, rss_url: str, index: int = 0) -> EpisodeMeta:
        """Fetch metadata for episode at given index (0 = latest)."""
        ...

    def download_audio(self, url: str, dest_dir: Path) -> Path:
        """Download audio enclosure with progress bar."""
        ...
```

### Pattern 4: feedparser Enclosure and iTunes Tag Access
**What:** feedparser normalizes RSS enclosures and iTunes extension tags into a consistent dict interface. No custom XML parsing needed.

```python
# Source: feedparser official docs (pythonhosted.org/feedparser/uncommon-rss.html)
import feedparser

d = feedparser.parse(rss_url)
entry = d.entries[0]  # latest episode (most feeds are newest-first)

# Audio URL (enclosure)
audio_url = entry.enclosures[0].href  # e.g., "https://cdn.example.com/ep42.mp3"
mime_type = entry.enclosures[0].type  # e.g., "audio/mpeg"

# iTunes episode number (may be absent on older feeds)
episode_number = getattr(entry, "itunes_episode", None)  # "42" or None

# iTunes duration
duration = getattr(entry, "itunes_duration", None)  # "01:12:34" or "4354" (seconds)

# Standard fields
title = entry.get("title", "")
published = entry.get("published_parsed", None)  # time.struct_time or None
```

**Important:** feedparser returns iTunes episode numbers as strings, not ints — convert with `int(episode_number)` inside a try/except. Duration can be either `"HH:MM:SS"` or raw seconds as a string.

### Pattern 5: Streaming Audio Download
**What:** Reuse the existing requests + tqdm pattern from `dropbox_handler.py`. No new technique needed.

```python
# Pattern reused from dropbox_handler.py download approach
def download_audio(self, url: str, dest_dir: Path) -> Path:
    """Download audio with progress bar."""
    filename = url.split("/")[-1].split("?")[0]  # strip query params
    dest_path = dest_dir / filename
    if dest_path.exists():
        logger.info("Audio already downloaded: %s", dest_path.name)
        return dest_path
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(dest_path, "wb") as f, tqdm(
            total=total, unit="B", unit_scale=True, desc=filename[:40]
        ) as bar:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                f.write(chunk)
                bar.update(len(chunk))
    return dest_path
```

### Pattern 6: validate-client --ping for RSS Feed
**What:** Add an RSS feed reachability check to `validate_client()`. When `EPISODE_SOURCE == "rss"` and `RSS_FEED_URL` is set, `--ping` should make a HEAD request (or short GET) to confirm the feed URL is reachable.

```python
# Follows _ping_dropbox() pattern in client_config.py
def _ping_rss_feed():
    """Test RSS feed URL reachability."""
    url = getattr(Config, "RSS_FEED_URL", None)
    if not url:
        raise ValueError("RSS_FEED_URL not configured")
    import requests
    r = requests.head(url, timeout=10, allow_redirects=True)
    r.raise_for_status()

# In validate_client():
episode_source = getattr(Config, "EPISODE_SOURCE", "dropbox")
rss_url = getattr(Config, "RSS_FEED_URL", None)
if episode_source == "rss":
    _check(results, "RSS Feed URL", bool(rss_url), rss_url)
    if ping and rss_url:
        _ping(results, "RSS Feed", _ping_rss_feed)
```

### Pattern 7: Client YAML Extension
**What:** Two new YAML sections needed. The `episode_source` field defaults to `"dropbox"` when absent; existing clients are not affected.

```yaml
# Addition to clients/example-client.yaml (and any new client configs)
episode_source: "rss"   # "dropbox" (default) | "rss" | "local"

# Only required when episode_source: rss
rss_source:
  feed_url: "https://feeds.example.com/podcast.rss"
  episode_index: 0       # 0 = latest, 1 = second-most-recent
```

Note: The key `rss` is already used in client YAML for output RSS metadata (`rss.description`, `rss.author`, etc.). Use a distinct key `rss_source` for the input feed URL to avoid collision with the existing `rss` section in `_YAML_TO_CONFIG`.

### Anti-Patterns to Avoid
- **Subclassing DropboxHandler for RSS:** DropboxHandler owns Dropbox-specific auth and retry logic. RSS download is a peer module, not a subclass.
- **Unconditional DropboxHandler in `_init_components`:** This is the current blocker. Do not leave it — gate behind `episode_source == "dropbox"`.
- **Parsing RSS feed entries[0] without confirming entry count:** Some feeds return 0 entries (private feeds, feed URL 404). Guard with `if not d.entries: raise ValueError(...)`.
- **Using `rss` as the YAML key for input feed URL:** It collides with the existing `rss` section that maps to RSS output metadata (description, author, email, etc.).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RSS/Atom feed parsing | Custom xml.etree.ElementTree parser | feedparser | RSS 2.0 + iTunes namespace variations are numerous; feedparser handles all of them including edge cases |
| iTunes namespace tag access | Regex over raw XML | feedparser entry attributes | feedparser normalizes `<itunes:episode>`, `<itunes:duration>`, `<itunes:title>` etc. to flat dict keys |
| Date parsing from RSS pubDate | Manual strptime | feedparser's `published_parsed` (time.struct_time) | feedparser normalizes all RFC 822 / ISO 8601 / non-standard date formats |
| Episode number from RSS | Custom filename regex | `entry.itunes_episode` first, filename regex fallback | iTunes tag is the canonical source; regex already exists in DropboxHandler.extract_episode_number() |

**Key insight:** The only work that isn't covered by existing code or feedparser is: (1) the `EpisodeMeta` dataclass, (2) the `download_audio()` streaming method, and (3) the ingest/runner branching logic. Everything else is wiring existing pieces.

---

## Common Pitfalls

### Pitfall 1: YAML Key Collision Between `rss` (output) and RSS Feed URL (input)
**What goes wrong:** Adding `rss.feed_url` to `_YAML_TO_CONFIG` will collide with the existing `rss.description`, `rss.author`, etc. keys that configure the output RSS feed metadata.
**Why it happens:** The `rss` section in the client YAML already maps to podcast output feed configuration. Using `rss.feed_url` for input would make the client YAML semantically contradictory (same `rss` section means both "my output feed config" and "where to download from").
**How to avoid:** Use a distinct top-level key — `rss_source` or `episode_source.rss_feed_url` — in the client YAML for the input RSS feed URL.
**Warning signs:** `Config.RSS_DESCRIPTION` unexpectedly contains a URL string; `rss_feed_generator.py` tries to use the input feed URL as its own feed description.

### Pitfall 2: feedparser Silently Returns Empty entries on Feed Parse Failure
**What goes wrong:** `feedparser.parse(url)` never raises an exception, even on network errors, 404s, or malformed XML. It returns a dict with `d.bozo = True` and `d.bozo_exception` set, but `d.entries` will be an empty list. Accessing `d.entries[0]` raises `IndexError`.
**Why it happens:** feedparser's design goal is to never crash — it degrades gracefully. This is correct behavior but requires explicit checks in caller code.
**How to avoid:**
```python
d = feedparser.parse(rss_url)
if d.bozo:
    raise ValueError(f"RSS feed parse failed: {d.bozo_exception}")
if not d.entries:
    raise ValueError(f"RSS feed has no entries: {rss_url}")
```
**Warning signs:** `IndexError: list index out of range` in `fetch_latest()`; silent failure producing no audio file.

### Pitfall 3: ingest.py Line 45 Unconditional Dropbox Reference After Local File Bypass
**What goes wrong:** Even when `ctx.audio_file` is pre-set (local path), ingest.py line 45 executes `dropbox = components["dropbox"]` unconditionally for episode number extraction. For RSS clients, `components["dropbox"]` does not exist — `KeyError`.
**Why it happens:** The original code assumed Dropbox is always present. The local file bypass only skips the download, not the episode number extraction.
**How to avoid:** Refactor `ingest.py` to extract episode number within each source branch, not after them. Extract `DropboxHandler.extract_episode_number()` as a module-level regex helper that all source paths can call.
**Warning signs:** `KeyError: 'dropbox'` in `run_ingest()` even when the local file path is set correctly.

### Pitfall 4: feedparser Returns iTunes Episode Number as String
**What goes wrong:** `entry.itunes_episode` returns `"42"` (string), not `42` (int). Passing this directly to pipeline steps that expect `int` (checkpoint keys, output directory names) causes type errors or creates directories named `ep_42` correctly but analytics storage keyed as string `"42"` when expecting int.
**Why it happens:** feedparser preserves XML text node values as strings.
**How to avoid:**
```python
ep_num_raw = getattr(entry, "itunes_episode", None)
episode_number = int(ep_num_raw) if ep_num_raw and str(ep_num_raw).isdigit() else None
```
**Warning signs:** `ep_None` output directory; analytics records with string episode keys; checkpoint files named incorrectly.

### Pitfall 5: Audio File Extension from RSS URL May Not Be .wav
**What goes wrong:** Dropbox-sourced files are WAV by convention. RSS feeds typically deliver MP3 or AAC. Several path assumptions in the pipeline use `.wav` extension checks. pydub handles MP3, but some explicit extension guards exist.
**Why it happens:** Fake Problems pipeline was designed around WAV source files.
**How to avoid:** The filename is derived from the RSS enclosure URL. Do not assume `.wav` — use the actual extension from the URL. Confirm pydub loads MP3 correctly (it does via ffmpeg). Check that `is_video_file()` in ingest.py handles audio-only files correctly (it should).
**Warning signs:** `is_video_file()` returning `True` for `.mp3` files; pydub errors on non-WAV input.

### Pitfall 6: Missing feedparser in pyproject.toml (Confirmed Not Present)
**What goes wrong:** `import feedparser` raises `ModuleNotFoundError` at runtime.
**Why it happens:** feedparser is not currently in `pyproject.toml` (confirmed by grep — no match found).
**How to avoid:** Run `uv add feedparser` before any implementation. Verify it appears in `pyproject.toml` dependencies.
**Warning signs:** `ModuleNotFoundError: No module named 'feedparser'` on first run.

---

## Code Examples

### feedparser: Parse Feed and Extract Latest Episode
```python
# Source: feedparser docs (pythonhosted.org/feedparser/uncommon-rss.html)
import feedparser
from datetime import datetime
import time

d = feedparser.parse("https://feeds.example.com/podcast.rss")

if d.bozo:
    raise ValueError(f"Feed parse error: {d.bozo_exception}")
if not d.entries:
    raise ValueError("Feed has no entries")

entry = d.entries[0]  # latest episode (newest-first in standard feeds)

# Audio URL from enclosure
audio_url = entry.enclosures[0].href if entry.enclosures else None

# iTunes episode number (string, may be absent)
ep_raw = getattr(entry, "itunes_episode", None)
episode_number = int(ep_raw) if ep_raw and str(ep_raw).isdigit() else None

# iTunes duration (may be "HH:MM:SS" or raw seconds string)
duration_raw = getattr(entry, "itunes_duration", None)

# Publication date
pub = entry.get("published_parsed")
pub_date = datetime.fromtimestamp(time.mktime(pub)) if pub else None

title = entry.get("title", "")
```

### Streaming Audio Download (reuse from dropbox_handler.py pattern)
```python
# Source: existing dropbox_handler.py + requests docs
import requests
from tqdm import tqdm
from pathlib import Path

def download_audio(url: str, dest_dir: Path) -> Path:
    filename = url.split("/")[-1].split("?")[0]
    dest_path = dest_dir / filename
    if dest_path.exists():
        return dest_path
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(dest_path, "wb") as f, tqdm(
            total=total, unit="B", unit_scale=True, desc=filename[:40]
        ) as bar:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                f.write(chunk)
                bar.update(len(chunk))
    return dest_path
```

### client_config.py: New YAML Field Mappings
```python
# Addition to _YAML_TO_CONFIG in client_config.py
# Source: existing _YAML_TO_CONFIG pattern
"episode_source": "EPISODE_SOURCE",
"rss_source.feed_url": "RSS_FEED_URL",
"rss_source.episode_index": "RSS_EPISODE_INDEX",
```

### config.py: New Default Attributes
```python
# Addition to Config class in config.py
EPISODE_SOURCE = os.getenv("EPISODE_SOURCE", "dropbox")  # "dropbox" | "rss" | "local"
RSS_FEED_URL = os.getenv("RSS_FEED_URL", None)
RSS_EPISODE_INDEX = int(os.getenv("RSS_EPISODE_INDEX", "0"))  # 0 = latest
```

### validate_client: RSS Section Check
```python
# Addition to validate_client() in client_config.py
# Follows _check() and _ping() pattern already in the function
episode_source = getattr(Config, "EPISODE_SOURCE", "dropbox")
if episode_source == "rss":
    rss_url = getattr(Config, "RSS_FEED_URL", None)
    _check(results, "RSS Feed URL", bool(rss_url), rss_url)
    if ping and rss_url:
        _ping(results, "RSS Feed", _ping_rss_feed)
else:
    # existing Dropbox checks (unchanged)
    ...
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Dropbox-only ingest | Source-agnostic ingest (dropbox / rss / local) | Phase 16 | Clients without Dropbox can use the pipeline |
| Unconditional DropboxHandler() in runner | Conditional construction behind episode_source flag | Phase 16 | SRC-02: no ValueError for non-Dropbox clients |
| Episode number from Dropbox filename convention | episode number from iTunes tag first, filename fallback | Phase 16 | Works for standard podcast RSS feeds |

**No deprecated approaches** to remove — this is entirely additive.

---

## Open Questions

1. **RSS_EPISODE_INDEX behavior: does the user ever want a specific named episode vs. "latest"?**
   - What we know: The requirement says "download and process an episode." The success criteria uses `ep01` as an example episode argument.
   - What's unclear: Should `uv run main.py --client truecrime ep01` download episode 1 from the RSS feed, or is the `ep01` argument only used to name the output folder?
   - Recommendation: For Phase 16, `latest` downloads `entries[0]` (most recent). Episode-by-index (`RSS_EPISODE_INDEX`) is a YAML config field for test setups. Named episode routing from CLI (`ep01`) is not needed for SRC-01 or SRC-02 — defer to Phase 17 integration testing if needed.

2. **What to do when RSS feed entries are not newest-first?**
   - What we know: RSS 2.0 spec does not mandate ordering; most podcast hosts (Buzzsprout, Transistor, Libsyn) publish newest-first by convention.
   - What's unclear: True crime or archive feeds may be oldest-first.
   - Recommendation: Sort by `published_parsed` descending before selecting `entries[0]`. A 3-line sort covers this edge case without complexity.

3. **Does `DropboxHandler` need to remain in the dry-run components dict?**
   - What we know: `runner.py` dry-run sets `"dropbox": None`; ingest.py does not execute in dry-run mode.
   - Recommendation: For dry-run with RSS source, set `"rss_fetcher": None` in the dry-run components dict alongside `"dropbox": None` (or omit dropbox for RSS dry-run). Keep backward compatible.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (configured in pyproject.toml, testpaths = ["tests"]) |
| Config file | pyproject.toml |
| Quick run command | `uv run pytest tests/test_rss_episode_fetcher.py tests/test_client_config.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SRC-01 | `fetch_latest()` returns EpisodeMeta with audio_url from parsed RSS XML | unit | `uv run pytest tests/test_rss_episode_fetcher.py::TestFetchLatest -x` | ❌ Wave 0 |
| SRC-01 | `download_audio()` streams to dest_path with progress | unit | `uv run pytest tests/test_rss_episode_fetcher.py::TestDownloadAudio -x` | ❌ Wave 0 |
| SRC-01 | `fetch_latest()` raises ValueError when feed has no entries | unit | `uv run pytest tests/test_rss_episode_fetcher.py::TestFetchLatestErrors -x` | ❌ Wave 0 |
| SRC-01 | `fetch_latest()` raises ValueError on bozo feed parse error | unit | `uv run pytest tests/test_rss_episode_fetcher.py::TestFetchLatestErrors -x` | ❌ Wave 0 |
| SRC-01 | iTunes episode number extracted and converted to int | unit | `uv run pytest tests/test_rss_episode_fetcher.py -x` | ❌ Wave 0 |
| SRC-02 | `_init_components()` does not construct DropboxHandler when EPISODE_SOURCE=rss | unit | `uv run pytest tests/test_pipeline_refactor.py -x -k rss` | ❌ Wave 0 |
| SRC-02 | `run_ingest()` succeeds without components["dropbox"] when EPISODE_SOURCE=rss | unit | `uv run pytest tests/test_pipeline_refactor.py -x -k rss_ingest` | ❌ Wave 0 |
| SRC-02 | `validate_client --ping` checks RSS feed URL reachability | unit | `uv run pytest tests/test_client_config.py -x -k rss` | ❌ Wave 0 (add to existing file) |
| SRC-02 | Client YAML with episode_source=rss maps to Config.EPISODE_SOURCE | unit | `uv run pytest tests/test_client_config.py -x -k episode_source` | ❌ Wave 0 (add to existing file) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_rss_episode_fetcher.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_rss_episode_fetcher.py` — new test file covering SRC-01 (fetch, download, error handling)
- [ ] Add RSS-related tests to `tests/test_client_config.py` (existing file) — covers YAML mapping and validate-client ping
- [ ] Add RSS ingest branch tests to `tests/test_pipeline_refactor.py` (existing file) — covers SRC-02 runner and ingest changes
- [ ] `uv add feedparser` — adds feedparser 6.0.12 to pyproject.toml before any import

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `pipeline/steps/ingest.py` — confirmed unconditional `components["dropbox"]` at line 45
- Direct code inspection: `pipeline/runner.py` — confirmed unconditional `DropboxHandler()` at line 150
- Direct code inspection: `dropbox_handler.py` lines 38-42 — confirmed `ValueError` on missing credentials
- Direct code inspection: `client_config.py` `_YAML_TO_CONFIG` — confirmed `rss` key already used for output feed metadata (collision risk)
- Direct code inspection: `config.py` — confirmed `EPISODE_SOURCE`, `RSS_FEED_URL` not yet defined
- Direct grep: `pyproject.toml` — confirmed feedparser not yet in dependencies
- `.planning/research/STACK.md` — feedparser 6.0.12 version and enclosure API confirmed (researched 2026-03-28)
- `.planning/STATE.md` — DropboxHandler blocker confirmed as known concern for Phase 16

### Secondary (MEDIUM confidence)
- feedparser unofficial docs (pythonhosted.org/feedparser/uncommon-rss.html) — enclosure API structure confirmed: `entry.enclosures[0].href`, `.type`, `.length`
- WebSearch: feedparser iTunes tags (`itunes_episode`, `itunes_duration`) confirmed available in feedparser 6.x

### Tertiary (LOW confidence)
- iTunes tag exact key names (`itunes_episode` vs `itunes_episodenumber`) — feedparser may use `itunes_episodenumber` for some feeds; verify in tests with a real iTunes-tagged RSS feed

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — feedparser confirmed on PyPI, requests/tqdm already in project
- Architecture: HIGH — based on direct code inspection of all modified files
- Pitfalls: HIGH — most are confirmed code-level issues, not hypothetical
- iTunes tag exact names: LOW — should be validated against a real RSS feed in tests

**Research date:** 2026-03-28
**Valid until:** 2026-05-28 (feedparser is stable; ingest code is project-internal)
