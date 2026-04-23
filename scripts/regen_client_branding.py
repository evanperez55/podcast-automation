"""Regenerate branded artifacts (thumbnail + subtitle clip MP4s) for a client.

Use this after wiring a client's branding.logo_path when the original pipeline
run used the wrong (e.g., Fake Problems) logo. Only rebuilds the three
surfaces that depend on the logo or on clip boundaries:

  1. <ep_dir>/<audio_stem>_<timestamp>_thumbnail.png
  2. <ep_dir>/clips/*_censored_clip_*.wav  (re-sliced from censored.wav with
     word-snapped boundaries so clips no longer start/end mid-sentence)
  3. <ep_dir>/clips/*_censored_clip_*_subtitle.mp4

Does NOT re-transcribe, re-analyze, re-censor, or re-render the full episode
MP4 — those steps are expensive and their outputs don't carry the logo.

Usage:
    uv run python scripts/regen_client_branding.py <slug>
    uv run python scripts/regen_client_branding.py --all-churches
    uv run python scripts/regen_client_branding.py <slug> --skip-reslice
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from client_config import activate_client  # noqa: E402
from config import Config  # noqa: E402
from content_editor import snap_clip_boundary_to_words  # noqa: E402
from logger import logger  # noqa: E402

CHURCH_SLUGS = [
    "redeemer-city-church-tampa",
    "christ-community-church-columbus",
    "metro-tab-church",
    "the-crossings-church-collinsville",
    "faith-bible-church-edmond",
    "life-bridge-church-green-bay",
    "cottonwood-church",
    "mercy-village-church",
    "harbor-rock-tabernacle",
    "christ-community-church-johnson-city",
]

_TIMESTAMP_RE = re.compile(r"_(\d{8}_\d{6})_")


def _latest_ep_dir(slug: str) -> Optional[Path]:
    out = Config.BASE_DIR / "output" / slug
    if not out.exists():
        return None
    eps = [d for d in out.iterdir() if d.is_dir() and d.name.startswith("ep_")]
    return max(eps, key=lambda d: d.stat().st_mtime) if eps else None


def _latest_timestamp(ep_dir: Path) -> Optional[str]:
    stamps = set()
    for f in ep_dir.rglob("*"):
        m = _TIMESTAMP_RE.search(f.name)
        if m:
            stamps.add(m.group(1))
    return max(stamps) if stamps else None


def _find_file(ep_dir: Path, suffix: str, timestamp: str) -> Optional[Path]:
    for f in ep_dir.glob(f"*_{timestamp}_{suffix}"):
        return f
    return None


def _reslice_clips_with_snap(
    ep_dir: Path,
    timestamp: str,
    best_clips: list,
    words: list,
) -> int:
    """Re-slice censored.wav into *_clip_NN.wav using word-snapped boundaries.

    Overwrites the existing per-clip WAV files so downstream subtitle/video
    renders pick up the cleaner boundaries. Returns count of WAVs re-sliced.
    """
    from audio_processor import AudioProcessor

    censored = next(ep_dir.glob(f"*_{timestamp}_censored.wav"), None)
    if censored is None:
        logger.warning(
            "No censored.wav found for reslicing under %s (timestamp %s)",
            ep_dir,
            timestamp,
        )
        return 0

    clips_dir = ep_dir / "clips"
    clip_wavs = sorted(clips_dir.glob(f"*_{timestamp}_censored_clip_*.wav"))
    if not clip_wavs:
        logger.warning("No existing clip WAVs under %s", clips_dir)
        return 0

    processor = AudioProcessor()
    from pydub import AudioSegment

    full_audio = AudioSegment.from_file(str(censored))

    count = 0
    for i, wav_path in enumerate(clip_wavs):
        if i >= len(best_clips):
            break
        clip = best_clips[i]
        start_s = clip.get("start_seconds")
        end_s = clip.get("end_seconds")
        if start_s is None or end_s is None:
            logger.warning(
                "Clip %d missing start_seconds/end_seconds; skipping reslice",
                i + 1,
            )
            continue
        snapped_start, snapped_end = snap_clip_boundary_to_words(start_s, end_s, words)
        moved = abs(snapped_start - start_s) + abs(snapped_end - end_s)
        logger.info(
            "Clip %d: %.2f-%.2f -> %.2f-%.2f (moved %.2fs total)",
            i + 1,
            start_s,
            end_s,
            snapped_start,
            snapped_end,
            moved,
        )
        # Persist snapped boundaries back into analysis for future referenceand
        # rendering correctness (subtitle_clip_generator uses start_seconds).
        clip["start_seconds"] = snapped_start
        clip["end_seconds"] = snapped_end

        # Re-slice using the shared AudioProcessor helper (handles fades).
        processor.extract_clip(
            audio_file_path=str(censored),
            start_seconds=snapped_start,
            end_seconds=snapped_end,
            output_path=str(wav_path),
            _audio=full_audio,
        )
        count += 1

    return count


def regen_one(slug: str, skip_reslice: bool = False) -> dict:
    """Regenerate branded artifacts for one client. Returns a summary dict."""
    activate_client(slug)
    ep_dir = _latest_ep_dir(slug)
    if ep_dir is None:
        return {"slug": slug, "status": "no_episode_dir"}

    ts = _latest_timestamp(ep_dir)
    if not ts:
        return {"slug": slug, "status": "no_timestamp"}

    analysis_path = _find_file(ep_dir, "analysis.json", ts)
    transcript_path = _find_file(ep_dir, "transcript.json", ts)
    if not analysis_path or not transcript_path:
        return {
            "slug": slug,
            "status": "missing_analysis_or_transcript",
            "analysis": str(analysis_path),
            "transcript": str(transcript_path),
        }

    with open(analysis_path, encoding="utf-8") as f:
        analysis = json.load(f)
    with open(transcript_path, encoding="utf-8") as f:
        transcript_data = json.load(f)

    episode_title = analysis.get("episode_title", "")
    # Best effort episode number from directory name; default to 1 if unknown.
    m = re.search(r"ep_(\d+)", ep_dir.name)
    episode_number = int(m.group(1)) if m and m.group(1).isdigit() else 1

    # --- 1. Regenerate thumbnail (overwrite the existing one in place) ---
    from thumbnail_generator import ThumbnailGenerator

    tg = ThumbnailGenerator()
    existing_thumb = next(ep_dir.glob(f"*_{ts}_thumbnail.png"), None)
    if existing_thumb is None:
        return {"slug": slug, "status": "no_existing_thumbnail"}
    thumb_path = existing_thumb
    result = tg.generate_thumbnail(
        episode_title=episode_title,
        episode_number=episode_number,
        output_path=str(thumb_path),
    )
    thumb_ok = result is not None

    # --- 2. Re-slice clip WAVs with word-snapped boundaries ---
    best_clips = analysis.get("best_clips", [])
    words = transcript_data.get("words", [])
    resliced = 0
    if not skip_reslice:
        resliced = _reslice_clips_with_snap(ep_dir, ts, best_clips, words)
        # Persist the snapped start_seconds/end_seconds back to analysis.json
        # so future subtitle rendering runs see the refined values.
        with open(analysis_path, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        logger.info("Updated analysis.json with snapped clip boundaries")

    # --- 3. Regenerate subtitle clip MP4s ---
    from subtitle_clip_generator import SubtitleClipGenerator

    scg = SubtitleClipGenerator()
    clips_dir = ep_dir / "clips"
    clip_wavs = sorted(clips_dir.glob(f"*_{ts}_censored_clip_*.wav"))
    regen_clips = []
    for i, wav in enumerate(clip_wavs):
        clip_info = best_clips[i] if i < len(best_clips) else {}
        output_path = scg.create_subtitle_clip(
            audio_path=str(wav),
            srt_path=None,
            transcript_data=transcript_data,
            clip_info=clip_info,
            format_type="vertical",
        )
        regen_clips.append(output_path)
        logger.info(
            "Regenerated subtitle clip %d/%d: %s", i + 1, len(clip_wavs), output_path
        )

    # --- 4. Refresh clips/final/ with the new MP4 content (clean filenames) ---
    # The original pipeline publishes clips into <ep>/clips/final/ with
    # human-readable names like `clip_01_<slug>.mp4` (see pipeline/steps/video.py).
    # Those copies got stale when we regenerated the raw *_subtitle.mp4 files
    # above — refresh them here using the same naming convention so the
    # outreach_prepare step picks up the pretty names.
    final_refreshed = _refresh_clips_final(clips_dir, regen_clips, best_clips)

    return {
        "slug": slug,
        "status": "ok",
        "thumbnail": str(thumb_path) if thumb_ok else None,
        "resliced_wavs": resliced,
        "subtitle_clips": len([c for c in regen_clips if c]),
        "subtitle_clips_total": len(clip_wavs),
        "final_refreshed": final_refreshed,
        "ep_dir": str(ep_dir),
    }


def _refresh_clips_final(clips_dir: Path, regen_clips: list, best_clips: list) -> int:
    """Copy regenerated *_subtitle.mp4 content into clips/final/ with clean names.

    Matches the naming pattern used by pipeline/steps/video.py:
        clip_{idx:02d}_{sanitized_title}.mp4

    PURGES any existing clip_*.mp4 files first. Multi-run clients otherwise
    accumulate stale clips from prior pipeline runs (where suggested_title
    differed), which then leak into the Drive upload and show old FP-branded
    content alongside the newly-branded clips. Returns count of clips refreshed.
    """
    import shutil

    final_dir = clips_dir / "final"
    final_dir.mkdir(exist_ok=True)

    # Purge stale clip_*.mp4 leftover from previous pipeline runs with
    # different suggested_title naming. Anything non-clip stays.
    stale = sorted(final_dir.glob("clip_*.mp4"))
    for p in stale:
        try:
            p.unlink()
        except OSError as e:
            logger.warning("Could not remove stale %s: %s", p, e)
    if stale:
        logger.info("Purged %d stale clip_*.mp4 from %s", len(stale), final_dir)

    count = 0
    for i, vpath in enumerate(regen_clips):
        if not vpath or not Path(vpath).exists():
            continue
        title = "clip"
        if i < len(best_clips):
            title = best_clips[i].get("suggested_title", "clip")
        safe_title = re.sub(r"[^\w\s-]", "", title).strip()
        safe_title = re.sub(r"[\s]+", "_", safe_title).lower()[:50]
        dest = final_dir / f"clip_{i + 1:02d}_{safe_title}.mp4"
        shutil.copy2(str(vpath), str(dest))
        count += 1
    logger.info("Refreshed %d clip(s) in %s", count, final_dir)
    return count


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", nargs="?", help="Client slug (omit with --all-churches)")
    ap.add_argument(
        "--all-churches",
        action="store_true",
        help="Regenerate artifacts for all 10 church outreach prospects.",
    )
    ap.add_argument(
        "--skip-reslice",
        action="store_true",
        help="Skip re-slicing clip WAVs (use existing boundaries).",
    )
    args = ap.parse_args()

    if args.all_churches:
        targets = CHURCH_SLUGS
    elif args.slug:
        targets = [args.slug]
    else:
        ap.error("must pass a slug or --all-churches")
        return 2

    results = []
    for slug in targets:
        print(f"\n=== {slug} ===")
        try:
            r = regen_one(slug, skip_reslice=args.skip_reslice)
        except Exception as e:
            logger.exception("Regen failed for %s", slug)
            r = {"slug": slug, "status": "error", "error": str(e)}
        results.append(r)
        print(json.dumps(r, indent=2, default=str))

    print("\n=== SUMMARY ===")
    for r in results:
        print(f"  {r['slug']:40s} {r['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
