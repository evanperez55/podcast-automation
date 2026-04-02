# Eliminated Hypotheses

Hypotheses investigated and disproven during the bug hunt. Equally valuable — these confirm the code is correct in these areas.

1. **ThreadPoolExecutor swallows exceptions** — `future.result()` properly re-raises. Both video.py branches handle this correctly.
2. **Race condition in analytics engagement_history** — Non-atomic read-modify-write, but single-user CLI tool. Not a practical risk.
3. **_merge_censor_timestamps false duplicate via 0-default** — Defensive coding, not practical. Both paths always produce timestamps with proper values.
4. **Zero-duration censor entries cause pydub error** — 50ms padding on each side handles zero-duration entries correctly.
5. **RSS feed XML escaping for special chars** — ElementTree handles XML escaping automatically via `.text` assignment.
6. **Compliance checker truncates long transcripts** — Full transcript sent, well within GPT-4o's 128K context window.
7. **filter_clips misaligns paths and info** — Same indices used for both lists, bounded by preview_clips output.
8. **Concurrent Dropbox access race condition** — Same pattern as analytics — single-user CLI tool.
9. **upload_clips partial failure handling** — Individual failures handled; caller logs warning for empty results.
10. **Config.validate() misses optional API keys** — By design. Optional services use self.enabled pattern.
11. **ASS subtitle hardcoded font sizes** — Width/height parameterized, PlayRes scales proportionally.
12. **GPT response missing required keys** — Uses json_schema structured output, guaranteeing all fields.
13. **FTS5 search crashes on special characters** — Exception caught, returns empty list gracefully.
14. **Word matching fails with punctuation** — `strip(".,!?;:\"'-")` handles punctuation correctly.
15. **FFmpeg misinterprets float seconds** — FFmpeg natively accepts float seconds like `60.5`.
