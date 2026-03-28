"""Script to populate RSS feed with all historical episodes."""

from datetime import datetime, timedelta

from dropbox_handler import DropboxHandler
from rss_feed_generator import RSSFeedGenerator
from config import Config

# Episode data from episode_summaries.json
EPISODES = [
    {
        "number": 1,
        "title": "CTE Can't Hurt Me",
        "summary": "The hosts dive deep into recent train safety issues following the Ohio derailment, sharing personal stories about concussions and college fight clubs, and discussing everything from corrupt politicians to evolutionary changes in human anatomy.",
    },
    {
        "number": 2,
        "title": "Top Gun Ego Death",
        "summary": "The hosts discuss their experiences with open mic comedy nights, share stories about family dynamics and awkward shopping trips, and dive deep into various topics ranging from military intervention and government corruption to animal behavior and fashion trends.",
    },
    {
        "number": 3,
        "title": "Being a Stoic With Bionic Limbs",
        "summary": "Two friends dive deep into coffee addiction, workout culture, and random philosophical tangents while discussing everything from David Goggins to medieval torture methods.",
    },
    {
        "number": 4,
        "title": "It Follows Helen Keller",
        "summary": "The hosts dive into movie analysis starting with 'It Follows' and its mysterious 1980s technology, then explore controversial topics like zoos, child labor laws, and whether animals are truly happy in captivity.",
    },
    {
        "number": 5,
        "title": "Sad Justice",
        "summary": "The hosts discuss one member's transformative jury duty experience that restored his faith in the judicial system. They also share a bizarre story about being recruited by a stranger to cheer during an impromptu lap dance at a restaurant.",
    },
    {
        "number": 6,
        "title": "Love Thy Biker",
        "summary": "The hosts return after a long break to discuss everything from half marathons and Mormon soaking practices to the importance of loving your enemies.",
    },
    # Episode 7 is missing from Dropbox - uncomment when available
    # {"number": 7, "title": "Tolerating Techno", "summary": "The hosts discuss a disastrous techno festival experience, dive deep into recent alien/UFO testimony to Congress, and explore various random topics from buffets to Down syndrome demographics."},
    {
        "number": 8,
        "title": "Camp Cuck",
        "summary": "The hosts return from a break to discuss various fake problems including whether skipping grades is child abuse, wild middle school camp stories involving Axe Body Spray incidents, and Stephen Hawking's surprising love life.",
    },
    {
        "number": 9,
        "title": "Are You Hotter Than A Magician",
        "summary": "The hosts dive into various fake problems including the mystery of how modern magic actually works, the persistence of duck face photos on dating apps, and whether it's better to know what you look like or live without mirrors.",
    },
    {
        "number": 10,
        "title": "Monodontia",
        "summary": "The hosts discuss various awkward and gross situations including cats eating their dead owners, drinking from a moldy water bottle, and a plane emergency landing due to someone having explosive diarrhea.",
    },
    {
        "number": 11,
        "title": "Hepeating Black Hole",
        "summary": "The hosts dive into follow-ups from previous episodes including the giant seaweed blob that never materialized, then explore controversial topics like fake boobs being potentially transphobic and skincare routines as accidental blackface.",
    },
    {
        "number": 12,
        "title": "Japanese Robot Cafes",
        "summary": "The Fake Problems Podcast tackles bizarre hypotheticals and observations with a special guest, covering everything from the social dynamics of petting strangers' dogs to why smartphones never appear in our dreams.",
    },
    {
        "number": 13,
        "title": "Magical Spice Wars",
        "summary": "The hosts dive into research updates revealing Chris Angel as a complete fraud who pays audiences to react to fake magic tricks, then explore the wild world of naked dating shows and bizarre social phenomena.",
    },
    {
        "number": 14,
        "title": "Solar Powered Food Addiction",
        "summary": "The hosts dive into various pet peeves including people overusing '100 percent' as a response, the logistics of powering the world with solar panels, and the awkwardness of animal buttholes being constantly visible.",
    },
    {
        "number": 15,
        "title": "Gas Powered Dating Apps",
        "summary": "The hosts dive into fake problems ranging from quarter-zip fashion confusion to dating app morning messages, while exploring wild hypotheticals about gas-powered adult toys and prison simulation technology.",
    },
    {
        "number": 16,
        "title": "What is Love",
        "summary": "The hosts dive into various 'fake problems' including dating app pet peeves, coffee addiction struggles, and philosophical discussions about perception and relationships.",
    },
    {
        "number": 17,
        "title": "Totally Safe for Work",
        "summary": "The hosts dive deep into uncomfortable territory, debating incest laws, sharing threesome experiences, and discussing a disturbing Reddit story. They also cover facial recognition bias and cloud seeding conspiracy theories.",
    },
    {
        "number": 18,
        "title": "Snake Church Glow Up",
        "summary": "The hosts dive deep into controversial topics including historical labor dynamics, the psychology of female vs male pedophiles, and modern phenomena like cyber trucks and Amazon's AI stores.",
    },
    {
        "number": 19,
        "title": "Solar Powered Roasting",
        "summary": "The hosts dive into fascinating follow-ups including why powering the world with Sahara Desert solar panels could destroy the Amazon rainforest, and whether you can actually burp out a fart.",
    },
    {
        "number": 20,
        "title": "A 4 Day Love Story",
        "summary": "The hosts dive into various 'fake problems' including the psychology of Amazon reviews, the awkwardness of certain medical specialties, and a personal experiment with non-alcoholic beer.",
    },
    {
        "number": 21,
        "title": "Space Therapy",
        "summary": "The hosts dive into bizarre topics ranging from towns with sexual names getting free Pornhub premium to North Korean soldiers discovering internet porn for the first time.",
    },
    {
        "number": 22,
        "title": "Lesbian Choir Boys",
        "summary": "The hosts return from holiday break to discuss various random topics including Project 2025, pet peeves about people saying 'I'm proud of you,' and whether bartenders should serve mentally handicapped people alcohol.",
    },
    {
        "number": 23,
        "title": "Lots of Government Stuff",
        "summary": "The hosts dive into Michael Jackson castration conspiracy theories, debate the flaws of democracy and government efficiency, and explore random topics from James Bond's terrible spy skills to exposure therapy hacks.",
    },
    {
        "number": 24,
        "title": "Drunk Persistance",
        "summary": "The hosts dive into various 'fake problems' including Ashley Madison cheating websites, persistent dating advice, and whether there are income caps on disabled people but not billionaires.",
    },
]

# We'll look up files dynamically from Dropbox
DROPBOX_FILES = {}  # Will be populated at runtime

# Approximate file sizes in bytes (from Dropbox listing)
FILE_SIZES = {
    1: 134166528,  # 127.93 MB
    2: 161218560,  # 153.75 MB
    3: 165945344,  # 158.26 MB
    4: 163522560,  # 155.95 MB
    5: 156631040,  # 149.38 MB
    6: 101239808,  # 96.55 MB
    8: 81223680,  # 77.46 MB
    9: 79200256,  # 75.53 MB
    10: 88046592,  # 83.97 MB
    11: 84123648,  # 80.23 MB
    12: 86819840,  # 82.80 MB
    13: 91420672,  # 87.19 MB
    14: 82083840,  # 78.28 MB
    15: 88575488,  # 84.47 MB
    16: 80068608,  # 76.36 MB
    17: 91052032,  # 86.84 MB
    18: 87717888,  # 83.66 MB
    19: 89249792,  # 85.12 MB
    20: 95174656,  # 90.77 MB
    21: 89636864,  # 85.48 MB
    22: 70040576,  # 66.80 MB
    23: 90247168,  # 86.07 MB
    24: 88604672,  # 84.50 MB
    25: 88014723,  # From existing RSS feed
    26: 79556065,  # From existing RSS feed
}

# Approximate durations in seconds (estimated ~1 hour each for older episodes)
DURATIONS = {
    1: 3840,  # ~64 min (larger file)
    2: 4620,  # ~77 min (larger file)
    3: 4740,  # ~79 min (larger file)
    4: 4680,  # ~78 min (larger file)
    5: 4500,  # ~75 min (larger file)
    6: 2940,  # ~49 min (smaller file)
    8: 2340,  # ~39 min
    9: 2280,  # ~38 min
    10: 2520,  # ~42 min
    11: 2400,  # ~40 min
    12: 2520,  # ~42 min
    13: 2640,  # ~44 min
    14: 2340,  # ~39 min
    15: 2520,  # ~42 min
    16: 2280,  # ~38 min
    17: 2640,  # ~44 min
    18: 2520,  # ~42 min
    19: 2580,  # ~43 min
    20: 2760,  # ~46 min
    21: 2580,  # ~43 min
    22: 2040,  # ~34 min (smallest file)
    23: 2580,  # ~43 min
    24: 2520,  # ~42 min
    25: 3666,  # 01:01:06 from existing RSS
    26: 3448,  # 57:28 from existing RSS
}


def main():
    print("=" * 60)
    print("POPULATING RSS FEED WITH ALL EPISODES")
    print("=" * 60)
    print()

    # Initialize handlers
    dropbox = DropboxHandler()
    rss_gen = RSSFeedGenerator()

    # Build file mapping from actual Dropbox contents
    print("[INFO] Scanning Dropbox for episode files...")
    DROPBOX_FILES = {}
    try:
        result = dropbox.dbx.files_list_folder("/podcast/finished_files")
        for entry in result.entries:
            if hasattr(entry, "name") and entry.name.endswith(".mp3"):
                # Extract episode number from filename
                ep_num = dropbox.extract_episode_number(entry.name)
                if ep_num:
                    DROPBOX_FILES[ep_num] = entry.path_display
                    print(f"  Found Episode {ep_num}: {entry.name}")
    except Exception as e:
        print(f"[ERROR] Failed to list Dropbox files: {e}")
        return
    print()

    # Load podcast metadata
    metadata = rss_gen.load_podcast_metadata()
    if not metadata:
        metadata = {
            "title": Config.PODCAST_NAME,
            "description": f"Welcome to {Config.PODCAST_NAME}.",
            "website_url": "https://example.com",
            "author": Config.PODCAST_NAME,
            "email": "podcast@example.com",
            "categories": ["Comedy"],
            "language": "en-us",
            "artwork_url": "https://www.dropbox.com/scl/fo/pjebq6m0sj60hlkw4mwtk/h?rlkey=83pqox6zgf28g5z8528cp38et&dl=1",
            "explicit": True,
        }

    # Create fresh RSS feed
    rss = rss_gen.create_feed(
        title=metadata["title"],
        description=metadata["description"],
        website_url=metadata["website_url"],
        author=metadata["author"],
        email=metadata["email"],
        categories=metadata["categories"],
        language=metadata.get("language", "en-us"),
        artwork_url=metadata.get("artwork_url"),
        explicit=metadata.get("explicit", True),
    )

    # Calculate publication dates (working backwards from today)
    # Assuming roughly monthly releases
    base_date = datetime(2025, 1, 26)  # Episode 26 date

    # Process each episode
    for ep in EPISODES:
        ep_num = ep["number"]

        if ep_num not in DROPBOX_FILES:
            print(f"[SKIP] Episode {ep_num} - No file in Dropbox")
            continue

        print(f"[INFO] Processing Episode {ep_num}: {ep['title']}")

        # Get shared link from Dropbox
        dropbox_path = DROPBOX_FILES[ep_num]
        try:
            audio_url = dropbox.get_shared_link(dropbox_path)
            if not audio_url:
                print(f"[ERROR] Could not get shared link for Episode {ep_num}")
                continue
        except Exception as e:
            print(f"[ERROR] Dropbox error for Episode {ep_num}: {e}")
            continue

        # Calculate pub date (older episodes get earlier dates)
        days_back = (26 - ep_num) * 30  # ~30 days per episode
        pub_date = base_date - timedelta(days=days_back)

        # Format title correctly
        title = f"Episode #{ep_num} - {ep['title']}"

        # Add episode to feed
        rss_gen.add_episode(
            rss=rss,
            episode_number=ep_num,
            title=title,
            description=ep["summary"],
            audio_url=audio_url,
            audio_file_size=FILE_SIZES.get(ep_num, 80000000),
            duration_seconds=DURATIONS.get(ep_num, 2400),
            pub_date=pub_date,
            episode_type="full",
            explicit=True,
            keywords=["podcast", "comedy", "fake-problems"],
        )

        print(f"[OK] Added Episode #{ep_num} - {ep['title']}")

    # Also add episodes 25 and 26 with correct titles
    print()
    print("[INFO] Re-adding Episodes 25 and 26 with correct titles...")

    # Episode 25
    if 25 in DROPBOX_FILES:
        ep25_url = dropbox.get_shared_link(DROPBOX_FILES[25])
        if ep25_url:
            rss_gen.add_episode(
                rss=rss,
                episode_number=25,
                title="Episode #25 - POV: You Don't Know What POV Means",
                description="In this episode, the hosts dive into the quirky world of godfather titles, the absurdity of extreme diets, and the misuse of POV on social media. They also tackle the complexities of healthcare regulations and the pitfalls of political rhetoric.",
                audio_url=ep25_url,
                audio_file_size=FILE_SIZES.get(25, 88014723),
                duration_seconds=DURATIONS.get(25, 3666),
                pub_date=datetime(2025, 12, 4),
                episode_type="full",
                explicit=True,
                keywords=["podcast", "comedy", "fake-problems"],
            )
            print("[OK] Added Episode #25")

    # Episode 26
    if 26 in DROPBOX_FILES:
        ep26_url = dropbox.get_shared_link(DROPBOX_FILES[26])
        if ep26_url:
            rss_gen.add_episode(
                rss=rss,
                episode_number=26,
                title="Episode #26 - God's Butt Plug and Other Scientific Discoveries",
                description="In this episode, the hosts discuss climate change skepticism, the potential eruption of Yellowstone, and the humorous concept of God's anatomy. They also share a funny encounter with bike cops and delve into critical race theory and its implications.",
                audio_url=ep26_url,
                audio_file_size=FILE_SIZES.get(26, 79556065),
                duration_seconds=DURATIONS.get(26, 3448),
                pub_date=datetime(2026, 1, 26),
                episode_type="full",
                explicit=True,
                keywords=["podcast", "comedy", "fake-problems"],
            )
            print("[OK] Added Episode #26")

    # Save the feed
    print()
    print("[INFO] Saving RSS feed...")
    rss_gen.save_feed(rss)

    # Validate
    validation = rss_gen.validate_feed()
    print(f"[INFO] Validation: {validation}")

    print()
    print("=" * 60)
    print("RSS FEED POPULATION COMPLETE!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Review the feed at: output/podcast_feed.xml")
    print(
        "2. Upload to Dropbox: python -c \"from dropbox_handler import DropboxHandler; d=DropboxHandler(); d.upload_file('output/podcast_feed.xml', '/podcast/podcast_feed.xml', overwrite=True)\""
    )
    print("3. Wait for Spotify to refresh (2-8 hours)")
    print()
    print("NOTE: Episode 7 is missing from Dropbox - upload it to restore that episode")


if __name__ == "__main__":
    main()
