# Debug Session Summary — 2026-04-04

## Stats
- **Iterations:** 30
- **Bugs found:** 10 (3 HIGH, 4 MEDIUM, 3 LOW)
- **Hypotheses tested:** 29 (10 confirmed, 15 disproven, 4 reclassified)
- **Files investigated:** ~25 of ~60
- **Techniques used:** binary search, direct inspection, trace, pattern search, differential

## Top 3 Priority Fixes

1. **Staggered Instagram Reels broken in CI** — clip files are local-only, need to store Dropbox URLs in calendar
2. **Instagram token refresh wastes API calls** — runs unconditionally, ignores REFRESH_THRESHOLD, useless in CI
3. **Test suite pollution** — 19 of 26 failures are false negatives from Config state leaking between test files

## Debug Score
```
debug_score = 10 * 15 + 29 * 3 + (25/60) * 40 + (4/7) * 10
            = 150 + 87 + 16.7 + 5.7
            = 259.4
```
