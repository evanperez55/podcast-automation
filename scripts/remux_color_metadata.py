"""Patch H.264 SPS color metadata to bt709 in-place, no re-encode.

Rewrites the colour_primaries / transfer_characteristics / matrix_coefficients
fields in each MP4's SPS so Google Drive's transcoder doesn't stall on the
mismatch between bt709 primaries and bt470m transfer that lavfi `color=`
sources produce. Stream copy + bitstream filter — fast (~1s per clip),
lossless.

Usage:
    uv run python scripts/remux_color_metadata.py <path_or_glob> [<path_or_glob>...]
    uv run python scripts/remux_color_metadata.py "output/*/ep_*/clips/final/*.mp4"
    uv run python scripts/remux_color_metadata.py --all-churches

Exit codes:
    0 — every file remuxed successfully
    1 — at least one file failed
"""

import argparse
import glob
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

# Make repo root importable when run directly from scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Config  # noqa: E402
from logger import logger  # noqa: E402

# AVC values for primaries / transfer / matrix that mean bt709.
# See ITU-T H.264 Annex E (VUI parameters).
H264_METADATA_BT709 = (
    "h264_metadata="
    "colour_primaries=1:"
    "transfer_characteristics=1:"
    "matrix_coefficients=1:"
    "video_full_range_flag=0"
)

# Active outreach church slugs (kept in sync with MEMORY.md outreach list).
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


def build_remux_cmd(src: Path, dst: Path) -> list[str]:
    """FFmpeg command to stream-copy `src` to `dst` patching H.264 color VUI."""
    return [
        Config.FFMPEG_PATH,
        "-y",
        "-i",
        str(src),
        "-c",
        "copy",
        "-bsf:v",
        H264_METADATA_BT709,
        "-movflags",
        "+faststart",
        str(dst),
    ]


def remux_one(path: Path) -> bool:
    """Patch color metadata in-place. Returns True on success."""
    if not path.exists():
        logger.error("missing: %s", path)
        return False

    tmp = path.with_suffix(path.suffix + ".colorfix.tmp.mp4")
    try:
        result = subprocess.run(
            build_remux_cmd(path, tmp),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            logger.error(
                "ffmpeg failed for %s: %s",
                path.name,
                result.stderr.strip().splitlines()[-1:],
            )
            tmp.unlink(missing_ok=True)
            return False
        shutil.move(str(tmp), str(path))
        logger.info("remuxed: %s", path.name)
        return True
    except subprocess.TimeoutExpired:
        logger.error("ffmpeg timeout: %s", path)
        tmp.unlink(missing_ok=True)
        return False


def expand_inputs(args: list[str], all_churches: bool) -> list[Path]:
    """Resolve CLI arguments to a deduplicated list of MP4 paths."""
    paths: list[Path] = []
    if all_churches:
        for slug in CHURCH_SLUGS:
            paths.extend(_glob_church_clips(slug))
    for arg in args:
        if any(ch in arg for ch in "*?["):
            paths.extend(Path(p) for p in glob.glob(arg, recursive=True))
        else:
            paths.append(Path(arg))
    seen: set[Path] = set()
    out: list[Path] = []
    for p in paths:
        rp = p.resolve()
        if rp not in seen and p.suffix.lower() == ".mp4":
            seen.add(rp)
            out.append(p)
    return out


def _glob_church_clips(slug: str) -> Iterable[Path]:
    """Find all final/*.mp4 clips for an outreach church under output/."""
    pattern = f"output/{slug}/ep_*/clips/final/*.mp4"
    return (Path(p) for p in glob.glob(pattern))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("paths", nargs="*", help="MP4 file paths or globs")
    parser.add_argument(
        "--all-churches",
        action="store_true",
        help="Apply to final/*.mp4 of all 10 active outreach churches",
    )
    args = parser.parse_args(argv)

    targets = expand_inputs(args.paths, args.all_churches)
    if not targets:
        parser.error("no MP4 files matched")

    logger.info("remuxing %d file(s) for bt709 color metadata", len(targets))
    failed = [p for p in targets if not remux_one(p)]
    logger.info("done: %d ok, %d failed", len(targets) - len(failed), len(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
