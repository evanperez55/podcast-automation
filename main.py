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
        "--ping",
    }
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
        "ping": "--ping" in raw,
        "client_name": client_name,
    }


def _activate_client(client_name):
    """Apply client config if specified."""
    if client_name:
        from client_config import activate_client

        activate_client(client_name)


def _handle_client_command(cmd, args):
    """Handle client management commands. Returns True if handled."""
    name = args["client_name"]
    if cmd == "init-client" and len(sys.argv) > 2:
        from client_config import init_client

        init_client(sys.argv[2])
    elif cmd == "setup-client" and len(sys.argv) > 3:
        from client_config import setup_client_platform

        setup_client_platform(sys.argv[2], sys.argv[3])
    elif cmd == "list-clients":
        from client_config import list_clients

        list_clients()
    elif cmd == "validate-client":
        from client_config import validate_client

        n = name or (sys.argv[2] if len(sys.argv) > 2 else None)
        if not n:
            print("Usage: uv run main.py validate-client <name>")
            return True
        validate_client(n, ping=args.get("ping", False))
    elif cmd == "status":
        from client_config import client_status

        n = name or (sys.argv[2] if len(sys.argv) > 2 else None)
        if not n:
            print("Usage: uv run main.py status <name>")
            return True
        client_status(n)
    elif cmd == "process-all":
        from client_config import process_all

        process_all(args)
    else:
        return False
    return True


def main():
    """Main entry point."""
    args = _parse_flags()
    client_name = args["client_name"]

    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()

        if _handle_client_command(cmd, args):
            return

        if cmd == "upload-scheduled":
            _activate_client(client_name)
            run_upload_scheduled()
            return
        if cmd == "backfill-ids":
            run_backfill_ids()
            return
        if cmd == "analytics":
            _activate_client(client_name)
            run_analytics(sys.argv[2] if len(sys.argv) > 2 else "all")
            return
        if cmd == "search" and len(sys.argv) > 2:
            _activate_client(client_name)
            run_search(" ".join(sys.argv[2:]))
            return

    if args["dry_run"]:
        _activate_client(client_name)
        dry_run()
        return

    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == "list":
            list_episodes_by_number()
        elif arg == "latest":
            run_with_notification(args)
        elif arg.startswith("ep") or arg.startswith("episode"):
            match = re.search(r"(\d+)", arg)
            if match:
                ep = int(match.group(1))
            elif len(sys.argv) > 2:
                ep = int(sys.argv[2])
            else:
                print("Usage: python main.py ep25 or python main.py episode 25")
                return
            run_with_notification(args, episode_number=ep)
        else:
            path = sys.argv[1]
            if path.startswith("/"):
                run_with_notification(args, dropbox_path=path)
            else:
                run_with_notification(args, local_audio_path=path)
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
