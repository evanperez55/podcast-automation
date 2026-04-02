"""Autoresearch composite metric: coverage% * 0.7 + (passing/total) * 30."""

import re
import subprocess


def main():
    result = subprocess.run(
        ["uv", "run", "pytest", "--cov", "--tb=no", "-q"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    output = result.stdout + result.stderr

    # Parse pass/fail from pytest summary line like "768 passed, 1 failed"
    passed = failed = errors = 0
    summary_match = re.search(
        r"(\d+) passed(?:.*?(\d+) failed)?(?:.*?(\d+) error)?", output
    )
    if summary_match:
        passed = int(summary_match.group(1))
        failed = int(summary_match.group(2) or 0)
        errors = int(summary_match.group(3) or 0)

    total = passed + failed + errors
    pass_rate = (passed / total * 100) if total > 0 else 0

    # Parse coverage from TOTAL line like "TOTAL    14647   2831    81%"
    coverage = 0.0
    cov_match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", output)
    if cov_match:
        coverage = float(cov_match.group(1))

    # Composite: coverage * 0.7 + pass_rate * 0.3
    score = coverage * 0.7 + pass_rate * 0.3
    print(f"passed={passed} failed={failed} errors={errors} coverage={coverage}%")
    print(f"SCORE: {score:.2f}")


if __name__ == "__main__":
    main()
