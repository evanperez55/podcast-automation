Process podcast episode $ARGUMENTS through the full pipeline.

1. Validate the episode identifier (should be "latest" or "epNN")
2. Run `uv run main.py $ARGUMENTS --dry-run` first to check for issues
3. If dry-run passes, confirm with user before running the real pipeline
4. Run `uv run main.py $ARGUMENTS`
5. Report results and any warnings
