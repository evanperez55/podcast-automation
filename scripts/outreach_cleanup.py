"""Delete outreach Drive folders + Gmail drafts for a list of church prospects.

Used to recover after an upload mistake where the wrong content (e.g., wrong
branding baked into thumbnails + clip backgrounds) was uploaded to Drive and
linked in drafts. This script only removes app-created Drive folders that
match the expected naming (`<slug> - Demo`) and Gmail drafts whose recipient
matches the known contact email for each slug.

Usage:
    uv run python scripts/outreach_cleanup.py --dry-run  # preview only
    uv run python scripts/outreach_cleanup.py --confirm  # actually delete
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from drive_uploader import DriveUploader  # noqa: E402
from gmail_sender import GmailSender  # noqa: E402

# Each tuple: (slug, contact_email). Drafts are matched by recipient; Drive
# folders are matched by name prefix.
CHURCH_TARGETS = [
    ("redeemer-city-church-tampa", "office@redeemertampa.com"),
    ("christ-community-church-columbus", "communications@ccclive.org"),
    ("metro-tab-church", "info@metrotab.net"),
    ("the-crossings-church-collinsville", "admin@crossingscollinsville.com"),
    ("faith-bible-church-edmond", "fbc@faithbibleok.com"),
    ("life-bridge-church-green-bay", "lbccgb@gmail.com"),
    ("cottonwood-church", "guestservices@cottonwood.org"),
    ("mercy-village-church", "info@mercyvillage.church"),
    ("harbor-rock-tabernacle", "paul@harborrock.org"),
    ("christ-community-church-johnson-city", "office@christcommunityjc.com"),
]


def find_drive_folders(drive: DriveUploader, slugs: List[str]) -> List[dict]:
    """Return folder dicts {id, name} that match '<slug> - Demo' for any slug.

    Uses drive.file scope so only folders this app created are visible.
    Filters to mimeType=folder and not trashed.
    """
    matches: List[dict] = []
    q = "mimeType='application/vnd.google-apps.folder' and trashed=false"
    page_token = None
    while True:
        resp = (
            drive.service.files()
            .list(
                q=q,
                fields="nextPageToken, files(id, name, createdTime)",
                pageSize=200,
                pageToken=page_token,
            )
            .execute()
        )
        for f in resp.get("files", []):
            for slug in slugs:
                if f["name"].startswith(f"{slug} -") or f["name"] == slug:
                    matches.append(
                        {
                            "id": f["id"],
                            "name": f["name"],
                            "slug": slug,
                            "createdTime": f.get("createdTime", ""),
                        }
                    )
                    break
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return matches


def find_drafts(gmail: GmailSender, emails: List[str]) -> List[dict]:
    """Return draft metadata {id, to, subject} for drafts addressed to any of `emails`."""
    matches: List[dict] = []
    page_token = None
    while True:
        resp = (
            gmail.service.users()
            .drafts()
            .list(userId="me", maxResults=500, pageToken=page_token)
            .execute()
        )
        for d in resp.get("drafts", []):
            draft_id = d["id"]
            detail = (
                gmail.service.users()
                .drafts()
                .get(userId="me", id=draft_id, format="metadata")
                .execute()
            )
            headers = {
                h["name"].lower(): h["value"]
                for h in detail.get("message", {}).get("payload", {}).get("headers", [])
            }
            to = headers.get("to", "")
            subject = headers.get("subject", "")
            if any(email.lower() in to.lower() for email in emails):
                matches.append({"id": draft_id, "to": to, "subject": subject})
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return matches


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Show what would be deleted")
    ap.add_argument("--confirm", action="store_true", help="Actually delete")
    args = ap.parse_args()
    if not args.dry_run and not args.confirm:
        ap.error("pass --dry-run or --confirm")
        return 2

    slugs = [s for s, _ in CHURCH_TARGETS]
    emails = [e for _, e in CHURCH_TARGETS]

    drive = DriveUploader()
    gmail = GmailSender()

    folders = find_drive_folders(drive, slugs)
    drafts = find_drafts(gmail, emails)

    print(f"\n=== Drive folders matching church slugs ({len(folders)}) ===")
    for f in sorted(folders, key=lambda x: (x["slug"], x.get("createdTime", ""))):
        print(f"  [{f['slug']:40s}] {f['id']:35s} {f['name']}")

    print(f"\n=== Gmail drafts addressed to church contacts ({len(drafts)}) ===")
    for d in drafts:
        print(f"  [{d['id']:25s}] to={d['to']!r:45s} subj={d['subject'][:60]!r}")

    if args.dry_run:
        print("\n[DRY RUN] nothing deleted. Pass --confirm to delete the above.")
        return 0

    print("\nDeleting Drive folders...")
    for f in folders:
        try:
            drive.service.files().delete(fileId=f["id"]).execute()
            print(f"  [OK] {f['name']}")
        except Exception as e:
            print(f"  [ERR] {f['name']}: {e}")

    print("\nDeleting Gmail drafts...")
    for d in drafts:
        try:
            gmail.service.users().drafts().delete(userId="me", id=d["id"]).execute()
            print(f"  [OK] {d['to']}")
        except Exception as e:
            print(f"  [ERR] {d['to']}: {e}")

    print("\nCleanup done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
