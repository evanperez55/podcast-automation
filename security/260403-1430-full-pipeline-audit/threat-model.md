# Threat Model — Podcast Automation Pipeline

## Assets

| Asset Type | Asset | Location | Priority |
|------------|-------|----------|----------|
| **API Keys** | OpenAI, Anthropic, Dropbox, Twitter, Bluesky, Spotify, HuggingFace, Notion | `.env` file | Critical |
| **OAuth Tokens** | YouTube (pickle), Dropbox (refresh token), Google Docs | `credentials/`, `.env` | Critical |
| **User Data** | Podcast transcripts, episode audio | `output/`, `downloads/` | Medium |
| **Database** | SQLite FTS5 search index | `output/episode_search.db` | Medium |
| **External APIs** | OpenAI, YouTube, Twitter, Bluesky, Dropbox, Spotify, Reddit | Network calls | High |
| **GitHub Pages** | Website repo access via PyGithub | GITHUB_TOKEN env var | High |
| **Generated Content** | Blog posts, HTML pages, RSS feed | `output/`, website repo | Medium |
| **Config** | Client YAML configs, pipeline state JSON | `clients/`, `output/.pipeline_state/` | Medium |

## Trust Boundaries

```
Trust Boundaries:
  ├── Local machine ←→ External APIs (OpenAI, YouTube, Twitter, etc.)
  ├── Local machine ←→ GitHub Pages (PyGithub deploy)
  ├── RSS feeds (untrusted) ←→ Pipeline processing
  ├── LLM output (semi-trusted) ←→ Pipeline data flow
  ├── Subprocess/FFmpeg calls ←→ OS shell
  ├── User input (CLI args) ←→ Pipeline processing
  └── Generated HTML ←→ End-user browsers (XSS surface)
```

## STRIDE Threats

| Threat | Asset/Boundary | Risk | Priority |
|--------|---------------|------|----------|
| **S** Spoofing | OAuth tokens could be stolen from disk | If `.env` or `credentials/` leaked, attacker has full API access | Critical |
| **T** Tampering | RSS feed content → transcript → LLM prompt | Malicious RSS content could influence LLM analysis output | Medium |
| **T** Tampering | FFmpeg subprocess args from untrusted data | Filenames with shell metacharacters could inject commands | High |
| **R** Repudiation | No audit log of API calls or uploads | Uploads to YouTube/Twitter have no local audit trail beyond logs | Low |
| **I** Info Disclosure | API keys in .env, error messages with keys | Keys could leak via error logs, stack traces, or git history | Critical |
| **I** Info Disclosure | Generated HTML may contain host names | Blog posts, website could leak NAMES_TO_REMOVE despite censoring | High |
| **D** Denial of Service | No rate limiting on pipeline commands | Multiple concurrent runs could exhaust API quotas | Low |
| **E** Elevation | GitHub token scope too broad | GITHUB_TOKEN with `delete_repo` scope is more than needed | Medium |

## Attack Surface

```
Entry Points:
  ├── CLI arguments (main.py) → episode IDs, file paths, client names
  ├── RSS feeds (external XML) → parsed by feedparser → episode metadata
  ├── OpenAI API responses (JSON) → parsed into analysis dict → drives all downstream
  ├── Dropbox API responses → file downloads to local disk
  ├── YouTube API → OAuth token refresh, video uploads
  └── Whisper/WhisperX → audio transcription → text content

Data Flows:
  ├── RSS XML → feedparser → EpisodeMeta → audio download → file path
  ├── Audio file → FFmpeg subprocess → processed audio → more FFmpeg
  ├── Transcript text → OpenAI prompt → JSON analysis → blog/HTML/social captions
  ├── Analysis dict → HTML generation (blog, website) → GitHub Pages deploy
  ├── Analysis dict → SQLite FTS5 index → search queries
  └── Content calendar JSON → scheduled posting → Twitter/Bluesky API calls

Abuse Paths:
  ├── Malicious RSS feed → path traversal in download filename
  ├── Crafted audio filename → FFmpeg command injection
  ├── LLM hallucinated XSS in HTML output → stored XSS on website
  ├── SQL injection via episode title → SQLite search index
  └── Pickle deserialization → YouTube token file → code execution
```
