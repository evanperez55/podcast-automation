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
    health_check,
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
    elif cmd == "test-upload":
        from test_upload import run_test_upload

        run_test_upload(
            keep=args.get("keep", "--keep" in sys.argv),
            yes=args.get("yes", "--yes" in sys.argv),
        )
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
    elif cmd == "package-demo":
        from demo_packager import DemoPackager

        n = name or (sys.argv[2] if len(sys.argv) > 2 else None)
        ep = sys.argv[3] if len(sys.argv) > 3 else None
        if not n or not ep:
            print("Usage: uv run main.py package-demo <client> <ep_id>")
            return True
        _activate_client(n)
        demo_path = DemoPackager().package_demo(n, ep)
        print(f"\nDemo packaged: {demo_path}")
    elif cmd == "find-prospects":
        from prospect_finder import run_find_prospects_cli

        run_find_prospects_cli(sys.argv)
    elif cmd == "gen-pitch":
        from pitch_generator import run_gen_pitch_cli

        run_gen_pitch_cli(sys.argv)
    elif cmd == "demo-workflow":
        from demo_packager import run_demo_workflow_cli

        run_demo_workflow_cli(sys.argv, args)
    elif cmd == "outreach":
        from outreach_tracker import OutreachTracker

        subcmd = sys.argv[2] if len(sys.argv) > 2 else None
        tracker = OutreachTracker()
        if subcmd == "add" and len(sys.argv) > 3:
            slug = sys.argv[3]
            show_name = sys.argv[4] if len(sys.argv) > 4 else slug
            email = sys.argv[5] if len(sys.argv) > 5 else None
            data = {"show_name": show_name}
            if email:
                data["contact_email"] = email
            result = tracker.add_prospect(slug, data)
            if result:
                print(f"Added prospect: {slug}")
            else:
                print(f"Prospect already exists: {slug}")
        elif subcmd == "list":
            prospects = tracker.list_prospects()
            if not prospects:
                print("No prospects found.")
            else:
                fmt = "{:<20} {:<30} {:<15} {:<12}"
                print(fmt.format("Slug", "Show Name", "Status", "Last Contact"))
                print("-" * 80)
                for p in prospects:
                    print(
                        fmt.format(
                            p["slug"][:20],
                            p["show_name"][:30],
                            p["status"],
                            (p.get("last_contact_date") or "-")[:12],
                        )
                    )
        elif subcmd == "update" and len(sys.argv) > 4:
            slug = sys.argv[3]
            new_status = sys.argv[4]
            try:
                result = tracker.update_status(slug, new_status)
                if result:
                    print(f"Updated {slug} -> {new_status}")
                else:
                    print(f"Prospect not found: {slug}")
            except ValueError as e:
                print(f"Error: {e}")
        elif subcmd == "status" and len(sys.argv) > 3:
            p = tracker.get_prospect(sys.argv[3])
            if p:
                for key, val in p.items():
                    print(f"  {key}: {val}")
            else:
                print(f"Prospect not found: {sys.argv[3]}")
        else:
            print("Usage: uv run main.py outreach <add|list|update|status> ...")
    else:
        return False
    return True


def main():
    """Main entry point."""
    args = _parse_flags()
    client_name = args["client_name"]
    _activate_client(client_name)

    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()

        if _handle_client_command(cmd, args):
            return

        if cmd == "health-check":
            health_check()
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
        if cmd == "best-of":
            from compilation_generator import CompilationGenerator

            gen = CompilationGenerator()
            max_clips = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            result = gen.generate_best_of(max_clips=max_clips)
            if result:
                print(f"Best-of compilation created: {result}")
            else:
                print("Failed to create compilation")
            return
        if cmd == "daily-content":
            from daily_content_generator import DailyContentGenerator

            gen = DailyContentGenerator()
            topic = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else None
            result = gen.generate_fake_problem(topic_hint=topic)
            if result:
                print("\n--- Fake Problem of the Day ---")
                for platform, text in result.items():
                    print(f"\n{platform.upper()}:\n  {text}")
            else:
                print("Failed to generate content")
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
