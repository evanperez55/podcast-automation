"""One-time: generate clients/{slug}.yaml + clients/{slug}/logo.png for the 20 batch-2 church prospects.

Reads PROSPECTS list from gen_church_pitches.py for slugs, looks up iTunes for each
to get feedUrl and artworkUrl600, downloads artwork as logo.png, writes yaml from
church-template.yaml using the looked-up feed URL.

Safe to re-run; skips work that's already done.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

# Slugs added in batch 2 (must match gen_church_pitches.py PROSPECTS entries)
BATCH2_SLUGS = [
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

# iTunes lookup hints: known Apple IDs preferred (guarantees exact match)
# IDs sourced from output/prospect_candidates/itunes_filtered_2026-04-27.json
ITUNES_HINTS = {
    "christ-community-franklin-tn": {"id": "1382431493"},
    "north-village-church-austin": {
        "feed": "https://anchor.fm/s/2692b2a8/podcast/rss"
    },  # no Apple ID — iTunes search unreliable
    "doxology-bible-church": {
        "id": "1605815051",
        "feed": "https://rss.buzzsprout.com/254230.rss",
    },
    "park-church-denver": {
        "id": "689349232",
        "feed": "https://parkchurch.org/category/sermons/feed/",
    },
    "northside-church-of-christ-wichita": {
        "id": "575688284",
        "feed": "http://northside-sermons.sermon.net/rss/NorthsideSermons/audio",
    },
    "pacific-crossroads-church-la": {
        "id": "301642735",
        "feed": "https://publishing.planningcenteronline.com/52203/podcast_feeds/25870.xml",
    },
    "cornerstone-fellowship-bible-church": {
        "id": "1531711097",
        "feed": "https://www.cornerstonebible.org/category/sermons/feed/",
    },
    "coram-deo-bible-church": {
        "id": "1457449460",
        "feed": "https://coramdeobible.church/mediafiles/sermons.xml",
    },
    "trinity-baptist-church-nashua": {
        "id": "186699463",
        "feed": "https://yetanothersermon.host/_/trinitybcnh/feed.rss",
    },
    "go-church": {
        "id": "1486096750",
        "feed": "https://GOChurch.sermon.net/rss/main/audio",
    },
    "the-tree-church-lancaster": {
        "id": "538449552",
        "feed": "http://feeds.feedburner.com/LancasterCommunityChurchSermon",
    },
    "high-point-church-madison": {
        "id": "453294855",
        "feed": "https://highpointchurch.org/mediafiles/sermons.xml",
    },
    "north-wake-church": {
        "id": "1747364979",
        "feed": "https://app.branchcast.com/north-wake-church/podcasts/north-wake-church-sermons.xml",
    },
    "first-family-church-ankeny": {
        "id": "1482284449",
        "feed": "https://firstfamily.church/podcast-category/first-family-church/feed/podcast",
    },
    "cornerstone-church-cefc": {
        "id": "1845942306",
        "feed": "https://anchor.fm/s/1078212cc/podcast/rss",
    },
    "denton-church-of-christ": {
        "id": "1499012816",
        "feed": "https://dentonchurchofchrist.org/podcast/feed3.php",
    },
    "imago-dei-church-raleigh": {
        "id": "535371424",
        "feed": "https://idcraleigh.com/category/podcast/feed/",
    },
    "faith-baptist-church-fbcnet": {
        "id": "1245695364",
        "feed": "https://podcasts.subsplash.com:443/e96b755/podcast.rss",
    },
    "emergence-church-nj": {
        "id": "1450884759",
        "feed": "https://podcasts.subsplash.com/wy38r4x/podcast.rss",
    },
    "park-cities-presbyterian-dallas": {
        "id": "145688010",
        "feed": "https://anchor.fm/s/63eaaaac/podcast/rss",
    },
}


def _http_json(url: str, timeout: int = 15) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def lookup_itunes(slug: str) -> dict | None:
    """Return iTunes record (artworkUrl600, feedUrl, etc.) for this prospect."""
    hint = ITUNES_HINTS.get(slug, {})
    apple_id = hint.get("id")
    if apple_id:
        url = f"https://itunes.apple.com/lookup?id={apple_id}"
        try:
            data = _http_json(url)
            results = data.get("results", [])
            if results:
                return results[0]
        except Exception as e:
            print(f"  iTunes lookup-by-id failed: {e}")

    search_term = hint.get("search") or slug.replace("-", " ")
    url = f"https://itunes.apple.com/search?term={urllib.parse.quote(search_term)}&entity=podcast&limit=10&country=US"
    try:
        data = _http_json(url)
        results = data.get("results", [])
        if not results:
            return None
        # Prefer result whose feed URL matches our hint (if provided)
        hint_feed = hint.get("feed")
        if hint_feed:
            for r in results:
                if r.get("feedUrl") == hint_feed:
                    return r
        return results[0]
    except Exception as e:
        print(f"  iTunes search failed: {e}")
        return None


def download_artwork(url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 1024:
        print(f"  logo exists: {dest}")
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            content = r.read()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        print(f"  logo downloaded: {dest} ({len(content) // 1024} KB)")
        return True
    except Exception as e:
        print(f"  logo download failed: {e}")
        return False


# Load PROSPECTS from gen_church_pitches.py for display names + flags
_GEN_PATH = Path(__file__).parent / "gen_church_pitches.py"


def load_prospects() -> dict:
    """Eval gen_church_pitches.py to extract PROSPECTS list (no side effects since main() is gated)."""
    src = _GEN_PATH.read_text(encoding="utf-8")
    ns: dict = {}
    exec(src, ns)
    return {p["slug"]: p for p in ns["PROSPECTS"]}


YAML_TEMPLATE = """# Church client config (auto-generated 2026-04-27 batch 2)
client_name: "{slug}"
podcast_name: "{podcast_name}"

episode_source: rss
rss_source:
  feed_url: "{feed_url}"
  episode_index: 0  # 0 = latest sermon

# --- Platform credentials (all null = disabled until configured) ---
youtube:
  client_id: null
  client_secret: null
  token_pickle: "clients/{slug}/youtube_token.pickle"

twitter:
  api_key: null
  api_secret: null
  access_token: null
  access_secret: null

instagram:
  access_token: null
  account_id: null

tiktok:
  client_key: null
  client_secret: null
  access_token: null

discord:
  webhook_url: null

# --- Branding (logo baked into thumbnails + clip backgrounds) ---
branding:
  logo_path: clients/{slug}/logo.png

# --- Content settings tuned for sermons ---
content:
  num_clips: 5
  clip_min_duration: 30
  clip_max_duration: 90
  clip_selection_mode: content
  names_to_remove: []
  words_to_censor: []

  voice_persona: |
    You write content for a church that wants to extend the reach of their
    weekly sermons. Your tone is warm, reverent, and encouraging — never
    preachy or judgmental. You speak to both longtime members and people
    discovering this church for the first time.

    You treat sermon content with respect — these are teachings that matter
    deeply to the congregation. When summarizing, preserve the pastor's
    key points and the scripture they reference. Never trivialize the message.

    Your writing is clear and accessible. Avoid church jargon that outsiders
    wouldn't understand (explain terms like "sanctification" if you use them).
    Think of it as: how would you explain this sermon to a thoughtful friend
    over coffee?

    For social media: be genuine, not performative. No "🙏🔥 THIS MESSAGE
    CHANGED MY LIFE" energy. Instead: "This week's sermon on forgiveness
    hit different. Here's the part that stuck with me."

  clip_criteria: |
       - Powerful scripture quotes read or explained by the pastor
       - Key sermon points — the "if you remember one thing" moments
       - Personal stories or illustrations that make the teaching real
       - Moments of conviction, encouragement, or challenge
       - Clear, quotable statements of faith that stand alone
       - Practical application — "here's what this means for your week"

  blog_voice: |
    Write this as a devotional-style blog post based on the sermon.
    Structure it as:
    1. Opening hook — a relatable situation or question the sermon addresses
    2. Key scripture(s) referenced, quoted in full
    3. The pastor's main teaching points, in your own words
    4. A practical takeaway — what can the reader do this week?
    5. A brief closing prayer or reflection prompt

    Tone: warm, thoughtful, accessible. Not academic theology — this is
    for someone reading on their phone between meetings. Use short paragraphs.
    Include the full scripture references (e.g., "Romans 8:28, NIV") so
    readers can look them up.

    Do NOT use churchy cliches like "unpack this passage" or "let's dive in."
    Just write naturally.

rss:
  description: null
  author: "{author}"
  email: null
  website_url: null
  artwork_url: null
  language: "en-us"
  explicit: false
  categories: ["Religion & Spirituality", "Christianity"]
"""


def main() -> None:
    project_root = Path(__file__).parent.parent
    clients_dir = project_root / "clients"
    prospects = load_prospects()

    summary = []
    for slug in BATCH2_SLUGS:
        prospect = prospects.get(slug)
        if prospect is None:
            print(f"!! {slug}: NOT in PROSPECTS — skipping")
            continue

        print(f"\n=== {slug} ===")
        rec = lookup_itunes(slug)
        time.sleep(0.3)  # be polite to iTunes

        # Determine feed URL: explicit hint wins (we curated these), iTunes search fallback
        hint_feed = ITUNES_HINTS.get(slug, {}).get("feed")
        itunes_feed = (rec or {}).get("feedUrl")
        feed_url = hint_feed or itunes_feed or ""
        feed_match = bool(hint_feed and itunes_feed and hint_feed == itunes_feed)
        if not feed_url:
            print("  WARN: no feed URL found — yaml will need manual fill")
            feed_url = "TBD-manual-fill"
        elif hint_feed and itunes_feed and hint_feed != itunes_feed:
            print(
                "  NOTE: iTunes search returned different feed than hint — using HINT"
            )
            print(f"        hint:   {hint_feed}")
            print(f"        itunes: {itunes_feed}")

        # Logo: only use iTunes artwork if iTunes feed matches our hint (else it's a different church!)
        if hint_feed and not feed_match:
            artwork_url = (
                None  # iTunes record is for a different podcast — don't use its artwork
            )
            print(
                "  SKIP_ITUNES_ARTWORK: iTunes returned wrong church, no artwork to use"
            )
        else:
            artwork_url = (rec or {}).get("artworkUrl600") or (rec or {}).get(
                "artworkUrl100"
            )
        logo_dest = clients_dir / slug / "logo.png"
        logo_ok = False
        if artwork_url:
            logo_ok = download_artwork(artwork_url, logo_dest)
        if not logo_ok:
            print(f"  WARN: no logo for {slug} — pipeline will hard-fail until added")

        # Write yaml
        yaml_path = clients_dir / f"{slug}.yaml"
        if yaml_path.exists():
            print(f"  yaml exists: {yaml_path} (overwriting)")
        author = prospect.get("pastor_name") or "Pastor"
        text = YAML_TEMPLATE.format(
            slug=slug,
            podcast_name=prospect["church_name"],
            feed_url=feed_url,
            author=author,
        )
        yaml_path.write_text(text, encoding="utf-8")
        print(f"  yaml written: {yaml_path}")

        summary.append(
            {
                "slug": slug,
                "feed_url": feed_url,
                "logo_ok": logo_ok,
                "ep_count": (rec or {}).get("trackCount"),
                "last_pub": ((rec or {}).get("releaseDate") or "")[:10],
            }
        )

    print("\n\n=== SUMMARY ===")
    print(f"{'SLUG':45} {'EP_CT':>5} {'LAST_PUB':12} {'LOGO':5} {'FEED'}")
    print("-" * 130)
    for s in summary:
        feed_short = (s["feed_url"] or "")[:55]
        print(
            f"{s['slug']:45} {(s['ep_count'] or 0):>5} {s['last_pub']:12} {'OK' if s['logo_ok'] else 'NO':5} {feed_short}"
        )

    print(f"\nTotal: {len(summary)}/{len(BATCH2_SLUGS)}")
    print(f"With logos: {sum(1 for s in summary if s['logo_ok'])}")
    print(
        f"With feed: {sum(1 for s in summary if s['feed_url'] and s['feed_url'] != 'TBD-manual-fill')}"
    )


if __name__ == "__main__":
    main()
