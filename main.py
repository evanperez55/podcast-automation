"""CLI entry point for podcast automation — thin shim that delegates to pipeline/."""

import re
import sys

from pipeline import (
    run_with_notification,
    run_upload_scheduled,
    run_analytics,
    run_search,
    dry_run,
    list_episodes_by_number,
    list_available_episodes,
)


def main():
    """Main entry point."""
    # Check for flags
    test_mode = "--test" in sys.argv or "--test-mode" in sys.argv
    resume = "--resume" in sys.argv
    _dry_run = "--dry-run" in sys.argv
    auto_approve = "--auto-approve" in sys.argv
    force = "--force" in sys.argv

    # Strip flags from argv before parsing positional args
    flag_args = [
        "--test",
        "--test-mode",
        "--resume",
        "--dry-run",
        "--auto-approve",
        "--force",
    ]
    sys.argv = [arg for arg in sys.argv if arg not in flag_args]

    args = {
        "test_mode": test_mode,
        "resume": resume,
        "dry_run": _dry_run,
        "auto_approve": auto_approve,
        "force": force,
    }

    # Handle commands that don't need full component init
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()

        if cmd == "upload-scheduled":
            run_upload_scheduled()
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
    if _dry_run:
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
        # Interactive mode
        print("Podcast Automation - Interactive Mode")
        print()
        print("Options:")
        print("  1. Process latest episode from Dropbox")
        print("  2. Process episode by episode number (e.g., Episode 25)")
        print("  3. List all episodes sorted by number")
        print("  4. List all episodes by date")
        print("  5. Process specific Dropbox episode by path")
        print("  6. Process local audio file")
        print()

        choice = input("Enter choice (1-6): ").strip()

        if choice == "1":
            run_with_notification(args)
        elif choice == "2":
            list_episodes_by_number()
            episode_num = input("\nEnter episode number: ").strip()
            try:
                run_with_notification(args, episode_number=int(episode_num))
            except ValueError:
                print("Invalid episode number")
        elif choice == "3":
            list_episodes_by_number()
        elif choice == "4":
            list_available_episodes()
        elif choice == "5":
            list_available_episodes()
            path = input("\nEnter Dropbox path: ").strip()
            run_with_notification(args, dropbox_path=path)
        elif choice == "6":
            path = input("Enter local audio file path: ").strip()
            run_with_notification(args, local_audio_path=path)
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
