"""Render a reply template for a given prospect — paste the output into Gmail.

When a prospect replies to your initial outreach, you don't want to write
from scratch each time. This script loads the prospect's data from the
outreach tracker (and optionally their PITCH.md for first_name + preview URL),
substitutes into one of the canned reply templates, and prints the rendered
text to stdout. Copy and paste into your Gmail reply.

Available scenarios (--list-scenarios):
    interested          They want to move forward — re-send preview, offer 4 free
    pricing             They asked what it costs — reveal $49/$99/$199 tiers
    decline             They said no thanks — graceful close
    already_have_someone They already use a vendor / in-house person
    call_request        They want to hop on a call
    forward_to_team     They want to share with their comms person

Usage:
    uv run python scripts/draft_reply.py <slug> <scenario>
    uv run python scripts/draft_reply.py --list-scenarios
    uv run python scripts/draft_reply.py redeemer-city-church-tampa interested
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# scripts/ → project-root sys.path shim
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import Config  # noqa: E402
from outreach_tracker import OutreachTracker  # noqa: E402

TEMPLATES_DIR = Config.BASE_DIR / "templates" / "replies"
DEMO_ROOT = Config.BASE_DIR / "demo" / "church-vertical"


def list_scenarios() -> list[str]:
    """Return all available reply scenarios (sorted, lowercase)."""
    if not TEMPLATES_DIR.exists():
        return []
    return sorted(p.stem.lower() for p in TEMPLATES_DIR.glob("*.md"))


def load_template(scenario: str) -> str:
    """Read the template file for `scenario` (case-insensitive). Raises if missing."""
    path = TEMPLATES_DIR / f"{scenario.lower()}.md"
    if not path.exists():
        available = ", ".join(list_scenarios()) or "(none)"
        raise FileNotFoundError(
            f"Unknown scenario '{scenario}'. Available: {available}"
        )
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Prospect context — pull first_name + preview_url from PITCH.md when available
# ---------------------------------------------------------------------------

# Match the contact line: `**Contact:** <Name>` or `**Contact:** <Name> / **EMAIL: ...`
PASTOR_NAME_RE = re.compile(
    r"\*\*Contact:\*\*\s*([^/\n*]+?)(?:\s*/|\s*\*\*|\s*$)", re.MULTILINE
)
# Match the rendered preview URL injected by outreach_prepare. Falls back to
# the [PREVIEW URL] placeholder if outreach_prepare hasn't run yet.
PREVIEW_URL_RE = re.compile(r"https://episodespreview\.com/[\w./-]+")


def derive_first_name(pitch_text: str, fallback: str = "there") -> str:
    """Pull the addressee's first name from PITCH.md.

    Looks at `**Contact:** Mitch Kuhn / **EMAIL: ...` and returns "Mitch".
    Falls back to `fallback` if no contact line found or it parses to a generic
    placeholder ("Pastor", "there").
    """
    m = PASTOR_NAME_RE.search(pitch_text)
    if not m:
        return fallback
    name = m.group(1).strip()
    # Drop common honorifics so "Dr. Steve Ball" → "Steve"
    name = re.sub(r"^(Dr\.|Pastor|Rev\.|Mr\.|Ms\.|Mrs\.)\s+", "", name)
    first = name.split()[0] if name else fallback
    if first.lower() in {"pastor", "office", "x"}:
        return fallback
    return first


def derive_preview_url(pitch_text: str) -> str | None:
    """Find the rendered preview URL in PITCH.md, if outreach_prepare has substituted it."""
    m = PREVIEW_URL_RE.search(pitch_text)
    return m.group(0) if m else None


def build_context(slug: str, tracker: OutreachTracker) -> dict:
    """Assemble the substitution context for a slug.

    Pulls church_name from the tracker (show_name field), first_name + preview_url
    from PITCH.md when available. Missing fields fall back to placeholders so
    the rendered text always parses (the user can hand-edit before pasting).
    """
    prospect = tracker.get_prospect(slug)
    church_name = (prospect or {}).get("show_name") or slug
    first_name = "there"
    preview_url = (
        "[PREVIEW URL — paste from your sent email or run preview_page_publish.py]"
    )

    pitch_path = DEMO_ROOT / slug / "PITCH.md"
    if pitch_path.exists():
        pitch_text = pitch_path.read_text(encoding="utf-8")
        first_name = derive_first_name(pitch_text)
        derived_preview = derive_preview_url(pitch_text)
        if derived_preview:
            preview_url = derived_preview

    return {
        "slug": slug,
        "church_name": church_name,
        "first_name": first_name,
        "preview_url": preview_url,
    }


def render(scenario: str, context: dict) -> str:
    """Render the named scenario template against `context`.

    Uses str.format_map so missing keys raise KeyError rather than silently
    leaving placeholders unfilled.
    """
    template = load_template(scenario)
    return template.format_map(context)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "slug", nargs="?", help="Prospect slug (e.g. redeemer-city-church-tampa)"
    )
    ap.add_argument(
        "scenario", nargs="?", help="One of: " + ", ".join(list_scenarios())
    )
    ap.add_argument(
        "--list-scenarios",
        action="store_true",
        help="Print available reply scenarios and exit",
    )
    ap.add_argument(
        "--show-context",
        action="store_true",
        help="Print the substitution context (church_name, first_name, etc.) "
        "before the rendered text. Useful for debugging template fills.",
    )
    args = ap.parse_args()

    if args.list_scenarios or not args.slug or not args.scenario:
        print("Available reply scenarios:")
        for s in list_scenarios():
            print(f"  {s}")
        if not args.list_scenarios:
            print("\nUsage: uv run python scripts/draft_reply.py <slug> <scenario>")
            return 1
        return 0

    tracker = OutreachTracker()
    context = build_context(args.slug, tracker)

    if args.show_context:
        print("# Context", file=sys.stderr)
        for k, v in context.items():
            print(f"#   {k}: {v}", file=sys.stderr)
        print("# ---", file=sys.stderr)

    try:
        rendered = render(args.scenario, context)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except KeyError as e:
        print(
            f"ERROR: template references {e} but no value in context. "
            f"Context keys: {list(context.keys())}",
            file=sys.stderr,
        )
        return 1

    print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
