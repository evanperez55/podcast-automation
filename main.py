"""CLI entry point for podcast automation — thin shim that delegates to pipeline/."""

import re
import sys

from pipeline import (
    run_with_notification,
    run_upload_scheduled,
    run_analytics,
    run_backfill_ids,
    run_search,
    dry_run,
    list_episodes_by_number,
    list_available_episodes,
)


def _parse_flags():
    """Parse and strip flags from sys.argv, return args dict."""
    raw = sys.argv[:]
    flags = {
        "--test",
        "--test-mode",
        "--resume",
        "--dry-run",
        "--auto-approve",
        "--force",
    }  # noqa: E501
    client_name = None
    cleaned = []
    skip_next = False
    for i, arg in enumerate(raw):
        if skip_next:
            skip_next = False
            continue
        if arg == "--client" and i + 1 < len(raw):
            client_name = raw[i + 1]
            skip_next = True
        elif arg not in flags:
            cleaned.append(arg)
    sys.argv = cleaned
    return {
        "test_mode": "--test" in raw or "--test-mode" in raw,
        "resume": "--resume" in raw,
        "dry_run": "--dry-run" in raw,
        "auto_approve": "--auto-approve" in raw,
        "force": "--force" in raw,
        "client_name": client_name,
    }


def main():
    """Main entry point."""
    args = _parse_flags()

    # Handle commands that don't need full component init
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()

        if cmd == "upload-scheduled":
            run_upload_scheduled()
            return

        if cmd == "backfill-ids":
            run_backfill_ids()
            return

        if cmd == "analytics":
            episode_arg = sys.argv[2] if len(sys.argv) > 2 else "all"
            run_analytics(episode_arg)
            return

        if cmd == "search" and len(sys.argv) > 2:
            query = " ".join(sys.argv[2:])
            run_search(query)
            return

    # Dry run mode: validate pipeline and exit
    if args["dry_run"]:
        dry_run()
        return

    # Check command line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()

        if arg == "list":
            list_episodes_by_number()
        elif arg == "latest":
            run_with_notification(args)
        elif arg.startswith("ep") or arg.startswith("episode"):
            # Support formats: ep25, episode25, ep 25, episode 25
            match = re.search(r"(\d+)", arg)
            if match:
                episode_num = int(match.group(1))
            elif len(sys.argv) > 2:
                episode_num = int(sys.argv[2])
            else:
                print("Usage: python main.py ep25 or python main.py episode 25")
                return
            run_with_notification(args, episode_number=episode_num)
        else:
            # Process specific file (local or dropbox path)
            file_path = sys.argv[1]
            if file_path.startswith("/"):
                run_with_notification(args, dropbox_path=file_path)
            else:
                run_with_notification(args, local_audio_path=file_path)
    else:
        _interactive_mode(args)


def _interactive_mode(args):
    """Prompt user for action when no command is given."""
    print("Podcast Automation - Interactive Mode\n")
    print("  1. Process latest episode from Dropbox")
    print("  2. Process episode by number")
    print("  3. List episodes by number")
    print("  4. List episodes by date")
    print("  5. Process Dropbox episode by path")
    print("  6. Process local audio file\n")
    choice = input("Enter choice (1-6): ").strip()
    if choice == "1":
        run_with_notification(args)
    elif choice == "2":
        list_episodes_by_number()
        ep = input("\nEnter episode number: ").strip()
        try:
            run_with_notification(args, episode_number=int(ep))
        except ValueError:
            print("Invalid episode number")
    elif choice == "3":
        list_episodes_by_number()
    elif choice == "4":
        list_available_episodes()
    elif choice == "5":
        list_available_episodes()
        run_with_notification(
            args, dropbox_path=input("\nEnter Dropbox path: ").strip()
        )
    elif choice == "6":
        run_with_notification(args, local_audio_path=input("Enter path: ").strip())
    else:
        print("Invalid choice")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[WARNING] Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] {e}")
        import traceback

        traceback.print_exc()
