"""One-shot recovery: patch EMAIL fields in batch-2 PITCH.md files, then
re-run outreach_prepare --drive-link for each so Gmail drafts get created
without re-uploading to Drive.

Background: the 20 PITCH.md files generated 2026-04-27 had `**EMAIL: TBD**`
as a placeholder (the gen_church_pitches.py template was designed to be
hand-filled). When prepare_batch2 ran, Drive uploads succeeded but Gmail
rejected `to=TBD` with HTTP 400 'Invalid To header'. This script replaces
TBD with the real address for each prospect (sourced from the contact_hint
field in gen_church_pitches.py PROSPECTS) and recovers the Gmail draft
step by reusing the already-uploaded Drive folder URL.

Use --dry-run to see what would be patched without touching files or the
Gmail API.

This is a one-shot script. The systemic fix (adding an `email` field to
PROSPECTS in gen_church_pitches.py so the template substitutes it directly)
should land before the next batch.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# Slug -> primary email address (from RSS feed itunes_owner / contact_hint).
# None means we have no direct email — only a contact form (skip from recovery).
SLUG_EMAILS: dict[str, str | None] = {
    "christ-community-franklin-tn": "info@christcommunity.org",
    "north-village-church-austin": None,  # contact form only, no direct email
    "doxology-bible-church": "info@doxology.church",
    "park-church-denver": "renew@parkchurchdenver.org",
    "northside-church-of-christ-wichita": "office@northsidecoc.org",
    "pacific-crossroads-church-la": "info@pacificcrossroads.org",
    "cornerstone-fellowship-bible-church": "jonathand@cornerstonebible.org",
    "coram-deo-bible-church": "info@cdbible.org",
    "trinity-baptist-church-nashua": "admin@trinity-baptist.org",
    "go-church": "marketing@mygochurch.com",
    "the-tree-church-lancaster": "info@thetree.church",
    "high-point-church-madison": "info@highpointchurch.org",
    "north-wake-church": "tech@northwake.com",
    "first-family-church-ankeny": "info@firstfamily.church",
    "cornerstone-church-cefc": "cefc@cornerstonechurches.org",
    "denton-church-of-christ": "podcast@dentonchurchofchrist.org",
    "imago-dei-church-raleigh": "idcworship@gmail.com",
    "faith-baptist-church-fbcnet": "webmaster@fbcnet.org",
    "emergence-church-nj": "Steve.hawthorne@emergencenj.org",
    "park-cities-presbyterian-dallas": "webmaster@pcpc.org",
}

DEMO_ROOT = _PROJECT_ROOT / "demo" / "church-vertical"
EMAIL_FIELD_RE = re.compile(r"\*\*EMAIL:\s*TBD\*\*")


def patch_email(slug: str, email: str, dry_run: bool = False) -> str:
    """Replace `**EMAIL: TBD**` with `**EMAIL: <real>**` in the prospect's PITCH.md.

    Returns 'patched' / 'already_set' / 'no_pitch' / 'no_placeholder' / 'dry_run'.
    """
    pitch_path = DEMO_ROOT / slug / "PITCH.md"
    if not pitch_path.exists():
        return "no_pitch"
    text = pitch_path.read_text(encoding="utf-8")
    if f"**EMAIL: {email}**" in text:
        return "already_set"
    if not EMAIL_FIELD_RE.search(text):
        return "no_placeholder"
    new_text = EMAIL_FIELD_RE.sub(f"**EMAIL: {email}**", text)
    if dry_run:
        return "dry_run"
    pitch_path.write_text(new_text, encoding="utf-8")
    return "patched"


def recover_draft(slug: str, drive_link: str, dry_run: bool = False) -> dict:
    """Re-run outreach_prepare for slug with --drive-link to skip re-upload
    and just create the Gmail draft. Returns the prepare_one result dict."""
    from scripts import outreach_prepare as op

    if dry_run:
        gmail = op._make_dry_run_gmail()
        return op.prepare_one(
            slug, drive=None, gmail=gmail, dry_run=True, drive_link=drive_link
        )

    from gmail_sender import GmailSender

    gmail = GmailSender()
    return op.prepare_one(
        slug,
        drive=None,
        gmail=gmail,
        dry_run=False,
        drive_link=drive_link,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--status-file",
        default=str(_PROJECT_ROOT / "output" / "prepare2_wed" / "status.json"),
        help="Path to the prepare_batch2 status.json that already has Drive uploads recorded",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without touching PITCH.md or calling Gmail.",
    )
    args = ap.parse_args()

    status_path = Path(args.status_file)
    if not status_path.exists():
        print(f"ERROR: status.json not found at {status_path}", file=sys.stderr)
        return 1
    state = json.loads(status_path.read_text(encoding="utf-8"))

    summary = {
        "patched": [],
        "skipped_no_email": [],
        "skipped_no_drive_link": [],
        "drafted": [],
        "failed": [],
    }

    for entry in state.get("results", []):
        slug = entry["slug"]
        email = SLUG_EMAILS.get(slug)
        drive_link = entry.get("drive_link")

        if email is None:
            print(f"SKIP {slug}: no direct email known (only contact form)")
            summary["skipped_no_email"].append(slug)
            continue
        if not drive_link or "DRY_RUN" in drive_link:
            print(
                f"SKIP {slug}: no real drive_link in status.json (status={entry.get('status')})"
            )
            summary["skipped_no_drive_link"].append(slug)
            continue

        # Step 1: patch the EMAIL field
        patch_result = patch_email(slug, email, dry_run=args.dry_run)
        print(f"  PATCH {slug:40} -> {email:35} [{patch_result}]")
        summary["patched"].append(
            {"slug": slug, "email": email, "result": patch_result}
        )

        # Step 2: recover the Gmail draft using existing Drive link
        try:
            result = recover_draft(slug, drive_link, dry_run=args.dry_run)
            draft_id = result.get("draft_id")
            if draft_id and draft_id != "DRY_RUN" and draft_id is not None:
                print(f"  DRAFT {slug:40} -> draft_id={draft_id}")
                summary["drafted"].append(
                    {"slug": slug, "draft_id": draft_id, "to": email}
                )
            elif args.dry_run:
                print(f"  DRAFT {slug:40} -> (dry-run, no real call)")
            else:
                print(f"  DRAFT {slug:40} -> FAILED (draft_id={draft_id})")
                summary["failed"].append(
                    {"slug": slug, "reason": f"draft_id={draft_id}"}
                )
        except Exception as e:
            print(f"  ERR   {slug:40} -> {type(e).__name__}: {e}")
            summary["failed"].append({"slug": slug, "reason": str(e)})

    print()
    print("=== SUMMARY ===")
    print(f"  Patched:           {len(summary['patched'])}")
    print(f"  Drafted:           {len(summary['drafted'])}")
    print(
        f"  Skipped (no email): {len(summary['skipped_no_email'])} ({summary['skipped_no_email']})"
    )
    print(
        f"  Skipped (no drive): {len(summary['skipped_no_drive_link'])} ({summary['skipped_no_drive_link']})"
    )
    print(f"  Failed:            {len(summary['failed'])}")
    if summary["failed"]:
        for f in summary["failed"]:
            print(f"    - {f['slug']}: {f['reason']}")

    return 0 if not summary["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())
