# Scenario Exploration Summary

**Date:** 2026-04-02
**Iterations:** 25
**Domain:** Software — Full podcast pipeline

## Score

```
scenario_score = 25 * 10 + 32 * 15 + (12/12) * 30 + 6 * 5 + 11 * 3
              = 250 + 480 + 30 + 30 + 33
              = 823
```

## Coverage Matrix

| Dimension | Scenarios | Highest Severity |
|-----------|-----------|-----------------|
| Happy path | 1 | - |
| Error path | 1 | HIGH |
| Edge case | 5 | HIGH |
| Integration | 3 | HIGH |
| Concurrent | 2 | CRITICAL |
| Temporal | 3 | MEDIUM |
| Recovery | 3 | HIGH |
| Data variation | 2 | MEDIUM |
| State transition | 2 | HIGH |
| Scale | 1 | HIGH |
| Abuse/misuse | 2 | CRITICAL |
| Permission | 1 | HIGH |

**All 12 dimensions covered.**

## Severity Breakdown

- **CRITICAL (2):** Concurrent pipeline runs (#5), command injection (#13)
- **HIGH (11):** Partial downloads (#2), YouTube quota (#4), platform outage partial state (#6), Bluesky token expiry (#10), stuck failed slots (#11), 3-hour episode limits (#12), YouTube auth loss (#14), malformed GPT output (#16), duplicate GitHub Actions (#17), OpenAI rate limits (#21), calendar corruption (#25)
- **MEDIUM (8):** Zero profanity (#3), special chars (#7), crash recovery (#8), short episode (#9), DST drift (#15), burst posting (#19), 60s clip boundary (#20), long title (#24)
- **LOW (4):** MP3 input (#18), checkpoint key mismatch (#22), cross-platform pickle (#23)

## Top 5 Actionable Findings

1. **No concurrent run protection** (#5) — Add PID file or file lock to prevent two pipeline runs
2. **Failed calendar slots never retry** (#11) — Add retry logic or "pending_retry" status
3. **YouTube quota leaves orphan calendar slots** (#4) — Don't create calendar slots until upload succeeds
4. **Partial platform failure in scheduling** (#6) — Track per-platform status, not just overall slot status
5. **GPT output not validated** (#16) — Add schema validation for analysis JSON before downstream use

## Already Handled (Verified)

- Calendar JSON corruption (#25) — `load_all()` catches JSONDecodeError ✓
- Command injection (#13) — All subprocess calls use list args (shell=False) ✓
- Cross-platform pickle (#23) — google-auth objects are platform-independent ✓
