"""Search and episode listing commands extracted from pipeline/runner.py."""

from search_index import EpisodeSearchIndex


def run_search(query):
    """Search across all indexed episodes."""
    print(f'Searching for: "{query}"')
    print("-" * 60)

    index = EpisodeSearchIndex()
    results = index.search(query, limit=10)

    if not results:
        print("No results found")
        return

    for r in results:
        print(f"\nEpisode {r['episode_number']}: {r['title']}")
        print(f"  {r['snippet']}")

    print(f"\n{len(results)} result(s) found")


def list_available_episodes(components=None):
    """List all available episodes in Dropbox."""
    from dropbox_handler import DropboxHandler

    print("Available episodes in Dropbox:")
    print("-" * 60)

    if components is None:
        dropbox = DropboxHandler()
    else:
        dropbox = components.get("dropbox") or DropboxHandler()

    episodes = dropbox.list_episodes()

    if not episodes:
        print("No episodes found")
        return []

    for i, ep in enumerate(episodes, 1):
        size_mb = ep["size"] / 1024 / 1024
        modified = ep["modified"].strftime("%Y-%m-%d %H:%M")
        print(f"{i}. {ep['name']}")
        print(f"   Size: {size_mb:.1f} MB | Modified: {modified}")
        print(f"   Path: {ep['path']}")
        print()

    return episodes


def list_episodes_by_number(components=None):
    """List all episodes sorted by episode number."""
    from dropbox_handler import DropboxHandler

    print("Available episodes (sorted by episode number):")
    print("-" * 60)

    if components is None:
        dropbox = DropboxHandler()
    else:
        dropbox = components.get("dropbox") or DropboxHandler()

    episodes_with_numbers = dropbox.list_episodes_with_numbers()

    if not episodes_with_numbers:
        print("No episodes found")
        return []

    for ep_num, ep in episodes_with_numbers:
        size_mb = ep["size"] / 1024 / 1024
        modified = ep["modified"].strftime("%Y-%m-%d %H:%M")

        if ep_num:
            print(f"Episode {ep_num}: {ep['name']}")
        else:
            print(f"[No Episode #]: {ep['name']}")

        print(f"   Size: {size_mb:.1f} MB | Modified: {modified}")
        print()

    return episodes_with_numbers
