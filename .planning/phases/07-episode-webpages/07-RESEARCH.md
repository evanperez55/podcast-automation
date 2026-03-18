# Phase 7: Episode Webpages - Research

**Researched:** 2026-03-18
**Domain:** Static HTML generation, GitHub Pages deployment, SEO structured data, keyword extraction
**Confidence:** HIGH (core stack verified), MEDIUM (GitHub Pages API interaction patterns)

## Summary

Phase 7 adds a new pipeline step that generates SEO-optimized static HTML pages per episode and publishes them to a GitHub Pages site. Each page contains the full transcript, PodcastEpisode JSON-LD structured data, Open Graph/Twitter Card meta tags with extracted keywords, and chapter jump navigation. A sitemap.xml is updated automatically on each run.

The implementation follows the established project pattern: a new `EpisodeWebpageGenerator` class with a `self.enabled` gate, integrated into `run_distribute` in `pipeline/steps/distribute.py` as a new Step 8.6 (after blog post, before search indexing). Deployment uses PyGithub to push HTML files directly to a GitHub Pages repository via the REST API — no Git binary required on the pipeline host.

The biggest technical risk is PyGithub's upsert pattern: `create_file` vs `update_file` requires checking whether the file already exists (to retrieve its SHA). This is a known footgun. YAKE keyword extraction on 10,000-word transcripts is unvalidated — the STATE.md already flagged this as needing a benchmark.

**Primary recommendation:** Use Jinja2 for HTML templating (already in-ecosystem via blog generator), PyGithub for GitHub API commits, YAKE for keyword extraction, and Python stdlib `xml.etree.ElementTree` for sitemap generation. No new major dependencies needed.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| WEB-01 | Static HTML episode page with full searchable transcript | Jinja2 template + transcript segments from `ctx.transcript_data` |
| WEB-02 | PodcastEpisode JSON-LD structured data on each page | Schema.org PodcastEpisode type; required fields: name, description, datePublished, url, partOfSeries, episodeNumber |
| WEB-03 | SEO meta tags (Open Graph, Twitter Card) with episode-specific keywords | YAKE keyword extraction from transcript; standard og: and twitter: meta tag properties |
| WEB-04 | Chapter navigation within the transcript page | Chapter data already in `ctx.analysis["chapters"]`; render as `<a href="#t-{seconds}">` anchors |
| WEB-05 | Sitemap.xml auto-generated and updated with each new episode | Python stdlib xml.etree.ElementTree; read/write at GitHub Pages repo root |
| WEB-06 | Pages deployed to GitHub Pages automatically | PyGithub `create_file`/`update_file` to gh-pages branch; env vars `GITHUB_TOKEN`, `GITHUB_PAGES_REPO`, `SITE_BASE_URL` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyGithub | 2.x | GitHub REST API — create/update files in Pages repo | Official Python wrapper; no git binary required |
| Jinja2 | 3.x | HTML templating | Already used in project ecosystem; cleaner than f-string HTML |
| yake | 0.4.8 | Unsupervised keyword extraction from transcript | No API, no model download, works on arbitrary text length |
| xml.etree.ElementTree | stdlib | sitemap.xml generation and update | Zero new dependencies; sufficient for simple sitemaps |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| html (stdlib) | stdlib | HTML entity escaping in transcript | Always — transcripts contain `&`, `<`, `>` |
| datetime (stdlib) | stdlib | ISO 8601 dates for JSON-LD and sitemap | Always |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyGithub | subprocess + git | git requires binary on PATH; PyGithub works headless |
| PyGithub | GitHub Actions | Actions require separate workflow file; pipeline is CLI-first |
| yake | KeyBERT | KeyBERT requires transformers/torch (already heavy); YAKE is zero-dependency |
| Jinja2 | f-string templates | f-strings are error-prone for multi-KB HTML; Jinja2 is safer |
| xml.etree.ElementTree | lxml | lxml is faster but not needed for small sitemaps |

**Installation:**
```bash
pip install PyGithub jinja2 yake
```
Note: Jinja2 is likely already installed (common Python dependency). Verify with `pip show jinja2` before adding.

## Architecture Patterns

### Recommended Project Structure
```
episode_webpage_generator.py   # new top-level module (matches flat structure)
templates/
└── episode.html.j2            # Jinja2 template for episode page
tests/
└── test_episode_webpage_generator.py
```

The `templates/` directory sits at project root alongside `assets/`.

### Pattern 1: EpisodeWebpageGenerator class with self.enabled
**What:** All new modules follow `self.enabled = os.getenv("PAGES_ENABLED", "true").lower() == "true"`
**When to use:** Every pipeline feature module — allows graceful skip when env vars absent

```python
# Source: project convention (blog_generator.py, subtitle_clip_generator.py)
class EpisodeWebpageGenerator:
    def __init__(self):
        self.enabled = os.getenv("PAGES_ENABLED", "true").lower() == "true"
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.pages_repo = os.getenv("GITHUB_PAGES_REPO")   # "username/repo"
        self.site_base_url = os.getenv("SITE_BASE_URL")    # "https://username.github.io/repo"
        self.branch = os.getenv("GITHUB_PAGES_BRANCH", "main")
```

### Pattern 2: PyGithub upsert (create or update)
**What:** GitHub API requires file SHA to update an existing file. Must check existence first.
**When to use:** Every file write to GitHub Pages repo

```python
# Source: PyGithub docs (pygithub.readthedocs.io/en/stable/examples/Repository.html)
from github import Github

def _github_upsert(repo, path: str, content: str, commit_message: str):
    """Create or update a file in the GitHub Pages repo."""
    try:
        existing = repo.get_contents(path, ref=branch)
        repo.update_file(
            path=existing.path,
            message=commit_message,
            content=content,
            sha=existing.sha,
            branch=branch,
        )
    except Exception:  # GithubException 404 = file does not exist
        repo.create_file(
            path=path,
            message=commit_message,
            content=content,
            branch=branch,
        )
```

### Pattern 3: PodcastEpisode JSON-LD block
**What:** Embeds structured data in `<script type="application/ld+json">` in HTML `<head>`
**When to use:** Every episode page

```python
# Source: schema.org/PodcastEpisode, verified against Google Rich Results patterns
import json
from datetime import datetime

structured_data = {
    "@context": "https://schema.org",
    "@type": "PodcastEpisode",
    "name": episode_title,
    "description": episode_summary,
    "url": episode_url,
    "datePublished": datetime.now().strftime("%Y-%m-%d"),
    "episodeNumber": episode_number,
    "inLanguage": "en",
    "partOfSeries": {
        "@type": "PodcastSeries",
        "name": "Fake Problems Podcast",
        "url": site_base_url,
    },
    "associatedMedia": {
        "@type": "AudioObject",
        "contentUrl": audio_url,   # Dropbox shared link or None
        "encodingFormat": "audio/mpeg",
    },
}
json_ld_block = f'<script type="application/ld+json">{json.dumps(structured_data, indent=2)}</script>'
```

### Pattern 4: YAKE keyword extraction
**What:** Extract top N keywords from full transcript text for SEO meta tags
**When to use:** WEB-03 — building og:keywords and twitter:description enrichment

```python
# Source: github.com/LIAAD/yake (verified)
import yake

def extract_keywords(transcript_text: str, n: int = 10) -> list[str]:
    """Extract top n keywords from transcript. Lower score = more relevant."""
    kw_extractor = yake.KeywordExtractor(
        lan="en",
        n=2,          # max bigrams — short keywords work better for meta tags
        dedupLim=0.7, # remove near-duplicate phrases
        top=n,
    )
    keywords = kw_extractor.extract_keywords(transcript_text)
    return [kw for kw, _score in keywords]
```

### Pattern 5: Sitemap.xml generation
**What:** Build/update sitemap.xml with all episode URLs at the GitHub Pages root
**When to use:** WEB-05, every pipeline run

```python
# Source: Python stdlib xml.etree.ElementTree docs
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime

def generate_sitemap(episode_urls: list[str]) -> str:
    """Generate sitemap.xml content from list of episode URLs."""
    urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for url in episode_urls:
        url_el = ET.SubElement(urlset, "url")
        ET.SubElement(url_el, "loc").text = url
        ET.SubElement(url_el, "changefreq").text = "monthly"
        ET.SubElement(url_el, "lastmod").text = datetime.now().strftime("%Y-%m-%d")
    xml_str = ET.tostring(urlset, encoding="unicode")
    return minidom.parseString(xml_str).toprettyxml(indent="  ")
```

### Pattern 6: Chapter anchors in transcript HTML
**What:** Chapters from `analysis["chapters"]` rendered as jump links; transcript segments get `id="t-{seconds}"` anchors
**When to use:** WEB-04

```python
# Chapters list: [{"start_seconds": 0, "start_timestamp": "00:00:00", "title": "Intro"}, ...]
# Render navigation bar:
chapters_html = "<nav class='chapters'>"
for ch in chapters:
    anchor_id = f"t-{int(ch['start_seconds'])}"
    chapters_html += f'<a href="#{anchor_id}">{ch["start_timestamp"]} {ch["title"]}</a>'
chapters_html += "</nav>"

# In transcript, each segment gets an anchor:
# <span id="t-300" class="segment">...</span>
```

### Pattern 7: Integration in distribute.py as Step 8.6
**What:** Follows blog generator (Step 8.5), before search index (Step 9)
**When to use:** WEB-06 integration point

```python
# Source: project convention from pipeline/steps/distribute.py pattern
# Step 8.6: Deploy episode webpage
print("STEP 8.6: DEPLOYING EPISODE WEBPAGE")
print("-" * 60)
webpage_generator = components.get("webpage_generator")
if webpage_generator and webpage_generator.enabled:
    try:
        page_url = webpage_generator.generate_and_deploy(
            episode_number=episode_number,
            analysis=analysis,
            transcript_data=transcript_data,
        )
        if page_url:
            logger.info("Episode webpage deployed: %s", page_url)
    except Exception as e:
        logger.warning("Webpage deployment failed: %s", e)
else:
    logger.info("Webpage deployment disabled or not configured")
print()
```

### Anti-Patterns to Avoid

- **Calling GitHub API without try/except:** Network failures are common; always wrap in try/except and log warnings rather than raising (matches blog_generator pattern)
- **Rebuilding sitemap from scratch on each run:** Fetch existing sitemap from GitHub repo, parse existing URLs, merge new episode URL in, then push update — avoid clobbering other episodes
- **Blocking pipeline on missing env vars:** `PAGES_ENABLED` should auto-disable (default True), but if `GITHUB_TOKEN` or `GITHUB_PAGES_REPO` is None, log a warning and skip rather than raising
- **Embedding transcript as raw text:** Must HTML-escape with `html.escape()` before insertion; transcripts contain `&`, `<`, `>`

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GitHub API file push | Custom REST calls with requests | PyGithub | Handles auth, rate-limiting, SHA lookup |
| HTML templating | f-string HTML assembly | Jinja2 | Escaping, maintainability, readability |
| Keyword extraction | Regex/frequency counting | YAKE | Statistical features, deduplication, multilingual |
| XML generation | String concatenation | xml.etree.ElementTree | Correct encoding, namespace handling |

**Key insight:** GitHub Pages deployment requires a SHA to update existing files — this is a two-step API call (read then write) that PyGithub encapsulates cleanly.

## Common Pitfalls

### Pitfall 1: PyGithub upsert SHA mismatch
**What goes wrong:** Calling `update_file` without the current file's SHA raises a 409 Conflict error; calling `create_file` on an existing path raises a 422 Unprocessable Entity.
**Why it happens:** GitHub's REST API enforces optimistic concurrency on file updates.
**How to avoid:** Always use the upsert pattern — call `get_contents()` first, catch the 404 exception for new files, use the returned `.sha` for updates.
**Warning signs:** `GithubException: 422` or `GithubException: 409` in logs.

### Pitfall 2: Sitemap clobber (new episode erases old episodes)
**What goes wrong:** Generating sitemap from only the current episode's URL overwrites all previous episode URLs.
**Why it happens:** Not reading the existing sitemap before writing.
**How to avoid:** Fetch existing sitemap via `repo.get_contents("sitemap.xml")`, parse existing `<loc>` URLs, merge new URL, then push. If sitemap doesn't exist yet, create with just the new URL.
**Warning signs:** Sitemap only ever has one `<url>` entry.

### Pitfall 3: YAKE on very long transcripts
**What goes wrong:** YAKE may be slow or produce poor-quality keywords on 10,000-word podcast transcripts (conversational, repetitive language).
**Why it happens:** YAKE was benchmarked on formal documents, not conversational speech.
**How to avoid:** Truncate input to first 5,000 words (or use `episode_summary` + `show_notes` from analysis instead of raw transcript). Benchmark during implementation.
**Warning signs:** Keywords like "you know", "I mean", "like" dominating output.

### Pitfall 4: GitHub Pages propagation delay
**What goes wrong:** Test asserts page is live immediately after deploy, but GitHub Pages CDN takes 30-120 seconds to propagate.
**Why it happens:** GitHub Pages is eventually consistent; the file is committed instantly but serving lags.
**How to avoid:** In tests, assert the file was committed to the repo (via PyGithub), not that the URL is HTTP 200. Don't test live URL in unit tests.

### Pitfall 5: GITHUB_TOKEN scope
**What goes wrong:** Token has `repo` scope but Pages repo is a different repository — `repo.get_contents()` raises 404/403.
**Why it happens:** Fine-grained tokens may restrict by repository.
**How to avoid:** Document that `GITHUB_TOKEN` needs read/write access to `GITHUB_PAGES_REPO` specifically. If the Pages repo is separate from the podcast-automation repo (likely), a classic token with `repo` scope or a fine-grained token scoped to the Pages repo is required.

### Pitfall 6: HTML injection via transcript
**What goes wrong:** Transcript text inserted directly into HTML contains `<script>` tags or `&` characters that break the page.
**Why it happens:** Whisper transcripts are raw text, not pre-escaped.
**How to avoid:** Always call `html.escape(text)` on every segment text before inserting into HTML template. In Jinja2, use `{{ text | e }}` (auto-escape in the template).

## Code Examples

Verified patterns from official sources:

### PyGithub: Initialize and get repo
```python
# Source: pygithub.readthedocs.io/en/stable/examples/Repository.html
from github import Github

g = Github(github_token)
repo = g.get_repo("username/pages-repo")  # e.g. "fakeproblemspodcast/website"
```

### PyGithub: Create or update file (upsert)
```python
# Source: PyGithub docs + issue #1069 (encoding note)
def upsert_file(repo, path: str, content: str, message: str, branch: str = "main"):
    try:
        existing = repo.get_contents(path, ref=branch)
        repo.update_file(
            path=existing.path,
            message=message,
            content=content,   # PyGithub handles UTF-8 -> base64 internally
            sha=existing.sha,
            branch=branch,
        )
    except Exception:  # file not found = create
        repo.create_file(
            path=path,
            message=message,
            content=content,
            branch=branch,
        )
```

### YAKE: Extract keywords from transcript
```python
# Source: github.com/LIAAD/yake (verified)
import yake

kw_extractor = yake.KeywordExtractor(lan="en", n=2, dedupLim=0.7, top=10)
keywords = kw_extractor.extract_keywords(transcript_text[:5000])  # truncate
kw_list = [kw for kw, _score in keywords]
# Returns: ["fake problems podcast", "stand up comedy", ...]
```

### Open Graph + Twitter Card meta tags
```html
<!-- Source: ogp.me spec + developer.twitter.com/en/docs/twitter-for-websites/cards -->
<meta property="og:type" content="music.song" />
<meta property="og:title" content="{{ episode_title }}" />
<meta property="og:description" content="{{ episode_summary[:200] }}" />
<meta property="og:url" content="{{ episode_url }}" />
<meta property="og:image" content="{{ thumbnail_url }}" />
<meta property="og:site_name" content="Fake Problems Podcast" />
<meta name="keywords" content="{{ keywords | join(', ') }}" />

<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="{{ episode_title }}" />
<meta name="twitter:description" content="{{ episode_summary[:200] }}" />
<meta name="twitter:image" content="{{ thumbnail_url }}" />
```

### JSON-LD PodcastEpisode block (Google Rich Results compatible)
```json
{
  "@context": "https://schema.org",
  "@type": "PodcastEpisode",
  "name": "Episode #42 - The One About Nothing",
  "description": "Joey and Evan debate whether nothing exists.",
  "url": "https://username.github.io/podcast/episodes/42.html",
  "datePublished": "2026-03-18",
  "episodeNumber": 42,
  "inLanguage": "en",
  "partOfSeries": {
    "@type": "PodcastSeries",
    "name": "Fake Problems Podcast"
  },
  "associatedMedia": {
    "@type": "AudioObject",
    "contentUrl": "https://dl.dropboxusercontent.com/...",
    "encodingFormat": "audio/mpeg"
  }
}
```

### Sitemap.xml upsert with merge
```python
# Source: Python docs xml.etree.ElementTree + project pattern
import xml.etree.ElementTree as ET
from xml.dom import minidom

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"

def upsert_sitemap(repo, new_url: str, branch: str = "main") -> None:
    existing_urls = []
    try:
        sm_file = repo.get_contents("sitemap.xml", ref=branch)
        root = ET.fromstring(sm_file.decoded_content)
        existing_urls = [el.text for el in root.findall(f"{{{SITEMAP_NS}}}url/{{{SITEMAP_NS}}}loc")]
    except Exception:
        pass  # sitemap doesn't exist yet

    if new_url not in existing_urls:
        existing_urls.append(new_url)

    urlset = ET.Element("urlset", xmlns=SITEMAP_NS)
    for url in existing_urls:
        url_el = ET.SubElement(urlset, "url")
        ET.SubElement(url_el, "loc").text = url
        ET.SubElement(url_el, "changefreq").text = "monthly"

    xml_bytes = ET.tostring(urlset, encoding="unicode", xml_declaration=False)
    pretty = minidom.parseString(xml_bytes).toprettyxml(indent="  ")

    upsert_file(repo, "sitemap.xml", pretty, f"chore: add episode {new_url} to sitemap", branch)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Static site with Jekyll | Direct HTML push via GitHub API | Evergreen | Eliminates Jekyll build overhead for simple pages |
| Manual `requests` GitHub API | PyGithub 2.x | 2022+ | Handles auth, pagination, SHA lookups |
| `update_file` requires pre-encoded base64 | Pass plain str/bytes, PyGithub encodes | PyGithub ~1.5x | Simplified content passing |

**Deprecated/outdated:**
- `PyGithub <2.0`: Old `InputGitAuthor` / `InputGitTreeElement` patterns in tutorials — use current `create_file`/`update_file` directly
- Jekyll-based GitHub Pages templates: Out of scope; we push raw HTML, not Jekyll source

## Open Questions

1. **YAKE quality on podcast transcripts**
   - What we know: YAKE works well on formal documents; transcripts are conversational
   - What's unclear: Whether top-10 keywords will be useful vs. filled with filler phrases
   - Recommendation: Use `analysis["episode_summary"]` + `analysis["show_notes"]` as YAKE input instead of raw transcript; this is cleaner text. Fallback: extract from `show_notes` only.

2. **GitHub Pages repository structure**
   - What we know: Env vars `GITHUB_PAGES_REPO` and `SITE_BASE_URL` are planned (per STATE.md)
   - What's unclear: Whether a separate GitHub repo is used for Pages or a `gh-pages` branch in the same repo
   - Recommendation: Design `EpisodeWebpageGenerator` to accept a `GITHUB_PAGES_REPO` in `owner/repo` format (separate repo is cleanest); make branch configurable via `GITHUB_PAGES_BRANCH` (default `main`).

3. **Thumbnail URL availability**
   - What we know: `ctx.thumbnail_path` is a local path; no public URL exists until uploaded
   - What's unclear: Whether thumbnail can be included in og:image without a public host
   - Recommendation: Upload thumbnail to the GitHub Pages repo alongside the HTML page (e.g., `images/ep42-thumbnail.jpg`); use that as og:image. If `ctx.thumbnail_path` is None, omit og:image tags.

4. **Audio URL for JSON-LD associatedMedia**
   - What we know: `ctx.finished_path` is the Dropbox path; `audio_url` (Dropbox shared link) is only available inside `run_distribute` Step 7.5 scope
   - What's unclear: Whether to surface `audio_url` to the webpage step
   - Recommendation: Pass `audio_url` (or None) as a parameter to `generate_and_deploy()`; if None, omit `associatedMedia` from JSON-LD.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | none (auto-discovery) |
| Quick run command | `pytest tests/test_episode_webpage_generator.py -x` |
| Full suite command | `pytest` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WEB-01 | `generate_html()` returns string containing transcript segment text | unit | `pytest tests/test_episode_webpage_generator.py::TestGenerateHtml::test_transcript_segments_in_html -x` | Wave 0 |
| WEB-01 | HTML-escapes `<`, `>`, `&` in transcript text | unit | `pytest tests/test_episode_webpage_generator.py::TestGenerateHtml::test_html_escaping -x` | Wave 0 |
| WEB-02 | JSON-LD block present and valid for PodcastEpisode | unit | `pytest tests/test_episode_webpage_generator.py::TestJsonLd::test_jsonld_type_and_fields -x` | Wave 0 |
| WEB-03 | og:title, og:description, keywords meta tags present | unit | `pytest tests/test_episode_webpage_generator.py::TestMetaTags::test_og_tags_present -x` | Wave 0 |
| WEB-03 | YAKE extracts non-empty keyword list from sample text | unit | `pytest tests/test_episode_webpage_generator.py::TestKeywordExtraction::test_keywords_nonempty -x` | Wave 0 |
| WEB-04 | Chapter nav links rendered with correct `#t-{seconds}` hrefs | unit | `pytest tests/test_episode_webpage_generator.py::TestChapterNav::test_chapter_anchors -x` | Wave 0 |
| WEB-05 | `upsert_sitemap()` adds new URL without removing existing URLs | unit | `pytest tests/test_episode_webpage_generator.py::TestSitemap::test_sitemap_merges_existing_urls -x` | Wave 0 |
| WEB-05 | sitemap.xml is valid XML with correct namespace | unit | `pytest tests/test_episode_webpage_generator.py::TestSitemap::test_sitemap_xml_valid -x` | Wave 0 |
| WEB-06 | `deploy()` calls PyGithub upsert; skips gracefully when token missing | unit | `pytest tests/test_episode_webpage_generator.py::TestDeploy::test_skip_when_no_token -x` | Wave 0 |
| WEB-06 | `deploy()` calls `create_file` for new page, `update_file` for existing | unit | `pytest tests/test_episode_webpage_generator.py::TestDeploy::test_upsert_calls_update_for_existing -x` | Wave 0 |

All tests use `unittest.mock.patch` for PyGithub and YAKE — no real GitHub API calls in test suite.

### Sampling Rate
- **Per task commit:** `pytest tests/test_episode_webpage_generator.py -x`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_episode_webpage_generator.py` — covers all WEB-01 through WEB-06 tests
- [ ] `templates/episode.html.j2` — Jinja2 HTML template (needed for WEB-01, WEB-02, WEB-03, WEB-04)

*(Framework pytest is already installed and configured. No conftest.py changes needed.)*

## Sources

### Primary (HIGH confidence)
- PyGithub docs (pygithub.readthedocs.io/en/stable/examples/Repository.html) — `create_file`, `update_file`, `get_contents` method signatures
- PyGithub issue #1069 — confirmed plain string content works, no manual base64 needed
- schema.org/PodcastEpisode — all property names and types verified directly
- github.com/LIAAD/yake — KeywordExtractor parameters `lan`, `n`, `dedupLim`, `top` verified
- Python docs xml.etree.ElementTree — ElementTree, SubElement, tostring API

### Secondary (MEDIUM confidence)
- Google Rich Results Test behavior for PodcastEpisode — verified via schema.org + Rich Results Test tool description; Google doesn't publish an exhaustive list of required PodcastEpisode fields but name/description/datePublished/url are standard across all schema types
- YAKE performance on conversational text — not formally benchmarked; flagged as an open question

### Tertiary (LOW confidence)
- YAKE quality on 10,000-word podcast transcripts — no specific benchmark found; recommendation to use `show_notes` input is a mitigation strategy

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — PyGithub, Jinja2, YAKE, xml.etree.ElementTree all directly verified via official docs/repos
- Architecture: HIGH — follows established project patterns from blog_generator.py and distribute.py
- Pitfalls: HIGH — upsert SHA pattern and sitemap merge verified against PyGithub issues and API docs; YAKE quality on transcripts is MEDIUM (unvalidated)

**Research date:** 2026-03-18
**Valid until:** 2026-09-18 (stable ecosystem — PyGithub, schema.org, YAKE change infrequently)
