Run the test suite and report results.

1. Run `rtk uv run pytest --tb=short -q`
2. If any tests fail, show the failure details
3. If all pass, report the count
4. Optionally run `rtk uv run pytest --cov --cov-report=term-missing` if "$ARGUMENTS" includes "coverage"
