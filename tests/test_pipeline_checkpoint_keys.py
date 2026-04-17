"""Checkpoint key regression tests for the pipeline architecture refactor.

Ensures that checkpoint keys used in pipeline/steps/*.py match the known-good
set from the original main.py implementation.

RED now: step modules are stubs with no complete_step() calls.
Goes GREEN in Plan 02 when real step code is extracted from main.py.
"""

import re
from pathlib import Path


KNOWN_CHECKPOINT_KEYS = {
    "transcribe",
    "analyze",
    "censor",
    "denoise",
    "normalize",
    "create_clips",
    "subtitles",
    "convert_videos",
    "convert_mp3",
    "blog_post",
    "website",
}


class TestCheckpointKeyNames:
    """Checkpoint key regression: keys must match KNOWN_CHECKPOINT_KEYS."""

    def test_checkpoint_key_names_unchanged(self):
        """Scan pipeline/steps/*.py for complete_step("...") calls.

        The collected key names must equal KNOWN_CHECKPOINT_KEYS exactly.
        This test is EXPECTED TO FAIL until Plan 02 extracts step code from main.py.
        """
        steps_dir = Path("pipeline/steps")
        pattern = re.compile(r'complete_step\(\s*["\'](\w+)["\']')

        found_keys: set[str] = set()
        for py_file in steps_dir.glob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            found_keys.update(pattern.findall(text))

        assert found_keys == KNOWN_CHECKPOINT_KEYS, (
            f"Checkpoint key mismatch.\n"
            f"  Expected: {sorted(KNOWN_CHECKPOINT_KEYS)}\n"
            f"  Found:    {sorted(found_keys)}\n"
            f"  Missing:  {sorted(KNOWN_CHECKPOINT_KEYS - found_keys)}\n"
            f"  Extra:    {sorted(found_keys - KNOWN_CHECKPOINT_KEYS)}\n"
            f"\nRun Plan 02 to extract step code from main.py."
        )
