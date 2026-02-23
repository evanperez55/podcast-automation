"""Extract audio clips for a specific speaker from a diarized transcript.

Two modes:
  --identify: Print sample text from each speaker so you can identify who is who.
  --speaker SPEAKER_XX --audio <file>: Extract that speaker's turns as WAV clips.

Usage:
    python extract_speaker_clips.py transcript_diarized.json --identify
    python extract_speaker_clips.py transcript_diarized.json --speaker SPEAKER_02 --audio downloads/ep_27_raw.WAV

Options:
    --min-duration N   Minimum turn duration in seconds (default: 10)
    --output-dir DIR   Output directory for clips (default: clips/<audio_stem>_<speaker>/)
    --merge-gap N      Max gap in seconds to merge consecutive segments (default: 2.0)
"""

import argparse
import json
import sys
from pathlib import Path

from audio_processor import AudioProcessor
from config import Config


def load_transcript(transcript_path):
    """Load a diarized transcript JSON file."""
    transcript_path = Path(transcript_path)
    if not transcript_path.exists():
        print(f"[ERROR] Transcript not found: {transcript_path}")
        sys.exit(1)

    with open(transcript_path, "r", encoding="utf-8") as f:
        return json.load(f)


def identify_speakers(data):
    """Print sample text from each speaker for identification."""
    speakers = data.get("speakers", {})
    segments = data.get("segments", [])

    print(f"Audio: {data.get('audio_file', 'unknown')}")
    print(f"Found {len(speakers)} speakers:\n")

    for spk, info in speakers.items():
        mins = info["speaking_time"] / 60
        print(f"{'='*60}")
        print(f"{spk}  |  {mins:.1f} min  |  {info['segment_count']} segments")
        print(f"{'='*60}")

        # Collect segments for this speaker
        spk_segments = [s for s in segments if s.get("speaker") == spk]

        # Show first 5 segments as samples
        samples = spk_segments[:5]
        for seg in samples:
            start = seg.get("start", 0)
            end = seg.get("end", 0)
            text = seg.get("text", "").strip()
            print(f"  [{_fmt_time(start)} -> {_fmt_time(end)}] {text}")

        if len(spk_segments) > 5:
            print(f"  ... and {len(spk_segments) - 5} more segments")
        print()

    print("Use --speaker SPEAKER_XX to extract clips for a specific speaker.")


def extract_clips(data, speaker_id, audio_path, output_dir, min_duration=10.0, merge_gap=2.0):
    """Extract audio clips for the target speaker.

    Merges consecutive segments from the same speaker into "turns",
    then exports turns longer than min_duration as WAV clips.
    """
    segments = data.get("segments", [])
    audio_path = Path(audio_path)

    if not audio_path.exists():
        print(f"[ERROR] Audio file not found: {audio_path}")
        sys.exit(1)

    # Check speaker exists
    speakers = data.get("speakers", {})
    if speaker_id not in speakers:
        print(f"[ERROR] Speaker '{speaker_id}' not found. Available: {', '.join(speakers.keys())}")
        sys.exit(1)

    # Filter segments for target speaker
    spk_segments = [s for s in segments if s.get("speaker") == speaker_id]
    print(f"[INFO] {speaker_id} has {len(spk_segments)} segments")

    # Merge consecutive segments into turns
    turns = _merge_segments(spk_segments, merge_gap)
    print(f"[INFO] Merged into {len(turns)} turns (gap threshold: {merge_gap}s)")

    # Filter by minimum duration
    long_turns = [t for t in turns if t["duration"] >= min_duration]
    print(f"[INFO] {len(long_turns)} turns >= {min_duration}s")

    if not long_turns:
        print("[WARN] No turns meet the minimum duration. Try --min-duration with a lower value.")
        return []

    # Setup output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract clips
    processor = AudioProcessor()
    clip_paths = []

    print(f"\nExtracting {len(long_turns)} clips to: {output_dir}\n")

    for i, turn in enumerate(long_turns, 1):
        filename = f"turn_{i:03d}_{turn['start']:.0f}s.wav"
        output_path = output_dir / filename

        clip_path = processor.extract_clip(
            audio_path, turn["start"], turn["end"], output_path
        )
        clip_paths.append(clip_path)

        # Preview text (truncate to 80 chars)
        preview = turn["text"][:80] + ("..." if len(turn["text"]) > 80 else "")
        print(f"  [{i}/{len(long_turns)}] {_fmt_time(turn['start'])} -> {_fmt_time(turn['end'])} "
              f"({turn['duration']:.1f}s)")
        print(f"           {preview}")

    print(f"\n[OK] Extracted {len(clip_paths)} clips to: {output_dir}")

    # Print summary
    print(f"\nSummary:")
    total_duration = sum(t["duration"] for t in long_turns)
    print(f"  Total clip duration: {total_duration / 60:.1f} min")
    print(f"  Longest turn: {max(t['duration'] for t in long_turns):.1f}s")
    print(f"  Shortest turn: {min(t['duration'] for t in long_turns):.1f}s")

    return clip_paths


def _merge_segments(segments, max_gap):
    """Merge consecutive segments into turns based on time gap.

    Args:
        segments: List of segment dicts with start, end, text.
        max_gap: Maximum gap between segments to merge (seconds).

    Returns:
        List of turn dicts with start, end, duration, text, segment_count.
    """
    if not segments:
        return []

    # Sort by start time
    sorted_segs = sorted(segments, key=lambda s: s.get("start", 0))

    turns = []
    current = {
        "start": sorted_segs[0].get("start", 0),
        "end": sorted_segs[0].get("end", 0),
        "text": sorted_segs[0].get("text", "").strip(),
        "segment_count": 1,
    }

    for seg in sorted_segs[1:]:
        seg_start = seg.get("start", 0)
        seg_end = seg.get("end", 0)
        seg_text = seg.get("text", "").strip()

        gap = seg_start - current["end"]

        if gap <= max_gap:
            # Merge into current turn
            current["end"] = seg_end
            current["text"] += " " + seg_text
            current["segment_count"] += 1
        else:
            # Finalize current turn, start new one
            current["duration"] = current["end"] - current["start"]
            turns.append(current)
            current = {
                "start": seg_start,
                "end": seg_end,
                "text": seg_text,
                "segment_count": 1,
            }

    # Don't forget the last turn
    current["duration"] = current["end"] - current["start"]
    turns.append(current)

    return turns


def _fmt_time(seconds):
    """Format seconds as MM:SS."""
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def main():
    parser = argparse.ArgumentParser(
        description="Extract audio clips for a specific speaker from a diarized transcript"
    )
    parser.add_argument("transcript", help="Path to diarized transcript JSON")
    parser.add_argument(
        "--identify", action="store_true",
        help="Print sample text from each speaker for identification"
    )
    parser.add_argument(
        "--speaker", default=None,
        help="Speaker ID to extract (e.g., SPEAKER_02)"
    )
    parser.add_argument(
        "--audio", default=None,
        help="Path to audio file (required with --speaker)"
    )
    parser.add_argument(
        "--min-duration", type=float, default=10.0,
        help="Minimum turn duration in seconds (default: 10)"
    )
    parser.add_argument(
        "--merge-gap", type=float, default=2.0,
        help="Max gap in seconds to merge consecutive segments (default: 2.0)"
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="Output directory for clips"
    )

    args = parser.parse_args()
    data = load_transcript(args.transcript)

    if args.identify:
        identify_speakers(data)
    elif args.speaker:
        if not args.audio:
            print("[ERROR] --audio is required with --speaker")
            sys.exit(1)

        # Default output dir: clips/<audio_stem>_<speaker>/
        if args.output_dir is None:
            audio_stem = Path(args.audio).stem
            speaker_lower = args.speaker.lower()
            output_dir = Config.CLIPS_DIR / f"{audio_stem}_{speaker_lower}"
        else:
            output_dir = args.output_dir

        extract_clips(
            data,
            args.speaker,
            args.audio,
            output_dir,
            min_duration=args.min_duration,
            merge_gap=args.merge_gap,
        )
    else:
        print("[ERROR] Must specify --identify or --speaker")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
