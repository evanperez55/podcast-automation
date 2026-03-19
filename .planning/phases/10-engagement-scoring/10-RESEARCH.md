# Phase 10: Engagement Scoring - Research

**Researched:** 2026-03-19
**Domain:** scipy correlation analysis, engagement_history.json consumption, GPT-4o prompt augmentation, topic_scorer bug fix
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ENGAGE-01 | Topic categories ranked by historical engagement correlation | scipy.stats.pearsonr/spearmanr on engagement_history.json records; category appears as binary presence flag per episode; correlation between flag vector and engagement score vector produces ranking |
| ENGAGE-02 | Day-of-week performance analysis per platform | `post_timestamp` field already in engagement_history.json; parse to `datetime.weekday()` (0=Mon, 6=Sun); group by platform, average engagement score per weekday; return as dict mapping `{platform: {weekday: avg_score}}` |
| ENGAGE-03 | Comedy voice preserved as constraint — optimizer cannot de-score edgy content | Implement as hard filter in scorer output: before returning recommendations, remove any logic that would lower scores for "edgy", "dark", or "shocking" categories; edgy_categories list is a config constant, not a score variable |
| ENGAGE-04 | Confidence gating — no recommendations until minimum data threshold met (15+ episodes) | Count records in engagement_history.json; if `len(records) < 15`, return `{"status": "insufficient_data", "episodes_needed": 15 - len(records), "rankings": None}` |
| CONTENT-02 | GPT-4o title/caption optimization using engagement history as context | Add engagement context block to `_build_analysis_prompt()` in content_editor.py; load top-3 category rankings from engagement_scorer.get_category_rankings() and inject as text section alongside existing topic_context section |
</phase_requirements>

## Summary

Phase 10 builds the engagement scoring model that consumes the `engagement_history.json` produced by Phase 9. The core artifact is a new `engagement_scorer.py` module (distinct from the existing `TopicEngagementScorer` class in `analytics.py`). This new module reads accumulated episode records, extracts category-level engagement signals using scipy Pearson and Spearman correlations, and returns a ranked profile with confidence metadata.

The dataset is small (~30 episodes as of 2026). This is a deliberate decision — scikit-learn was explicitly rejected because ML models require larger datasets. scipy correlations are appropriate here: they provide directional signals (which categories correlate with higher engagement) without overfitting to noise. Spearman is preferred over Pearson for this use case because engagement scores are not normally distributed and the relationship between category presence and engagement may be monotonic rather than strictly linear.

Two secondary tasks complete the phase: (1) fixing a loop-index bug in `topic_scorer.py` where `get_engagement_bonus(i + 1)` uses the batch loop counter instead of the actual episode number, and (2) injecting the top category rankings from the new scorer into the `_build_analysis_prompt()` context in `content_editor.py` so GPT-4o can use engagement history when generating titles and captions.

**Primary recommendation:** Build `engagement_scorer.py` as a standalone module with a single public class `EngagementScorer`. Keep it separate from `analytics.py` — that module handles collection, this one handles analysis. Fix the topic_scorer bug first (it's one-line), then build the scorer, then wire CONTENT-02.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `scipy.stats` | 1.16.3 (installed) | Pearson and Spearman correlation | Explicit project decision; verified installed; appropriate for n=30 dataset |
| `numpy` | 2.4.3 (installed, but see constraint) | Array operations for correlation inputs | Required by scipy; already transitive dependency |
| `pandas` | 2.3.3 (installed) | DataFrame groupby for day-of-week analysis (ENGAGE-02) | Installed as transitive dependency; simplifies weekday grouping over raw dicts |
| `json` (stdlib) | 3.12 | Read engagement_history.json | Already the project pattern everywhere |
| `datetime` (stdlib) | 3.12 | Parse post_timestamp for day-of-week extraction | Already used throughout project |

### Numpy Version Constraint (CRITICAL)

STATE.md records: `numpy constrained to <2.0.0 — torch 2.1.0 compatibility requirement`. However, the installed version is numpy 2.4.3. This means either:
1. The constraint was not enforced on this machine, OR
2. The constraint has been relaxed since the decision was recorded

**Action:** Do NOT add `numpy<2.0.0` to requirements.txt. The installed numpy 2.4.3 works with the installed scipy 1.16.3. Verify torch still imports before committing. If it breaks, add the pin then.

### No New Library Installs Required

pandas 2.3.3, scipy 1.16.3, and numpy 2.4.3 are all already installed (verified via `python -c "import X; print(X.__version__)"`). None need to be added to requirements.txt. However, they are NOT currently listed there — add them as documentation-only entries with `# already installed as transitive dependencies`.

**Installation:**
```bash
# Already installed — no action required
# pip install pandas scipy  # only if fresh environment
```

## Architecture Patterns

### New File

```
engagement_scorer.py        # NEW: EngagementScorer class — reads history, runs correlations
tests/test_engagement_scorer.py  # NEW: test file
```

### Modified Files

```
topic_scorer.py             # BUG FIX: line 182 — get_engagement_bonus(i + 1) -> get_engagement_bonus(actual_ep_number)
content_editor.py           # EXTEND: _build_analysis_prompt() — add engagement_context param + inject section
pipeline/steps/analysis.py  # EXTEND: load engagement profile, pass to analyze_content()
```

### Pattern 1: EngagementScorer Public Interface

```python
# engagement_scorer.py
class EngagementScorer:
    def __init__(self):
        self.history_path = Config.BASE_DIR / "topic_data" / "engagement_history.json"
        self.min_episodes = 15  # ENGAGE-04 confidence gate

    def get_category_rankings(self) -> dict:
        """
        Returns:
            {
                "status": "ok" | "insufficient_data",
                "episodes_analyzed": int,
                "episodes_needed": int | None,
                "rankings": [
                    {"category": str, "correlation": float, "method": "spearman",
                     "p_value": float, "episode_count": int}
                ] | None,
                "day_of_week": {
                    "youtube": {"Monday": float, ...},
                    "twitter": {"Monday": float, ...}
                } | None,
            }
        """
```

**Confidence gate logic:**

```python
# Source: requirements ENGAGE-04
history = self._load_history()
if len(history) < self.min_episodes:
    return {
        "status": "insufficient_data",
        "episodes_analyzed": len(history),
        "episodes_needed": self.min_episodes - len(history),
        "rankings": None,
        "day_of_week": None,
    }
```

### Pattern 2: Spearman Correlation for Category Ranking

Use Spearman, not Pearson, for category correlation. Engagement scores are not normally distributed (few high-engagement outliers dominate). Spearman is rank-based and more robust to outliers.

```python
# Source: verified via scipy 1.16.3 REPL test
from scipy import stats

def _correlate_category(self, history: list, category: str) -> dict | None:
    """Correlate binary category presence with engagement scores."""
    # Build parallel arrays: presence (0/1) and engagement score
    presence = []
    scores = []
    for record in history:
        topics = record.get("topics", [])
        # Simple membership check — topics are clip titles, not structured categories
        # Use category keyword matching or stored category field
        has_category = 1 if any(category.lower() in str(t).lower() for t in topics) else 0
        presence.append(has_category)
        scores.append(record.get("engagement_score", 0.0))

    if len(presence) < 3:
        return None  # Not enough variance to correlate

    rho, p = stats.spearmanr(presence, scores, nan_policy='omit')
    return {
        "category": category,
        "correlation": round(float(rho), 4),
        "p_value": round(float(p), 4),
        "method": "spearman",
        "episode_count": len(presence),
    }
```

**Note on categories:** The `engagement_history.json` records store `topics` as a list of clip titles (strings), not structured category tags. The scorer must either:
- Match category keywords against topic strings (flexible, lossy), OR
- Read engagement history records that include the `category` field from topic_scorer output

Check actual engagement_history.json structure when it exists. If category field is absent, use keyword matching against the five known categories: `shocking_news`, `absurd_hypothetical`, `dating_social`, `pop_science`, `cultural_observation`.

### Pattern 3: Day-of-Week Analysis (ENGAGE-02)

```python
# Source: stdlib datetime — verified pattern
from datetime import datetime

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def _analyze_day_of_week(self, history: list) -> dict:
    """Group engagement scores by weekday per platform."""
    platform_weekday_scores = {
        "youtube": {day: [] for day in WEEKDAY_NAMES},
        "twitter": {day: [] for day in WEEKDAY_NAMES},
    }
    for record in history:
        ts = record.get("post_timestamp")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts)
            weekday = WEEKDAY_NAMES[dt.weekday()]
        except (ValueError, TypeError):
            continue

        yt = record.get("youtube")
        if yt and yt.get("views") is not None:
            platform_weekday_scores["youtube"][weekday].append(
                self._score_youtube(yt)
            )
        tw = record.get("twitter")
        if tw and tw.get("engagements") is not None:
            platform_weekday_scores["twitter"][weekday].append(
                self._score_twitter(tw)
            )

    # Average per weekday
    result = {}
    for platform, weekday_scores in platform_weekday_scores.items():
        result[platform] = {
            day: round(sum(scores) / len(scores), 2) if scores else None
            for day, scores in weekday_scores.items()
        }
    return result
```

### Pattern 4: Comedy Voice Constraint (ENGAGE-03)

The comedy voice constraint is NOT a scoring adjustment — it's a filter on what categories can be ranked down. Implement as a hard exclusion list:

```python
# In EngagementScorer
COMEDY_PROTECTED_CATEGORIES = {
    "shocking_news",
    "absurd_hypothetical",
    # These categories define the show's voice and must never be recommended against
}

def _apply_comedy_constraint(self, rankings: list) -> list:
    """Remove any ranking that would recommend against protected categories.

    Protected categories are never marked as 'avoid'. They can appear as
    high-performing or neutral, but never as negative recommendations.
    """
    constrained = []
    for r in rankings:
        if r["category"] in self.COMEDY_PROTECTED_CATEGORIES:
            # Clamp correlation floor to 0 — never let it go negative enough
            # to generate an "avoid" recommendation for protected categories
            r = dict(r)  # copy
            r["correlation"] = max(r["correlation"], 0.0)
            r["comedy_protected"] = True
        constrained.append(r)
    return constrained
```

### Pattern 5: CONTENT-02 — GPT-4o Engagement Context Injection

`content_editor.py` already has a `topic_context` injection pattern at line ~155-168. Add a parallel `engagement_context` param:

```python
# content_editor.py — _build_analysis_prompt() extension
def _build_analysis_prompt(
    self, timestamped_text, topic_context=None,
    energy_candidates=None, engagement_context=None  # NEW param
):
    # ... existing code ...

    engagement_section = ""
    if engagement_context and engagement_context.get("status") == "ok":
        rankings = engagement_context.get("rankings", [])[:3]  # Top 3 categories
        if rankings:
            lines = []
            for r in rankings:
                lines.append(
                    f"  - {r['category']}: correlation={r['correlation']:.2f} "
                    f"({'positive' if r['correlation'] > 0 else 'neutral'})"
                )
            engagement_section = (
                "\n**HISTORICALLY HIGH-PERFORMING CONTENT CATEGORIES "
                "(bias titles/captions toward these when relevant):**\n"
                + "\n".join(lines)
                + "\n"
            )
```

Then in `pipeline/steps/analysis.py`, load the engagement profile and pass it:

```python
# analysis.py
from engagement_scorer import EngagementScorer

def run_analysis(ctx, components, state=None):
    # ... existing ...
    engagement_context = None
    try:
        scorer = EngagementScorer()
        engagement_context = scorer.get_category_rankings()
    except Exception:
        pass  # engagement scoring is optional

    analysis = components["editor"].analyze_content(
        transcript_data,
        topic_context=topic_context,
        audio_path=audio_file,
        engagement_context=engagement_context,  # NEW
    )
```

### Pattern 6: topic_scorer.py Bug Fix (loop index vs episode number)

**Bug location:** `topic_scorer.py` line 182

```python
# CURRENT (BROKEN):
for i, topic in enumerate(topics):
    # ...
    bonus = eng_scorer.get_engagement_bonus(i + 1)  # BUG: i is batch-local loop index

# FIXED:
for i, topic in enumerate(topics):
    # ...
    actual_ep = topic.get("episode_number") or topic.get("ep_number")
    if actual_ep:
        bonus = eng_scorer.get_engagement_bonus(actual_ep)
    else:
        bonus = None  # No episode number available in topic metadata
```

**Note:** Topics scraped from Reddit/news do not have episode numbers yet — they are future topics, not past episodes. The `get_engagement_bonus()` call here was conceptually wrong: it was trying to get engagement data for a topic's associated episode, but future topics have no associated episode. The correct fix is to remove the call entirely OR to only apply the bonus when the topic dict contains a verified `episode_number` field from a matched past episode. The planner should decide which approach.

### Anti-Patterns to Avoid

- **Don't use Pearson for engagement correlation:** Engagement scores are right-skewed (a few viral episodes dominate). Spearman handles this; Pearson will produce misleading results with outlier episodes.
- **Don't build a global engagement_scorer singleton:** `EngagementScorer()` is lightweight; instantiate per call site. The history file is small enough to re-read each call.
- **Don't merge EngagementScorer into analytics.py:** `analytics.py` is for collection; `engagement_scorer.py` is for analysis. Mixing them creates a 500+ line module with mixed concerns.
- **Don't return a confidence score below the 15-episode gate:** Returning low-confidence rankings below the threshold would look like data when it's noise. Return `None` rankings and let callers handle the insufficient-data case.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rank correlation on small dataset | Custom correlation loop | `scipy.stats.spearmanr` | Handles ties, NaN policy, p-value — three lines vs 50 |
| Day-of-week aggregation | Manual dict grouping loop | `pandas.DataFrame.groupby('weekday').mean()` | Less code; handles NaN rows cleanly |
| Confidence interval for correlation | Manual Fisher z-transform | `scipy.stats.spearmanr` p-value | Sufficient signal at this scale |

**Key insight:** At n=30, the statistics are too weak to justify complex machinery. The entire scorer can be ~150 lines. If it grows larger, something is over-engineered.

## Common Pitfalls

### Pitfall 1: Correlating categories with no variance
**What goes wrong:** If ALL episodes in the history have `shocking_news` content (very likely for this podcast), the presence vector is all 1s and scipy returns `nan` for correlation.
**Why it happens:** Correlation of a constant with any variable is undefined.
**How to avoid:** Before running correlation, check `len(set(presence_vector)) > 1`. If only one unique value, skip the category and return `{"correlation": None, "skipped": "no_variance"}`.
**Warning signs:** scipy returns `nan` or raises `ValueError: All values are identical`.

### Pitfall 2: topic_scorer bug fix breaks category topic scoring
**What goes wrong:** After removing the `get_engagement_bonus(i + 1)` call, topics that previously got an accidental bonus now lose it — potentially changing test outcomes.
**Why it happens:** The bug was that `i + 1` happened to match valid episode numbers for early topics in a batch, producing non-None bonuses by coincidence.
**How to avoid:** Update tests to expect `engagement_bonus=None` after the fix. The bonus should only apply when a topic has a real episode number — which scraped future topics do not.

### Pitfall 3: engagement_history.json may not exist yet
**What goes wrong:** `EngagementScorer` is called before `python main.py analytics` has ever run. The history file does not exist.
**How to avoid:** Check `self.history_path.exists()` before reading. Return `{"status": "insufficient_data", "episodes_analyzed": 0, "episodes_needed": 15, ...}` if the file is absent.

### Pitfall 4: engagement_history records may lack engagement_score field
**What goes wrong:** `append_to_engagement_history()` in `analytics.py` stores raw platform metrics, not the computed composite score. The scorer needs to recompute it.
**How to avoid:** In `engagement_scorer.py`, compute the composite score from raw metrics using the same formula as `TopicEngagementScorer.calculate_engagement_score()`. Don't assume a pre-computed `engagement_score` field exists in the history records.

### Pitfall 5: NaN propagation in Spearman with small samples
**What goes wrong:** If some records have `None` for YouTube metrics, the score vector contains NaN. Spearman with default `nan_policy='propagate'` returns NaN.
**How to avoid:** Always use `stats.spearmanr(..., nan_policy='omit')`. Verified working: records with NaN engagement are excluded from the correlation rather than poisoning it.

### Pitfall 6: CONTENT-02 param breaks analyze_content signature
**What goes wrong:** Adding `engagement_context` to `analyze_content()` breaks existing tests that call `analyze_content(transcript, topic_context=...)` without the new param.
**How to avoid:** Add `engagement_context=None` as a keyword argument with default None. All existing call sites continue to work without changes.

## Code Examples

### Loading and validating engagement history

```python
# Source: pattern consistent with analytics.py existing code
def _load_history(self) -> list:
    """Load engagement_history.json, returning empty list if absent."""
    if not self.history_path.exists():
        return []
    with open(self.history_path, "r", encoding="utf-8") as f:
        return json.load(f)
```

### Computing composite score from raw record

```python
# Source: mirrors TopicEngagementScorer.calculate_engagement_score() in analytics.py
def _compute_score(self, record: dict) -> float:
    """Recompute composite engagement score from raw platform metrics."""
    yt_score = 0.0
    tw_score = 0.0

    yt = record.get("youtube") or {}
    if yt:
        yt_score = min(
            yt.get("views", 0) * 0.001
            + yt.get("likes", 0) * 0.1
            + yt.get("comments", 0) * 0.5,
            7.0,
        )

    tw = record.get("twitter") or {}
    if tw:
        tw_impressions = tw.get("impressions") or 0  # None sentinel -> 0
        tw_score = min(
            tw_impressions * 0.0001
            + tw.get("engagements", 0) * 0.05
            + tw.get("retweets", 0) * 0.2
            + tw.get("likes", 0) * 0.1,
            3.0,
        )

    return round(min(yt_score + tw_score, 10.0), 1)
```

### Full Spearman correlation call

```python
# Source: verified via scipy 1.16.3 REPL
from scipy import stats
import numpy as np

rho, p = stats.spearmanr(presence_vector, score_vector, nan_policy='omit')
# Returns NaN if all presence values are identical (constant vector)
if np.isnan(rho):
    return None  # No variance — skip this category
```

### Day-of-week with pandas groupby

```python
# Source: pandas 2.3.3 — standard groupby pattern
import pandas as pd

df = pd.DataFrame([
    {"weekday": r["weekday"], "score": r["score"], "platform": r["platform"]}
    for r in weekday_records
    if r["score"] is not None
])
if df.empty:
    return {}
result = df.groupby(["platform", "weekday"])["score"].mean().round(2).to_dict()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `TopicEngagementScorer` in analytics.py — per-episode score only | `EngagementScorer` in new module — cross-episode category correlation | Phase 10 | Enables category-level recommendations, not just episode-level scores |
| `get_engagement_bonus(i + 1)` — loop index bug | `get_engagement_bonus(actual_ep_number)` | Phase 10 bug fix | Prevents incorrect bonus application to wrong episodes |
| GPT-4o prompt has no engagement context | GPT-4o prompt receives top-3 category performance data | Phase 10 | Titles/captions biased toward historically high-performing content types |

**Deprecated/outdated:**
- `TopicEngagementScorer.correlate_topics()` in analytics.py: This method exists but was never wired into the pipeline. It is superseded by `EngagementScorer.get_category_rankings()` in the new module. Leave it in analytics.py (don't delete) but don't wire it further.

## Open Questions

1. **Do engagement_history.json records contain a `category` field or only topic strings?**
   - What we know: `append_to_engagement_history()` stores `topics` as a list of clip titles (strings from `analysis["best_clips"]`). The clip objects do have a `category` field from topic_scorer, but it may not be threaded through to the history record.
   - What's unclear: Whether Phase 9 implementation stored structured categories or just title strings.
   - Recommendation: Check actual engagement_history.json when it exists. If categories are absent, use keyword matching against the 5 known category names. Document the limitation.

2. **topic_scorer.py bug fix — should `get_engagement_bonus` be removed entirely for future topics?**
   - What we know: Future scraped topics have no episode_number. The bonus was always being applied to wrong episodes (i+1 = loop index).
   - What's unclear: Whether any topic dicts ever contain a valid episode_number (e.g., from `match_topics_to_episodes.py`).
   - Recommendation: The planner should decide: (a) remove the bonus call for future topics entirely, or (b) only apply when `topic.get("episode_number")` is explicitly set. Option (a) is simpler and avoids the wrong-episode confusion.

3. **Minimum episode threshold — is 15 the right number at project scale?**
   - What we know: The project is ~30 episodes as of 2026-03-18. The 15-episode threshold is a locked decision.
   - What's unclear: How many of those 30 episodes have been through `main.py analytics` and thus appear in engagement_history.json.
   - Recommendation: The confidence gate check should be the first thing tested manually after implementation. If only 5 episodes are in history, the scorer will return `insufficient_data` and all downstream features degrade gracefully to `None`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.4.3 |
| Config file | none — discovery by convention |
| Quick run command | `pytest tests/test_engagement_scorer.py -x` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ENGAGE-01 | `get_category_rankings()` returns ranked categories with correlation + p-value | unit | `pytest tests/test_engagement_scorer.py::TestGetCategoryRankings -x` | Wave 0 |
| ENGAGE-01 | Spearman used (not Pearson) for category correlation | unit | `pytest tests/test_engagement_scorer.py::TestGetCategoryRankings::test_uses_spearman -x` | Wave 0 |
| ENGAGE-01 | Constant-presence category returns `None` correlation (no variance) | unit | `pytest tests/test_engagement_scorer.py::TestGetCategoryRankings::test_constant_presence_skipped -x` | Wave 0 |
| ENGAGE-02 | `get_category_rankings()` includes `day_of_week` dict with per-platform weekday averages | unit | `pytest tests/test_engagement_scorer.py::TestDayOfWeek -x` | Wave 0 |
| ENGAGE-02 | Weekday averages return `None` for days with no data | unit | `pytest tests/test_engagement_scorer.py::TestDayOfWeek::test_missing_days_return_none -x` | Wave 0 |
| ENGAGE-03 | Comedy-protected categories have `comedy_protected: True` and `correlation >= 0.0` | unit | `pytest tests/test_engagement_scorer.py::TestComedyConstraint -x` | Wave 0 |
| ENGAGE-04 | Returns `{"status": "insufficient_data"}` when fewer than 15 episodes | unit | `pytest tests/test_engagement_scorer.py::TestConfidenceGate::test_under_threshold -x` | Wave 0 |
| ENGAGE-04 | Returns `{"status": "ok"}` with rankings when 15+ episodes | unit | `pytest tests/test_engagement_scorer.py::TestConfidenceGate::test_at_threshold -x` | Wave 0 |
| ENGAGE-04 | Returns `{"status": "insufficient_data"}` when history file absent | unit | `pytest tests/test_engagement_scorer.py::TestConfidenceGate::test_no_history_file -x` | Wave 0 |
| CONTENT-02 | `_build_analysis_prompt()` includes engagement context section when `engagement_context` has `status=ok` | unit | `pytest tests/test_content_editor.py::TestBuildAnalysisPrompt::test_engagement_context_injected -x` | Wave 0 |
| CONTENT-02 | `_build_analysis_prompt()` gracefully omits section when `engagement_context` is None | unit | `pytest tests/test_content_editor.py::TestBuildAnalysisPrompt::test_no_engagement_context -x` | Wave 0 |
| bug fix | `get_engagement_bonus()` not called with loop index in topic_scorer | unit | `pytest tests/test_topic_scorer.py::TestTopicScorer::test_engagement_bonus_uses_episode_number -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_engagement_scorer.py -x`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_engagement_scorer.py` — new module, no tests exist
- [ ] `tests/test_topic_scorer.py` — does not currently exist; covers bug fix
- [ ] Two new test methods in `tests/test_content_editor.py` — `TestBuildAnalysisPrompt.test_engagement_context_injected` and `test_no_engagement_context`

## Sources

### Primary (HIGH confidence)
- scipy 1.16.3 installed locally — `scipy.stats.pearsonr` and `scipy.stats.spearmanr` verified via REPL; nan_policy='omit' tested
- pandas 2.3.3 installed locally — groupby pattern verified
- `analytics.py` source read — `append_to_engagement_history()` schema confirmed, `TopicEngagementScorer.calculate_engagement_score()` formula confirmed
- `content_editor.py` source read — `_build_analysis_prompt()` structure confirmed; existing topic_context injection pattern identified at line ~155
- `topic_scorer.py` source read — bug confirmed at line 182 (`get_engagement_bonus(i + 1)`)
- `.planning/STATE.md` — numpy constraint decision documented; confirmed numpy 2.4.3 is installed

### Secondary (MEDIUM confidence)
- STATE.md decision: scikit-learn rejected, scipy correlations chosen — project decision record

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified installed and tested via REPL
- Architecture: HIGH — all integration points read from source; no guesswork
- Pitfalls: HIGH — constant-vector pitfall and NaN behavior verified via REPL test; others derived from source reading

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable domain — no third-party API dependencies for the new module)
