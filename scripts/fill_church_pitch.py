"""Fill Wave C placeholders in a church prospect's PITCH.md from processed output.

Usage:
    uv run python scripts/fill_church_pitch.py <slug> [--lead-clip N]

Reads the analysis.json from output/<slug>/ep_*/ (picks most recent) and
substitutes template placeholders with episode-specific content.

Placeholders filled:
    {{SERMON_TITLE}}, {{SPECIFIC_MOMENT_REFERENCE}}, {{NUM_CLIPS}},
    {{BEST_CLIP_TITLE}}, {{CLIP_TIMESTAMP}}, {{WHY_THIS_CLIP_WORKS}},
    {{CLIP_N_TITLE}}, {{CLIP_N_DURATION}} for N in 1..5
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def fmt_mmss(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def fmt_timestamp_range(start: str, end: str) -> str:
    """Convert 'HH:MM:SS' timestamps to a compact range for email pitches.

    Drops the hour component when it is 00 and strips leading zeros from
    the resulting minute field so '00:05:30' renders as '5:30', not '05:30'.
    Keeps the hour when non-zero ('01:05:30' → '01:05:30').
    """

    def compact(t: str) -> str:
        parts = t.split(":")
        if len(parts) == 3 and parts[0] == "00":
            mm, ss = parts[1], parts[2]
            return f"{int(mm)}:{ss}"
        return t

    return f"{compact(start)}-{compact(end)}"


class FillResult(dict):
    """Status dict returned by fill(). Sentinel ok=False means filling did
    not happen for an expected reason (no episode processed yet, no PITCH);
    callers can choose to skip silently. ok=False with err=... is a real error."""


def fill(
    slug: str,
    lead_clip: int = 1,
    moment: str | None = None,
    why: str | None = None,
) -> FillResult:
    """Fill template placeholders in a prospect's PITCH.md from latest analysis.

    Returns a FillResult dict:
      {ok: True, ep_dir, sermon_title, lead_clip_title, leftover_placeholders}
      {ok: False, reason: 'no_episode' | 'no_analysis' | 'no_clips' | 'no_pitch' | 'lead_clip_out_of_range', err: str}

    Idempotent — re-running on an already-filled PITCH is a no-op for placeholders
    already replaced (str.replace finds nothing to replace). Safe to call from
    outreach_prepare.py before each draft.
    """
    output_root = Path(f"output/{slug}")
    if not output_root.exists():
        return FillResult(
            ok=False, reason="no_episode", err=f"No output directory at {output_root}"
        )

    ep_dirs = sorted(
        [d for d in output_root.iterdir() if d.is_dir() and d.name.startswith("ep_")],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    if not ep_dirs:
        return FillResult(
            ok=False, reason="no_episode", err=f"No processed episodes in {output_root}"
        )
    ep_dir = ep_dirs[0]

    analysis_files = sorted(
        ep_dir.glob("*_analysis.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not analysis_files:
        return FillResult(
            ok=False, reason="no_analysis", err=f"No analysis.json in {ep_dir}"
        )
    analysis = json.loads(analysis_files[0].read_text(encoding="utf-8"))

    sermon_title = analysis.get("episode_title", "")
    clips = analysis.get("best_clips", [])
    if not clips:
        return FillResult(ok=False, reason="no_clips", err="no best_clips in analysis")

    lead_idx = lead_clip - 1
    if lead_idx < 0 or lead_idx >= len(clips):
        return FillResult(
            ok=False,
            reason="lead_clip_out_of_range",
            err=f"--lead-clip {lead_clip} out of range 1..{len(clips)}",
        )
    lead = clips[lead_idx]

    derived_moment = moment or (
        f'the part that grabbed me was "{analysis.get("hot_take", "").strip()}"'
        if analysis.get("hot_take")
        else f"the {lead.get('description', '').lower().rstrip('.')} section landed especially well"
    )
    derived_why = why or (
        f'{lead.get("why_interesting", "").rstrip(".")}. The hook "{lead.get("hook_caption", "")}" works in the first 2 seconds'
        if lead.get("why_interesting")
        else "strong hook + clear payoff, works as a Short on its own"
    )

    pitch_path = Path(f"demo/church-vertical/{slug}/PITCH.md")
    if not pitch_path.exists():
        return FillResult(
            ok=False, reason="no_pitch", err=f"No PITCH.md at {pitch_path}"
        )
    text = pitch_path.read_text(encoding="utf-8")

    replacements = {
        "{{SERMON_TITLE}}": sermon_title,
        "{{SPECIFIC_MOMENT_REFERENCE}}": derived_moment,
        "{{NUM_CLIPS}}": str(len(clips)),
        "{{BEST_CLIP_TITLE}}": lead.get("suggested_title", ""),
        "{{CLIP_TIMESTAMP}}": fmt_timestamp_range(lead["start"], lead["end"]),
        "{{WHY_THIS_CLIP_WORKS}}": derived_why,
        "{{EP_DIR}}": ep_dir.name,
    }
    for i, clip in enumerate(clips[:5], start=1):
        replacements[f"{{{{CLIP_{i}_TITLE}}}}"] = clip.get("suggested_title", "")
        replacements[f"{{{{CLIP_{i}_DURATION}}}}"] = fmt_mmss(
            clip.get("duration_seconds", 0)
        )
    for i in range(len(clips) + 1, 6):
        replacements[f"{{{{CLIP_{i}_TITLE}}}}"] = "(n/a)"
        replacements[f"{{{{CLIP_{i}_DURATION}}}}"] = "--"

    for placeholder, value in replacements.items():
        text = text.replace(placeholder, value)

    text = re.sub(
        r"- \[ \] Process latest episode:[^\n]+",
        f"- [x] Episode processed: {ep_dir.name}",
        text,
    )

    pitch_path.write_text(text, encoding="utf-8")
    leftover = sorted(set(re.findall(r"\{\{[A-Z_0-9]+\}\}", text)))

    return FillResult(
        ok=True,
        ep_dir=ep_dir.name,
        sermon_title=sermon_title,
        lead_clip_title=lead.get("suggested_title", ""),
        clip_timestamp=replacements["{{CLIP_TIMESTAMP}}"],
        leftover_placeholders=leftover,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", help="Prospect slug (e.g. redeemer-city-church-tampa)")
    ap.add_argument(
        "--lead-clip",
        type=int,
        default=1,
        help="1-indexed clip number to lead with (default: 1)",
    )
    ap.add_argument(
        "--moment",
        default=None,
        help="Custom SPECIFIC_MOMENT_REFERENCE sentence. If omitted, derived from hot_take.",
    )
    ap.add_argument(
        "--why",
        default=None,
        help="Custom WHY_THIS_CLIP_WORKS sentence. If omitted, derived from clip's why_interesting.",
    )
    args = ap.parse_args()

    result = fill(args.slug, args.lead_clip, args.moment, args.why)
    if not result.get("ok"):
        print(
            f"ERROR: {result.get('err', 'unknown')} (reason={result.get('reason')})",
            file=sys.stderr,
        )
        return 1

    pitch_path = Path(f"demo/church-vertical/{args.slug}/PITCH.md")
    print(f"FILLED: {pitch_path}")
    print(f"  Sermon: {result['sermon_title']}")
    print(f"  Lead clip: [{args.lead_clip}] {result['lead_clip_title']}")
    print(f"  Timestamp: {result['clip_timestamp']}")
    if result["leftover_placeholders"]:
        print(
            f"\nRemaining placeholders (still need manual fill): {result['leftover_placeholders']}"
        )
    else:
        print("\nAll template placeholders filled.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
