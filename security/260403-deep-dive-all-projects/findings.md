# Deep Dive: All Projects — Findings Report

**Date:** 2026-04-03
**Scope:** podcast-automation, genai-edge, ufc-predictor, swing-trader, dopamine-detox-app, preschool-ai

---

## Executive Summary

| Project | Overall Risk | Critical | High | Medium | Low |
|---------|-------------|----------|------|--------|-----|
| **podcast-automation** | LOW | 0 | 0 | 2 | 2 |
| **genai-edge** | LOW | 0 | 0 | 1 | 2 |
| **ufc-predictor** | HIGH | 1 | 2 | 4 | 2 |
| **swing-trader** | HIGH | 0 | 3 | 4 | 2 |
| **dopamine-detox-app** | MEDIUM | 2 | 0 | 6 | 2 |
| **preschool-ai** | CRITICAL | 3 | 7 | 5 | 1 |

**Top 3 urgent items across all projects:**
1. **preschool-ai:** Missing COPPA compliance (children's data app with no age gating or parental consent)
2. **ufc-predictor:** Pickle deserialization in worker process (`engineering.py:204`) — arbitrary code execution
3. **swing-trader:** Race condition in `PortfolioState` — concurrent access can corrupt capital/positions

---

## 1. podcast-automation (Python) — LOW RISK

**Strengths:** All credentials from env vars, parameterized SQL, consistent `self.enabled` pattern across 16 modules, proper timeouts on all I/O.

| # | Finding | Severity | File:Line |
|---|---------|----------|-----------|
| 1 | 160+ `print()` calls should be `logger.info()` | MEDIUM | `pipeline/runner.py` throughout |
| 2 | Commented-out test classes (cleanup) | LOW | `tests/test_content_calendar.py:34-617` |
| 3 | pickle.load for OAuth tokens (trusted source, but no type assertion) | LOW | `analytics.py:47`, `uploaders/youtube_uploader.py:55` |
| 4 | `shell=True` on Windows `start` command (necessary, suppressed) | LOW | `clip_previewer.py:128` |

**No critical or high issues. Codebase is well-maintained.**

---

## 2. genai-edge (Python) — LOW RISK

**Strengths:** Parameterized SQL throughout, `yaml.safe_load()`, all HTTPS with cert verification, comprehensive type hints, timeouts on all network ops, hard caps on items.

| # | Finding | Severity | File:Line |
|---|---------|----------|-----------|
| 1 | Loose `openai>=1.0.0` version constraint (should cap `<2.0.0`) | MEDIUM | `requirements.txt` |
| 2 | Broad `except Exception:` in scrapers (acceptable for fault-tolerance) | LOW | `runner.py:80`, `twitter_scraper.py:51,68` |
| 3 | Email/webhook URLs from env vars not validated | LOW | `email_sender.py`, `discord_sender.py` |

**Cleanest codebase of the group.**

---

## 3. ufc-predictor (Python/FastAPI) — HIGH RISK

**Strengths:** Ruff+Bandit security linting enabled, file upload path sanitization, subprocess uses list format, intentional `# noqa` suppressions show security awareness.

| # | Finding | Severity | File:Line |
|---|---------|----------|-----------|
| 1 | **Pickle deserialization** — `pd.read_pickle()` in worker process | CRITICAL | `src/features/engineering.py:204` |
| 2 | **SSRF** — Unvalidated `video_url` passed to subprocess (yt-dlp) | HIGH | `src/api/app.py:455`, `src/intelligence/presser_sentiment.py:113-130` |
| 3 | **Missing CSRF** on POST endpoints (`/api/log-bet`, `/api/settle-bet`) | HIGH | `src/api/routes/bets.py:17-41,57-83` |
| 4 | Dynamic SQL with f-strings (values from constants, not user input) | MEDIUM | `src/db/database.py:92,126,132` |
| 5 | Bare `except Exception: pass` blocks (8+ locations) | MEDIUM | `src/api/app.py:58,729,750`, `src/macro/indicators.py:65+` |
| 6 | Missing form validation bounds (negative odds, unbounded capital) | MEDIUM | `src/api/routes/bets.py:20-30` |
| 7 | `open()` without context manager | MEDIUM | `src/api/app.py:345` |
| 8 | XML parser without defusedxml (mitigated by Python 3 defaults) | LOW | `src/scraper/news.py:49` |

**Recommended fixes:**
- Replace `pd.read_pickle()` with JSON/msgpack serialization
- Validate `video_url` to HTTPS + YouTube domains only
- Add Pydantic models for form validation with bounds

---

## 4. swing-trader (Python/FastAPI) — HIGH RISK

**Strengths:** API key auth implemented, atomic file writes for state, good SQLite indexing, comprehensive backtest/risk framework.

| # | Finding | Severity | File:Line |
|---|---------|----------|-----------|
| 1 | **Auth bypass** — empty `API_SECRET_KEY` env var allows unauthenticated access | HIGH | `src/api/app.py:34-44` |
| 2 | **Race condition** — concurrent `execute_signals()`/`check_stops()` corrupt positions+capital | HIGH | `src/execution/paper_broker.py:202-336` |
| 3 | **Float precision** — financial calculations use `float` instead of `Decimal` | HIGH | `src/execution/paper_broker.py:215,227-232,248` |
| 4 | Incomplete SSRF validation (missing IPv6, Docker bridge, DNS rebinding) | MEDIUM | `src/execution/alerts.py:234-257` |
| 5 | 20+ bare `except Exception:` blocks | MEDIUM | `src/macro/indicators.py` (12 locations), `src/data/provider.py:174`, etc. |
| 6 | No rate limiting on API endpoints | MEDIUM | `src/api/app.py` |
| 7 | Missing DB composite indices for trade queries | MEDIUM | `src/data/database.py:102-106` |
| 8 | Potential division by zero in z-score calculations | LOW | `src/macro/indicators.py:117` |

**Recommended fixes:**
- Fail fast if `API_SECRET_KEY` is empty (raise on startup)
- Add `threading.RLock` around `PortfolioState` mutations
- Switch financial math to `decimal.Decimal`

---

## 5. dopamine-detox-app (Node.js/Express) — MEDIUM RISK

**Strengths:** Excellent security headers (7 headers via middleware), parameterized SQL (`$1,$2`), bcrypt password hashing, refresh token rotation, error sanitization in production, content-type validation, parameter pollution prevention.

| # | Finding | Severity | File:Line |
|---|---------|----------|-----------|
| 1 | **SSL disabled** — `rejectUnauthorized: false` in production DB connection | HIGH | `src/config/database.js:13` |
| 2 | **Broken import** — `require("../utils/validators")` should be `../utils/validation` (crashes password reset) | HIGH | `src/controllers/passwordResetController.js:103` |
| 3 | Unverified JWT claims in `decodeIdToken()` (no aud/iss/exp check) | MEDIUM | `src/controllers/oauthController.js:22-35` |
| 4 | Unsafe `JSON.parse()` without try-catch (6 locations) | MEDIUM | `src/controllers/coachingController.js:61`, `src/services/aiService.js:250,313,395,475` |
| 5 | Rate limiter fails open on Redis failure | MEDIUM | `src/middleware/rateLimiter.js:73-76` |
| 6 | Bare catch blocks silently swallowing errors | MEDIUM | `src/controllers/oauthController.js:32`, `src/controllers/coachingController.js:173,305` |
| 7 | Missing DB connection pool limits | MEDIUM | `src/config/database.js` |
| 8 | Inconsistent error response format (`{error}` vs `{message}`) | LOW | Multiple controllers |

**Recommended fixes:**
- Fix the broken import immediately (password reset is non-functional)
- Use proper SSL certs or Railway's internal cert chain
- Wrap all `JSON.parse()` calls in try-catch

---

## 6. preschool-ai (Node.js/Express) — CRITICAL RISK

**Strengths:** Parameterized SQL, helmet headers, bcrypt(12), JWT auth, rate limiting, proper pool config.

| # | Finding | Severity | File:Line |
|---|---------|----------|-----------|
| 1 | **No COPPA compliance** — no age gating, no parental consent for children's data app | CRITICAL | `src/routes/authRoutes.js:17-67` |
| 2 | **IP/user-agent stored in plaintext** — PII for users discussing children's development | CRITICAL | `src/routes/chatRoutes.js:207`, `src/services/ragService.js:231,265` |
| 3 | **Email verification disabled** (TODO comment) — allows fake account registration | CRITICAL | `src/routes/authRoutes.js:144-147` |
| 4 | SQL injection fragile pattern (safe now but refactor-risky) | HIGH | `src/routes/adminRoutes.js:52-87` |
| 5 | Weak password validation (min 8 chars, no complexity) | HIGH | `src/routes/authRoutes.js:22` |
| 6 | No audit logging for admin actions (disable users, delete data) | HIGH | `src/routes/adminRoutes.js:325-354` |
| 7 | Missing rate limit per reset token (brute-force risk) | HIGH | `src/routes/authRoutes.js:221-265` |
| 8 | No CSRF protection on state-changing endpoints | HIGH | All POST/PATCH/DELETE routes |
| 9 | NULL user_id ownership check allows access to anonymous conversations | HIGH | `src/routes/chatRoutes.js:9-16` |
| 10 | Tokens in email URLs exposed via Referrer header | HIGH | `src/services/emailService.js:27,44` |
| 11 | PII in server logs without sanitization | MEDIUM | `src/routes/authRoutes.js`, `src/routes/conversationRoutes.js:28,57` |
| 12 | No data retention policy or user data export/deletion | MEDIUM | Entire codebase |
| 13 | Missing input validation on admin query params | MEDIUM | `src/routes/adminRoutes.js:54-87` |
| 14 | No prompt injection filters for LLM queries | MEDIUM | `src/services/ragService.js` |
| 15 | Bcrypt cost factor 12 (lower end, consider 13-14) | MEDIUM | `src/services/authService.js:12-14` |
| 16 | Bare error handler in JWT middleware | LOW | `src/middleware/authenticateJWT.js:40` |

**This project needs the most work before any public deployment, especially given it handles children's data.**

---

## Cross-Project Patterns

### Common Issues Seen in 3+ Projects:
1. **Bare exception handlers** — podcast-automation (minor), ufc-predictor (8+), swing-trader (20+), dopamine-detox (4+), preschool-ai (1)
2. **Missing input validation on API endpoints** — ufc-predictor, swing-trader, preschool-ai
3. **Missing CSRF protection** — ufc-predictor, preschool-ai
4. **Rate limiting gaps** — swing-trader (none), preschool-ai (per-token)

### Projects That Are Production-Ready:
- **podcast-automation** — Yes (batch pipeline, not public-facing)
- **genai-edge** — Yes (well-maintained, good practices)

### Projects That Need Work Before Production:
- **ufc-predictor** — Fix pickle deserialization + SSRF before exposing publicly
- **swing-trader** — Fix auth bypass + race condition + float math before trading real money
- **dopamine-detox-app** — Fix broken import + SSL before user-facing
- **preschool-ai** — Significant work needed (COPPA, email verification, audit logging, PII handling)
