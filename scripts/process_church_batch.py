"""Sequentially process church prospect episodes for the outreach batch.

Respects B006 (no parallel pipelines — GPU/RAM constraint).
Writes per-prospect logs and a rolling status.json.
Does not abort the batch on individual prospect failure.

Usage:
    uv run python scripts/process_church_batch.py

Status can be polled via:
    output/church_batch/status.json
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROSPECTS = [
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

# 45 min per episode should be ample; most finish in 10-25.
PER_PROSPECT_TIMEOUT_SEC = 45 * 60

BATCH_DIR = Path("output/church_batch")
LOG_DIR = BATCH_DIR / "logs"
STATUS_PATH = BATCH_DIR / "status.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_status(state: dict) -> None:
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def run_one(slug: str) -> dict:
    log_path = LOG_DIR / f"{slug}.log"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    cmd = ["uv", "run", "main.py", "--client", slug, "latest", "--auto-approve"]
    start = time.monotonic()
    started_at = now_iso()

    with log_path.open("w", encoding="utf-8") as logf:
        logf.write(f"=== {slug} started at {started_at} ===\n")
        logf.write(f"CMD: {' '.join(cmd)}\n\n")
        logf.flush()
        try:
            proc = subprocess.run(
                cmd,
                stdout=logf,
                stderr=subprocess.STDOUT,
                timeout=PER_PROSPECT_TIMEOUT_SEC,
                check=False,
            )
            rc = proc.returncode
            status = "success" if rc == 0 else "failed"
            err = None if rc == 0 else f"exit code {rc}"
        except subprocess.TimeoutExpired:
            status = "timeout"
            rc = -1
            err = f"timed out after {PER_PROSPECT_TIMEOUT_SEC}s"
            logf.write(f"\n!!! TIMEOUT after {PER_PROSPECT_TIMEOUT_SEC}s !!!\n")
        except Exception as e:
            status = "error"
            rc = -2
            err = f"exception: {e}"
            logf.write(f"\n!!! EXCEPTION: {e} !!!\n")

    duration = time.monotonic() - start
    return {
        "slug": slug,
        "status": status,
        "return_code": rc,
        "error": err,
        "started_at": started_at,
        "finished_at": now_iso(),
        "duration_sec": round(duration, 1),
        "log_path": str(log_path),
    }


def main() -> int:
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    state: dict = {
        "batch_started_at": now_iso(),
        "prospects_total": len(PROSPECTS),
        "prospects_done": 0,
        "current": None,
        "results": [],
    }
    write_status(state)

    for slug in PROSPECTS:
        state["current"] = slug
        state["current_started_at"] = now_iso()
        write_status(state)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting {slug}...", flush=True)

        result = run_one(slug)

        state["results"].append(result)
        state["prospects_done"] = len(state["results"])
        state["current"] = None
        state.pop("current_started_at", None)
        write_status(state)

        emoji = "OK" if result["status"] == "success" else "FAIL"
        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] {emoji} {slug} "
            f"({result['status']}, {result['duration_sec']}s)",
            flush=True,
        )

    state["batch_finished_at"] = now_iso()
    write_status(state)

    succeeded = sum(1 for r in state["results"] if r["status"] == "success")
    print(f"\nBatch complete: {succeeded}/{len(PROSPECTS)} succeeded")
    return 0 if succeeded == len(PROSPECTS) else 1


if __name__ == "__main__":
    sys.exit(main())
