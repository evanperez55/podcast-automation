"""One-time script: inject resolved contact emails into church PITCH.md files
and outreach tracker.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

# Resolved via WebFetch + WebSearch on 2026-04-13
CONTACTS = {
    "bear-creek-bible-church": {
        "email": "john@bcbc.org",
        "contact_person": "John Salvesen (Senior Pastor)",
        "note": "DIRECT — pastor's personal staff email from bcbc.org/about-us/staff-leadership",
    },
    "redeemer-city-church-tampa": {
        "email": "office@redeemertampa.com",
        "contact_person": "Mitch Kuhn (via office)",
        "note": "General office — no direct pastor email found. Phone: 813-355-9475. CC a follow-up via the contact form on redeemertampa.com/contact if no reply in 1 week.",
    },
    "christ-community-church-columbus": {
        "email": "communications@ccclive.org",
        "contact_person": "Kelli Wommack (via comms team)",
        "note": "Communications inbox — IDEAL target for this pitch. Phone: 706-565-7240.",
    },
    "metro-tab-church": {
        "email": "info@metrotab.net",
        "contact_person": "Dr. Steve Ball (via info)",
        "note": "General info inbox. Phone: 423-894-3377. May need to ask for comms director by name in the email.",
    },
    "the-crossings-church-collinsville": {
        "email": "admin@crossingscollinsville.com",
        "contact_person": "Pastor / Admin team",
        "note": "Site appears active despite Oct 2025 stale feed — restart angle is live. Phone: 636-442-2778.",
    },
    "faith-bible-church-edmond": {
        "email": "fbc@faithbibleok.com",
        "contact_person": "Dr. Mark Hitchcock (Senior Pastor, via general church inbox)",
        "note": "Pastor is Mark Hitchcock — notable prophecy teacher + DTS faculty. Staff pages at /our-staff and /our-elders may have direct addresses. Phone: 405-340-1000.",
    },
    "life-bridge-church-green-bay": {
        "email": "lbccgb@gmail.com",
        "contact_person": "Pastor (via general)",
        "note": "VERIFY podcast match: search result was for 'Life Bridge Christian Church Green Bay' (lifebridgegb.org) — iTunes feed is 'Life Bridge Sermons Podcast' by 'Life Bridge Studios'. Likely same entity; confirm before sending. Phone: 920-494-4042.",
    },
    "cottonwood-church": {
        "email": "guestservices@cottonwood.org",
        "contact_person": "Pastor (via guest services — weak)",
        "note": "RESIZE FLAG: Cottonwood hosts 'Answers with Bayless Conley' broadcast — this is a LARGE church/media operation, not mid-size ICP. They likely already have professional media staff and Pulpit AI. Consider deprioritizing or pitching at a higher price tier. Phone: 714-947-5300.",
    },
    "mercy-village-church": {
        "email": "info@mercyvillage.church",
        "contact_person": "Pastor (via general info)",
        "note": "Small-town church, stewardship angle still applies. Phone: 304-410-0371.",
    },
    "harbor-rock-tabernacle": {
        "email": "paul@harborrock.org",
        "contact_person": "Pastor Paul Rhoads (Lead Pastor)",
        "note": "DIRECT — lead pastor's email. Phone: 262-633-3206. Also info@harborrock.org available as fallback.",
    },
    "christ-community-church-johnson-city": {
        "email": "office@christcommunityjc.com",
        "contact_person": "Elders team (Jim Powell, Bill Leuzinger, AJ Babel)",
        "note": "Church is elder-led (no single senior pastor). Teaching elders: Jim Powell, Bill Leuzinger, AJ Babel. Alternate address: elders@christcommunityjc.com for direct pastoral contact.",
    },
}


def update_pitch_file(slug: str, contact: dict) -> None:
    path = Path(f"demo/church-vertical/{slug}/PITCH.md")
    if not path.exists():
        print(f"  SKIP (no PITCH.md): {slug}")
        return
    text = path.read_text(encoding="utf-8")

    # Replace the EMAIL: TBD line
    email = contact["email"]
    person = contact["contact_person"]
    note = contact["note"]

    # Find the contact line and rewrite it
    new_contact_line = f"**Contact:** {person} / **EMAIL: {email}**"
    text = re.sub(
        r"\*\*Contact:\*\*[^\n]+\*\*EMAIL: TBD\*\*[^\n]*",
        new_contact_line,
        text,
        count=1,
    )

    # Insert a contact notes block right after the contact line if not already there
    notes_block = f"\n**Contact notes:** {note}"
    if "**Contact notes:**" not in text:
        text = text.replace(
            new_contact_line,
            new_contact_line + notes_block,
            1,
        )

    # Update "EMAIL: TBD" note in checklist section to a checked reference
    text = text.replace(
        f"- [ ] Find {person.split(' (')[0]} contact email",
        f"- [x] Contact email resolved: {email}",
    )
    # Catch-all for any "Find X contact email" still present
    text = re.sub(
        r"- \[ \] Find (.+?) contact email \([^)]+\)",
        lambda m: f"- [x] Contact email resolved: {email}",
        text,
    )

    path.write_text(text, encoding="utf-8")
    print(f"  UPDATED: {slug} -> {email}")


def update_tracker(slug: str, email: str) -> None:
    # outreach_tracker expects: outreach update <slug> <status>
    # We need to set contact_email. Check if a key=value form works.
    result = subprocess.run(
        ["uv", "run", "main.py", "outreach", "update", slug, f"contact_email={email}"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    out = (result.stdout + result.stderr).strip().splitlines()
    last = out[-1] if out else "(no output)"
    print(f"  TRACKER {slug}: {last}")


def main() -> None:
    print("Updating PITCH.md files:")
    for slug, contact in CONTACTS.items():
        update_pitch_file(slug, contact)

    print("\nUpdating outreach tracker:")
    for slug, contact in CONTACTS.items():
        update_tracker(slug, contact["email"])


if __name__ == "__main__":
    main()
