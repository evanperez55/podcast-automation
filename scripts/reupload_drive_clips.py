"""Re-upload clip MP4s to existing Drive folders, preserving file IDs.

Recovery utility for the B023 regression of 2026-04-27: clips were rendered
without bt709 color metadata, uploaded to Drive, and Drive's transcoder hangs
on them ("Still processing, check back later"). The local files have since
been healed (in-encoder bsf as of commit e5a8635 + remux_color_metadata.py
back-fill), so we just need to push the healed bytes over the broken ones.

Strategy: use Drive's `files().update()` with a fresh MediaFileUpload to
overwrite the binary content while keeping the file ID, name, parents, and
sharing settings intact. That preserves any links the recipient already has,
any preview pages embedding by file ID, and the Gmail drafts referencing the
folder URL.

Slug → Drive folder ID mapping is recovered from the batch status JSONs at
`output/prepare2_*/status.json` (later runs win on conflict, so re-prep
batches like `prepare2_denver-fix` correctly override the failed `wed` row).

Usage:
    uv run python scripts/reupload_drive_clips.py --dry-run
    uv run python scripts/reupload_drive_clips.py --slug coram-deo-bible-church
    uv run python scripts/reupload_drive_clips.py --all
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from logger import logger  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = PROJECT_ROOT / "output"


def collect_slug_folder_map(batch_dirs: Iterable[Path]) -> dict[str, str]:
    """Build {slug: folder_id} from prepare2_*/status.json files.

    Later batches (by `batch_started_at`) override earlier ones for the same
    slug, so re-prep runs (e.g., `prepare2_denver-fix`) correctly replace
    failed rows from the original wed/thu batches.
    """
    rows: list[tuple[str, str, str]] = []  # (slug, folder_id, started_at)
    for batch_dir in batch_dirs:
        status_path = batch_dir / "status.json"
        if not status_path.exists():
            continue
        try:
            data = json.loads(status_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("skipping %s: %s", status_path, e)
            continue
        started = data.get("batch_started_at", "")
        for row in data.get("results", []):
            if row.get("status") != "prepared":
                continue
            link = row.get("drive_link") or ""
            slug = row.get("slug")
            folder_id = _folder_id_from_link(link)
            if slug and folder_id:
                rows.append((slug, folder_id, started))

    rows.sort(key=lambda r: r[2])  # oldest first; later overwrites
    return {slug: fid for slug, fid, _ in rows}


def _folder_id_from_link(link: str) -> Optional[str]:
    """Extract the Drive folder ID from a webViewLink URL."""
    marker = "/folders/"
    idx = link.find(marker)
    if idx == -1:
        return None
    tail = link[idx + len(marker) :]
    return tail.split("?", 1)[0].split("/", 1)[0] or None


def find_local_clips(slug: str) -> dict[str, Path]:
    """Return {clip_filename: local_path} for the slug's latest ep_dir."""
    slug_root = OUTPUT_ROOT / slug
    if not slug_root.exists():
        return {}
    ep_dirs = sorted(
        (d for d in slug_root.iterdir() if d.is_dir() and d.name.startswith("ep_")),
        key=lambda d: d.stat().st_mtime,
    )
    if not ep_dirs:
        return {}
    final_dir = ep_dirs[-1] / "clips" / "final"
    if not final_dir.exists():
        return {}
    return {p.name: p for p in final_dir.glob("clip_*.mp4")}


def list_drive_mp4s(service, folder_id: str) -> list[dict]:
    """List all MP4 files reachable from `folder_id` (recurses into subfolders).

    Returns a list of {id, name, parent_id} dicts. Drive list pagination is
    handled.
    """
    out: list[dict] = []
    queue = [folder_id]
    while queue:
        parent = queue.pop(0)
        page_token = None
        while True:
            resp = (
                service.files()
                .list(
                    q=f"'{parent}' in parents and trashed=false",
                    fields="nextPageToken, files(id, name, mimeType)",
                    pageSize=200,
                    pageToken=page_token,
                )
                .execute()
            )
            for f in resp.get("files", []):
                if f["mimeType"] == "application/vnd.google-apps.folder":
                    queue.append(f["id"])
                elif f["name"].lower().endswith(".mp4"):
                    out.append({"id": f["id"], "name": f["name"], "parent_id": parent})
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
    return out


def update_file_blob(service, file_id: str, local_path: Path) -> None:
    """Overwrite the binary content of `file_id` with `local_path`.

    Preserves the file ID, name, parents, and sharing settings. Drive
    re-transcodes the new content automatically.
    """
    from googleapiclient.http import MediaFileUpload

    media = MediaFileUpload(str(local_path), mimetype="video/mp4", resumable=False)
    service.files().update(fileId=file_id, media_body=media).execute()


def reupload_one(
    service,
    slug: str,
    folder_id: str,
    *,
    dry_run: bool,
) -> tuple[int, int, int]:
    """Re-upload all clips for one slug. Returns (matched, updated, skipped)."""
    locals_by_name = find_local_clips(slug)
    if not locals_by_name:
        logger.warning("[%s] no local clips/final/*.mp4 found — skipping", slug)
        return (0, 0, 0)

    drive_files = list_drive_mp4s(service, folder_id)
    if not drive_files:
        logger.warning("[%s] no .mp4 files in Drive folder %s", slug, folder_id)
        return (0, 0, 0)

    matched = 0
    updated = 0
    skipped = 0
    for f in drive_files:
        local = locals_by_name.get(f["name"])
        if local is None:
            logger.info("[%s] no local match for %s — leaving as-is", slug, f["name"])
            skipped += 1
            continue
        matched += 1
        if dry_run:
            logger.info(
                "[%s] DRY would update %s (id=%s) ← %s",
                slug,
                f["name"],
                f["id"],
                local,
            )
            continue
        try:
            update_file_blob(service, f["id"], local)
            logger.info("[%s] updated %s", slug, f["name"])
            updated += 1
        except Exception as e:
            logger.error("[%s] update failed for %s: %s", slug, f["name"], e)
    return matched, updated, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--dry-run", action="store_true", help="Print actions, no Drive writes"
    )
    parser.add_argument(
        "--slug", action="append", help="Limit to one slug (repeatable)"
    )
    parser.add_argument(
        "--all", action="store_true", help="Process all slugs in batch status files"
    )
    args = parser.parse_args(argv)

    if not args.slug and not args.all:
        parser.error("specify --all or one or more --slug values")

    batch_dirs = sorted(OUTPUT_ROOT.glob("prepare2_*"))
    folder_map = collect_slug_folder_map(batch_dirs)
    if not folder_map:
        logger.error("no slug→folder mapping found under %s", OUTPUT_ROOT)
        return 1

    if args.slug:
        targets = {s: folder_map[s] for s in args.slug if s in folder_map}
        missing = [s for s in args.slug if s not in folder_map]
        if missing:
            logger.error("no Drive folder mapping for: %s", ", ".join(missing))
    else:
        targets = folder_map

    if not targets:
        logger.error("nothing to do")
        return 1

    if args.dry_run:
        service = None
        # In dry-run we still need Drive listing to show what would change.
        from drive_uploader import DriveUploader

        service = DriveUploader().service
    else:
        from drive_uploader import DriveUploader

        service = DriveUploader().service

    total_matched = 0
    total_updated = 0
    total_skipped = 0
    for slug, fid in targets.items():
        m, u, s = reupload_one(service, slug, fid, dry_run=args.dry_run)
        total_matched += m
        total_updated += u
        total_skipped += s

    logger.info(
        "done: %d matched, %d updated, %d skipped (%d slugs)",
        total_matched,
        total_updated,
        total_skipped,
        len(targets),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
