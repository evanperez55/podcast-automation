"""Speaker diarization using WhisperX + pyannote.

Transcribes audio with word-level alignment, runs speaker diarization,
and outputs JSON with speaker labels on each segment.

Usage:
    python diarize.py <audio_file> [--speakers N] [--model SIZE] [--output PATH]

Examples:
    python diarize.py downloads/ep_27_raw.WAV --speakers 3
    python diarize.py downloads/ep_27_raw.WAV --speakers 3 --model large-v2
"""

import argparse
import gc
import json
import sys
from pathlib import Path

import torch
import whisperx
from whisperx.diarize import DiarizationPipeline

from config import Config


def get_device():
    """Get the best available compute device."""
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def diarize(
    audio_path, num_speakers=None, model_size="large-v2", output_path=None, batch_size=4
):
    """Run full diarization pipeline: transcribe, align, diarize.

    Args:
        audio_path: Path to audio file.
        num_speakers: Expected number of speakers (helps accuracy). None for auto-detect.
        model_size: Whisper model size (tiny, base, small, medium, large-v2).
        output_path: Path for output JSON. Defaults to <audio_stem>_diarized.json.
        batch_size: Transcription batch size (lower = less memory, default 4).

    Returns:
        Path to output JSON file.
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        print(f"[ERROR] Audio file not found: {audio_path}")
        sys.exit(1)

    hf_token = Config.HF_TOKEN
    if not hf_token:
        print("[ERROR] HF_TOKEN not set in .env")
        print("  1. Create a token at https://huggingface.co/settings/tokens")
        print("  2. Accept model terms at:")
        print("     https://huggingface.co/pyannote/speaker-diarization-3.1")
        print("     https://huggingface.co/pyannote/segmentation-3.0")
        print("  3. Add HF_TOKEN=hf_... to your .env file")
        sys.exit(1)

    device = get_device()
    compute_type = "float16" if device == "cuda" else "int8"
    print(f"[INFO] Device: {device}, Compute type: {compute_type}")
    print(f"[INFO] Audio: {audio_path}")
    print(f"[INFO] Expected speakers: {num_speakers or 'auto-detect'}")
    print()

    # --- Step 1: Transcribe ---
    print("[1/4] Loading Whisper model and transcribing...")
    model = whisperx.load_model(model_size, device, compute_type=compute_type)
    audio = whisperx.load_audio(str(audio_path))
    result = model.transcribe(audio, batch_size=batch_size)
    print(f"  Found {len(result['segments'])} segments, language: {result['language']}")

    # Free GPU memory before next step
    del model
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()

    # --- Step 2: Align ---
    print("[2/4] Aligning words to audio...")
    align_model, metadata = whisperx.load_align_model(
        language_code=result["language"], device=device
    )
    result = whisperx.align(
        result["segments"],
        align_model,
        metadata,
        audio,
        device,
        return_char_alignments=False,
    )
    print(f"  Aligned {sum(len(s.get('words', [])) for s in result['segments'])} words")

    del align_model
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()

    # --- Step 3: Diarize ---
    print("[3/4] Running speaker diarization...")
    diarize_model = DiarizationPipeline(token=hf_token, device=device)

    diarize_kwargs = {}
    if num_speakers is not None:
        diarize_kwargs["min_speakers"] = num_speakers
        diarize_kwargs["max_speakers"] = num_speakers

    diarize_segments = diarize_model(audio, **diarize_kwargs)

    del diarize_model
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()

    # --- Step 4: Assign speakers ---
    print("[4/4] Assigning speakers to segments...")
    result = whisperx.assign_word_speakers(diarize_segments, result)

    # Build speaker summary
    speakers = {}
    for seg in result["segments"]:
        spk = seg.get("speaker", "UNKNOWN")
        duration = seg.get("end", 0) - seg.get("start", 0)
        if spk not in speakers:
            speakers[spk] = {"speaking_time": 0.0, "segment_count": 0}
        speakers[spk]["speaking_time"] += duration
        speakers[spk]["segment_count"] += 1

    # Round speaking times
    for spk in speakers:
        speakers[spk]["speaking_time"] = round(speakers[spk]["speaking_time"], 1)

    # Sort speakers by speaking time (most first)
    speakers = dict(
        sorted(speakers.items(), key=lambda x: x[1]["speaking_time"], reverse=True)
    )

    # Build output
    output = {
        "audio_file": str(audio_path),
        "language": result.get("language", "en"),
        "num_speakers": len(speakers),
        "speakers": speakers,
        "segments": result["segments"],
    }

    # Write JSON
    if output_path is None:
        output_path = audio_path.parent / f"{audio_path.stem}_diarized.json"
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print()
    print(f"[OK] Diarized transcript saved to: {output_path}")
    print()
    print("Speaker summary:")
    for spk, info in speakers.items():
        mins = info["speaking_time"] / 60
        print(f"  {spk}: {mins:.1f} min ({info['segment_count']} segments)")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Speaker diarization using WhisperX + pyannote"
    )
    parser.add_argument("audio", help="Path to audio file (WAV, MP3, etc.)")
    parser.add_argument(
        "--speakers",
        type=int,
        default=None,
        help="Expected number of speakers (improves accuracy)",
    )
    parser.add_argument(
        "--model", default="large-v2", help="Whisper model size (default: large-v2)"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON path (default: <audio_stem>_diarized.json)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=4,
        help="Transcription batch size - lower uses less memory (default: 4)",
    )

    args = parser.parse_args()
    diarize(
        args.audio,
        num_speakers=args.speakers,
        model_size=args.model,
        output_path=args.output,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
