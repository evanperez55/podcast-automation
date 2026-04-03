# OWASP Top 10 Coverage

| ID | Category | Tested | Findings | Status |
|----|----------|--------|----------|--------|
| A01 | Broken Access Control | Yes | 0 actionable | Clean (parameterized SQL, int-derived paths) |
| A02 | Cryptographic Failures | No | - | Not tested (no crypto in pipeline) |
| A03 | Injection | Yes | 1 Medium (XSS) | Blog generator lacks HTML sanitization |
| A04 | Insecure Design | Yes | 1 Low | 13 requests without timeout |
| A05 | Security Misconfiguration | Yes | 0 | feedparser XXE-safe, no debug mode exposure |
| A06 | Vulnerable Components | No | - | pip audit not available; manual review needed |
| A07 | Auth & Identification Failures | Yes | 1 Low | Static credentials (Twitter/Bluesky), no rotation |
| A08 | Software & Data Integrity Failures | Yes | 2 Low | Pickle deserialization, calendar JSON tampering |
| A09 | Security Logging & Monitoring Failures | Yes | 1 Low | API key could appear in DEBUG stack traces |
| A10 | Server-Side Request Forgery | Yes | 1 Low | RSS URLs fetched without internal network filtering |

**Coverage: 8/10 categories tested**

# STRIDE Coverage

| Category | Tested | Findings |
|----------|--------|----------|
| Spoofing | Yes | 1 Low (static credentials) |
| Tampering | Yes | 1 Medium (blog XSS), 2 Low |
| Repudiation | No | Not tested |
| Information Disclosure | Yes | 2 Low (API key in traces, SSRF) |
| Denial of Service | Yes | 1 Low (no timeouts) |
| Elevation of Privilege | Yes | 2 Low (pickle, GitHub token scope) |

**Coverage: 5/6 categories tested**
