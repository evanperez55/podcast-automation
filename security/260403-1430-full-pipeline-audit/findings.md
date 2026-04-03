# Security Findings — Podcast Automation Pipeline

## [MEDIUM] Finding 5: Blog Generator Has No HTML Sanitization

- **OWASP:** A03 (Injection)
- **STRIDE:** Tampering
- **Location:** `blog_generator.py` (entire generate_blog_post method)
- **Confidence:** Likely
- **Description:** LLM-generated markdown is saved as `.md` files and could be published via Jekyll/GitHub Pages. The LLM could emit `<script>` tags, `<iframe>`, or other HTML within the markdown. Most markdown renderers (Jekyll, GitHub Pages) will render inline HTML in markdown files.
- **Attack Scenario:**
  1. Transcript contains adversarial text that influences LLM to emit script tags
  2. `generate_blog_post()` returns markdown containing `<script>alert('xss')</script>`
  3. Blog post saved to `output/ep_N/` and deployed
  4. Visitor loads the blog page, script executes
- **Mitigation:** Sanitize the markdown output before saving. Strip all HTML tags or use an allowlist (headings, bold, italic, links, blockquotes only). Example:
  ```python
  import re
  def sanitize_markdown(md: str) -> str:
      # Remove all HTML tags except safe inline formatting
      return re.sub(r'<(?!/?(?:b|i|em|strong|a|blockquote|code|pre|h[1-6]|ul|ol|li|p|br)\b)[^>]+>', '', md)
  ```

---

## [LOW] Finding 1: Pickle Deserialization on YouTube Token

- **OWASP:** A08 (Software & Data Integrity Failures)
- **STRIDE:** Elevation of Privilege
- **Location:** `uploaders/youtube_uploader.py:55`
- **Confidence:** Possible
- **Description:** `pickle.load()` on `credentials/youtube_token.pickle`. Pickle can execute arbitrary code during deserialization. Requires attacker to replace the local file.
- **Mitigation:** Consider migrating to JSON token storage or `google-auth`'s JSON serialization.

## [LOW] Finding 2: shell=True in Clip Previewer

- **OWASP:** A03 (Injection)
- **STRIDE:** Elevation of Privilege
- **Location:** `clip_previewer.py:128`
- **Confidence:** Possible
- **Description:** `subprocess.Popen(["start", "", str(clip_path)], shell=True)` on Windows. File paths are pipeline-generated, not user-controlled.
- **Mitigation:** Low priority. Consider using `os.startfile()` on Windows instead.

## [LOW] Finding 6: Requests Without Timeout

- **OWASP:** A04 (Insecure Design)
- **STRIDE:** Denial of Service
- **Location:** `uploaders/instagram_uploader.py:139,174,229,260,311`, `uploaders/tiktok_uploader.py:166,210,246,312`, `setup_instagram.py:62,221,275,320`
- **Confidence:** Confirmed
- **Description:** 13 HTTP requests calls without timeout parameter. A hung API could block the pipeline indefinitely.
- **Mitigation:** Add `timeout=30` to all requests calls.

## [LOW] Finding 11: API Key in Stack Traces

- **OWASP:** A09 (Security Logging & Monitoring Failures)
- **STRIDE:** Information Disclosure
- **Location:** `content_editor.py:133`
- **Confidence:** Possible
- **Description:** `Config.OPENAI_API_KEY` could appear in stack trace locals logged at DEBUG level if an unhandled exception occurs during OpenAI initialization.
- **Mitigation:** No immediate action needed. The log file is local. Consider masking the key in Config repr.

## [LOW] Finding 12: GitHub Token Scope

- **OWASP:** A01 (Broken Access Control)
- **STRIDE:** Elevation of Privilege
- **Location:** `config.py:174`, `website_generator.py:304`
- **Confidence:** Possible
- **Description:** GITHUB_TOKEN grants write access to entire repo, not just specific paths. Standard for GitHub Pages but overly broad.
- **Mitigation:** Use fine-grained PAT scoped to specific repository if available.

## [LOW] Finding 16: Content Calendar JSON Tampering

- **OWASP:** A08 (Software & Data Integrity Failures)
- **STRIDE:** Tampering
- **Location:** `content_calendar.py:336`
- **Confidence:** Possible
- **Description:** A tampered `content_calendar.json` could set `clip_path` to any local file, which would be read and uploaded by the posting script.
- **Mitigation:** Validate that clip_path is within the expected output directory before upload.

## [LOW] Finding 18: RSS Feed SSRF

- **OWASP:** A10 (Server-Side Request Forgery)
- **STRIDE:** Information Disclosure
- **Location:** `rss_episode_fetcher.py:141`
- **Confidence:** Possible
- **Description:** User-provided RSS URLs are fetched without filtering for internal network addresses. In current local/GitHub Actions deployment this is low risk, but would be exploitable in a cloud deployment.
- **Mitigation:** Add URL validation (block private IP ranges) if deploying to cloud.

## [LOW] Finding 20: Static API Credentials

- **OWASP:** A07 (Auth & Identification Failures)
- **STRIDE:** Spoofing
- **Location:** `uploaders/twitter_uploader.py:58`, `uploaders/bluesky_uploader.py:19`
- **Confidence:** Confirmed
- **Description:** Twitter and Bluesky credentials don't auto-rotate. Compromised credentials remain valid until manually revoked.
- **Mitigation:** Accepted risk. Set calendar reminder to rotate credentials quarterly.
