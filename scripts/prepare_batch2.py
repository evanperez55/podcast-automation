"""Sequentially run outreach_prepare.py for each batch-2 prospect.

Wraps outreach_prepare.prepare_one() in a for-loop with:
  - --thu / --all / --slugs subset selection (mirrors process_batch2.py)
  - Date-tagged Drive folder names ('YYYY-MM-DD - <slug>') so the batch is
    visible at a glance in the Drive UI.
  - Per-slug status logging to output/prepare2_<label>/status.json so a
    partial failure (one prospect's verify gate trips, etc.) doesn't take
    down the rest of the batch.

Usage:
    uv run python scripts/prepare_batch2.py             # Wed group, today's date tag
    uv run python scripts/prepare_batch2.py --thu       # Thu group, today's date tag
    uv run python scripts/prepare_batch2.py --all       # all 20
    uv run python scripts/prepare_batch2.py --slugs a,b
    uv run python scripts/prepare_batch2.py --date 2026-04-29   # override date
    uv run python scripts/prepare_batch2.py --dry-run

Skips slugs that lack a processed episode (output/<slug>/ep_*) so failed
pipeline runs (e.g. cornerstone-fellowship-bible-church which had a
malformed RSS feed) don't crash the prepare batch — they just get
skipped with a clear note.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import date as _date
from datetime import datetime, timezone
from pathlib import Path

# scripts/ → project-root sys.path shim
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from process_batch2 import THU_GROUP, WED_GROUP  # noqa: E402
from scripts import outreach_prepare as op  # noqa: E402


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def has_processed_episode(slug: str) -> bool:
    """True iff there's at least one ep_* directory under output/<slug>/.
    Pipeline failures leave the slug without an ep_dir; we skip those rather
    than crashing prepare_one's _find_latest_ep_dir."""
    output_dir = _PROJECT_ROOT / "output" / slug
    if not output_dir.exists():
        return False
    return any(d.is_dir() and d.name.startswith("ep_") for d in output_dir.iterdir())


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument(
        "--thu", action="store_true", help="Process Thu group instead of Wed"
    )
    g.add_argument("--all", action="store_true", help="Process all 20")
    g.add_argument("--slugs", help="Comma-separated custom slug list")
    ap.add_argument(
        "--date",
        default=None,
        help="Date tag for Drive folder names (YYYY-MM-DD). Defaults to today.",
    )
    ap.add_argument(
        "--label",
        default=None,
        help="Optional label for log dir (default: 'wed' / 'thu' / 'all' / 'custom')",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse + log only. No Drive upload, no Gmail draft.",
    )
    ap.add_argument(
        "--no-preview",
        action="store_true",
        help="Skip preview page render+push for the whole batch (Drive-only).",
    )
    args = ap.parse_args()

    if args.slugs:
        slugs = [s.strip() for s in args.slugs.split(",") if s.strip()]
        label = args.label or "custom"
    elif args.thu:
        slugs = THU_GROUP
        label = args.label or "thu"
    elif args.all:
        slugs = WED_GROUP + THU_GROUP
        label = args.label or "all"
    else:
        slugs = WED_GROUP
        label = args.label or "wed"

    folder_date = args.date or _date.today().isoformat()

    batch_dir = _PROJECT_ROOT / "output" / f"prepare2_{label}"
    batch_dir.mkdir(parents=True, exist_ok=True)
    status_path = batch_dir / "status.json"

    # Build clients lazily — outreach_prepare wires them up via main(), but
    # we're using prepare_one() directly so we need to construct them here.
    drive = None
    gmail = None
    if args.dry_run:
        gmail = op._make_dry_run_gmail()
    else:
        from drive_uploader import DriveUploader
        from gmail_sender import GmailSender

        drive = DriveUploader()
        gmail = GmailSender()

    state: dict = {
        "label": label,
        "folder_date": folder_date,
        "batch_started_at": now_iso(),
        "prospects_total": len(slugs),
        "prospects_done": 0,
        "current": None,
        "results": [],
    }
    status_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    for slug in slugs:
        state["current"] = slug
        status_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] === {slug} ===", flush=True)

        if not has_processed_episode(slug):
            print(f"  SKIP — no processed episode in output/{slug}/", flush=True)
            state["results"].append(
                {
                    "slug": slug,
                    "status": "skipped",
                    "reason": "no_episode_processed",
                    "ts": now_iso(),
                }
            )
            state["prospects_done"] = len(state["results"])
            status_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
            continue

        try:
            result = op.prepare_one(
                slug,
                drive=drive,
                gmail=gmail,
                dry_run=args.dry_run,
                publish_preview=not args.no_preview,
                folder_date=folder_date,
            )
            # Distinguish "fully prepared" (Drive + Gmail draft both succeeded)
            # from "Drive uploaded but Gmail draft failed silently". gmail_sender
            # logs the HttpError and returns None on failure, so a None draft_id
            # means the draft was NOT created — record it as a partial failure
            # so the operator sees it instead of trusting a misleading "prepared".
            draft_id = result.get("draft_id")
            if draft_id is None and not args.dry_run:
                state["results"].append(
                    {
                        "slug": slug,
                        "status": "partial",
                        "drive_link": result.get("drive_link"),
                        "preview_url": result.get("preview_url"),
                        "draft_id": None,
                        "error": "drive_uploaded_but_gmail_draft_failed",
                        "ts": now_iso(),
                    }
                )
                print(
                    f"  PARTIAL drive uploaded but Gmail draft failed "
                    f"(see Gmail API error in log) — drive={result.get('drive_link', '?')[:60]}",
                    flush=True,
                )
            else:
                state["results"].append(
                    {
                        "slug": slug,
                        "status": "prepared",
                        "draft_id": draft_id,
                        "drive_link": result.get("drive_link"),
                        "preview_url": result.get("preview_url"),
                        "ts": now_iso(),
                    }
                )
                print(
                    f"  OK   draft={draft_id}  "
                    f"drive={result.get('drive_link', '?')[:60]}",
                    flush=True,
                )
        except Exception as e:
            tb = traceback.format_exc()
            state["results"].append(
                {
                    "slug": slug,
                    "status": "failed",
                    "error": str(e),
                    "traceback": tb,
                    "ts": now_iso(),
                }
            )
            print(f"  FAIL  {type(e).__name__}: {e}", flush=True)

        state["prospects_done"] = len(state["results"])
        state["current"] = None
        status_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    state["batch_finished_at"] = now_iso()
    status_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    prepared = sum(1 for r in state["results"] if r["status"] == "prepared")
    partial = sum(1 for r in state["results"] if r["status"] == "partial")
    skipped = sum(1 for r in state["results"] if r["status"] == "skipped")
    failed = sum(1 for r in state["results"] if r["status"] == "failed")
    print(
        f"\nPrepare batch complete: {prepared} prepared, "
        f"{partial} partial, {skipped} skipped, {failed} failed "
        f"(of {len(slugs)} total)",
        flush=True,
    )
    # Partial counts as a non-success (Drive uploaded but Gmail draft missing
    # — operator needs to know to fix it, otherwise the prospect can't be sent).
    return 0 if (failed == 0 and partial == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
