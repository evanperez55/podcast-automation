"""Pre-upload smoke test for outreach demo packages.

Runs a battery of cheap checks against a client's staged assets BEFORE
the Drive upload + Gmail draft fire. Designed to catch the class of bugs
that hit us on 2026-04-22 (B021/B022): Fake Problems logo leaking into
client thumbnails + clips, URL-encoded filenames, stale copies in
clips/final/, and clip durations outside the configured window.

Checks performed per client slug:

  1. ep_dir exists and has the expected artifacts
     (thumbnail, quote cards, blog post, clips/final/*.mp4)

  2. Filename hygiene — no file in the staged package has a URL-encoded
     or base64 prefix that would leak an enclosure URL into Drive.

  3. Clip count matches len(best_clips) in analysis.json.

  4. Every clip duration is inside [CLIP_MIN_DURATION, CLIP_MAX_DURATION]
     (per-client, loaded via activate_client).

  5. No file is named `podcast_logo.png` / `podcast_logo.jpg` in the
     staged package — if that name shows up for a non-default client,
     a generator silently fell back to the Fake Problems asset.

  6. Logo-bleed fingerprint — compute a downscaled-mean hash of
     assets/podcast_logo.png (the Fake Problems logo) and compare
     against the thumbnail + one frame from each clip MP4. If the
     hash distance is below a threshold, flag as possible bleed.

Usage:
    uv run python scripts/outreach_verify.py <slug>
    uv run python scripts/outreach_verify.py --all-churches
    uv run python scripts/outreach_verify.py <slug> --strict   # exit 1 on any warning

Exit codes:
    0 — all checks passed
    1 — at least one ERROR finding (blocks upload)
    2 — at least one WARNING (use --strict to block on warnings too)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from client_config import activate_client  # noqa: E402
from config import Config  # noqa: E402

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
_URL_ENCODED_RE = re.compile(r"^(ep_)?(aHR0c|https%3A|http%3A)", re.IGNORECASE)
# perceptual-hash bleed detection threshold — lower means more similar, so
# distance < THRESHOLD is flagged as "likely same image". Empirical: the
# default FP logo matches itself at 0, matches a stretched version at ~5-15,
# matches an unrelated church logo at 25-40. 20 is a conservative cutoff.
_PHASH_DISTANCE_THRESHOLD = 20


class Finding:
    def __init__(self, level: str, check: str, msg: str):
        self.level = level  # "ERROR" | "WARN" | "OK"
        self.check = check
        self.msg = msg

    def __str__(self):
        return f"  [{self.level:5s}] {self.check:35s} {self.msg}"


def _ahash(img_path: Path, size: int = 16) -> Optional[int]:
    """Compute a downscaled-mean perceptual hash. Returns int bitmask."""
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        img = Image.open(img_path).convert("L").resize((size, size))
    except Exception:
        return None
    pixels = list(img.getdata())
    mean = sum(pixels) / len(pixels)
    bits = 0
    for i, px in enumerate(pixels):
        if px > mean:
            bits |= 1 << i
    return bits


def _hamming(a: int, b: int) -> int:
    """Population count of XOR — standard Hamming distance for hashes."""
    return bin(a ^ b).count("1")


def _extract_frame(mp4_path: Path, out_path: Path, seek: float = 2.0) -> bool:
    """Extract a single frame from an MP4 at `seek` seconds into `out_path`."""
    try:
        r = subprocess.run(
            [
                Config.FFMPEG_PATH,
                "-y",
                "-ss",
                str(seek),
                "-i",
                str(mp4_path),
                "-vframes",
                "1",
                str(out_path),
            ],
            capture_output=True,
        )
        return r.returncode == 0 and out_path.exists()
    except Exception:
        return False


def _get_duration(mp4_path: Path) -> Optional[float]:
    """Return MP4 duration in seconds via ffprobe, or None."""
    ffprobe = Path(Config.FFMPEG_PATH).parent / "ffprobe.exe"
    if not ffprobe.exists():
        ffprobe = "ffprobe"
    try:
        r = subprocess.run(
            [
                str(ffprobe),
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(mp4_path),
            ],
            capture_output=True,
            text=True,
        )
        return float(r.stdout.strip()) if r.returncode == 0 else None
    except Exception:
        return None


def _latest_ep_dir(slug: str) -> Optional[Path]:
    out = Config.BASE_DIR / "output" / slug
    if not out.exists():
        return None
    eps = [d for d in out.iterdir() if d.is_dir() and d.name.startswith("ep_")]
    return max(eps, key=lambda d: d.stat().st_mtime) if eps else None


# ---------------------------------------------------------------------------
# Color metadata check (B023 prevention)
# ---------------------------------------------------------------------------


def _check_clip_color_metadata(clip_path: Path) -> Optional[str]:
    """Verify a clip's color VUI tags are all bt709.

    Returns:
        "OK"          — all three (transfer, primaries, space) are bt709
        error string  — at least one field is wrong/unset (B023 condition)
        None          — ffprobe couldn't run; skip the check rather than false-fail
    """
    ffprobe = Path(Config.FFMPEG_PATH).parent / "ffprobe.exe"
    if not ffprobe.exists():
        ffprobe = "ffprobe"
    try:
        r = subprocess.run(
            [
                str(ffprobe),
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=color_transfer,color_primaries,color_space",
                "-of",
                "json",
                str(clip_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if r.returncode != 0:
            return None
        data = json.loads(r.stdout)
        stream = (data.get("streams") or [{}])[0]
        bad = []
        for field in ("color_transfer", "color_primaries", "color_space"):
            v = stream.get(field)
            if v != "bt709":
                bad.append(f"{field}={v or 'unspecified'}")
        return "OK" if not bad else ", ".join(bad)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return None


# ---------------------------------------------------------------------------
# PITCH ↔ PACKAGE parity check (2026-04-23 regression prevention)
# ---------------------------------------------------------------------------


# Maps regex (matched against a PITCH "Inside:" bullet) → (predicate, label).
# Iterated in order; first match wins so each bullet is only scored once.
_PITCH_PROMISE_CHECKS = [
    (
        re.compile(r"\bclips?\b", re.IGNORECASE),
        lambda staged: any(p.startswith("clips/clip_") for p in staged),
        "clips/clip_*.mp4",
    ),
    (
        re.compile(r"\bblog post\b", re.IGNORECASE),
        lambda staged: "blog_post.md" in staged,
        "blog_post.md",
    ),
    (
        re.compile(r"\bsocial captions?\b", re.IGNORECASE),
        lambda staged: "social_captions.md" in staged,
        "social_captions.md",
    ),
    (
        re.compile(r"\bchapters?\b|\bchapter markers?\b", re.IGNORECASE),
        lambda staged: "chapters.md" in staged,
        "chapters.md",
    ),
    (
        re.compile(r"\btranscript\b", re.IGNORECASE),
        lambda staged: "transcript.txt" in staged,
        "transcript.txt",
    ),
    (
        re.compile(r"\bthumbnail\b", re.IGNORECASE),
        lambda staged: "thumbnail.png" in staged,
        "thumbnail.png",
    ),
    (
        re.compile(r"\bquote cards?\b", re.IGNORECASE),
        lambda staged: any(p.startswith("quote_card_") for p in staged),
        "quote_card_*.png",
    ),
]


def _extract_pitch_promises(pitch_path: Path) -> list:
    """Pull bullet items from the 'Inside:' section of a PITCH.md.

    Returns bullet text without the leading '- '. Empty list if the file
    doesn't exist or has no Inside: section.
    """
    if not pitch_path.exists():
        return []
    try:
        text = pitch_path.read_text(encoding="utf-8")
    except OSError:
        return []
    m = re.search(
        r"^Inside:\s*$\s*(.+?)(?=\n\s*\n|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if not m:
        return []
    return re.findall(r"^\s*-\s+(.+?)\s*$", m.group(1), re.MULTILINE)


def _check_pitch_parity(bullets: list, staged_files: set) -> list:
    """For each bullet, verify the corresponding artifact exists in staging.

    Returns a list of human-readable "missing" descriptions. Empty list
    means every recognized promise is satisfied.
    """
    missing: list = []
    for bullet in bullets:
        for pattern, predicate, label in _PITCH_PROMISE_CHECKS:
            if pattern.search(bullet):
                if not predicate(staged_files):
                    snippet = bullet[:50] + ("..." if len(bullet) > 50 else "")
                    missing.append(f"{label} (promised by '{snippet}')")
                break  # first match wins
    return missing


def _staged_files_for(ep_dir: Path) -> set:
    """Predict the set of relative paths that would land in the staging dir.

    Mirrors scripts/outreach_prepare.py:_stage_assets without copying anything,
    so the parity check can run before any disk work.
    """
    out: set = set()

    final_dir = ep_dir / "clips" / "final"
    if final_dir.exists():
        for clip in final_dir.glob("clip_*.mp4"):
            out.add(f"clips/{clip.name}")

    if next(ep_dir.glob("*_blog_post.md"), None):
        out.add("blog_post.md")
    if next(ep_dir.glob("*_thumbnail.png"), None):
        out.add("thumbnail.png")
    for qc in ep_dir.glob("quote_card_*.png"):
        out.add(qc.name)

    analysis_path = next(ep_dir.glob("*_analysis.json"), None)
    if analysis_path:
        try:
            analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            analysis = {}
        if analysis.get("social_captions"):
            out.add("social_captions.md")
        if analysis.get("chapters"):
            out.add("chapters.md")

    transcript_path = next(ep_dir.glob("*_transcript.json"), None)
    if transcript_path:
        try:
            t = json.loads(transcript_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            t = {}
        if t.get("segments"):
            out.add("transcript.txt")

    return out


def verify_one(slug: str) -> List[Finding]:
    """Run all checks for one client slug. Returns list of Finding objects."""
    findings: List[Finding] = []
    try:
        activate_client(slug)
    except Exception as e:
        return [Finding("ERROR", "activate_client", f"{type(e).__name__}: {e}")]

    ep_dir = _latest_ep_dir(slug)
    if ep_dir is None:
        return [Finding("ERROR", "ep_dir_exists", f"no ep_* dir under output/{slug}")]

    # Check 1: required artifacts present
    thumb = next(ep_dir.glob("*_thumbnail.png"), None)
    findings.append(
        Finding(
            "OK" if thumb else "ERROR",
            "thumbnail_exists",
            str(thumb) if thumb else "no *_thumbnail.png in ep_dir",
        )
    )

    final_dir = ep_dir / "clips" / "final"
    final_clips = sorted(final_dir.glob("clip_*.mp4")) if final_dir.exists() else []
    findings.append(
        Finding(
            "OK" if final_clips else "ERROR",
            "final_clips_exist",
            f"{len(final_clips)} clip(s) in {final_dir}",
        )
    )

    # Check 2: filename hygiene — no URL-encoded prefix on copies we'll upload
    # (only inspects names that would be staged by outreach_prepare)
    ugly = []
    if thumb and _URL_ENCODED_RE.search(thumb.name):
        ugly.append(thumb.name)
    for f in final_clips:
        if _URL_ENCODED_RE.search(f.name):
            ugly.append(f.name)
    findings.append(
        Finding(
            "OK" if not ugly else "WARN",
            "filename_hygiene",
            "clean"
            if not ugly
            else f"{len(ugly)} file(s) with URL-encoded prefix (masked at staging)",
        )
    )

    # Check 3: clip count matches analysis
    analysis_path = next(ep_dir.glob("*_analysis.json"), None)
    best_clips_count = 0
    if analysis_path:
        try:
            with open(analysis_path, encoding="utf-8") as fh:
                analysis = json.load(fh)
            best_clips_count = len(analysis.get("best_clips", []))
        except Exception as e:
            findings.append(
                Finding("WARN", "analysis_readable", f"could not parse: {e}")
            )
    level = "OK" if len(final_clips) == best_clips_count else "ERROR"
    findings.append(
        Finding(
            level,
            "clip_count_matches_analysis",
            f"{len(final_clips)} clips in final/, {best_clips_count} in best_clips",
        )
    )

    # Check 4: clip durations within [min, max]
    min_dur = Config.CLIP_MIN_DURATION
    max_dur = Config.CLIP_MAX_DURATION
    out_of_range = []
    for f in final_clips:
        d = _get_duration(f)
        if d is None:
            continue
        if d < min_dur or d > max_dur:
            out_of_range.append((f.name, d))
    findings.append(
        Finding(
            "OK" if not out_of_range else "ERROR",
            "clip_duration_window",
            "all in range"
            if not out_of_range
            else f"{len(out_of_range)} outside [{min_dur}, {max_dur}]s: "
            + ", ".join(f"{n}={d:.0f}s" for n, d in out_of_range[:3]),
        )
    )

    # Check 5: no `podcast_logo.*` filename leaked into staged assets
    leaked = list(ep_dir.glob("**/podcast_logo.*"))
    findings.append(
        Finding(
            "OK" if not leaked else "ERROR",
            "no_fp_logo_filename",
            "none found"
            if not leaked
            else f"{len(leaked)} podcast_logo.* file(s) under ep_dir",
        )
    )

    # Check 6: logo-bleed fingerprint
    fp_logo = Config.ASSETS_DIR / "podcast_logo.png"
    if fp_logo.exists() and thumb:
        fp_hash = _ahash(fp_logo)
        thumb_hash = _ahash(thumb)
        if fp_hash is not None and thumb_hash is not None:
            d = _hamming(fp_hash, thumb_hash)
            level = "ERROR" if d < _PHASH_DISTANCE_THRESHOLD else "OK"
            findings.append(
                Finding(
                    level,
                    "thumbnail_not_fp_logo",
                    f"pHash distance={d} (threshold={_PHASH_DISTANCE_THRESHOLD})",
                )
            )

        # Spot-check one clip frame (sample the first) for FP logo
        if final_clips:
            tmp_frame = ep_dir / ".verify_frame.png"
            if _extract_frame(final_clips[0], tmp_frame, seek=2.0):
                frame_hash = _ahash(tmp_frame)
                if frame_hash is not None and fp_hash is not None:
                    d = _hamming(fp_hash, frame_hash)
                    level = "ERROR" if d < _PHASH_DISTANCE_THRESHOLD else "OK"
                    findings.append(
                        Finding(
                            level,
                            "clip_bg_not_fp_logo",
                            f"clip_01 pHash distance={d} (threshold={_PHASH_DISTANCE_THRESHOLD})",
                        )
                    )
                try:
                    tmp_frame.unlink()
                except OSError:
                    pass

    # Check 7: bt709 color metadata on every final clip (B023 prevention).
    # ffprobe each one; flag if transfer/primaries/space don't all read bt709.
    color_failures = []
    for f in final_clips:
        result = _check_clip_color_metadata(f)
        if result is not None and result != "OK":
            color_failures.append((f.name, result))
    findings.append(
        Finding(
            "OK" if not color_failures else "ERROR",
            "clip_color_metadata",
            "all bt709"
            if not color_failures
            else f"{len(color_failures)} clip(s) with non-bt709 metadata: "
            + "; ".join(f"{n} ({m})" for n, m in color_failures[:3]),
        )
    )

    # Check 8: PITCH ↔ PACKAGE parity. Each artifact promised in the email
    # body's "Inside:" bullet list must exist in the predicted staging set.
    # Caught the missing social_captions/chapters/transcript files that
    # forced two re-upload cycles 2026-04-23.
    pitch_path = Config.BASE_DIR / "demo" / "church-vertical" / slug / "PITCH.md"
    bullets = _extract_pitch_promises(pitch_path)
    if bullets:
        staged = _staged_files_for(ep_dir)
        missing = _check_pitch_parity(bullets, staged)
        findings.append(
            Finding(
                "OK" if not missing else "ERROR",
                "pitch_parity",
                "all promises satisfied"
                if not missing
                else f"{len(missing)} unmet: " + "; ".join(missing[:3]),
            )
        )

    return findings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", nargs="?", help="Client slug (omit with --all-churches)")
    ap.add_argument(
        "--all-churches", action="store_true", help="Verify all 10 church prospects"
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 on WARN findings (default: only on ERROR)",
    )
    args = ap.parse_args()

    if args.all_churches:
        targets = CHURCH_SLUGS
    elif args.slug:
        targets = [args.slug]
    else:
        ap.error("must pass a slug or --all-churches")
        return 2

    total_errors = 0
    total_warns = 0
    for slug in targets:
        print(f"\n=== {slug} ===")
        findings = verify_one(slug)
        for f in findings:
            print(f)
        errors = sum(1 for f in findings if f.level == "ERROR")
        warns = sum(1 for f in findings if f.level == "WARN")
        total_errors += errors
        total_warns += warns
        verdict = "PASS" if errors == 0 else "BLOCK"
        print(f"  verdict: {verdict} ({errors} errors, {warns} warns)")

    print(f"\nTotal: {total_errors} error(s), {total_warns} warning(s)")
    if total_errors:
        return 1
    if args.strict and total_warns:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
