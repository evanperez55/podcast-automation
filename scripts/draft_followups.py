"""Auto-draft follow-up emails for prospects who haven't replied within N days.

Scans the outreach tracker for prospects in `contacted` status whose
last_contact_date is older than --days (default 5). For each, parses the
"## Follow-Up Email" section from demo/church-vertical/<slug>/PITCH.md and
creates a Gmail DRAFT — never sends.

Idempotency: a prospect that already has a follow-up draft created today
is skipped (marker stored in the tracker's `notes` column as
`FOLLOWED_UP=YYYY-MM-DD`). Pass --force to redraft anyway.

Usage:
    uv run python scripts/draft_followups.py
    uv run python scripts/draft_followups.py --days 7
    uv run python scripts/draft_followups.py --slug redeemer-city-church-tampa
    uv run python scripts/draft_followups.py --dry-run
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# Standard scripts/ → project-root sys.path shim so flat top-level modules import.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import Config  # noqa: E402
from logger import logger  # noqa: E402
from outreach_tracker import OutreachTracker  # noqa: E402

DEMO_ROOT = Config.BASE_DIR / "demo" / "church-vertical"

# Marker stored in the tracker `notes` column when a follow-up draft is created.
# Lets us skip on re-run without a schema migration.
FOLLOWED_UP_MARKER_RE = re.compile(r"FOLLOWED_UP=(\d{4}-\d{2}-\d{2})")


# ---------------------------------------------------------------------------
# Follow-up parsing — finds the second `## ` email section (after the primary)
# ---------------------------------------------------------------------------

FOLLOWUP_HEADER_RE = re.compile(r"^##\s+Follow.?Up", re.IGNORECASE | re.MULTILINE)
SUBJECT_RE = re.compile(r"^\s*\*\*Subject:\*\*\s*(.+?)\s*$", re.MULTILINE)


def parse_followup(pitch_path: Path) -> dict:
    """Extract {subject, body} from the Follow-Up Email section of PITCH.md.

    The follow-up section is delimited by:
      - START: a `## Follow-Up Email...` header (case insensitive, hyphen optional)
      - END: the next horizontal divider `---` on its own line, or EOF.

    Subject = first **Subject:** line within that section.
    Body    = prose between the Subject line and the section's terminator.
    """
    text = pitch_path.read_text(encoding="utf-8")

    header_match = FOLLOWUP_HEADER_RE.search(text)
    if not header_match:
        raise ValueError(f"No '## Follow-Up Email' section in {pitch_path}")
    section_start = header_match.end()

    # Section ends at the next `---` divider on its own line, or EOF.
    divider_match = re.search(r"^\s*---\s*$", text[section_start:], re.MULTILINE)
    section_end = section_start + divider_match.start() if divider_match else len(text)
    section = text[section_start:section_end]

    subj_match = SUBJECT_RE.search(section)
    if not subj_match:
        raise ValueError(f"No **Subject:** line in follow-up section of {pitch_path}")
    subject = subj_match.group(1).strip()

    # Body = everything after the subject line in this section
    body = section[subj_match.end() :].strip()

    return {"subject": subject, "body": body}


# ---------------------------------------------------------------------------
# Tracker query — filter for "contacted, no reply, not yet followed up"
# ---------------------------------------------------------------------------


def is_recently_followed_up(notes: Optional[str], today_iso: str) -> bool:
    """True if notes contains a FOLLOWED_UP marker dated today.

    We only skip same-day re-runs. A marker from a previous date is OK to
    re-trigger off of (covers the case where the operator wants a second
    follow-up two weeks later from a fresh template).
    """
    if not notes:
        return False
    m = FOLLOWED_UP_MARKER_RE.search(notes)
    if not m:
        return False
    return m.group(1) == today_iso


def select_prospects(
    tracker: OutreachTracker,
    days: int,
    today: Optional[datetime] = None,
    force: bool = False,
    only_slug: Optional[str] = None,
) -> list[dict]:
    """Return prospects eligible for a follow-up draft.

    Eligibility:
      - status == 'contacted'
      - last_contact_date <= (today - days)
      - notes does NOT contain FOLLOWED_UP=<today> (unless force)
      - if only_slug is set, the slug matches
    """
    today = today or datetime.now(timezone.utc)
    today_iso = today.date().isoformat()
    cutoff = (today - timedelta(days=days)).isoformat()

    eligible: list[dict] = []
    for prospect in tracker.list_prospects():
        if only_slug and prospect["slug"] != only_slug:
            continue
        if prospect.get("status") != "contacted":
            continue
        last_contact = prospect.get("last_contact_date") or ""
        if not last_contact:
            continue  # never contacted but flagged contacted — skip defensively
        if last_contact > cutoff:
            continue  # contacted within the window, too soon
        if not force and is_recently_followed_up(prospect.get("notes"), today_iso):
            continue
        eligible.append(prospect)
    return eligible


# ---------------------------------------------------------------------------
# Marker write — append FOLLOWED_UP=YYYY-MM-DD to notes
# ---------------------------------------------------------------------------


def mark_followed_up(tracker: OutreachTracker, slug: str, today_iso: str) -> bool:
    """Append `FOLLOWED_UP=<date>` to the prospect's notes (or replace existing
    FOLLOWED_UP marker if one was set on a prior date). Returns True on success.
    """
    prospect = tracker.get_prospect(slug)
    if prospect is None:
        return False
    notes = prospect.get("notes") or ""
    new_marker = f"FOLLOWED_UP={today_iso}"

    if FOLLOWED_UP_MARKER_RE.search(notes):
        notes = FOLLOWED_UP_MARKER_RE.sub(new_marker, notes)
    else:
        sep = "\n" if notes else ""
        notes = f"{notes}{sep}{new_marker}"

    # Direct DB write — tracker doesn't expose an update_notes method.
    conn = sqlite3.connect(tracker.db_path)
    try:
        conn.execute(
            "UPDATE prospects SET notes = ?, updated_at = ? WHERE slug = ?",
            (notes, datetime.now(timezone.utc).isoformat(), slug),
        )
        conn.commit()
        return conn.execute("SELECT changes()").fetchone()[0] > 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Main draft-creation flow
# ---------------------------------------------------------------------------


def draft_one(
    prospect: dict,
    gmail,
    today_iso: str,
    tracker: Optional[OutreachTracker] = None,
    dry_run: bool = False,
) -> dict:
    """Create one follow-up draft. Returns {slug, status, draft_id|err}."""
    slug = prospect["slug"]
    pitch_path = DEMO_ROOT / slug / "PITCH.md"
    if not pitch_path.exists():
        return {
            "slug": slug,
            "status": "error",
            "err": f"PITCH.md missing: {pitch_path}",
        }

    try:
        parsed = parse_followup(pitch_path)
    except ValueError as e:
        return {"slug": slug, "status": "error", "err": str(e)}

    email = prospect.get("contact_email")
    if not email:
        return {"slug": slug, "status": "error", "err": "no contact_email in tracker"}

    draft_id = gmail.create_draft(
        to=email,
        subject=parsed["subject"],
        body=parsed["body"],
        dry_run=dry_run,
        include_signature=True,
    )
    if not draft_id:
        return {"slug": slug, "status": "error", "err": "gmail returned no draft id"}

    if not dry_run and tracker is not None:
        mark_followed_up(tracker, slug, today_iso)

    return {"slug": slug, "status": "drafted", "draft_id": draft_id, "to": email}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--days",
        type=int,
        default=5,
        help="Days since last_contact_date before a follow-up is eligible (default: 5)",
    )
    ap.add_argument(
        "--slug",
        default=None,
        help="Limit to a single prospect slug (useful for testing on one)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="List eligible prospects + parse their follow-up sections, but "
        "don't create Gmail drafts and don't mark notes.",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Redraft even for prospects already followed up today (overrides "
        "the FOLLOWED_UP=<date> marker check).",
    )
    args = ap.parse_args()

    today = datetime.now(timezone.utc)
    today_iso = today.date().isoformat()

    tracker = OutreachTracker()
    eligible = select_prospects(
        tracker, args.days, today=today, force=args.force, only_slug=args.slug
    )

    if not eligible:
        print(
            f"No prospects eligible for follow-up (status=contacted, no reply >{args.days}d)"
        )
        return 0

    print(f"Eligible prospects ({len(eligible)}):")
    for p in eligible:
        print(
            f"  {p['slug']:45} last_contact={p.get('last_contact_date', '')[:10]}  email={p.get('contact_email', '(none)')}"
        )
    print()

    if args.dry_run:
        gmail = _DryRunGmail()
    else:
        from gmail_sender import GmailSender

        gmail = GmailSender()

    results = []
    for prospect in eligible:
        result = draft_one(
            prospect,
            gmail=gmail,
            today_iso=today_iso,
            tracker=None if args.dry_run else tracker,
            dry_run=args.dry_run,
        )
        results.append(result)
        if result["status"] == "drafted":
            print(
                f"  DRAFTED {result['slug']:40} → {result.get('to', '?')}  draft_id={result.get('draft_id')}"
            )
        else:
            logger.warning(
                "follow-up failed for %s: %s", result["slug"], result.get("err")
            )
            print(f"  FAILED  {result['slug']:40} → {result.get('err', '?')}")

    drafted = sum(1 for r in results if r["status"] == "drafted")
    print(f"\nFollow-up batch complete: {drafted}/{len(eligible)} drafted")
    return 0 if drafted == len(eligible) else 1


class _DryRunGmail:
    """Drop-in for GmailSender that records calls instead of hitting the API."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        dry_run: bool = False,
        include_signature: bool = False,
    ) -> str:
        self.calls.append({"to": to, "subject": subject, "body_len": len(body)})
        return "DRY_RUN"


if __name__ == "__main__":
    sys.exit(main())
