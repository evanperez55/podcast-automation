"""Render a hosted episode preview page from existing client + episode data.

Pure renderer — given a slug, returns the HTML string and the list of asset
files that need to ship alongside index.html (clips, logo, thumbnail). The
publisher script wraps this with git operations.

Inputs:
  - clients/<slug>.yaml      → display name, logo path
  - output/<slug>/<ep_dir>/  → analysis.json, transcript.json, blog post,
                                final clips, thumbnail

Outputs (returned as a dict):
  - "html":   str — fully rendered, self-contained HTML page
  - "assets": list[Path] — files to copy alongside index.html

The page is for ONE prospect, deliberately tagged noindex/nofollow so it
doesn't pollute Google with non-canonical copies of the church's content.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Optional

import markdown as md
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Make repo root importable when run from scripts/.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

_TEMPLATES_DIR = _PROJECT_ROOT / "templates"
_DEFAULT_CLIENTS_DIR = _PROJECT_ROOT / "clients"
_DEFAULT_OUTPUT_DIR = _PROJECT_ROOT / "output"


def generate_preview_page(
    slug: str,
    *,
    clients_dir: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> dict:
    """Render the preview HTML + collect assets for prospect `slug`.

    Returns:
        {
            "html":   str,                    # full HTML page
            "assets": list[Path],             # files to copy alongside index.html
            "ep_dir": Path,                   # the chosen episode directory
            "church_name": str,               # display name used in the page
        }

    Raises:
        FileNotFoundError: if the client YAML or any episode dir is missing.
    """
    clients_dir = Path(clients_dir) if clients_dir else _DEFAULT_CLIENTS_DIR
    output_dir = Path(output_dir) if output_dir else _DEFAULT_OUTPUT_DIR

    client_yaml = clients_dir / f"{slug}.yaml"
    if not client_yaml.exists():
        raise FileNotFoundError(f"client YAML not found: {client_yaml}")

    cfg = yaml.safe_load(client_yaml.read_text(encoding="utf-8")) or {}
    church_name = cfg.get("podcast_name") or slug

    ep_dir = _find_latest_ep_dir(output_dir / slug)
    if ep_dir is None:
        raise FileNotFoundError(f"no episode directory under {output_dir / slug}")

    analysis = _read_json(next(ep_dir.glob("*_analysis.json"), None))
    transcript = _read_json(next(ep_dir.glob("*_transcript.json"), None))
    blog_md_path = next(ep_dir.glob("*_blog_post.md"), None)

    clips = _collect_clips(ep_dir)
    logo_path = _resolve_logo(cfg, clients_dir)
    thumbnail_path = next(ep_dir.glob("*_thumbnail.png"), None)

    context = {
        "church_name": church_name,
        "episode_title": analysis.get("episode_title", ""),
        "clips": clips,
        "chapters": _build_chapters(analysis),
        "transcript_segments": _build_transcript(transcript),
        "blog_html": _render_blog(blog_md_path),
        "has_logo": logo_path is not None,
        "has_thumbnail": thumbnail_path is not None,
    }

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "j2"]),
    )
    html = env.get_template("preview_page.html.j2").render(**context)

    # Assets carry both source path and destination filename. The template
    # references logo.png and thumbnail.png by literal name, so the publisher
    # must rename them on copy. Clips keep their clean names from final/.
    assets: list[dict] = [
        {"src": c["src_path"], "dst_name": c["filename"]} for c in clips
    ]
    if logo_path:
        assets.append({"src": logo_path, "dst_name": "logo.png"})
    if thumbnail_path:
        assets.append({"src": thumbnail_path, "dst_name": "thumbnail.png"})

    return {
        "html": html,
        "assets": assets,
        "ep_dir": ep_dir,
        "church_name": church_name,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_latest_ep_dir(slug_root: Path) -> Optional[Path]:
    if not slug_root.exists():
        return None
    candidates = sorted(
        (p for p in slug_root.iterdir() if p.is_dir() and p.name.startswith("ep_")),
        reverse=True,
    )
    return candidates[0] if candidates else None


def _read_json(path: Optional[Path]) -> dict:
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _collect_clips(ep_dir: Path) -> list[dict]:
    """Return list of {filename, title, src_path} for final/clip_*.mp4 files.

    Falls back to *_subtitle.mp4 if final/ doesn't exist (older episodes).
    """
    final_dir = ep_dir / "clips" / "final"
    if final_dir.exists():
        sources = sorted(final_dir.glob("clip_*.mp4"))
    else:
        sources = sorted((ep_dir / "clips").glob("*_subtitle.mp4"))
    return [
        {
            "filename": p.name,
            "title": _humanize_clip_name(p.stem),
            "src_path": p,
        }
        for p in sources
    ]


def _humanize_clip_name(stem: str) -> str:
    """clip_01_the_mission_that_started_it_all → "The Mission That Started It All".

    Strips the clip_NN_ prefix (and timestamp prefixes from raw subtitle clips)
    and converts underscores to spaces with title casing.
    """
    cleaned = re.sub(r"^clip_\d+_", "", stem)
    cleaned = re.sub(r"^.*_clip_\d+", "", cleaned)
    cleaned = cleaned.replace("_subtitle", "").replace("_censored", "")
    cleaned = cleaned.replace("_", " ").strip()
    if not cleaned:
        return stem
    return " ".join(w.capitalize() if not w.isupper() else w for w in cleaned.split())


def _build_chapters(analysis: dict) -> list[dict]:
    chapters = analysis.get("chapters") or []
    return [
        {
            "timestamp": str(c.get("start_timestamp", "00:00:00")),
            "title": str(c.get("title", "")).strip(),
        }
        for c in chapters
        if c.get("title")
    ]


def _build_transcript(transcript: dict) -> list[dict]:
    segments = transcript.get("segments") or []
    out = []
    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        out.append({"timestamp": _seconds_to_hms(seg.get("start", 0.0)), "text": text})
    return out


def _seconds_to_hms(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _render_blog(blog_md_path: Optional[Path]) -> str:
    if blog_md_path is None or not blog_md_path.exists():
        return ""
    try:
        text = blog_md_path.read_text(encoding="utf-8")
    except OSError:
        return ""
    return md.markdown(text, extensions=["extra"])


def _resolve_logo(cfg: dict, clients_dir: Path) -> Optional[Path]:
    """Return absolute path to client logo, or None if missing."""
    branding = cfg.get("branding") or {}
    rel = branding.get("logo_path")
    if not rel:
        return None
    # logo_path in YAML is relative to project root (e.g., "clients/<slug>/logo.png").
    # Resolve relative to the clients_dir's parent so tests work with tmp_path.
    candidate = (clients_dir.parent / rel).resolve()
    if candidate.exists():
        return candidate
    # Fallback: maybe the YAML stored a path relative to clients_dir directly.
    alt = (clients_dir / Path(rel).name).resolve()
    return alt if alt.exists() else None
