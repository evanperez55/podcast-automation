# Technology Stack

**Project:** Podcast Automation — v1.4 Real-World Testing & Sales Readiness
**Researched:** 2026-03-28
**Confidence:** HIGH (feedparser, requests+tqdm), HIGH (stdlib packaging), HIGH (no-new-packages for genre tuning)

---

## Existing Stack (Do Not Replace)

Validated, working dependencies from v1.0–v1.3. Not candidates for replacement or re-research.

| Technology | Version (pinned) | Role |
|------------|-----------------|------|
| Python | 3.12+ | Language |
| FFmpeg binary | C:\ffmpeg\bin\ffmpeg.exe | Media processing engine |
| openai | >=1.0.0 | GPT-4o for content analysis and blog generation |
| pyyaml | >=6.0.1 | Client YAML config loading (already in use) |
| requests | >=2.31.0 | HTTP calls (already in use for social APIs) |
| tqdm | >=4.66.1 | Progress bars (already in use for Dropbox downloads) |
| jinja2 | >=3.0.0 | HTML template rendering (already in use for webpages) |
| Pillow | >=10.2.0 | Thumbnail generation (already in use) |
| pydub | >=0.25.1 | Audio processing (already in use) |

---

## New Stack Additions (v1.4 Only)

Three new capabilities are required. Two use a single new library each; the third requires no new packages.

---

### 1. RSS Feed Parsing and Episode Download: `feedparser` + stdlib `urllib` / existing `requests`

**New package:** `feedparser>=6.0.12`

**Why feedparser:**
- Version 6.0.12 (released September 10, 2025) — actively maintained, production/stable.
- Handles all podcast feed variants: RSS 0.9x, RSS 1.0, RSS 2.0, Atom 0.3, Atom 1.0, CDF, and JSON feeds.
- Natively parses iTunes extension tags (`itunes_title`, `itunes_duration`, `itunes_explicit`, `itunes_episode`, `itunes_episodetype`) — required for correct podcast metadata extraction.
- Extracts enclosure URLs from feed entries (the audio file URL) as a list — handles feeds with multiple enclosures gracefully.
- The `entries[n].enclosures[0].href` pattern gives the direct audio download URL without any custom XML parsing.
- Alternative `podcastparser` (v0.6.11, Nov 2025) is lighter but has a simpler API and fewer namespace extensions — only matters if feedparser's footprint is a concern, which it is not here.

**Audio download via existing `requests`:**
No new package needed. The existing `requests>=2.31.0` already in `pyproject.toml` handles streaming downloads. The existing `tqdm` integration pattern (already used in `dropbox_handler.py`) applies directly.

Pattern for streaming audio download with progress:
```python
import requests
from tqdm import tqdm

def download_rss_episode(url: str, dest_path: Path) -> Path:
    """Download audio enclosure from RSS feed with progress bar."""
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(dest_path, "wb") as f, tqdm(total=total, unit="B", unit_scale=True) as bar:
            for chunk in r.iter_content(chunk_size=1024 * 64):
                f.write(chunk)
                bar.update(len(chunk))
    return dest_path
```

**Integration point:** New `rss_downloader.py` module called from `pipeline/steps/ingest.py`. The ingest step already handles a `local_audio_path` bypass; a new `rss_feed_url` + `episode_index` path follows the same pattern. `DropboxHandler` is skipped when RSS source is configured in the client YAML.

**Client YAML addition (no code change to `client_config.py` structure — adds new keys to `_YAML_TO_CONFIG`):**
```yaml
source:
  type: rss           # "dropbox" (default) | "rss" | "local"
  rss_feed_url: "https://feeds.example.com/podcast.xml"
  episode_index: 0    # 0 = latest, 1 = second-most-recent, etc.
```

**Confidence:** HIGH — feedparser 6.0.12 confirmed on PyPI; enclosure/iTunes tag support confirmed in official docs at feedparser.readthedocs.io.

---

### 2. Genre-Specific Pipeline Tuning: No New Package — YAML Config Extension

**New package:** None.

**Why no new package:**
Genre tuning is entirely about what goes into the GPT-4o prompts and which pipeline parameters are applied — not about new libraries. The multi-client YAML config system (`client_config.py` + `clients/*.yaml`) already provides per-client `voice_persona`, `blog_voice`, `scoring_profile`, `names_to_remove`, and `words_to_censor`. These fields already flow into `ContentEditor.analyze_content()` and `BlogPostGenerator`.

The gap is not missing infrastructure — it is missing YAML content for non-comedy genres. The work is:

1. **Write client configs** for 2-3 target genres (true crime, business/interview, etc.) with genre-appropriate `voice_persona`, `blog_voice`, and `scoring_profile` values.

2. **Tune censorship defaults per genre.** True crime likely needs zero censorship; business interview may need none either. The `names_to_remove` and `words_to_censor` lists already accept empty arrays.

3. **Validate `content.compliance_check_enabled` per genre.** The compliance checker was tuned for comedy — its prompt needs a genre-aware branch or a per-client `compliance_prompt_override` field in the YAML (another config extension, no new package).

4. **Adjust clip scoring** via `scoring_profile`. Non-comedy genres prioritize informativeness and clarity over energy/humor — the existing `AudioClipScorer` criteria already accept custom weights through the YAML scoring profile.

The `example-client.yaml` already shows the true crime scoring profile pattern. Adapting it for business/interview is authoring work, not engineering work.

**The one code gap:** `ContentEditor` currently reads `Config.VOICE_PERSONA` (a module-level constant) via `VOICE_PERSONA` string in `content_editor.py`. Client YAML `content.voice_persona` must override this at runtime. Verify this override actually flows through `client_config.py` → `Config.VOICE_PERSONA` before building anything new. If the wire is broken, fix it — don't add a new abstraction.

**Confidence:** HIGH — client config system is implemented; existing YAML fields cover the tuning surface. Risk is a missing wire in `ContentEditor`, not missing infrastructure.

---

### 3. Demo Output Packaging: stdlib `zipfile` + `shutil` + existing `jinja2`

**New package:** None.

**Why no new package:**
A sales demo package for a prospective client is:
1. A self-contained HTML summary page (client name, episode processed, key metrics, embedded media)
2. Sample clips as `.mp4` files
3. Sample thumbnail as `.png`
4. Blog post excerpt as `.html` or `.md`
5. Social captions as `.txt`
6. Everything in a `.zip` archive named `demo-{client}-{episode}.zip`

All of this is covered by:
- **`jinja2`** (already in `pyproject.toml`) for generating the HTML summary page — same pattern as `episode_webpage_generator.py`
- **`shutil.make_archive()`** or **`zipfile.ZipFile`** (Python stdlib) for creating the `.zip` — no external dependency needed
- **`Pillow`** (already present) for any image resizing/watermarking in the demo package

**Do not use WeasyPrint or pdfkit for PDF generation.** WeasyPrint requires GTK+ (complex Windows install via MSYS2); pdfkit depends on the abandoned wkhtmltopdf binary (archived January 2023). A self-contained HTML file opened in a browser is a better prospect demo than a PDF — it embeds the actual clips and lets the prospect play them. HTML is the right output format.

**Implementation:** New `demo_packager.py` module with a `DemoPackager` class following the existing `self.enabled` pattern. Called as a post-pipeline step, reads from the episode output directory, writes `output/{client}/demo-{episode}.zip`.

**Confidence:** HIGH — stdlib only for zip; jinja2 already in use for webpage generation.

---

## Installation (v1.4 diff only)

```bash
# Add to pyproject.toml dependencies:
# "feedparser>=6.0.12",

uv add feedparser
```

No other new packages. `requests`, `tqdm`, `jinja2`, `zipfile` (stdlib), `shutil` (stdlib) are all already present.

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| `feedparser>=6.0.12` | `podcastparser>=0.6.11` | podcastparser is lighter but has fewer namespace extensions and a more limited API; feedparser handles all RSS/Atom variants and iTunes tags in one library |
| `feedparser>=6.0.12` | Manual `xml.etree.ElementTree` parsing | RSS 2.0 feeds have numerous namespace variations (iTunes, Google, Podcastindex 2.0); feedparser normalizes all of them — hand-rolling this is weeks of edge-case work |
| `requests` streaming (existing) | `httpx` (async) | No async in the pipeline; requests is already present and sufficient for single-file sequential downloads |
| YAML config extension for genre tuning | New `GenreAdapter` class or plugin registry | PROJECT.md explicitly rules out "plugin registry / dynamic step discovery"; YAML configs already provide the tuning surface |
| `jinja2` + stdlib `zipfile` for demo | `WeasyPrint` for PDF | WeasyPrint requires GTK+ on Windows (MSYS2 install) — fragile setup on the project's Windows 11 environment; HTML is a better demo format for media-rich content |
| `jinja2` + stdlib `zipfile` for demo | `pdfkit` / wkhtmltopdf | wkhtmltopdf was archived January 2023 — frozen CSS support, no active maintenance |
| `jinja2` + stdlib `zipfile` for demo | `report-creator` / `HTMLArk` | Adds a new dependency for functionality already covered by existing jinja2 patterns in the codebase |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `WeasyPrint` | Complex Windows install (GTK+ via MSYS2); no JavaScript support | `jinja2` → self-contained HTML with embedded base64 media |
| `pdfkit` / `wkhtmltopdf` | Archived Jan 2023; frozen WebKit CSS support | `jinja2` HTML output |
| `podcast-downloader` (PyPI package) | Full CLI tool, not a library — not importable as a module in the pipeline | `feedparser` + `requests` streaming (5 lines of code) |
| `httpx` | Async HTTP client — pipeline is synchronous; adds unnecessary complexity | `requests` streaming (already present) |
| `python-dateutil` / `pendulum` | Overkill for episode date parsing from RSS `published_parsed` | feedparser already normalizes dates to `time.struct_time`; `datetime.fromtimestamp()` converts it |
| Any new LLM/AI library | Genre tuning is prompt authoring, not model switching | Edit YAML client configs and `voice_persona` fields |

---

## Integration Points with Existing Code

| New Component | Integrates With | What Changes |
|--------------|----------------|--------------|
| `feedparser` (new dep) | `rss_downloader.py` (new module) | Added to `pyproject.toml` |
| `rss_downloader.py` (new) | `pipeline/steps/ingest.py` | Ingest step checks `client_config.source.type == "rss"` and calls `RSSDownloader` instead of `DropboxHandler` |
| `client_config.py` | `_YAML_TO_CONFIG` mapping | Add `source.type`, `source.rss_feed_url`, `source.episode_index` key mappings |
| `demo_packager.py` (new) | `pipeline/steps/distribute.py` | Called after blog/webpage steps; reads existing episode output files; no pipeline state changes |
| `clients/{genre}.yaml` | `client_config.py` (existing) | New config files — no code changes |

---

## Version Compatibility

| Package | Version | Python Requirement | Notes |
|---------|---------|-------------------|-------|
| feedparser | >=6.0.12 | Python >=3.6 | No conflicts with existing deps; pure Python |
| requests | >=2.31.0 (existing) | Python >=3.7 | Already pinned; streaming download is stable API |
| tqdm | >=4.66.1 (existing) | Python >=3.7 | Already pinned; used in dropbox_handler.py |
| jinja2 | >=3.0.0 (existing) | Python >=3.7 | Already pinned; used in episode_webpage_generator.py |
| zipfile | stdlib | Python 3.x | No install needed |
| shutil | stdlib | Python 3.x | No install needed |

---

## Sources

- [feedparser 6.0.12 on PyPI](https://pypi.org/project/feedparser/) — version 6.0.12, released September 10, 2025 confirmed
- [feedparser official docs](https://feedparser.readthedocs.io/en/latest/introduction/) — iTunes tags and enclosure parsing confirmed
- [podcastparser 0.6.11 on PyPI](https://pypi.org/project/podcastparser/) — version and scope confirmed for alternative comparison
- [Python zipfile stdlib docs](https://docs.python.org/3/library/zipfile.html) — packaging approach confirmed
- [Python shutil stdlib docs](https://docs.python.org/3/library/shutil.html) — `make_archive()` confirmed
- [WeasyPrint Windows issues](https://github.com/Kozea/WeasyPrint/issues/1464) — GTK+/MSYS2 complexity on Windows 11 confirmed; rejected
- [wkhtmltopdf archived](https://github.com/wkhtmltopdf/wkhtmltopdf) — archived January 2023, confirmed abandoned
- [requests streaming download pattern](https://docs.python-requests.org/en/latest/user/advanced/#streaming-uploads) — `stream=True` + `iter_content()` confirmed

---

*Stack research for: v1.4 RSS podcast ingestion, genre tuning, and sales demo packaging*
*Researched: 2026-03-28*
