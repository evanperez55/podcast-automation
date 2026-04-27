"""Sequentially process the 2026-04-27 batch-2 church prospects.

Thin wrapper around process_church_batch.run_one() that processes the new
20 slugs. Splits them into Wed/Thu groups by default; pass `--all` to run
all 20 in one go, or `--slugs slug1,slug2,...` for a custom subset.

Respects B006 (no parallel pipelines), B011 (PYTHONUNBUFFERED=1 inside
run_one), and B016 (--auto-approve always passed).

Usage:
    uv run python scripts/process_batch2.py             # Wed group (first 10)
    uv run python scripts/process_batch2.py --thu       # Thu group (last 10)
    uv run python scripts/process_batch2.py --all       # all 20
    uv run python scripts/process_batch2.py --slugs a,b # custom subset
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from process_church_batch import run_one  # noqa: E402

WED_GROUP = [
    "christ-community-franklin-tn",
    "north-village-church-austin",
    "doxology-bible-church",
    "park-church-denver",
    "northside-church-of-christ-wichita",
    "pacific-crossroads-church-la",
    "cornerstone-fellowship-bible-church",
    "coram-deo-bible-church",
    "trinity-baptist-church-nashua",
    "go-church",
]

THU_GROUP = [
    "the-tree-church-lancaster",
    "high-point-church-madison",
    "north-wake-church",
    "first-family-church-ankeny",
    "cornerstone-church-cefc",
    "denton-church-of-christ",
    "imago-dei-church-raleigh",
    "faith-baptist-church-fbcnet",
    "emergence-church-nj",
    "park-cities-presbyterian-dallas",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument(
        "--thu", action="store_true", help="Process Thu group instead of Wed"
    )
    g.add_argument("--all", action="store_true", help="Process all 20")
    g.add_argument("--slugs", help="Comma-separated custom slug list")
    ap.add_argument(
        "--label",
        default=None,
        help="Optional label for log dir (default: 'wed', 'thu', 'all', or 'custom')",
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

    batch_dir = Path("output") / f"batch2_{label}"
    batch_dir.mkdir(parents=True, exist_ok=True)
    status_path = batch_dir / "status.json"
    log_dir = batch_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Override run_one's log location by tweaking process_church_batch globals.
    import process_church_batch as pcb

    pcb.LOG_DIR = log_dir

    state: dict = {
        "label": label,
        "batch_started_at": now_iso(),
        "prospects_total": len(slugs),
        "prospects_done": 0,
        "current": None,
        "results": [],
    }
    status_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    for slug in slugs:
        state["current"] = slug
        state["current_started_at"] = now_iso()
        status_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] START {slug}", flush=True)

        result = run_one(slug)

        state["results"].append(result)
        state["prospects_done"] = len(state["results"])
        state["current"] = None
        state.pop("current_started_at", None)
        status_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

        verdict = "OK" if result["status"] == "success" else "FAIL"
        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] {verdict} {slug} "
            f"({result['status']}, {result['duration_sec']}s)",
            flush=True,
        )

    state["batch_finished_at"] = now_iso()
    status_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    succeeded = sum(1 for r in state["results"] if r["status"] == "success")
    print(f"\nBatch complete: {succeeded}/{len(slugs)} succeeded", flush=True)
    return 0 if succeeded == len(slugs) else 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main())
