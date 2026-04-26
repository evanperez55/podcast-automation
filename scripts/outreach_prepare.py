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
import json
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
PREVIEW_URL_PLACEHOLDER = "[PREVIEW URL]"


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


def inject_preview_link(body: str, url: str) -> str:
    """Replace the preview-URL placeholder, or insert near the top if missing.

    The preview page is the "show, don't tell" hook — a hosted, branded page
    with embedded clips. We want it to appear ABOVE the Drive link in the
    email, since most prospects will click the polished page first.
    """
    if PREVIEW_URL_PLACEHOLDER in body:
        return body.replace(PREVIEW_URL_PLACEHOLDER, url)
    # Fallback: insert a "Preview:" line before any Drive link reference,
    # or before the first blank line if no Drive link is present.
    insert = f"Preview (clips embedded, no download needed): {url}"
    if DRIVE_LINK_PLACEHOLDER in body:
        return body.replace(
            DRIVE_LINK_PLACEHOLDER, f"{insert}\n\n{DRIVE_LINK_PLACEHOLDER}"
        )
    return f"{insert}\n\n{body}"


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

    Clip videos are preferred from clips/final/ (human-readable names like
    `clip_01_topic_headline.mp4`) over the raw `*_subtitle.mp4` files, which
    carry the ugly URL-encoded or base64-encoded episode ID prefix for RSS
    feeds that don't expose clean episode IDs (e.g., Subsplash).

    When multiple processing runs coexist in one ep_dir, only files stamped
    with the latest timestamp are returned. Files without a timestamp
    (quote_card_*.png, clips/final/*) are always kept — they're regenerated
    in place each run, so only the latest set exists on disk.
    """
    candidates: List[Path] = []

    # Clips: prefer clips/final/ with clean names; fall back to *_subtitle.mp4
    final_dir = ep_dir / "clips" / "final"
    final_clips = sorted(final_dir.glob("clip_*.mp4")) if final_dir.exists() else []
    if final_clips:
        candidates.extend(final_clips)
    else:
        candidates.extend(ep_dir.rglob("*_subtitle.mp4"))

    # Non-clip user-facing assets
    for pattern in ("*_thumbnail.png", "quote_card_*.png", "*_blog_post.md"):
        candidates.extend(ep_dir.rglob(pattern))

    latest_ts = _latest_run_timestamp(ep_dir)

    seen = set()
    result = []
    for p in candidates:
        if p in seen:
            continue
        if any(p.match(bad) for bad in EXCLUDE_PATTERNS):
            continue
        # If the file carries a timestamp, it must match the latest run.
        # Clean final/clip_*.mp4 files have no timestamp by design.
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
    ep_dir contains internal JSON we never want to ship. Asset names are
    also normalized here so prospects don't see the ugly URL-encoded or
    base64 episode prefix on filenames from Subsplash / direct-cloudfront
    feeds.
    """
    import shutil

    staging_dir.mkdir(parents=True, exist_ok=True)
    clips_sub = staging_dir / "clips"
    for asset in collect_demo_assets(ep_dir):
        name = asset.name
        if asset.suffix == ".mp4" and "clip" in name.lower():
            # Clips from final/ already have clean names (clip_NN_topic.mp4);
            # raw *_subtitle.mp4 files carry the ugly prefix — rename them.
            clips_sub.mkdir(exist_ok=True)
            if name.startswith("clip_"):
                clean_name = name
            else:
                clean_name = _clean_clip_name(asset, list(clips_sub.iterdir()))
            shutil.copy2(asset, clips_sub / clean_name)
        elif name.endswith("_thumbnail.png"):
            shutil.copy2(asset, staging_dir / "thumbnail.png")
        elif name.endswith("_blog_post.md"):
            shutil.copy2(asset, staging_dir / "blog_post.md")
        else:
            # quote_card_*.png etc — already clean
            shutil.copy2(asset, staging_dir / name)

    # Derived files the email body promises but collect_demo_assets does not
    # ship (analysis.json + transcript.json are excluded as internal JSON).
    # We extract the prospect-facing pieces here.
    analysis_path = next(ep_dir.glob("*_analysis.json"), None)
    if analysis_path:
        try:
            analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            analysis = {}
        _write_social_captions_md(analysis, staging_dir / "social_captions.md")
        _write_chapters_md(analysis, staging_dir / "chapters.md")

    transcript_path = next(ep_dir.glob("*_transcript.json"), None)
    if transcript_path:
        try:
            transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            transcript = {}
        _write_transcript_txt(transcript, staging_dir / "transcript.txt")


_PLATFORM_LABELS = [
    ("youtube", "YouTube (long-form description)"),
    ("instagram", "Instagram"),
    ("twitter", "Twitter / X"),
    ("tiktok", "TikTok"),
]


def _write_social_captions_md(analysis: dict, dst: Path) -> None:
    """Render analysis['social_captions'] as a copy/paste-ready markdown file.

    Skips silently when no captions are available so older episodes that
    pre-date the social-captions field don't ship an empty file.
    """
    captions = analysis.get("social_captions") or {}
    sections = [
        (label, captions[key].strip())
        for key, label in _PLATFORM_LABELS
        if captions.get(key) and captions[key].strip()
    ]
    if not sections:
        return
    parts = [
        "# Social captions",
        "",
        "Copy/paste-ready captions for each platform. Tweak hashtags before posting.",
        "",
    ]
    for label, body in sections:
        parts.append(f"## {label}")
        parts.append("")
        parts.append(body)
        parts.append("")
    dst.write_text("\n".join(parts), encoding="utf-8")


def _write_chapters_md(analysis: dict, dst: Path) -> None:
    """Render analysis['chapters'] as a timestamped table-of-contents.

    Output format is a markdown table — drops cleanly into YouTube
    descriptions, podcast show notes, or a website episode page.
    """
    chapters = analysis.get("chapters") or []
    rows = [
        (str(c.get("start_timestamp", "00:00:00")), str(c.get("title", "")).strip())
        for c in chapters
        if c.get("title")
    ]
    if not rows:
        return
    parts = [
        "# Chapters",
        "",
        "| Time | Chapter |",
        "|------|---------|",
    ]
    parts.extend(f"| {ts} | {title} |" for ts, title in rows)
    parts.append("")
    dst.write_text("\n".join(parts), encoding="utf-8")


def _write_transcript_txt(transcript: dict, dst: Path) -> None:
    """Render transcript.json segments as a [HH:MM:SS]-prefixed readable text.

    One line per segment so the prospect can search/scroll. Blank or
    whitespace-only segments are dropped.
    """
    segments = transcript.get("segments") or []
    lines = []
    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        lines.append(f"[{_seconds_to_hms(seg.get('start', 0.0))}] {text}")
    if not lines:
        return
    dst.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _seconds_to_hms(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _print_staged_tree(slug: str, staging_dir: Path) -> None:
    """Print the staged file tree for visual confirmation in --dry-run mode."""
    print()
    print("=" * 60)
    print(f"PACKAGE PREVIEW: {slug}")
    print("=" * 60)
    print(f"  staging dir: {staging_dir}")
    print()
    files = sorted(p for p in staging_dir.rglob("*") if p.is_file())
    total_bytes = 0
    for p in files:
        rel = p.relative_to(staging_dir)
        size = p.stat().st_size
        total_bytes += size
        print(f"  {str(rel):60s} {_human_size(size):>10s}")
    print()
    print(f"  {len(files)} file(s), {_human_size(total_bytes)} total")
    print()


def _human_size(num_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}" if unit != "B" else f"{num_bytes} B"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def _verify_drive_public_access(drive_url: str, timeout: float = 10.0) -> Optional[str]:
    """Post-upload smoke test: hit the Drive URL with no auth, confirm public.

    Drive serves a "Request access" / "You need permission" interstitial
    when a folder is locked even though file-level perms claim otherwise
    (Workspace policy, race conditions, partial permission propagation).
    This catches that gap without needing an external test account.

    Returns:
        None if the folder is genuinely public-accessible
        Error description string otherwise
        None for transient network failures (don't false-fail on those)
    """
    try:
        import requests

        r = requests.get(drive_url, timeout=timeout, allow_redirects=True)
    except Exception:
        return None  # transient network issue — skip rather than false-fail
    if r.status_code == 404:
        return "HTTP 404 — folder not found at returned URL"
    if r.status_code != 200:
        return f"HTTP {r.status_code} on public access check"
    body = r.text.lower()
    for marker in ("request access", "you need permission", "you need access"):
        if marker in body:
            return f"Drive shows '{marker}' page — folder is NOT actually public"
    return None


def _clean_clip_name(asset: Path, existing_in_staging: list) -> str:
    """Generate a clean `clip_NN.mp4` name for a raw *_subtitle.mp4 file.

    Uses the count of already-staged clips to build the index. Keeps
    output predictable for the prospect (clip_01.mp4, clip_02.mp4, ...).
    """
    existing_count = sum(1 for p in existing_in_staging if p.name.startswith("clip_"))
    return f"clip_{existing_count + 1:02d}.mp4"


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def _publish_preview(slug: str) -> Optional[str]:
    """Render the preview page and push it to the previews repo.

    Returns the public URL on success, None on any failure (caller logs and
    continues without a preview URL — the Drive package alone is still a
    valid send). Soft-failure is intentional: a transient git push error or
    a missing previews repo should not lose the prospect.
    """
    try:
        from scripts.preview_page_publish import (
            DEFAULT_BASE_URL,
            DEFAULT_REPO,
            publish_preview_page,
        )

        return publish_preview_page(
            slug, repo_dir=DEFAULT_REPO, base_url=DEFAULT_BASE_URL, push=True
        )
    except Exception as e:
        logger.warning(
            "preview page publish failed for %s: %s — sending Drive-only package",
            slug,
            e,
        )
        return None


def prepare_one(
    slug: str,
    drive=None,
    gmail=None,
    dry_run: bool = False,
    drive_link: Optional[str] = None,
    skip_verify: bool = False,
    publish_preview: bool = True,
    preview_url: Optional[str] = None,
) -> dict:
    """Do one prospect end-to-end. Returns {draft_id, drive_link, preview_url, pitch_path}.

    `drive` and `gmail` are injected for testability. In real CLI use, the
    main() wrapper instantiates DriveUploader + GmailSender.

    If `drive_link` is provided, the Drive upload is skipped and the given
    link is used directly. Use this to recover from a partial failure where
    the upload succeeded but the Gmail draft did not (e.g. Gmail API quota
    or enablement propagation) — avoids re-uploading the demo package.

    If `preview_url` is provided, the preview page render+push is skipped and
    the given URL is used directly. If `publish_preview` is False, no preview
    URL is generated or injected at all (Drive-only package).

    Before the upload, runs the pre-upload verification battery (filename
    hygiene, clip count, duration window, logo-bleed fingerprint). Any ERROR
    finding aborts the prepare. Pass `skip_verify=True` to bypass (e.g.,
    for dry-run tests or when iterating on the verify script itself).
    """
    pitch_path = DEMO_ROOT / slug / "PITCH.md"
    if not pitch_path.exists():
        raise FileNotFoundError(f"PITCH.md not found: {pitch_path}")

    # Pre-upload verification — blocks upload on any ERROR finding. Warnings
    # (e.g., URL-encoded source filenames, which get masked at staging) are
    # informational and don't block.
    if not skip_verify and not dry_run and not drive_link:
        from scripts.outreach_verify import verify_one

        findings = verify_one(slug)
        errors = [f for f in findings if f.level == "ERROR"]
        if errors:
            raise RuntimeError(
                f"outreach_verify found {len(errors)} ERROR finding(s) for "
                f"{slug}; aborting upload. Run "
                f"`uv run python scripts/outreach_verify.py {slug}` for details."
            )

    parsed = parse_pitch(pitch_path)
    logger.info("Parsed pitch for %s: to=%s", slug, parsed["email"])

    if drive_link:
        logger.info("Using existing Drive link, skipping upload: %s", drive_link)
    else:
        ep_dir = _find_latest_ep_dir(slug)
        logger.info("Using ep_dir: %s", ep_dir)

        import tempfile

        if dry_run:
            # Stage anyway so we can show the prospect-facing tree as a preview.
            with tempfile.TemporaryDirectory() as td:
                staging = Path(td) / f"{slug}-demo"
                _stage_assets(ep_dir, staging)
                _print_staged_tree(slug, staging)
            drive_link = "https://drive.google.com/DRY_RUN"
        else:
            with tempfile.TemporaryDirectory() as td:
                staging = Path(td) / f"{slug}-demo"
                _stage_assets(ep_dir, staging)
                drive_link = drive.upload_folder(staging, folder_name=f"{slug} - Demo")

            # Post-upload smoke test: confirm the URL is actually publicly
            # accessible (catches Workspace policy gaps + permission races
            # without needing an external test account).
            issue = _verify_drive_public_access(drive_link)
            if issue:
                logger.warning(
                    "post-upload public-access check FAILED for %s: %s — "
                    "verify in incognito before sending",
                    slug,
                    issue,
                )
            else:
                logger.info("post-upload public-access check passed for %s", slug)

    if publish_preview and not preview_url and not dry_run:
        preview_url = _publish_preview(slug)

    # Order matters: inject preview FIRST so its placeholder fallback can find
    # [GOOGLE DRIVE LINK] and insert the preview line above it. Once Drive is
    # substituted, that anchor is gone and the fallback would prepend to the
    # whole email instead.
    body_with_link = parsed["body"]
    if preview_url:
        body_with_link = inject_preview_link(body_with_link, preview_url)
    body_with_link = inject_drive_link(body_with_link, drive_link)

    draft_id = gmail.create_draft(
        to=parsed["email"],
        subject=parsed["subject"],
        body=body_with_link,
        dry_run=dry_run,
        include_signature=True,
    )

    return {
        "slug": slug,
        "draft_id": draft_id,
        "drive_link": drive_link,
        "preview_url": preview_url,
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
    ap.add_argument(
        "--preview-url",
        default=None,
        help="Skip preview page render+push and use this existing URL. "
        "Mirrors --drive-link for recovery from a partial failure.",
    )
    ap.add_argument(
        "--no-preview",
        action="store_true",
        help="Don't render or include a preview page URL — Drive-only "
        "package. Use when the previews repo isn't reachable.",
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
        publish_preview=not args.no_preview,
        preview_url=args.preview_url,
    )

    print()
    print("=" * 60)
    print(f"OUTREACH PREPARED: {args.slug}")
    print("=" * 60)
    print(f"  Draft ID:   {result['draft_id']}")
    print(f"  Drive link: {result['drive_link']}")
    if result.get("preview_url"):
        print(f"  Preview:    {result['preview_url']}")
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
