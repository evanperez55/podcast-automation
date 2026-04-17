"""Prepare a single prospect for outreach: upload demo to Drive + draft Gmail.

Reads demo/church-vertical/<slug>/PITCH.md, finds the latest processed
episode in output/<slug>/, uploads a curated set of user-facing assets to
a new Drive folder ("anyone with link" viewer), substitutes the Drive URL
into the pitch body, and creates a Gmail DRAFT addressed to the prospect.

NEVER auto-sends. User reviews the draft in Gmail and sends manually.

Usage:
    uv run python scripts/outreach_prepare.py <slug> [--dry-run]

Run once per prospect. Idempotency: re-running will create a NEW Drive
folder + a NEW draft (no dedup) — intentional, lets you iterate without
tooling fighting you.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Optional

# When run as `python scripts/outreach_prepare.py`, the project root isn't on
# sys.path — add it so the flat top-level modules import cleanly.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import Config  # noqa: E402
from logger import logger  # noqa: E402

DEMO_ROOT = Config.BASE_DIR / "demo" / "church-vertical"
OUTPUT_ROOT = Config.BASE_DIR / "output"

# ---------------------------------------------------------------------------
# PITCH.md parsing
# ---------------------------------------------------------------------------

EMAIL_PATTERN = re.compile(r"\*\*EMAIL:\s*([^\s*]+)\s*\*\*", re.IGNORECASE)
SUBJECT_PATTERN = re.compile(r"^\s*\*\*Subject:\*\*\s*(.+?)\s*$", re.MULTILINE)
DRIVE_LINK_PLACEHOLDER = "[GOOGLE DRIVE LINK]"


def parse_pitch(pitch_path: Path) -> dict:
    """Extract {email, subject, body} from a PITCH.md.

    Body is the prose between the Subject line and the next `---` divider
    (i.e. the primary outreach email only, not the follow-up).
    """
    text = pitch_path.read_text(encoding="utf-8")

    m = EMAIL_PATTERN.search(text)
    if not m:
        raise ValueError(f"No **EMAIL: ...** field found in {pitch_path}")
    email = m.group(1)

    m = SUBJECT_PATTERN.search(text)
    subject = m.group(1).strip() if m else ""

    body = _extract_primary_email_body(text)

    return {"email": email, "subject": subject, "body": body}


def _extract_primary_email_body(text: str) -> str:
    """Return the body between the first Subject line and the next `---`."""
    subject_match = SUBJECT_PATTERN.search(text)
    if not subject_match:
        return ""
    start = subject_match.end()
    # Next horizontal divider on its own line
    divider_match = re.search(r"^\s*---\s*$", text[start:], re.MULTILINE)
    end = start + divider_match.start() if divider_match else len(text)
    return text[start:end].strip()


def inject_drive_link(body: str, url: str) -> str:
    """Replace the Drive-link placeholder, or append if missing."""
    if DRIVE_LINK_PLACEHOLDER in body:
        return body.replace(DRIVE_LINK_PLACEHOLDER, url)
    # Fallback: prepend so prospect sees it above the fold
    return f"{body}\n\nDrive folder: {url}"


# ---------------------------------------------------------------------------
# Demo-asset curation
# ---------------------------------------------------------------------------

# Filename patterns to INCLUDE (user-facing deliverables).
# Full episode MP4 is intentionally omitted — it's 200+ MB and the prospect
# already has the original audio on their platform, so uploading it is mostly
# deadweight for cold outreach.
INCLUDE_PATTERNS = [
    "*_subtitle.mp4",  # vertical clips with burned-in captions
    "*_thumbnail.png",  # episode thumbnail
    "quote_card_*.png",  # quote cards
    "*_blog_post.md",  # blog post
]

# Filename patterns to EXCLUDE even if they match INCLUDE (internal artifacts).
EXCLUDE_PATTERNS = [
    "*_transcript.json",
    "*_analysis.json",
    "compliance_report_*.json",
    "*_censored.wav",
    "*_censored.mp3",
    "*_raw_snapshot.wav",
]

# Pipeline timestamp stamp baked into output filenames: _YYYYMMDD_HHMMSS_
_TIMESTAMP_RE = re.compile(r"_(\d{8}_\d{6})_")


def _latest_run_timestamp(ep_dir: Path) -> Optional[str]:
    """Scan ep_dir filenames for the most recent processing-run timestamp.

    Episode output dirs sometimes accumulate multiple runs (B011 reruns,
    manual re-processes) side-by-side. Return the lexicographically greatest
    stamp found, or None if no timestamped files exist.
    """
    stamps = set()
    for f in ep_dir.rglob("*"):
        m = _TIMESTAMP_RE.search(f.name)
        if m:
            stamps.add(m.group(1))
    return max(stamps) if stamps else None


def collect_demo_assets(ep_dir: Path) -> List[Path]:
    """Return user-facing asset paths under `ep_dir` (recursing into clips/).

    When multiple processing runs coexist in one ep_dir, only files stamped
    with the latest timestamp are returned. Files without a timestamp
    (quote_card_*.png) are always kept — they're regenerated in place each
    run, so only the latest set ever exists on disk.
    """
    candidates: List[Path] = []
    for pattern in INCLUDE_PATTERNS:
        candidates.extend(ep_dir.rglob(pattern))

    latest_ts = _latest_run_timestamp(ep_dir)

    seen = set()
    result = []
    for p in candidates:
        if p in seen:
            continue
        if any(p.match(bad) for bad in EXCLUDE_PATTERNS):
            continue
        # If the file carries a timestamp, it must match the latest run
        m = _TIMESTAMP_RE.search(p.name)
        if m and latest_ts and m.group(1) != latest_ts:
            continue
        seen.add(p)
        result.append(p)
    return sorted(result)


def _find_latest_ep_dir(slug: str) -> Path:
    slug_root = OUTPUT_ROOT / slug
    if not slug_root.exists():
        raise FileNotFoundError(f"No output directory for {slug}: {slug_root}")
    ep_dirs = [
        d for d in slug_root.iterdir() if d.is_dir() and d.name.startswith("ep_")
    ]
    if not ep_dirs:
        raise FileNotFoundError(f"No ep_* directories under {slug_root}")
    return max(ep_dirs, key=lambda d: d.stat().st_mtime)


def _stage_assets(ep_dir: Path, staging_dir: Path) -> None:
    """Copy curated assets into a flat staging dir for Drive upload.

    We use a staging dir (instead of uploading ep_dir directly) because
    ep_dir contains internal JSON we never want to ship.
    """
    import shutil

    staging_dir.mkdir(parents=True, exist_ok=True)
    clips_sub = staging_dir / "clips"
    for asset in collect_demo_assets(ep_dir):
        if "clip" in asset.name.lower() and asset.suffix == ".mp4":
            clips_sub.mkdir(exist_ok=True)
            shutil.copy2(asset, clips_sub / asset.name)
        else:
            shutil.copy2(asset, staging_dir / asset.name)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def prepare_one(
    slug: str,
    drive=None,
    gmail=None,
    dry_run: bool = False,
    drive_link: Optional[str] = None,
) -> dict:
    """Do one prospect end-to-end. Returns {draft_id, drive_link, pitch_path}.

    `drive` and `gmail` are injected for testability. In real CLI use, the
    main() wrapper instantiates DriveUploader + GmailSender.

    If `drive_link` is provided, the Drive upload is skipped and the given
    link is used directly. Use this to recover from a partial failure where
    the upload succeeded but the Gmail draft did not (e.g. Gmail API quota
    or enablement propagation) — avoids re-uploading the demo package.
    """
    pitch_path = DEMO_ROOT / slug / "PITCH.md"
    if not pitch_path.exists():
        raise FileNotFoundError(f"PITCH.md not found: {pitch_path}")

    parsed = parse_pitch(pitch_path)
    logger.info("Parsed pitch for %s: to=%s", slug, parsed["email"])

    if drive_link:
        logger.info("Using existing Drive link, skipping upload: %s", drive_link)
    else:
        ep_dir = _find_latest_ep_dir(slug)
        logger.info("Using ep_dir: %s", ep_dir)

        if dry_run:
            drive_link = "https://drive.google.com/DRY_RUN"
        else:
            # Stage assets into a clean temp dir then upload as a folder
            import tempfile

            with tempfile.TemporaryDirectory() as td:
                staging = Path(td) / f"{slug}-demo"
                _stage_assets(ep_dir, staging)
                drive_link = drive.upload_folder(staging, folder_name=f"{slug} - Demo")

    body_with_link = inject_drive_link(parsed["body"], drive_link)

    draft_id = gmail.create_draft(
        to=parsed["email"],
        subject=parsed["subject"],
        body=body_with_link,
        dry_run=dry_run,
    )

    return {
        "slug": slug,
        "draft_id": draft_id,
        "drive_link": drive_link,
        "pitch_path": str(pitch_path),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", help="Prospect slug (e.g. redeemer-city-church-tampa)")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse + log only. No Drive upload, no Gmail draft.",
    )
    ap.add_argument(
        "--drive-link",
        default=None,
        help="Skip Drive upload and use this existing folder URL. Use when a "
        "prior run uploaded to Drive but failed at the Gmail step.",
    )
    args = ap.parse_args()

    if args.dry_run:
        drive = None
        gmail = _make_dry_run_gmail()
    else:
        from gmail_sender import GmailSender

        gmail = GmailSender()
        if args.drive_link:
            drive = None  # not needed when reusing an existing link
        else:
            from drive_uploader import DriveUploader

            drive = DriveUploader()

    result = prepare_one(
        args.slug,
        drive=drive,
        gmail=gmail,
        dry_run=args.dry_run,
        drive_link=args.drive_link,
    )

    print()
    print("=" * 60)
    print(f"OUTREACH PREPARED: {args.slug}")
    print("=" * 60)
    print(f"  Draft ID:   {result['draft_id']}")
    print(f"  Drive link: {result['drive_link']}")
    print(f"  Pitch:      {result['pitch_path']}")
    print()
    print("Next: open Gmail -> Drafts, review the draft, send manually.")
    return 0


def _make_dry_run_gmail():
    """Stand-in Gmail object for --dry-run that needs no credentials."""

    class _Stub:
        def create_draft(self, **kwargs):
            logger.info(
                "[DRY RUN] Would draft to=%s subject=%s body_len=%d",
                kwargs.get("to"),
                kwargs.get("subject"),
                len(kwargs.get("body", "")),
            )
            return "DRY_RUN"

    return _Stub()


if __name__ == "__main__":
    sys.exit(main())
