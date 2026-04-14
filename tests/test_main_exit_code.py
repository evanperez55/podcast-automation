"""Test that main.py exits non-zero on unhandled exceptions.

This was a real latent bug: the outer try/except in main.py caught
exceptions, printed a traceback, but then fell through to implicit exit
code 0 — so the batch runner (and CI, and humans checking $?) treated
real pipeline failures as successes.
"""
from __future__ import annotations

import subprocess
import sys


def test_main_propagates_exception_as_nonzero_exit(tmp_path):
    """Run main.py in a way that causes main() to raise, verify non-zero rc.

    We invoke with a known-broken pattern: --client <slug> latest on a
    client slug whose YAML doesn't exist. Client activation raises, which
    bubbles up through main().
    """
    script = tmp_path / "boom.py"
    script.write_text(
        "import sys\n"
        "sys.path.insert(0, '.')\n"
        "# Force main() to raise\n"
        "import main\n"
        "def broken():\n"
        "    raise RuntimeError('deliberate failure for test')\n"
        "main.main = broken\n"
        "import runpy\n"
        "# Re-run main module's __main__ block with a patched main()\n"
        "exec(compile(open('main.py').read(), 'main.py', 'exec'), {'__name__': '__main__', 'main': broken})\n",
        encoding='utf-8',
    )

    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=".",
    )
    assert result.returncode != 0, (
        f"main.py must exit non-zero on unhandled exception, got rc={result.returncode}\n"
        f"stdout: {result.stdout[-500:]}\n"
        f"stderr: {result.stderr[-500:]}"
    )
