"""Publish a prospect's preview page: render → write to repo dir → optional push.

Wraps preview_page_generator.generate_preview_page() with the file-system and
git plumbing needed to actually deploy the page via Cloudflare-style auto-deploy
on git push (in our case, Netlify).

Layout in the previews repo:
  episode-previews/
  ├── <slug>/
  │   ├── index.html
  │   ├── logo.png
  │   ├── thumbnail.png
  │   └── clip_NN_*.mp4
  └── ...

Usage:
    uv run python scripts/preview_page_publish.py <slug> [--push]
        --push  also run git add/commit/push in the previews repo

Environment:
    EPISODE_PREVIEWS_REPO  local path to the cloned previews repo
                           (default: ../episode-previews relative to project root)
    EPISODE_PREVIEW_BASE_URL  override the printed URL host
                              (default: https://episodepreview.com)
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from logger import logger  # noqa: E402
from scripts.preview_page_generator import generate_preview_page  # noqa: E402

DEFAULT_REPO = _PROJECT_ROOT.parent / "episode-previews"
DEFAULT_BASE_URL = "https://episodepreview.com"


def publish_preview_page(
    slug: str,
    *,
    repo_dir: Path,
    base_url: str = DEFAULT_BASE_URL,
    push: bool = False,
    clients_dir: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> str:
    """Render preview for `slug` and write it under repo_dir/<slug>/.

    If push=True, also commits to and pushes the repo (Netlify will then
    auto-deploy the change).

    Returns the public URL the prospect should hit.
    """
    repo_dir = Path(repo_dir)
    if not repo_dir.exists():
        raise FileNotFoundError(
            f"previews repo not found at {repo_dir} — clone it first or set "
            "EPISODE_PREVIEWS_REPO"
        )

    result = generate_preview_page(slug, clients_dir=clients_dir, output_dir=output_dir)

    target = repo_dir / slug
    # Wipe any stale files from a prior render so renamed/removed clips don't linger
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    (target / "index.html").write_text(result["html"], encoding="utf-8")
    for asset in result["assets"]:
        shutil.copy2(asset["src"], target / asset["dst_name"])

    logger.info(
        "preview rendered: %s (%d assets) -> %s", slug, len(result["assets"]), target
    )

    if push:
        _git_publish(repo_dir, slug)

    url = f"{base_url.rstrip('/')}/{slug}/"
    logger.info("preview URL: %s", url)
    return url


def _git_publish(repo_dir: Path, slug: str) -> None:
    """git add . ; git commit -m "..." ; git push (in repo_dir).

    A no-op `git commit` (when the working tree is clean — e.g. re-publish
    of identical content) is treated as success, not an error.
    """

    def run(cmd: list[str], *, allow_fail: bool = False) -> subprocess.CompletedProcess:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0 and not allow_fail:
            raise RuntimeError(f"git command failed: {' '.join(cmd)}\n{result.stderr}")
        return result

    run(["git", "-C", str(repo_dir), "add", "."])
    commit = run(
        ["git", "-C", str(repo_dir), "commit", "-m", f"publish preview: {slug}"],
        allow_fail=True,
    )
    if commit.returncode != 0:
        # Most likely "nothing to commit, working tree clean" — fine, skip push.
        logger.info("no changes to commit for %s; skipping push", slug)
        return
    run(["git", "-C", str(repo_dir), "push"])


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("slug", help="Prospect slug (matches clients/<slug>.yaml)")
    ap.add_argument(
        "--push",
        action="store_true",
        help="git add + commit + push to deploy via Netlify",
    )
    ap.add_argument(
        "--repo-dir",
        type=Path,
        default=Path(os.getenv("EPISODE_PREVIEWS_REPO", str(DEFAULT_REPO))),
        help=f"local clone of the previews repo (default: {DEFAULT_REPO})",
    )
    ap.add_argument(
        "--base-url",
        default=os.getenv("EPISODE_PREVIEW_BASE_URL", DEFAULT_BASE_URL),
        help=f"deployed base URL (default: {DEFAULT_BASE_URL})",
    )
    args = ap.parse_args(argv)

    try:
        url = publish_preview_page(
            args.slug,
            repo_dir=args.repo_dir,
            base_url=args.base_url,
            push=args.push,
        )
    except (FileNotFoundError, RuntimeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print()
    print("=" * 60)
    print(f"PREVIEW PUBLISHED: {args.slug}")
    print("=" * 60)
    print(f"  URL: {url}")
    if not args.push:
        print("  (local only — pass --push to deploy)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
