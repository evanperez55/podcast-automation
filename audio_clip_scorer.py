"""Audio energy scoring for podcast clip selection using pydub RMS windowing."""

import statistics

from pydub import AudioSegment


class AudioClipScorer:
    """Score transcript segments by audio energy using pydub RMS windowing.

    Adds an 'audio_energy_score' (0.0–1.0) to each segment dict, where 1.0
    is the highest-energy moment in the episode. Used to bias GPT-4o clip
    selection toward genuinely animated moments.
    """

    def __init__(self, window_ms=500, hop_ms=250):
        self.window_ms = window_ms
        self.hop_ms = hop_ms

    def score_segments(self, audio_path: str, segments: list[dict]) -> list[dict]:
        """Score each transcript segment by average RMS energy.

        Args:
            audio_path: Path to the audio file (WAV, MP3, etc.)
            segments: List of segment dicts with 'start' and 'end' keys (seconds).

        Returns:
            List of segment dicts with 'audio_energy_score' (float 0.0–1.0) added.
            If audio cannot be loaded, returns the input segments unchanged.
        """
        if not segments:
            return segments

        try:
            audio = AudioSegment.from_file(audio_path)
        except Exception:
            return segments  # graceful degradation

        total_ms = len(audio)
        energy_map = {}
        pos = 0
        while pos + self.window_ms <= total_ms:
            chunk = audio[pos : pos + self.window_ms]
            energy_map[pos] = chunk.rms
            pos += self.hop_ms

        if not energy_map:
            return segments

        max_rms = max(energy_map.values()) or 1
        min_rms = min(energy_map.values())
        rms_range = max_rms - min_rms or 1

        scored = []
        for seg in segments:
            start_ms = int(seg["start"] * 1000)
            end_ms = int(seg["end"] * 1000)
            window_energies = [
                v for k, v in energy_map.items() if start_ms <= k < end_ms
            ]
            if window_energies:
                mean_energy = statistics.mean(window_energies)
                score = (mean_energy - min_rms) / rms_range
            else:
                score = 0.0
            scored.append({**seg, "audio_energy_score": round(score, 3)})

        return scored
