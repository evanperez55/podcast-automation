"""One-shot "show me what this prospect's email package looks like" command.

Wraps the existing pre-flight checks into a single dev-ergonomics surface so
you don't have to remember to run verify + dry-run + open-the-staging-dir
separately. Designed to be the last command you run before scheduling the
actual send.

Steps:
  1. outreach_verify.verify_one(slug) — full smoke-test battery
     (filename hygiene, clip count, durations, logo bleed, B023 color
     metadata, PITCH ↔ PACKAGE parity)
  2. If any ERROR findings → abort, surface the verdict
  3. Stage the assets to a persistent tmp dir (no auto-cleanup)
  4. Print the staged tree + open the dir in your OS file manager so you
     can eyeball clips, blog post, captions before pulling the trigger

Usage:
    uv run python scripts/outreach_review_package.py <slug>
    uv run python scripts/outreach_review_package.py <slug> --no-open

Exit codes:
    0 — verify passed, package staged + opened
    1 — verify ERROR (package not staged)
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import webbrowser
from pathlib import Path
from typing import Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from logger import logger  # noqa: E402
from scripts.outreach_prepare import (  # noqa: E402
    _find_latest_ep_dir,
    _print_staged_tree,
    _stage_assets,
)
from scripts.outreach_verify import verify_one  # noqa: E402


def review_package(
    slug: str,
    *,
    open_in_browser: bool = True,
    staging_root: Optional[Path] = None,
) -> int:
    """Run the full pre-send review for `slug`. Returns shell exit code."""
    print()
    print("=" * 60)
    print(f"REVIEWING PACKAGE: {slug}")
    print("=" * 60)
    print()

    # Step 1: smoke-test battery
    print("--- pre-upload checks ---")
    findings = verify_one(slug)
    for f in findings:
        print(f)
    errors = sum(1 for f in findings if f.level == "ERROR")
    warns = sum(1 for f in findings if f.level == "WARN")
    print(
        f"\n  verdict: {'PASS' if errors == 0 else 'BLOCK'}  "
        f"({errors} error(s), {warns} warning(s))"
    )

    if errors:
        print(
            "\nERROR: blocking issue(s) found. Fix and re-run before scheduling.",
            file=sys.stderr,
        )
        return 1

    # Step 2: stage to a persistent tmp dir
    ep_dir = _find_latest_ep_dir(slug)
    if ep_dir is None:
        print(f"\nERROR: no ep_dir under output/{slug}", file=sys.stderr)
        return 1

    if staging_root is None:
        staging_root = Path(tempfile.mkdtemp(prefix=f"review-{slug}-"))
    staging = staging_root / f"{slug}-package"
    _stage_assets(ep_dir, staging)
    _print_staged_tree(slug, staging)

    # Step 3: open the dir in OS file manager so user can inspect
    if open_in_browser:
        webbrowser.open(staging.resolve().as_uri())
        print(f"  opened in file manager: {staging}")

    print()
    print("If everything looks right:")
    print(f"  uv run python scripts/outreach_prepare.py {slug}    # upload + draft")
    print()
    return 0


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("slug", help="Prospect slug (matches clients/<slug>.yaml)")
    ap.add_argument(
        "--no-open",
        action="store_true",
        help="don't open the staging dir in OS file manager (CI / non-TTY)",
    )
    args = ap.parse_args(argv)

    try:
        return review_package(args.slug, open_in_browser=not args.no_open)
    except FileNotFoundError as e:
        logger.error("review aborted: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
