"""Regenerate branded artifacts (thumbnail + subtitle clip MP4s) for a client.

Use this after wiring a client's branding.logo_path when the original pipeline
run used the wrong (e.g., Fake Problems) logo. Only rebuilds the two surfaces
that bake the logo pixel-for-pixel:

  1. <ep_dir>/<audio_stem>_<timestamp>_thumbnail.png
  2. <ep_dir>/clips/*_censored_clip_*_subtitle.mp4

Does NOT re-transcribe, re-analyze, re-censor, or re-render the full episode
MP4 — those steps are expensive and their outputs don't carry the logo.

Usage:
    uv run python scripts/regen_client_branding.py <slug>
    uv run python scripts/regen_client_branding.py --all-churches
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


def regen_one(slug: str) -> dict:
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

    # --- 2. Regenerate subtitle clip MP4s ---
    from subtitle_clip_generator import SubtitleClipGenerator

    scg = SubtitleClipGenerator()
    clips_dir = ep_dir / "clips"
    clip_wavs = sorted(clips_dir.glob(f"*_{ts}_censored_clip_*.wav"))
    # Pair each wav with its best_clip (index matches: clip_01 → best_clips[0])
    best_clips = analysis.get("best_clips", [])
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

    return {
        "slug": slug,
        "status": "ok",
        "thumbnail": str(thumb_path) if thumb_ok else None,
        "subtitle_clips": len([c for c in regen_clips if c]),
        "subtitle_clips_total": len(clip_wavs),
        "ep_dir": str(ep_dir),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", nargs="?", help="Client slug (omit with --all-churches)")
    ap.add_argument(
        "--all-churches",
        action="store_true",
        help="Regenerate artifacts for all 10 church outreach prospects.",
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
            r = regen_one(slug)
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
