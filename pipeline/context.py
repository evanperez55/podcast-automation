"""PipelineContext dataclass — single state object passed between all step functions."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class PipelineContext:
    """Holds all state for a single episode processing run."""

    # Required fields (no default)
    episode_folder: str
    episode_number: Optional[int]
    episode_output_dir: Path
    timestamp: str

    # Audio
    audio_file: Optional[Path] = None
    transcript_path: Optional[Path] = None
    transcript_data: Optional[dict] = None
    analysis: Optional[dict] = None
    censored_audio: Optional[Path] = None
    mp3_path: Optional[Path] = None

    # Source video (when input is a video file, not audio-only)
    source_video_path: Optional[Path] = None
    video_metadata: Optional[dict] = None
    has_video_source: bool = False

    # Clips and video
    clip_paths: list = field(default_factory=list)
    video_clip_paths: list = field(default_factory=list)
    full_episode_video_path: Optional[str] = None
    srt_paths: list = field(default_factory=list)
    thumbnail_path: Optional[str] = None

    # Distribution
    finished_path: Optional[str] = None
    uploaded_clip_paths: list = field(default_factory=list)

    # Compliance
    compliance_result: Optional[dict] = (
        None  # From ContentComplianceChecker.check_transcript()
    )
    force: bool = False  # --force bypasses compliance upload block

    # Run mode flags
    test_mode: bool = False
    dry_run: bool = False
    auto_approve: bool = False
    resume: bool = False
