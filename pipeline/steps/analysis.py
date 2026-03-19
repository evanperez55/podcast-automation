"""Analysis step: AI content analysis and topic tracker."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from config import Config
from engagement_scorer import EngagementScorer
from pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


def _load_scored_topics():
    """Load the most recent scored topics from topic_data/ directory.

    Returns:
        List of topic dicts with 'topic', 'score', 'category', or None if unavailable
    """
    topic_dir = Config.BASE_DIR / "topic_data"
    if not topic_dir.exists():
        return None

    # Find the most recent scored_topics file
    scored_files = sorted(topic_dir.glob("scored_topics_*.json"), reverse=True)
    if not scored_files:
        return None

    try:
        with open(scored_files[0], "r", encoding="utf-8") as f:
            data = json.load(f)

        # Flatten topics from all categories into a single ranked list
        topics = []
        for category, category_topics in data.get("topics_by_category", {}).items():
            for t in category_topics:
                score = t.get("score", {})
                if isinstance(score, dict) and score.get("recommended", False):
                    topics.append(
                        {
                            "topic": t.get("title", ""),
                            "score": score.get("total", 0),
                            "category": score.get("category", category),
                        }
                    )

        # Sort by score descending
        topics.sort(key=lambda x: x["score"], reverse=True)
        logger.info(
            "Loaded %d scored topics from %s", len(topics), scored_files[0].name
        )
        return topics if topics else None
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Failed to load scored topics: %s", e)
        return None


def run_analysis(
    ctx: PipelineContext,
    components: dict,
    state=None,
) -> PipelineContext:
    """Run Steps 3 and 3.5: AI content analysis and topic tracker update."""
    audio_file = ctx.audio_file
    episode_output_dir = ctx.episode_output_dir
    timestamp = ctx.timestamp
    transcript_data = ctx.transcript_data
    episode_number = ctx.episode_number

    # Step 3: Analyze content with AI
    print("STEP 3: ANALYZING CONTENT WITH AI")
    print("-" * 60)

    # Load scored topics for context (if available)
    topic_context = _load_scored_topics()

    analysis_path = episode_output_dir / f"{audio_file.stem}_{timestamp}_analysis.json"
    # Load engagement context for prompt enrichment (optional — never blocks pipeline)
    engagement_context = None
    try:
        scorer = EngagementScorer()
        engagement_context = scorer.get_category_rankings()
        logger.info(
            "Engagement context: %s (%d episodes)",
            engagement_context.get("status"),
            engagement_context.get("episodes_analyzed", 0),
        )
    except Exception:
        pass  # Engagement scoring is optional — never blocks analysis

    if state and state.is_step_completed("analyze"):
        outputs = state.get_step_outputs("analyze")
        analysis_path = Path(outputs["analysis_path"])
        with open(analysis_path, "r", encoding="utf-8") as f:
            analysis = json.load(f)
        logger.info("[RESUME] Skipping analysis (already completed)")
    else:
        analysis = components["editor"].analyze_content(
            transcript_data,
            topic_context=topic_context,
            audio_path=audio_file,
            engagement_context=engagement_context,
        )
        with open(analysis_path, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        logger.info("Analysis saved to: %s", analysis_path)

        # Save show notes as a standalone text file
        show_notes_text = analysis.get("show_notes", "")
        if show_notes_text:
            show_notes_path = (
                episode_output_dir / f"{audio_file.stem}_{timestamp}_show_notes.txt"
            )
            with open(show_notes_path, "w", encoding="utf-8") as f:
                f.write(show_notes_text)
            logger.info("Show notes saved to: %s", show_notes_path)

        if state:
            state.complete_step("analyze", {"analysis_path": str(analysis_path)})
    print()

    ctx.analysis = analysis

    # Step 3.5: Update Google Docs topic tracker
    if components.get("topic_tracker") and episode_number:
        topic_tracker = components["topic_tracker"]
        # Get full transcript text for topic matching
        full_transcript = " ".join(
            [seg.get("text", "") for seg in transcript_data.get("segments", [])]
        )
        episode_summary = analysis.get("episode_summary", "")

        topic_tracker.update_topics_for_episode(
            transcript_text=full_transcript,
            episode_summary=episode_summary,
            episode_number=episode_number,
        )
    elif not components.get("topic_tracker"):
        logger.info("Google Docs topic tracker not configured - skipping")
    print()

    return ctx
